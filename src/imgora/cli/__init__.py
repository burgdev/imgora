"""Command-line interface for imgora."""

import click
from imgora import __version__

from .imagor import imagor
from .thumbor import thumbor


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Imgora - Chainable image URL generator for Imagor and Thumbor."""
    pass


# Add commands to the main group
main.add_command(imagor)
main.add_command(thumbor)

__all__ = ["main"]

if __name__ == "__main__":
    main()
