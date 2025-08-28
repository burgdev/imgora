"""Command-line interface for pymagor."""

import click
from pymagor import __version__

from .imagor import imagor
from .thumbor import thumbor


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Pymagor - Chainable image URL generator for Imagor and Thumbor."""
    pass


# Add commands to the main group
main.add_command(imagor)
main.add_command(thumbor)

__all__ = ["main"]

if __name__ == "__main__":
    main()
