"""Imgora - Chainable image URL generator for Imagor and Thumbor.

This package provides a Pythonic, chainable interface for generating image URLs
for Imagor and Thumbor image processing servers. It supports all standard
filters and operations with full type hints and documentation.

Example:
    ```python
    from imgora import Imagor
    url = (Imagor(key="secret")
            .fit_in(300, 300)
            .blur(5)
            .radius(10)
            .with_base("https://example.com")
            .with_image("image.jpg")
            .url())
    ```
"""

from imgora._core import (
    HALIGN,  # noqa: F401
    VALIGN,  # noqa: F401
    BaseImage,  # noqa: F401
    Filter,  # noqa: F401
    ImageFormats,  # noqa: F401
    Operation,  # noqa: F401
    Signer,  # noqa: F401
)
from imgora._imagor import Imagor  # noqa: F401
from imgora._thumbor import Thumbor  # noqa: F401
from imgora._wsrv_nl import WsrvNl  # noqa: F401

__version__ = "0.0.1"
__all__ = [
    "Imagor",
    "Thumbor",
    "WsrvNl",
    "Signer",
    "BaseImage",
    "Filter",
    "Operation",
    "HALIGN",
    "VALIGN",
    "ImageFormats",
]
