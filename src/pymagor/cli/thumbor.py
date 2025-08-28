"""Thumbor CLI implementation."""

from typing import Any

import click
from pymagor import Thumbor

from .base import BaseCLI


class ThumborCLI(BaseCLI):
    """CLI for Thumbor image processing."""

    @classmethod
    def get_processor_class(cls) -> type[Thumbor]:
        """Get the Thumbor processor class."""
        return Thumbor

    @classmethod
    def get_operations(cls) -> list[click.option]:
        """Get Thumbor-specific operation options."""
        return [
            click.option(
                "--brightness",
                type=click.IntRange(-100, 100),
                help="Adjust brightness (-100 to 100)",
            ),
            click.option(
                "--contrast",
                type=click.IntRange(-100, 100),
                help="Adjust contrast (-100 to 100)",
            ),
            click.option(
                "--rgb",
                nargs=3,
                type=int,
                metavar=("R", "G", "B"),
                help="RGB channel adjustment (0-255 each)",
            ),
        ]

    def _apply_processor_options(
        self,
        processor: Thumbor,
        brightness: float | None = None,
        contrast: float | None = None,
        rgb: tuple[float, float, float] | None = None,
        **kwargs: Any,
    ) -> Thumbor:
        """Apply Thumbor-specific options to the processor."""
        if brightness is not None and contrast is not None:
            processor = processor.brightness_contrast(brightness, contrast)
        elif brightness is not None:
            processor = processor.brightness(brightness)
        elif contrast is not None:
            processor = processor.contrast(contrast)

        if rgb:
            r, g, b = rgb
            processor = processor.rgb(r, g, b)

        return processor


@click.command()
@click.argument("image_url")
@click.option(
    "--base",
    default="http://localhost:8000",
    help="Base URL of the image processing service",
)
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default="-",
    help="Output file (default: stdout)",
)
@click.option(
    "--fit-in", is_flag=True, help="Fit the image within the given dimensions"
)
@click.option("--width", "-w", type=int, help="Width in pixels")
@click.option("--height", "-h", type=int, help="Height in pixels")
@click.option(
    "--crop",
    nargs=4,
    type=int,
    metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
    help="Crop the image (left, top, right, bottom)",
)
@click.option("--blur", type=float, help="Apply gaussian blur with the given radius")
@click.option(
    "--quality", "-q", type=click.IntRange(1, 100), help="Output quality (1-100)"
)
@click.option("--grayscale", is_flag=True, help="Convert to grayscale")
@click.option(
    "--brightness",
    type=click.IntRange(-100, 100),
    help="Adjust brightness (-100 to 100)",
)
@click.option(
    "--contrast", type=click.IntRange(-100, 100), help="Adjust contrast (-100 to 100)"
)
@click.option(
    "--rgb",
    nargs=3,
    type=int,
    metavar=("R", "G", "B"),
    help="RGB channel adjustment (0-255 each)",
)
@click.pass_context
def thumbor(
    ctx: click.Context,
    image_url: str,
    base: str,
    output: click.File,
    fit_in: bool,
    width: int | None,
    height: int | None,
    crop: tuple[int, int, int, int] | None,
    blur: float | None,
    quality: int | None,
    grayscale: bool,
    brightness: float | None,
    contrast: float | None,
    rgb: tuple[float, float, float] | None,
) -> None:
    """Process an image using Thumbor.

    Examples:

    \b
    $ pymagor thumbor path/to/image.jpg --width 800 --height 600 --fit-in
    $ pymagor thumbor https://example.com/image.jpg --crop 10 10 200 200 --blur 5 --quality 80
    $ pymagor thumbor image.jpg --brightness 20 --contrast 10
    """
    cli = ThumborCLI(base_url=base)

    try:
        url = cli.process_image(
            image_url,
            fit_in=fit_in,
            width=width,
            height=height,
            crop=crop,
            blur=blur,
            quality=quality,
            grayscale=grayscale,
            brightness=brightness,
            contrast=contrast,
            rgb=rgb,
        )
        output.write(f"{url}\n")
    except Exception as e:
        raise click.ClickException(str(e)) from e
