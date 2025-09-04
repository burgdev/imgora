#!/usr/bin/env python3
"""
Advanced Image Backend Comparison Tool

This script compares image processing results across multiple backends (Imagor, Thumbor, WsrvNl).
It uses a declarative approach to define transformations and supports nested transformations.
"""

import json
import os
import traceback
import webbrowser
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from jinja2 import Environment, FileSystemLoader

# Import backends
from pymagor import BaseImage, Imagor, Signer, Thumbor, WsrvNl

# Configure Jinja2 environment
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)


class Operation:
    def __init__(
        self,
        name: str,
        *args: tuple[any],
        title: str | None = None,
        description: str = "",
        **kwargs: dict[str, any],
    ):
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.title = title or name.replace("_", " ").title()
        self.description = description

    def __str__(self) -> str:
        args_str = ", ".join(repr(arg) for arg in self.args)
        kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))
        return f".{self.name}({all_args})"

    def __repr__(self) -> str:
        return f"<Operation {self}>"


@dataclass
class TransformResult:
    """Result of a transformation operation."""

    success: bool
    method_calls: List[str]
    meta: Dict[str, Any]
    url: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return asdict(self)


@dataclass
class Transformation:
    name: Optional[str] = field(default=None, repr=False)  # temporary input
    description: str = ""
    operations: List[Operation] = field(default_factory=list)

    # Internal field to hold the actual name
    _name: Optional[str] = field(init=False, default=None, repr=False)

    def __post_init__(self):
        # Move the user-provided name into the hidden field
        self._name = self.name
        self.name = None  # avoid confusion — we'll always go through the property

    @property
    def name(self) -> str:  # type: ignore  # noqa: F811
        """Return explicit name if set, otherwise generate from operations."""
        if self._name:
            return self._name
        titles = [op.title for op in self.operations]
        return self._human_join(titles) if titles else ""

    @name.setter
    def name(self, value: Optional[str]) -> None:
        self._name = value

    @staticmethod
    def _human_join(values: List[str]) -> str:
        """Join values as 'A, B and C' instead of 'A, B, C'."""
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        return ", ".join(values[:-1]) + " and " + values[-1]


class ImageComparator:
    """Compare image processing results across different backends."""

    def __init__(self, source_url: str, output_file: str = "comparison.html"):
        """Initialize the comparator with a source image URL and output file path."""
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["tojson"] = json.dumps

        def slugify(value):
            """Convert a string to a slug."""
            return "".join(c if c.isalnum() else "_" for c in str(value))

        self.env.filters["slugify"] = slugify

        self.source_url = source_url
        self.output_file = output_file
        self.backends: list[BaseImage] = []
        self.transformations: list[Transformation] = []

        # Ensure output directory exists
        output_dir = os.path.dirname(os.path.abspath(self.output_file))
        if output_dir:  # Only create if there's a directory path (not just a filename)
            os.makedirs(output_dir, exist_ok=True)

    def add_backend(
        self, name: str, backend_class: BaseImage, **kwargs
    ) -> "ImageComparator":
        """
        Add a backend to compare.

        Args:
            name: Display name for the backend
            backend_class: The backend class (e.g., Imagor, Thumbor, WsrvNl)
            **kwargs: Arguments to pass to the backend constructor

        Returns:
            self for method chaining
        """
        self.backends.append({"name": name, "class": backend_class, "kwargs": kwargs})
        return self

    def add_transformation(
        self,
        operations: List[Operation],
        name: str | None = None,
        description: str = "",
    ) -> "ImageComparator":
        """
        Add a transformation to apply to all backends.

        Args:
            operations: List of Operation objects representing the transformation steps
            name: Optional name for the transformation
            description: Optional description of what the transformation does

        Returns:
            self for method chaining
        """
        name = name or ", ".join(step.title for step in operations)
        self.transformations.append(
            Transformation(name=name, description=description, operations=operations)
        )
        return self

    def _run_transform(
        self, backend: Any, transform_steps: List[Operation]
    ) -> TransformResult:
        """
        Apply a series of transformation steps to a backend.

        Args:
            backend: The backend instance to transform
            transform_steps: List of Operation objects representing the transformations

        Returns:
            TransformResult: The result of the transformation
        """
        try:
            # Create a fresh copy of the backend for this transformation
            current = backend._clone()
            method_calls: List[str] = []

            # Apply each step in the transformation
            for step in transform_steps:
                method = getattr(current, step.name)
                current = method(*step.args, **(step.kwargs or {}))
                method_calls.append(str(step))

            # Get the final URL from the transformed backend
            url = current.url()

            # Try to get metadata if available
            meta: Dict[str, Any] = {}
            if hasattr(current, "meta"):
                try:
                    meta_result = requests.get(
                        current.meta().url(),
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "pymagor (https://github.com/burgdev/pymagor)",
                        },
                    )
                    meta = meta_result.json()
                except Exception as e:
                    meta = {"error": f"Failed to get metadata: {str(e)}"}

            # Ensure we have a valid URL
            if not url:
                return TransformResult(
                    success=False,
                    method_calls=method_calls,
                    meta=meta,
                    error="Failed to generate URL after transformations",
                )

            return TransformResult(
                success=True,
                url=url,
                method_calls=method_calls,
                meta=meta,
                error=None,
                path=current.path(),
            )

        except Exception as e:
            return TransformResult(
                success=False,
                method_calls=method_calls if "method_calls" in locals() else [],
                meta={},
                error=str(e),
                traceback=traceback.format_exc(),
            )

    def run(self, open_in_browser: bool = True) -> str:
        """
        Run all transformations on all backends and generate the comparison report.

        Args:
            open_in_browser: Whether to open the report in the default web browser

        Returns:
            Path to the generated HTML file
        """
        results = {}

        def step_to_dict(step):
            """Convert a step (Operation) to a string representation."""
            # Directly format the method call as a string
            if hasattr(step, "method_name"):
                args_str = ", ".join([repr(arg) for arg in step.args])
                kwargs_str = ", ".join(
                    [f"{k}={repr(v)}" for k, v in step.kwargs.items()]
                )
                all_args = ", ".join(filter(None, [args_str, kwargs_str]))
                return f".{step.method_name}({all_args})"
            return str(step)

        # Prepare results structure
        results = {}
        for transform in self.transformations:
            # Convert each step to its string representation
            step_strings = []
            for step in transform.operations:
                # Directly format the method call
                if hasattr(step, "method_name"):
                    args_str = ", ".join([repr(arg) for arg in step.args])
                    kwargs_str = ", ".join(
                        [f"{k}={repr(v)}" for k, v in step.kwargs.items()]
                    )
                    all_args = ", ".join(filter(None, [args_str, kwargs_str]))
                    step_str = f".{step.method_name}({all_args})"
                    step_strings.append(step_str)
                else:
                    step_strings.append(str(step))

            # Join all steps into a single string
            all_steps = "".join(step_strings)

            results[transform.name] = {
                "name": transform.name,
                "description": transform.description,
                "steps": all_steps,  # Single string with all steps
                "results": {},
            }

        # Process each backend
        for backend_info in self.backends:
            backend_name = backend_info["name"]
            backend_class = backend_info["class"]
            backend_kwargs = backend_info["kwargs"]

            # Initialize the backend
            try:
                # Create backend with the source URL and configuration
                backend = backend_class(image=self.source_url, **backend_kwargs)

                # Run each transformation
                for transform in self.transformations:
                    transform_name = transform.name
                    result = self._run_transform(backend, transform.operations)
                    results[transform_name]["results"][backend_name] = result

            except Exception as e:
                print(f"Error initializing backend {backend_name}: {str(e)}")
                # Add error to all transformations for this backend
                for transform in self.transformations:
                    results[transform.name]["results"][backend_name] = {
                        "success": False,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }

        # Convert results to list for template
        transformations_list = list(results.values())

        # Get source image dimensions if available
        source_size = None
        try:
            # Try to get image dimensions using Pillow
            from io import BytesIO

            import requests
            from PIL import Image

            response = requests.get(self.source_url)
            img = Image.open(BytesIO(response.content))
            source_size = img.size  # Returns (width, height)
        except Exception:
            # If we can't get dimensions, just use None
            pass

        # Render the template
        template = self.env.get_template("comparison_new.html")
        output = template.render(
            source_url=self.source_url,
            source_size=source_size,
            transformations=transformations_list,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Ensure output directory exists
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)

        # Open in browser if requested
        if open_in_browser:
            try:
                webbrowser.open(f"file://{output_path.absolute()}")
            except Exception as e:
                print(f"Could not open browser: {e}")

        print(f"Report generated at: {output_path.absolute()}")
        return str(output_path.absolute())


def create_sample_comparison():
    """Create a sample comparison with common transformations."""
    # Example image URL (can be replaced with any public image URL)
    source_url = "https://wsrv.nl/lichtenstein.jpg"

    # Create comparator
    comparator = ImageComparator(
        source_url=source_url, output_file="comparison_results/comparison.html"
    )

    # Add backends with their specific configurations
    # Imagor
    comparator.add_backend(
        "Imagor",
        Imagor,
        base_url="http://localhost:8018",
        signer=Signer(key="my_key", type="sha256"),
    )

    # Thumbor (using the signer instead of key)
    comparator.add_backend(
        "Thumbor",
        Thumbor,
        base_url="http://localhost:8019",
        signer=Signer(key="my_key", type="sha1"),
    )

    # WsrvNl
    comparator.add_backend("WsrvNl", WsrvNl, base_url="https://wsrv.nl")

    resize_step = Operation("resize", 1000, 600)
    # Add transformations
    # 1. Simple resize
    comparator.add_transformation(
        operations=[resize_step],
        description=f"Basic image resizing to {resize_step.args[0]}x{resize_step.args[1]} pixels",
    )

    # 2. Grayscale
    comparator.add_transformation(
        operations=[resize_step, Operation("grayscale")],
        name="Graysacle",
        description="Convert image to grayscale",
    )

    # 3. Multiple transformations
    comparator.add_transformation(
        operations=[
            resize_step,
            Operation("blur", radius=5),
            Operation("quality", 85),
            Operation("round_corner", 40),
        ],
        description="Resize, convert to grayscale, and set quality",
    )

    # Run the comparison
    output_path = comparator.run()
    print(f"Comparison generated at: {output_path}")
    return output_path


if __name__ == "__main__":
    create_sample_comparison()
