"""Core functionality for Imgora.

This module contains the base classes for the Imgora library, providing
common functionality for both Imagor and Thumbor clients.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Literal, Self, TypeAlias
from urllib.parse import quote

import requests
from imgora.decorator import chain


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
    args: tuple[any, ...] = field(default_factory=tuple)


class Signer:
    """Signer class for URL signing."""

    def __init__(
        self,
        type: Literal["sha1", "sha256", "sha512"] = "sha1",
        truncate: int | None = None,
        key: str | None = None,
        unsafe: bool | None = None,
    ):
        """
        Args:
            type: Hash algorithm for URL signing (sha1, sha256, sha512).
            truncate: Number of characters to truncate the signature to, defaults to `None`
            key: The signing key/secret, needs to be the same as defined in the Imagor/Thumbor server.
            unsafe: Whether to disable signing, if no key is set it defaults to unsafe, but with this option you can override it.
        """
        self._type = type
        self._truncate = truncate
        self._key = key
        self._unsafe = unsafe

    @property
    def type(self) -> Literal["sha1", "sha256", "sha512"]:
        """Hash algorithm for URL signing."""
        return self._type

    @property
    def truncate(self) -> int | None:
        """Number of characters to truncate the signature to, defaults to `None`"""
        return self._truncate

    @property
    def key(self) -> str | None:
        """Secret key for URL signing, if `unsafe` is set it returns `None`."""
        if self._unsafe:
            return None
        return self._key

    @property
    def unsafe(self) -> bool | None:
        """Whether to disable signing."""
        if self._key is None:
            return True
        return self._unsafe


HALIGN: TypeAlias = Literal["left", "center", "right"]
"""Horizontal alignment values type."""

VALIGN: TypeAlias = Literal["top", "middle", "bottom"]
"""Vertical alignment values type."""


@dataclass
class CropValues:
    left: int
    top: int
    right: int
    bottom: int
    image_width: int
    image_height: int
    crop_width: int
    crop_height: int
    halign: HALIGN
    valign: VALIGN


# /HASH|unsafe/trim/AxB:CxD/fit-in/stretch/-Ex-F/GxH:IxJ/HALIGN/VALIGN/smart/filters:NAME(ARGS):NAME(ARGS):.../IMAGE
#
THUMBOR_OP_ORDER = (
    "sign",
    "meta",
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
            signer: The signer to use. If None the default is used.
        """
        self._base_url = base_url.rstrip("/")
        self._image = image.lstrip("/")
        self._operations: List[Operation] = []
        self._filters: List[Filter] = []
        self._signer = signer

        # TODO: move
        self._op_order = None

    @property
    def signer(self) -> Signer | None:
        """Returns the signer object"""
        return self._signer

    def add_operation(
        self, op: str | Operation, arg: str | None = None, unique: bool = True
    ) -> None:
        """Add an operation to the image processing pipeline.

        Args:
            op: The name of the operation or an Operation object.
            arg: Optional argument for the operation.
            unique: Whether to remove existing operations with the same name before adding the new one."""
        if not isinstance(op, Operation):
            op = Operation(op, arg)
        if unique and op.name in (a.name for a in self._operations):
            self._operations = [a for a in self._operations if a.name != op.name]
        self._operations.append(op)

    def add_filter(self, filter: str | Filter, *args: Any, unique: bool = True) -> None:
        """Add a filter to the image processing pipeline.

        Args:
            filter: The name of the filter or a Filter object.
            unique: Whether to remove existing filters with the same name before adding the new one.
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
        if unique and filter.name in (f.name for f in self._filters):
            self._filters = [f for f in self._filters if f.name != filter.name]
        self._filters.append(filter)

    def remove(
        self,
        name: str,
        include: tuple[Literal["operations", "filters"]] = ("operations", "filters"),
    ) -> None:
        """Remove an operation or filter from the image processing pipeline by name.

        For example:

        ```python
        image.remove("crop")
        image.remove("upscale")
        ```

        Args:
            name: The name of the operation or filter to remove.
        """
        if "operations" in include:
            self._operations = [op for op in self._operations if op.name != name]
        if "filters" in include:
            self._filters = [f for f in self._filters if f.name != name]

    def remove_filters(self) -> None:
        """Remove all filters from the image processing pipeline."""
        self._filters = []

    def remove_operations(self) -> None:
        """Remove all operations from the image processing pipeline."""
        self._operations = []

    @chain
    def with_image(self, image: str) -> Self:
        """Set the source image.

        Args:
            image: Path or URL of the source image.
        """
        self._image = image.lstrip("/")

    @chain
    def with_base(self, base_url: str) -> Self:
        """Set the base URL of the Imagor/Thumbor server.

        Args:
            base_url: Base URL of the server.
        """
        self._base_url = base_url.rstrip("/")

    def path(
        self,
        with_image: str | None = None,
        encode_image: bool = True,
        signer: Signer | None = None,
    ) -> str:
        """Generate the URL path with all operations and filters applied.

        Args:
            with_image: The image to use. If None, the default image is used.
            encode_image: Whether to encode the image path.
            signer: The signer to use. If None the default is used.

        Returns:
            The generated URL path.
        """
        raise NotImplementedError

    def url(
        self,
        with_image: str | None = None,
        with_base: str | None = None,
        signer: Signer | None = None,
    ) -> str:
        """Generate the full URL.

        Args:
            with_image: The image to use. If None, the default image is used.
            with_base: The base URL to use. If None, the default base URL is used.
            signer: The signer to use. If None the default is used.

        Returns:
            The complete URL with all operations and filters applied.
        """
        path = self.path(with_image=with_image, signer=signer)
        base_url = with_base or self._base_url
        return f"{base_url}/{path}" if base_url else path

    def sign_path(self, path: str, signer: Signer | None = None) -> str:
        """Sign a URL path using HMAC.

        Args:
            path: The URL path to sign. The path is not encoded, this needs to be done previously.
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

    ## TODO: move

    def encode_image_path(self, path: str) -> str:
        """Encode the image path with [`urllib.parse.quote`](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote)."""
        return quote(path, safe="")

    @chain
    def sign(self, unsafe: bool = False, signer: Signer | None = None) -> Self:
        """Set the signer.

        Args:
            unsafe: If True, skip URL signing even if a key is configured.
            signer: The signer to use. If None the default is used.
        """
        if signer:
            self._signer = signer
        if unsafe:
            self._signer = None

    @chain
    def unsafe(self) -> Self:
        """Set the signer to unsafe."""
        self._signer = None

    @property
    def op_order(self) -> tuple[str, ...]:
        """Returns the operation order"""
        return self._op_order or THUMBOR_OP_ORDER

    @op_order.setter
    def op_order(self, value: tuple[str, ...]) -> None:
        """Sets the operation order"""
        self._op_order = value

    def _get_ordered_operations(self) -> list[str]:
        """Get operations in the correct order.

        Returns:
            List of operation strings in the correct order.
        """
        ops_dict = {op.name: op.arg or op.name for op in self._get_operations()}
        return [ops_dict[op_name] for op_name in self.op_order if op_name in ops_dict]

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

    def get_size(self, original: bool = False) -> tuple[int | None, int | None]:
        """Returns the image size."""
        # TODO use original image to get size??
        if original:
            other = self._clone()
            other.remove_operations()
            other.remove_filters()
            _url = other.meta().url()
        else:
            _url = self.meta().url()
        img = requests.get(
            _url, headers={"User-Agent": "imgora (https://github.com/burgdev/imgora)"}
        )
        _width = img.json().get("width")
        _height = img.json().get("height")
        assert _width is not None, f"Could not get width from '{_url}'"
        assert _height is not None, f"Could not get height from '{self.meta().url()}'"
        return int(_width), int(_height)

    # Common operations

    @chain
    def trim(self) -> Self:
        """Trim the image."""
        self.add_operation("trim")

    def _get_crop_values(
        self,
        left: int | float | None = None,
        top: int | float | None = None,
        right: int | float | None = None,
        bottom: int | float | None = None,
        width: int | float | None = None,
        height: int | float | None = None,
        halign: HALIGN | None = None,
        valign: VALIGN | None = None,
    ) -> CropValues:
        """Crop the image. Coordinates are in pixel or float values between 0 and 1 (percentage of image dimensions)

        Args:
            left: Left coordinate of the crop (pixel or relative).
            top: Top coordinate of the crop (pixel or relative).
            right: Right coordinate of the crop (pixel or relative).
            bottom: Bottom coordinate of the crop (pixel or relative).
            halign: Horizontal alignment of the crop (left, center, right).
            valign: Vertical alignment of the crop (top, middle, bottom).
        """
        image_width, image_height = self.get_size(original=True)
        # convert percentages to pixel
        left = int(image_width * left) if isinstance(left, float) else left
        top = int(image_height * top) if isinstance(top, float) else top
        right = int(image_width * right) if isinstance(right, float) else right
        bottom = int(image_height * bottom) if isinstance(bottom, float) else bottom

        # convert negative coordinates
        right = image_width + right if isinstance(right, int) and right < 0 else right
        bottom = (
            image_height + bottom if isinstance(bottom, int) and bottom < 0 else bottom
        )

        if (
            left is not None
            and top is not None
            and right is not None
            and bottom is not None
        ):
            pass  # do nothing
        elif (
            width is not None
            and height is not None
            and left is not None
            and top is not None
        ):
            right = left + width
            bottom = top + height
        elif (
            width is not None
            and height is not None
            and right is not None
            and bottom is not None
        ):
            left = right - width
            top = bottom - height
        elif (
            width is not None
            and height is not None
            and left is not None
            and right is not None
        ):
            middle_x = int(image_width / 2)
            middle_y = int(image_height / 2)
            if halign in ["center", None]:
                left = middle_x - int(width / 2)
                right = middle_x + int(width / 2)
            elif halign == "left":
                left = 0
                right = width
            elif halign == "right":
                left = image_width - width
                right = image_width
            if valign in ["middle", None]:
                top = middle_y - int(height / 2)
                bottom = middle_y + int(height / 2)
            elif valign == "top":
                top = 0
                bottom = height
            elif valign == "bottom":
                top = image_height - height
                bottom = image_height
        else:
            raise ValueError(
                "Either 'left', 'top', 'right', 'bottom' or 'width', 'height' must be specified"
            )

        crop_width = right - left
        crop_height = bottom - top
        return CropValues(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            image_width=image_width,
            image_height=image_height,
            crop_width=crop_width,
            crop_height=crop_height,
            halign=halign,
            valign=valign,
        )

    @chain
    def crop(
        self,
        left: int | float | None = None,
        top: int | float | None = None,
        right: int | float | None = None,
        bottom: int | float | None = None,
        width: int | float | None = None,
        height: int | float | None = None,
        halign: HALIGN | None = None,
        valign: VALIGN | None = None,
    ) -> Self:
        """Crop the image. Coordinates are in pixel or float values between 0 and 1 (percentage of image dimensions)
        The coordiantes start in the top/left corner and go down and right.

        Args:
            left: Left coordinate of the crop (pixel or relative).
            top: Top coordinate of the crop (pixel or relative).
            right: Right coordinate of the crop (pixel or relative), can be negative.
            bottom: Bottom coordinate of the crop (pixel or relative), can be negative.
            width: Width of the crop (pixel or relative).
            height: Height of the crop (pixel or relative).
            halign: Horizontal alignment of the crop (left, center, right).
            valign: Vertical alignment of the crop (top, middle, bottom).

        !!! Examples
            === "Code"
                ```python
                img.crop(left=5, top=2, right=10, bottom=4)
                img.crop(left=5, top=2, right=-4, bottom=-2)
                img.crop(left=5, top=2, width=5, height=2)
                img.crop(left=0.3, top=0.42, width=0.5, height=0.4)
                ```
            === "Coordinate System"
                ```
                  0    5    10          x
                0 *=============*------->
                  #    .    .   #
                2 #....+~~~~~+  #
                  # . .|     |  #
                4 # . .+~~~~~+  #
                  *=============*
                  |
                y v
                ```


        """
        crop = self._get_crop_values(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            width=width,
            height=height,
            halign=halign,
            valign=valign,
        )
        self.add_operation("crop", f"{crop.left}x{crop.top}:{crop.right}x{crop.bottom}")
        # if halign:
        #    self.add_operation("halign", halign)
        # if valign:
        #    self.add_operation("valign", valign)

    @chain
    def fit_in(self, width: int, height: int) -> Self:
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

    @chain
    def resize(
        self, width: int, height: int, method: Literal["fit-in", "stretch"] = "fit-in"
    ) -> Self:
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

    @chain
    def meta(
        self,
    ) -> Self:
        """Shows meta information of the image."""
        self.add_operation("meta")

    # ===== Common Filters =====
    @chain
    def background_color(self, color: str) -> Self:
        """The `background_color` filter sets the background layer to the specified color.
        This is specifically useful when converting transparent images (PNG) to JPEG.

        Args:
            color: Background color in hex format without # or 'auto' (e.g., 'FFFFFF', 'aab').
        """
        self.add_filter("background_color", color.removeprefix("#").lower())

    @chain
    def blur(self, radius: int, sigma: int | None = None) -> Self:
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

    @chain
    def brightness(self, amount: int) -> Self:
        """Adjust brightness of the image.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image brightness.
                    Positive numbers make the image brighter and negative numbers make the image darker.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("brightness", amount)

    @chain
    def contrast(self, amount: int) -> Self:
        """Adjust contrast of the image.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image contrast.
                     Positive numbers increase contrast and negative numbers decrease contrast.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("brightness_contrast", amount)

    @chain
    def rgb(
        self,
        r: float = 0,
        g: float = 0,
        b: float = 0,
    ) -> Self:
        """Adjust the RGB channels of the image.

        Args:
            r: `-100` to `100`. Red channel adjustment.
            g: `-100` to `100`. Green channel adjustment.
            b: `-100` to `100`. Blue channel adjustment.
        """
        self.add_filter("rgb", r, g, b)

    @chain
    def focal(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> Self:
        """Set the focal point of the image, which is used in later transforms (e.g. `crop`).

        Args:
            left: Left coordinate of the focal region.
            top: Top coordinate of the focal region.
            right: Right coordinate of the focal region.
            bottom: Bottom coordinate of the focal region.
        """
        self.add_filter("focal", f"{left}x{top}:{right}x{bottom}")

    @chain
    def quality(self, amount: int) -> Self:
        """Set the image quality (JPEG only).

        Args:
            amount: Quality percentage (1-100).
        """
        self.add_filter("quality", amount)

    def radius(self, rx: int, ry: int | None = None, color: str | None = None) -> Self:
        """Add rounded corners to the image (alias for round_corner).

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (defaults to rx).
            color: Corner color in CSS format (default: "none").
        """
        return self.round_corner(rx, ry, color)


class BaseImagorThumbor(BaseImage):
    """Base class with operations and filters common to both Imagor and Thumbor."""

    def path(
        self,
        with_image: str | None = None,
        encode_image: bool = True,
        signer: Signer | None = None,
    ) -> str:
        """Generate the URL path with all operations and filters applied.

        Args:
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
        if not signer:
            signature = "unsafe"
        else:
            signature = self.sign_path(path=path, signer=signer)
        return f"{signature}/{path}"

    def sign_path(self, path: str, signer: Signer | None = None) -> str:
        """Sign a URL path using HMAC.

        Args:
            path: The URL path to sign. The path is not encoded, this needs to be done previously.
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

    # ===== Common Operations =====
    @chain
    def halign(self, halign: Literal["left", "center", "right"]) -> Self:
        """Set the horizontal alignment of the image.

        Args:
            halign: Horizontal alignment of the image (left, center, right).
        """
        self.add_operation("halign", halign)

    @chain
    def valign(self, valign: Literal["top", "middle", "bottom"]) -> Self:
        """Set the vertical alignment of the image.

        Args:
            valign: Vertical alignment of the image (top, middle, bottom).
        """
        self.add_operation("valign", valign)

    @chain
    def fit_in(self, width: int, height: int) -> Self:
        """Fit the image within the specified dimensions while preserving aspect ratio.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
        """
        self.add_operation("fit-in", f"{width}x{height}")

    @chain
    def smart_crop(self) -> Self:
        """Enable smart cropping to detect the region of interest."""
        self.add_operation("smart")

    # ===== Common Filters =====
    @chain
    def grayscale(self) -> Self:
        """Convert the image to grayscale."""
        self.add_filter("grayscale")

    @chain
    def quality(self, amount: int) -> Self:
        """Set the quality of the output image.

        Args:
            amount: Quality level from 0 to 100.
        """
        self.add_filter("quality", str(amount))

    @chain
    def format(self, fmt: str) -> Self:
        """Set the output format of the image.

        Args:
            fmt: Output format (e.g., 'jpeg', 'png', 'webp', 'gif').
        """
        self.add_operation("format", fmt.lower())

    @chain
    def strip_exif(self) -> Self:
        """Remove EXIF metadata from the image."""
        self.add_filter("strip_exif")

    @chain
    def strip_icc(self) -> Self:
        """Remove ICC profile from the image."""
        self.add_filter("strip_icc")

    @chain
    def upscale(self) -> Self:
        """Allow upscaling the image beyond its original dimensions."""
        self.remove("no_upscale")

    @chain
    def no_upscale(self) -> Self:
        """Prevent upscaling the image beyond its original dimensions."""
        self.add_filter("no_upscale")

    @chain
    def max_bytes(self, amount: int) -> Self:
        """Set the maximum file size in bytes for the output image.

        Args:
            amount: Maximum file size in bytes.
        """
        self.add_filter("max_bytes", amount)

    @chain
    def proportion(self, percentage: float) -> Self:
        """Scale the image to the specified percentage of its original size.

        Args:
            percentage: Scale percentage (0-100).
        """
        assert 0 <= percentage <= 100, "Percentage must be between 0 and 100"
        self.add_filter("proportion", round(percentage / 100, 1))

    @chain
    def rotate(self, angle: int) -> Self:
        """Rotate the given image by the specified angle after processing.

        This is different from the 'orient' filter which rotates the image before processing.

        Args:
            angle: `0`, `90`, `180`, `270`. Rotation angle.
        """
        if angle % 90 != 0:
            raise ValueError("Rotation angle must be a multiple of 90 degrees")
        self.add_filter("rotate", angle)

    @chain
    def brightness(self, amount: float) -> Self:
        """Adjust the image brightness.

        Args:
            amount: Adjustment amount (-100 to 100).
        """
        self.add_filter("brightness", str(amount))

    @chain
    def contrast(self, amount: float) -> Self:
        """Adjust the image contrast.

        Args:
            amount: Adjustment amount (-100 to 100).
        """
        self.add_filter("contrast", str(amount))

    @chain
    def saturation(self, amount: float) -> Self:
        """Adjust the image saturation.

        Args:
            amount: Adjustment amount (-100 to 100).
        """
        self.add_filter("saturation", str(amount))

    @chain
    def sharpen(self, sigma: float, amount: float = 1.0) -> Self:
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
    img = BaseImagorThumbor(base_url="http://localhost:8018", signer=signer)
    img = img.with_image(image_url)

    # .crop(0.1, 0.1, 0.9, 0.9, halign="center", valign="middle")
    # .trim()
    # .rotate(90)
    # .radius(100)
    ## .round_corner(10, 30)
    # .resize(800, 600)  # Resize to 800x600
    # .blur(10)  # Apply blur with radius 3
    # .quality(40)  # Set quality to 85%
    img.blur(5)

    # Get and print the processed URL
    print(img.path())
    print(img.url())
