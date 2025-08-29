#!/usr/bin/env python3
"""
Advanced Image Backend Comparison Tool

This script compares image processing results across multiple backends (Imagor, Thumbor, WsrvNl).
It uses a declarative approach to define transformations and supports nested transformations.
"""

import json
import traceback
import webbrowser
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Type, Union

import requests
from jinja2 import Environment, FileSystemLoader

# Import backends
from pymagor import Imagor, Signer, Thumbor, WsrvNl

# Configure Jinja2 environment
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)


@dataclass
class MethodCall:
    """Represents a single method call with its arguments."""

    method_name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    name: str = ""
    description: str = ""

    def to_code(self) -> str:
        """Convert the method call to a string of Python code."""
        args_str = ", ".join([repr(arg) for arg in self.args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in self.kwargs.items()])
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))
        return f".{self.method_name}({all_args})"

    def __str__(self) -> str:
        return self.to_code()

    def __repr__(self) -> str:
        return f"<MethodCall {self}>"


@dataclass
class Chain:
    """Represents a chain of method calls."""

    steps: List[Union[MethodCall, "Chain"]]
    name: str = ""
    description: str = ""

    def __str__(self) -> str:
        """Convert the chain to a string of chained method calls."""
        if not self.steps:
            return ""

        # Join all steps with newlines
        return "".join(str(step) for step in self.steps)

    def __repr__(self) -> str:
        return f"<Chain {self}>"


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
        self.backends = []
        self.transformations = []

        # Ensure output directory exists
        output_dir = os.path.dirname(os.path.abspath(self.output_file))
        if output_dir:  # Only create if there's a directory path (not just a filename)
            os.makedirs(output_dir, exist_ok=True)

    def add_backend(
        self, name: str, backend_class: Type, **kwargs
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
        steps: List[Union[MethodCall, Chain]],
        name: str = "",
        description: str = "",
    ) -> "ImageComparator":
        """
        Add a transformation to apply to all backends.

        Args:
            steps: List of MethodCall or Chain objects representing the transformation steps
            name: Optional name for the transformation
            description: Optional description of what the transformation does

        Returns:
            self for method chaining
        """
        if not name:
            name = f"Transformation {len(self.transformations) + 1}"

        self.transformations.append(
            {"name": name, "description": description, "steps": steps}
        )
        return self

    def _run_transform(self, backend, transform_steps):
        """
        Apply a list of transformation steps to a backend instance.

        Args:
            backend: The backend instance to transform
            transform_steps: List of MethodCall or Chain objects

        Returns:
            dict: Result information including URL, metadata, and any errors
        """
        try:
            # Create a clone to avoid modifying the original
            result = backend._clone()
            method_calls = []

            # Apply each transformation step
            for step in transform_steps:
                if hasattr(step, "steps"):  # It's a Chain
                    for sub_step in step.steps:
                        method = getattr(result, sub_step.method_name)
                        method(*sub_step.args, **sub_step.kwargs)
                        method_calls.append(
                            f".{sub_step.method_name}({', '.join(map(str, sub_step.args))})"
                        )
                else:  # It's a MethodCall
                    method = getattr(result, step.method_name)
                    method(*step.args, **step.kwargs)
                    method_calls.append(
                        f".{step.method_name}({', '.join(map(str, step.args))})"
                    )

            # Get the final URL
            url = result.url()

            # Try to get metadata if available
            meta = {}
            if hasattr(result, "meta"):
                try:
                    meta_result = requests.get(
                        result.meta().url(),
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "pymagor (https://github.com/burgdev/pymagor)",
                        },
                    )
                    meta = meta_result.json()
                except Exception as e:
                    meta = {"error": f"Failed to get metadata: {str(e)}"}

            return {
                "success": True,
                "url": url,
                "method_calls": method_calls,
                "meta": meta,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "url": None,
                "method_calls": method_calls if "method_calls" in locals() else [],
                "meta": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

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
            """Convert a step (MethodCall or Chain) to a string representation."""
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
            for step in transform["steps"]:
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

            results[transform["name"]] = {
                "name": transform["name"],
                "description": transform["description"],
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
                    transform_name = transform["name"]
                    result = self._run_transform(backend, transform["steps"])
                    results[transform_name]["results"][backend_name] = result

            except Exception as e:
                print(f"Error initializing backend {backend_name}: {str(e)}")
                # Add error to all transformations for this backend
                for transform in self.transformations:
                    results[transform["name"]]["results"][backend_name] = {
                        "success": False,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }

        # Convert results to list for template
        transformations_list = list(results.values())

        # Render the template
        template = self.env.get_template("comparison.html")
        output = template.render(
            source_url=self.source_url,
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


class MethodCall:
    def __init__(
        self,
        method_name: str,
        args: tuple = (),
        kwargs: dict = {},
        name: str = "",
        description: str = "",
    ):
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.description = description


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

    # Add transformations
    # 1. Simple resize
    comparator.add_transformation(
        steps=[MethodCall("resize", (400, 300), name="Resize")],
        name="Simple Resize",
        description="Basic image resizing to 400x300 pixels",
    )

    # 2. Grayscale
    comparator.add_transformation(
        steps=[MethodCall("grayscale", name="Grayscale")],
        name="Grayscale",
        description="Convert image to grayscale",
    )

    # 3. Multiple transformations
    comparator.add_transformation(
        steps=[
            MethodCall("resize", (400, 300), name="Resize"),
            MethodCall("grayscale", name="Grayscale"),
            MethodCall("quality", (85,), name="Quality"),
        ],
        name="Combined Transformations",
        description="Resize, convert to grayscale, and set quality",
    )

    # Run the comparison
    output_path = comparator.run()
    print(f"Comparison generated at: {output_path}")
    return output_path


if __name__ == "__main__":
    create_sample_comparison()
