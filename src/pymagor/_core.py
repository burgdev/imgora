"""Core functionality for Pymagor.

This module contains the base classes for the Pymagor library, providing
common functionality for both Imagor and Thumbor clients.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Literal
from urllib.parse import quote

from pymagor.decorator import chained_method, filter, operation


@dataclass
class Operation:
    """Represents an image processing operation.

    Attributes:
        name: The name of the operation.
        arg: Arguments for the operation, if empty the name is used
    """

    name: str
    arg: str | None = None


@dataclass
class Filter:
    """Represents an image processing filter.

    Attributes:
        name: The name of the filter.
        args: Arguments for the filter, if empty the name is used
    """

    name: str
    args: tuple[str, ...] = field(default_factory=tuple)


class Signer:
    def __init__(
        self,
        type: Literal["sha1", "sha256", "sha512"] = "sha1",
        truncate: int | None = None,
        key: str | None = None,
        unsafe: bool | None = None,
    ):
        self._type = type
        self._truncate = truncate
        self._key = key
        self._unsafe = unsafe

    @property
    def type(self) -> Literal["sha1", "sha256", "sha512"]:
        return self._type

    @property
    def truncate(self) -> int | None:
        return self._truncate

    @property
    def key(self) -> str | None:
        if self.unsafe:
            return None
        return self._key

    @property
    def unsafe(self) -> bool | None:
        return self._unsafe


# /HASH|unsafe/trim/AxB:CxD/fit-in/stretch/-Ex-F/GxH:IxJ/HALIGN/VALIGN/smart/filters:NAME(ARGS):NAME(ARGS):.../IMAGE
#
THUMBOR_OP_ORDER = (
    "unsafe",
    "trim",
    "crop",
    "fit-in",
    "full-fit-in",  # only for thumbor
    "adaptive-fit-in",  # only for thumbor
    "stretch",  # only for imagor
    "resize",
    "halign",
    "valign",
    "smart",
    "filters",
)


class BaseImage(ABC):
    """Base class for image URL generation.

    This class provides the core functionality for building image URLs with
    chained operations and filters. It should not be instantiated directly;
    use one of the subclasses (Imagor or Thumbor) instead.
    """

    def __init__(
        self,
        base_url: str = "",
        image: str = "",
        signer: Signer | None = None,
    ) -> None:
        """Initialize a new image processor.

        Args:
            base_url: Base URL of the Imagor/Thumbor server.
            image: Path or URL of the source image.
            signer_type: Hash algorithm for URL signing (sha1, sha256, sha512).
            signer_truncate: Number of characters to truncate the signature to.
        """
        self._base_url = base_url.rstrip("/")
        self._image = image.lstrip("/")
        self._operations: List[Operation] = []
        self._filters: List[Filter] = []
        self._signer = signer
        self._op_order = None

    @property
    def signer(self) -> Signer | None:
        return self._signer

    @property
    def op_order(self) -> tuple[str, ...]:
        return self._op_order or THUMBOR_OP_ORDER

    @op_order.setter
    def op_order(self, value: tuple[str, ...]) -> None:
        self._op_order = value

    def add_operation(self, op: str | Operation, arg: str | None = None) -> None:
        """Add an operation to the image processing pipeline.

        Args:
            op: The name of the operation or an Operation object.
            arg: Optional argument for the operation.
        """
        if not isinstance(op, Operation):
            op = Operation(op, arg)
        if op.name in (a.name for a in self._operations):
            self._operations.remove(op)
        self._operations.append(op)

    def add_filter(self, filter: str | Filter, *args: Any) -> None:
        """Add a filter to the image processing pipeline.

        Args:
            filter: The name of the filter or a Filter object.
            *args: Arguments for the filter.
        """
        if not isinstance(filter, Filter):
            filter = Filter(
                filter,
                args
                if isinstance(args, (tuple, list))
                else (args)
                if args is not None
                else (),
            )
        if filter.name in (f.name for f in self._filters):
            self._filters.remove(filter)
        self._filters.append(filter)

    def remove(self, name: str) -> None:
        """Remove an operation or filter from the image processing pipeline by name.

        For example:

        >>> image.remove("crop")
        >>> image.remove("upscale")

        Args:
            name: The name of the operation or filter to remove.
        """
        self._operations = [op for op in self._operations if op.name != name]
        self._filters = [f for f in self._filters if f.name != name]

    def remove_filters(self) -> None:
        """Remove all filters from the image processing pipeline."""
        self._filters = []

    def _get_operations(self) -> list[Operation]:
        """Get the list of operations.

        Returns:
            A list of Operation objects.
        """
        return self._operations.copy()

    def _add_filters_to_operation(self) -> bool:
        """Add filters to the operations list.

        Returns:
            True if filters were added, False otherwise.
        """

        filters = [
            f"{f.name}({','.join(str(a) for a in f.args if a is not None) if isinstance(f.args, Iterable) else str(f.args)})"
            for f in self._filters
        ]

        if filters:
            self.add_operation("filters", "filters:" + ":".join(filters))
        return bool(filters)

    def _clone(self) -> "BaseImage":
        """Create a copy of the current instance.

        Returns:
            A new instance with the same configuration and operations.
        """
        new = self.__class__(
            base_url=self._base_url,
            image=self._image,
            signer=self._signer,
        )
        new._operations = self._operations.copy()
        new._filters = self._filters.copy()
        return new

    @chained_method
    def with_image(self, image: str) -> None:
        """Set the source image.

        Args:
            image: Path or URL of the source image.
        """
        self._image = image.lstrip("/")

    @chained_method
    def sign(self, unsafe: bool = False, signer: Signer | None = None) -> None:
        """Set the signer.

        Args:
            unsafe: If True, skip URL signing even if a key is configured.
            signer: The signer to use. If None the default is used.
        """
        if signer:
            self._signer = signer
        if unsafe:
            self._signer = None

    @chained_method
    def unsafe(self) -> None:
        """Set the signer to unsafe."""
        self._signer = None

    @chained_method
    def with_base(self, base_url: str) -> None:
        """Set the base URL of the Imagor/Thumbor server.

        Args:
            base_url: Base URL of the server.
        """
        self._base_url = base_url.rstrip("/")

    def sign_path(self, path: str, signer: Signer | None = None) -> str:
        """Sign a URL path using HMAC.

        Args:
            path: The URL path to sign.
            signer: The signer to use. If None the default is used.

        Returns:
            The signature.

        Raises:
            ValueError: If no key is configured for signing.
        """
        signer = signer or self._signer
        if signer.unsafe:
            return "unsafe"
        if not signer:
            raise ValueError("Signing object is required for URL signing")
        if not signer.key:
            raise ValueError("Signing key is required for URL signing")

        hash_fn = getattr(hashlib, signer.type)
        if not hash_fn:
            raise ValueError(f"Unsupported signer type: {signer.type}")

        hasher = hmac.new(
            signer.key.encode("utf-8"), path.encode("utf-8"), digestmod=hash_fn
        )
        signature = hasher.digest()
        signature_base64 = base64.urlsafe_b64encode(signature).decode("utf-8")
        return (
            signature_base64[: signer.truncate] if signer.truncate else signature_base64
        )

    def _get_ordered_operations(self) -> list[str]:
        """Get operations in the correct order.

        Returns:
            List of operation strings in the correct order.
        """
        ops_dict = {op.name: op.arg or op.name for op in self._get_operations()}
        return [ops_dict[op_name] for op_name in self.op_order if op_name in ops_dict]

    def path(
        self,
        unsafe: bool = False,
        with_image: str | None = None,
        encode_image: bool = True,
        signer: Signer | None = None,
    ) -> str:
        """Generate the URL path with all operations and filters applied.

        Args:
            unsafe: If True, skip URL signing even if a key is configured.
            with_image: The image to use. If None, the default image is used.
            encode_image: Whether to encode the image path.
            signer: The signer to use. If None the default is used.

        Returns:
            The generated URL path.
        """
        self._add_filters_to_operation()
        with_image = (with_image or "" if self._image is None else self._image).strip(
            "/"
        )
        if encode_image:
            with_image = self.encode_image_path(with_image)
        parts = self._get_ordered_operations() + [with_image]
        path = "/".join(parts).strip("/")
        signer = signer or self._signer
        if unsafe or not signer:
            signature = "unsafe"
        else:
            signature = self.sign_path(path=path, signer=signer)
        return f"{signature}/{path}"

    def encode_image_path(self, path: str) -> str:
        return quote(path, safe="")

    def url(
        self,
        with_image: str | None = None,
        unsafe: bool = False,
        with_base: str | None = None,
        signer: Signer | None = None,
    ) -> str:
        """Generate the full URL.

        Args:
            with_image: The image to use. If None, the default image is used.
            unsafe: If True, skip URL signing even if a key is configured.
            with_base: The base URL to use. If None, the default base URL is used.
            signer: The signer to use. If None the default is used.

        Returns:
            The complete URL with all operations and filters applied.
        """
        path = self.path(with_image=with_image, unsafe=unsafe, signer=signer)
        base_url = with_base or self._base_url
        return f"{base_url}/{path}" if base_url else path

    # Common operations

    @operation
    def trim(self) -> None:
        """Trim the image."""
        self.add_operation("trim")

    @operation
    def crop(
        self,
        left: int | float,
        top: int | float,
        right: int | float,
        bottom: int | float,
        halign: Literal["left", "center", "right"] | None = None,
        valign: Literal["top", "middle", "bottom"] | None = None,
    ) -> None:
        """Crop the image. Coordinates are in pixel or float values between 0 and 1 (percentage of image dimensions)

        Args:
            left: Left coordinate of the crop (pixel or relative).
            top: Top coordinate of the crop (pixel or relative).
            right: Right coordinate of the crop (pixel or relative).
            bottom: Bottom coordinate of the crop (pixel or relative).
            halign: Horizontal alignment of the crop (left, center, right).
            valign: Vertical alignment of the crop (top, middle, bottom).
        """
        self.add_operation("crop", f"{left}x{top}:{right}x{bottom}")
        if halign:
            self.add_operation("halign", halign)
        if valign:
            self.add_operation("valign", valign)

    @operation
    def fit_in(self, width: int, height: int) -> None:
        """Fit the image within the specified dimensions while preserving aspect ratio.

        Args:
            width: Maximum width in pixels.
            height: Maximum height in pixels.
        """
        assert "stretch" not in (
            a.name for a in self._get_operations()
        ), "Use either 'fit-in' or 'stretch'"
        self.add_operation("fit-in")
        self.add_operation("resize", f"{width}x{height}")

    @operation
    def resize(
        self, width: int, height: int, method: Literal["fit-in", "stretch"] = "fit-in"
    ) -> None:
        """Resize the image to the exact dimensions.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
        """
        assert method not in (
            a.name for a in self._get_operations()
        ), "Use either 'fit-in' or 'stretch'"
        self.add_operation(method)
        self.add_operation("resize", f"{width}x{height}")

    # ===== Common Filters =====
    @filter
    def background_color(self, color: str) -> None:
        """The `background_color` filter sets the background layer to the specified color.
        This is specifically useful when converting transparent images (PNG) to JPEG.

        Args:
            color: Background color in hex format without # or 'auto' (e.g., 'FFFFFF', 'aab').
        """
        self.add_filter("background_color", color.removeprefix("#").lower())

    @filter
    def blur(self, radius: int, sigma: int | None = None) -> None:
        """Apply gaussian blur to the image.

        Args:
            radius: Radius of the blur effect (0-150). The bigger the radius, the more blur.
            sigma: Standard deviation of the gaussian kernel, defaults to `radius`.
        """
        assert 0 <= radius <= 150, "Radius must be between 0 and 150"
        if sigma is None:
            self.add_filter("blur", radius)
        else:
            assert 0 <= sigma <= 150, "Sigma must be between 0 and 150"
            self.add_filter("blur", f"{radius},{sigma}")

    @filter
    def brightness(self, amount: int) -> None:
        """Adjust brightness of the image.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image brightness.
                    Positive numbers make the image brighter and negative numbers make the image darker.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("brightness", amount)

    @filter
    def contrast(self, amount: int) -> None:
        """Adjust contrast of the image.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image contrast.
                     Positive numbers increase contrast and negative numbers decrease contrast.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("brightness_contrast", amount)

    @filter
    def rgb(
        self,
        r: float = 0,
        g: float = 0,
        b: float = 0,
    ) -> None:
        """Adjust the RGB channels of the image.

        Args:
            r: `-100` to `100`. Red channel adjustment.
            g: `-100` to `100`. Green channel adjustment.
            b: `-100` to `100`. Blue channel adjustment.
        """
        self.add_filter("rgb", r, g, b)

    @filter
    def focal(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> None:
        """Set the focal point of the image, which is used in later transforms (e.g. `crop`).

        Args:
            left: Left coordinate of the focal region.
            top: Top coordinate of the focal region.
            right: Right coordinate of the focal region.
            bottom: Bottom coordinate of the focal region.
        """
        self.add_filter("focal", f"{left}x{top}:{right}x{bottom}")

    @filter
    def quality(self, amount: int) -> None:
        """Set the image quality (JPEG only).

        Args:
            amount: Quality percentage (1-100).
        """
        self.add_filter("quality", amount)

    def radius(self, rx: int, ry: int | None = None, color: str | None = None) -> None:
        """Add rounded corners to the image (alias for round_corner).

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (defaults to rx).
            color: Corner color in CSS format (default: "none").
        """
        return self.round_corner(rx, ry, color)

    @filter
    def round_corner(
        self, rx: int, ry: int | None = None, color: str | None = None
    ) -> None:
        """Add rounded corners to the image.

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (defaults to rx).
            color: Corner color in CSS format (default: "none").
        """
        ry = ry or rx
        self.add_filter("round_corner", rx, ry, color)


class BaseImagorThumbor(BaseImage):
    """Base class with operations and filters common to both Imagor and Thumbor."""

    # ===== Common Operations =====
    @operation
    def halign(self, halign: Literal["left", "center", "right"]) -> None:
        """Set the horizontal alignment of the image.

        Args:
            halign: Horizontal alignment of the image (left, center, right).
        """
        self.add_operation("halign", halign)

    @operation
    def valign(self, valign: Literal["top", "middle", "bottom"]) -> None:
        """Set the vertical alignment of the image.

        Args:
            valign: Vertical alignment of the image (top, middle, bottom).
        """
        self.add_operation("valign", valign)

    @operation
    def fit_in(self, width: int, height: int) -> None:
        """Fit the image within the specified dimensions while preserving aspect ratio.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
        """
        self.add_operation("fit-in", f"{width}x{height}")

    @operation
    def smart_crop(self) -> None:
        """Enable smart cropping to detect the region of interest."""
        self.add_operation("smart")

    # ===== Common Filters =====
    @filter
    def grayscale(self) -> None:
        """Convert the image to grayscale."""
        self.add_filter("grayscale")

    @filter
    def quality(self, amount: int) -> None:
        """Set the quality of the output image.

        Args:
            amount: Quality level from 0 to 100.
        """
        self.add_filter("quality", str(amount))

    @filter
    def format(self, fmt: str) -> None:
        """Set the output format of the image.

        Args:
            fmt: Output format (e.g., 'jpeg', 'png', 'webp', 'gif').
        """
        self.add_operation("format", fmt.lower())

    @filter
    def strip_exif(self) -> None:
        """Remove EXIF metadata from the image."""
        self.add_filter("strip_exif")

    @filter
    def strip_icc(self) -> None:
        """Remove ICC profile from the image."""
        self.add_filter("strip_icc")

    @filter
    def no_upscale(self) -> None:
        """Prevent upscaling the image beyond its original dimensions."""
        self.add_operation("no_upscale")

    @filter
    def max_bytes(self, amount: int) -> None:
        """Set the maximum file size in bytes for the output image.

        Args:
            amount: Maximum file size in bytes.
        """
        self.add_filter("max_bytes", amount)

    @filter
    def proportion(self, percentage: float) -> None:
        """Scale the image to the specified percentage of its original size.

        Args:
            percentage: Scale percentage (0-100).
        """
        assert 0 <= percentage <= 100, "Percentage must be between 0 and 100"
        self.add_filter("proportion", round(percentage / 100, 1))

    @filter
    def rotate(self, angle: int) -> None:
        """Rotate the given image by the specified angle after processing.

        This is different from the 'orient' filter which rotates the image before processing.

        Args:
            angle: `0`, `90`, `180`, `270`. Rotation angle.
        """
        if angle % 90 != 0:
            raise ValueError("Rotation angle must be a multiple of 90 degrees")
        self.add_filter("rotate", angle)

    @filter
    def brightness(self, amount: float) -> None:
        """Adjust the image brightness.

        Args:
            amount: Adjustment amount (-100 to 100).
        """
        self.add_filter("brightness", str(amount))

    @filter
    def contrast(self, amount: float) -> None:
        """Adjust the image contrast.

        Args:
            amount: Adjustment amount (-100 to 100).
        """
        self.add_filter("contrast", str(amount))

    @filter
    def saturation(self, amount: float) -> None:
        """Adjust the image saturation.

        Args:
            amount: Adjustment amount (-100 to 100).
        """
        self.add_filter("saturation", str(amount))

    @filter
    def sharpen(self, sigma: float, amount: float = 1.0) -> None:
        """Sharpen the image.

        Args:
            sigma: Standard deviation of the gaussian kernel.
            amount: Strength of the sharpening effect.
        """
        self.add_filter("sharpen", f"{sigma},{amount}")


if __name__ == "__main__":
    # Example image from Wikipedia
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
    signer = Signer(key="my_key", type="sha256", truncate=None)

    # Create an Imagor processor and apply some transformations
    img = (
        BaseImagorThumbor(base_url="http://localhost:8018", signer=signer)
        .with_image(image_url)
        .crop(0.1, 0.1, 0.9, 0.9, halign="center", valign="middle")
        .trim()
        .rotate(90)
        .radius(100)
        # .round_corner(10, 30)
        .resize(800, 600)  # Resize to 800x600
        .blur(10)  # Apply blur with radius 3
        .quality(40)  # Set quality to 85%
    )

    # Get and print the processed URL
    print(img.path())
    print(img.url())
