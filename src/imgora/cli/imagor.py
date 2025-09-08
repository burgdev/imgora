"""Imagor CLI implementation."""

from typing import Any

import click
from imgora import Imagor

from .base import BaseCLI


class ImagorCLI(BaseCLI):
    """CLI for Imagor image processing."""

    @classmethod
    def get_processor_class(cls) -> type[Imagor]:
        """Get the Imagor processor class."""
        return Imagor

    @classmethod
    def get_operations(cls) -> list[click.option]:
        """Get Imagor-specific operation options."""
        return [
            click.option(
                "--stretch",
                is_flag=True,
                help="Stretch the image to exact dimensions without preserving aspect ratio",
            ),
            click.option(
                "--upscale/--no-upscale",
                default=None,
                help="Enable or disable upscaling of the image",
            ),
            click.option(
                "--proportion", type=float, help="Scale the image by a percentage"
            ),
        ]

    def _apply_processor_options(
        self,
        processor: Imagor,
        stretch: bool = False,
        upscale: bool | None = None,
        proportion: float | None = None,
        **kwargs: Any,
    ) -> Imagor:
        """Apply Imagor-specific options to the processor."""
        if (
            stretch
            and processor._operations
            and processor._operations[-1].name == "resize"
        ):
            # Convert the last resize to stretch
            op = processor._operations.pop()
            width, height = op.args[0], op.args[1]
            processor = processor.stretch(width, height)

        if upscale is not None and upscale:
            processor = processor.upscale()

        if proportion is not None:
            processor = processor.proportion(proportion)

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
    "--stretch",
    is_flag=True,
    help="Stretch the image to exact dimensions without preserving aspect ratio",
)
@click.option(
    "--upscale/--no-upscale",
    default=None,
    help="Enable or disable upscaling of the image",
)
@click.option("--proportion", type=float, help="Scale the image by a percentage")
@click.pass_context
def imagor(
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
    stretch: bool,
    upscale: bool | None,
    proportion: float | None,
) -> None:
    """Process an image using Imagor.

    Examples:

    \b
    $ imgora imagor path/to/image.jpg --width 800 --height 600 --fit-in
    $ imgora imagor https://example.com/image.jpg --crop 10 10 200 200 --blur 5 --quality 80
    $ imgora imagor image.jpg --stretch --width 300 --height 200
    """
    cli = ImagorCLI(base_url=base)

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
            stretch=stretch,
            upscale=upscale,
            proportion=proportion,
        )
        output.write(f"{url}\n")
    except Exception as e:
        raise click.ClickException(str(e)) from e
