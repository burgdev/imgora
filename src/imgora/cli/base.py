"""Base CLI class for imgora commands."""

from abc import ABC, abstractmethod
from typing import Any, List, Type, TypeVar

import click
from imgora import Imagor, Thumbor

T = TypeVar("T", bound="BaseCLI")


class BaseCLI(ABC):
    """Base class for imgora CLI commands."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the CLI with a base URL.

        Args:
            base_url: Base URL of the image processing service
        """
        self.base_url = base_url

    @classmethod
    @abstractmethod
    def get_processor_class(cls) -> Type[Imagor] | Type[Thumbor]:
        """Get the processor class (Imagor or Thumbor)."""
        pass

    @classmethod
    def get_common_options(cls) -> List[click.option]:
        """Get common options for all commands."""
        return [
            click.option(
                "--base",
                default="http://localhost:8000",
                help="Base URL of the image processing service",
            ),
            click.option(
                "--output",
                "-o",
                type=click.File("w"),
                default="-",
                help="Output file (default: stdout)",
            ),
        ]

    @classmethod
    def add_common_operations(cls, command: click.Command) -> click.Command:
        """Add common operation options to a command."""
        command = click.option(
            "--fit-in", is_flag=True, help="Fit the image within the given dimensions"
        )(command)

        command = click.option("--width", "-w", type=int, help="Width in pixels")(
            command
        )

        command = click.option("--height", "-h", type=int, help="Height in pixels")(
            command
        )

        command = click.option(
            "--crop",
            nargs=4,
            type=int,
            metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
            help="Crop the image (left, top, right, bottom)",
        )(command)

        command = click.option(
            "--blur", type=float, help="Apply gaussian blur with the given radius"
        )(command)

        command = click.option(
            "--quality",
            "-q",
            type=click.IntRange(1, 100),
            help="Output quality (1-100)",
        )(command)

        command = click.option(
            "--grayscale", is_flag=True, help="Convert to grayscale"
        )(command)

        return command

    def process_image(
        self,
        image_path: str,
        fit_in: bool = False,
        width: int | None = None,
        height: int | None = None,
        crop: tuple[int, int, int, int] | None = None,
        blur: float | None = None,
        quality: int | None = None,
        grayscale: bool = False,
        **kwargs: Any,
    ) -> str:
        """Process an image with the given parameters.

        Args:
            image_path: Path or URL of the image to process
            fit_in: Whether to fit the image within the given dimensions
            width: Target width in pixels
            height: Target height in pixels
            crop: Tuple of (left, top, right, bottom) for cropping
            blur: Blur radius
            quality: Output quality (1-100)
            grayscale: Whether to convert to grayscale
            **kwargs: Additional keyword arguments for processor-specific options

        Returns:
            The processed image URL
        """
        processor = self.get_processor_class()(base_url=self.base_url)

        # Apply operations
        if fit_in and width and height:
            processor = processor.fit_in(width, height)
        elif width or height:
            processor = processor.resize(width or 0, height or 0)

        if crop:
            left, top, right, bottom = crop
            processor = processor.crop(left, top, right, bottom)

        # Apply filters
        if blur is not None:
            processor = processor.blur(blur)

        if quality is not None:
            processor = processor.quality(quality)

        if grayscale:
            processor = processor.grayscale()

        # Apply processor-specific options
        processor = self._apply_processor_options(processor, **kwargs)

        # Load and process the image
        return str(processor.with_image(image_path).url())

    def _apply_processor_options(
        self, processor: Imagor | Thumbor, **kwargs: Any
    ) -> Imagor | Thumbor:
        """Apply processor-specific options.

        Subclasses should override this method to add processor-specific options.
        """
        return processor
