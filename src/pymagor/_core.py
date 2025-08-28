"""Core functionality for Pymagor.

This module contains the base classes for the Pymagor library, providing
common functionality for both Imagor and Thumbor clients.
"""

from __future__ import annotations

import hashlib
import hmac
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Operation:
    """Represents an image processing operation.

    Attributes:
        name: The name of the operation.
        args: Positional arguments for the operation.
        kwargs: Keyword arguments for the operation.
    """

    name: str
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)


class BaseImage(ABC):
    """Base class for image URL generation.

    This class provides the core functionality for building image URLs with
    chained operations and filters. It should not be instantiated directly;
    use one of the subclasses (Imagor or Thumbor) instead.
    """

    def __init__(
        self,
        key: Optional[str] = None,
        base_url: str = "",
        image: str = "",
        signer_type: str = "sha256",
        signer_truncate: int = 40,
    ) -> None:
        """Initialize a new image processor.

        Args:
            key: Optional secret key for URL signing.
            base_url: Base URL of the Imagor/Thumbor server.
            image: Path or URL of the source image.
            signer_type: Hash algorithm for URL signing (sha1, sha256, sha512).
            signer_truncate: Number of characters to truncate the signature to.
        """
        self._key = key
        self._base_url = base_url.rstrip("/")
        self._image = image.lstrip("/")
        self._operations: List[Operation] = []
        self._filters: List[Tuple[str, ...]] = []
        self._signer_type = signer_type
        self._signer_truncate = signer_truncate

    def _clone(self) -> "BaseImage":
        """Create a copy of the current instance.

        Returns:
            A new instance with the same configuration and operations.
        """
        new = self.__class__(
            key=self._key,
            base_url=self._base_url,
            image=self._image,
            signer_type=self._signer_type,
            signer_truncate=self._signer_truncate,
        )
        new._operations = self._operations.copy()
        new._filters = self._filters.copy()
        return new

    def with_image(self, image: str) -> "BaseImage":
        """Set the source image.

        Args:
            image: Path or URL of the source image.

        Returns:
            A new instance with the updated image path.
        """
        new = self._clone()
        new._image = image.lstrip("/")
        return new

    def with_base(self, base_url: str) -> "BaseImage":
        """Set the base URL of the Imagor/Thumbor server.

        Args:
            base_url: Base URL of the server.

        Returns:
            A new instance with the updated base URL.
        """
        new = self._clone()
        new._base_url = base_url.rstrip("/")
        return new

    def _sign(self, path: str) -> str:
        """Sign a URL path using HMAC.

        Args:
            path: The URL path to sign.

        Returns:
            The signed URL path.

        Raises:
            ValueError: If no key is configured for signing.
        """
        if not self._key:
            raise ValueError("Signing key is required for URL signing")

        if self._signer_type == "sha1":
            hasher = hmac.new(self._key.encode(), digestmod=hashlib.sha1)
        elif self._signer_type == "sha256":
            hasher = hmac.new(self._key.encode(), digestmod=hashlib.sha256)
        elif self._signer_type == "sha512":
            hasher = hmac.new(self._key.encode(), digestmod=hashlib.sha512)
        else:
            raise ValueError(f"Unsupported signer type: {self._signer_type}")

        hasher.update(path.encode())
        signature = hasher.hexdigest()[: self._signer_truncate]
        return f"{signature}/{path}"

    def path(self) -> str:
        """Generate the URL path with all operations and filters applied.

        Returns:
            The generated URL path.
        """
        parts = []

        # Add operations
        for op in self._operations:
            op_str = op.name
            if op.args:
                op_str += f"({','.join(str(arg) for arg in op.args)})"
            parts.append(op_str)

        # Add filters
        if self._filters:
            filter_str = "".join(
                f"{':'.join(str(f) for f in filter_spec)}:"
                for filter_spec in self._filters
            )
            parts.append(f"filters:{filter_str}")

        # Add image path
        parts.append(self._image)

        # Join parts with slashes and clean up
        path = "/".join(parts).replace("///", "/").replace("//", "/")
        return path

    def url(self, unsafe: bool = False) -> str:
        """Generate the full URL.

        Args:
            unsafe: If True, skip URL signing even if a key is configured.

        Returns:
            The complete URL with all operations and filters applied.
        """
        path = self.path()

        # Sign the URL if we have a key and not marked as unsafe
        if not unsafe and self._key:
            path = self._sign(path)

        return f"{self._base_url}/{path}" if self._base_url else path

    # Common operations
    def fit_in(self, width: int, height: int) -> "BaseImage":
        """Fit the image within the specified dimensions while preserving aspect ratio.

        Args:
            width: Maximum width in pixels.
            height: Maximum height in pixels.

        Returns:
            A new instance with the fit_in operation applied.
        """
        new = self._clone()
        new._operations.append(Operation("fit-in", (width, height)))
        return new

    def resize(self, width: int, height: int) -> "BaseImage":
        """Resize the image to the exact dimensions.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.

        Returns:
            A new instance with the resize operation applied.
        """
        new = self._clone()
        new._operations.append(Operation("resize", (width, height)))
        return new

    # Common filters
    def blur(self, sigma: float) -> "BaseImage":
        """Apply a gaussian blur to the image.

        Args:
            sigma: Standard deviation of the gaussian kernel.

        Returns:
            A new instance with the blur filter applied.
        """
        new = self._clone()
        new._filters.append(("blur", str(sigma)))
        return new

    def quality(self, amount: int) -> "BaseImage":
        """Set the image quality (JPEG only).

        Args:
            amount: Quality percentage (1-100).

        Returns:
            A new instance with the quality filter applied.
        """
        new = self._clone()
        new._filters.append(("quality", str(amount)))
        return new

    # Alias for round_corner
    def radius(
        self, rx: int, ry: Optional[int] = None, color: str = "none"
    ) -> "BaseImage":
        """Add rounded corners to the image (alias for round_corner).

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (defaults to rx).
            color: Corner color in CSS format (default: "none").

        Returns:
            A new instance with the rounded corners filter applied.
        """
        return self.round_corner(rx, ry, color)

    def round_corner(
        self, rx: int, ry: Optional[int] = None, color: str = "none"
    ) -> "BaseImage":
        """Add rounded corners to the image.

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (defaults to rx).
            color: Corner color in CSS format (default: "none").

        Returns:
            A new instance with the rounded corners filter applied.
        """
        new = self._clone()
        ry = ry or rx
        new._filters(("round_corner", str(rx), str(ry), color))
        return new


class BaseImagorThumbor(BaseImage):
    """Base class with operations and filters common to both Imagor and Thumbor."""

    def grayscale(self) -> "BaseImagorThumbor":
        """Convert the image to grayscale.

        Returns:
            A new instance with the grayscale filter applied.
        """
        new = self._clone()
        new._filters.append(("grayscale",))
        return new

    def rotate(self, angle: int) -> "BaseImagorThumbor":
        """Rotate the image by the specified angle.

        Args:
            angle: Rotation angle in degrees (0-359).

        Returns:
            A new instance with the rotation applied.
        """
        if angle % 90 != 0:
            raise ValueError("Rotation angle must be a multiple of 90 degrees")
        new = self._clone()
        new._operations.append(Operation("rotate", (angle,)))
        return new

    def brightness(self, amount: float) -> "BaseImagorThumbor":
        """Adjust the image brightness.

        Args:
            amount: Adjustment amount (-100 to 100).

        Returns:
            A new instance with the brightness adjusted.
        """
        new = self._clone()
        new._filters.append(("brightness", str(amount)))
        return new

    def contrast(self, amount: float) -> "BaseImagorThumbor":
        """Adjust the image contrast.

        Args:
            amount: Adjustment amount (-100 to 100).

        Returns:
            A new instance with the contrast adjusted.
        """
        new = self._clone()
        new._filters.append(("contrast", str(amount)))
        return new

    def saturation(self, amount: float) -> "BaseImagorThumbor":
        """Adjust the image saturation.

        Args:
            amount: Adjustment amount (-100 to 100).

        Returns:
            A new instance with the saturation adjusted.
        """
        new = self._clone()
        new._filters.append(("saturation", str(amount)))
        return new

    def sharpen(self, sigma: float, amount: float = 1.0) -> "BaseImagorThumbor":
        """Sharpen the image.

        Args:
            sigma: Standard deviation of the gaussian kernel.
            amount: Strength of the sharpening effect.

        Returns:
            A new instance with the sharpening filter applied.
        """
        new = self._clone()
        new._filters.append(("sharpen", str(sigma), str(amount)))
        return new

    def strip_exif(self) -> "BaseImagorThumbor":
        """Remove EXIF data from the image.

        Returns:
            A new instance with EXIF data removed.
        """
        new = self._clone()
        new._filters.append(("strip_exif",))
        return new

    def strip_icc(self) -> "BaseImagorThumbor":
        """Remove ICC profile from the image.

        Returns:
            A new instance with ICC profile removed.
        """
        new = self._clone()
        new._filters.append(("strip_icc",))
        return new

    def strip_metadata(self) -> "BaseImagorThumbor":
        """Remove all metadata from the image.

        Returns:
            A new instance with all metadata removed.
        """
        new = self._clone()
        new._filters.append(("strip_metadata",))
        return new
