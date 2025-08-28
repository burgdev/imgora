"""Command-line interface for pymagor."""

from __future__ import annotations

import click

from pymagor import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Pymagor CLI - Chainable image URL generator for Imagor and Thumbor."""
    pass


@main.command()
@click.argument("image_url")
@click.option("--width", type=int, help="Resize width")
@click.option("--height", type=int, help="Resize height")
@click.option(
    "--fit-in", is_flag=True, help="Fit the image within the given dimensions"
)
@click.option("--grayscale", is_flag=True, help="Convert to grayscale")
@click.option("--blur", type=float, help="Apply blur with the given sigma")
@click.option("--output", "-o", help="Output file (default: print to stdout)")
def generate(
    image_url: str,
    width: int | None,
    height: int | None,
    fit_in: bool,
    grayscale: bool,
    blur: float | None,
    output: str | None,
) -> None:
    """Generate an image URL with the specified transformations."""
    from pymagor import Imagor

    processor = Imagor().with_image(image_url)

    if fit_in and width and height:
        processor = processor.fit_in(width, height)
    elif width or height:
        processor = processor.resize(width or 0, height or 0)

    if grayscale:
        processor = processor.grayscale()

    if blur is not None:
        processor = processor.blur(blur)

    result = processor.url()

    if output:
        with open(output, "w") as f:
            f.write(result)
    else:
        click.echo(result)


if __name__ == "__main__":
    main()
