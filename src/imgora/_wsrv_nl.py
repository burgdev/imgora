"""[wsrv.nl](https://wsrv.nl)-specific image processing operations and filters.

This module provides the wsrv.nl class, which implements wsrv.nl-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

import warnings
from typing import Literal, Self

from imgora._core import HALIGN, VALIGN, BaseImage
from imgora.decorator import chain


class WsrvNl(BaseImage):
    """[wsrv.nl](https://wsrv.nl) image processor with wsrv-specific operations and filters."""

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
            signer: The signer to use. Not needed for wsrv.nl.
        """
        base_url = base_url or "https://wsrv.nl"
        super().__init__(base_url, image)
        self._crop_method = "fit-in"

    def path(
        self,
        with_image: str | None = None,
        encode_image: bool = True,
        signer: Signer | None = None,
    ) -> str:
        with_image = (with_image or "" if not self._image else self._image).strip("/")
        if encode_image:
            with_image = self.encode_image_path(with_image)
        filters = self._filters
        if filters:
            filters_query = "&" + "&".join(
                f"{f.name}={','.join(map(str, f.args))}" if len(f.args) >= 1 else f.name
                for f in filters
            )
        else:
            filters_query = ""
        return f"?url={with_image}{filters_query}"

    # ===== Filters =====
    @chain
    def resize(
        self,
        width: int,
        height: int,
        method: Literal[
            "fit-in", "stretch", "smart", "focal", "cover", "inside", "fill"
        ]
        | None = None,
        upscale: bool = True,
    ) -> Self:
        """Resize the image to the exact dimensions.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
            method: Resizing method (fit-in, stretch, smart).
            upscale: Whether to upscale the image.
        """
        method_default = "fit-in"
        focal_point = self.get_filter("a")
        if focal_point:
            if focal_point.args[0] == "focal":
                method_default = "focal"
            elif focal_point.args[0] in ["entropy", "attention"]:
                method_default = "smart"
        method = method or method_default
        if method == "smart":
            self.add_filter("a", "entropy")
            method = "cover"
        if method == "focal":
            self.add_filter("a", "focal")
            method = "cover"
        elif method == "fit-in":
            method = "inside"
        elif method == "stretch":
            method = "fill"
        self.add_filter("fit", method)
        self.add_filter("w", width)
        self.add_filter("h", height)
        if not upscale:
            self.add_filter("we")
        return self

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
        prcrop: bool = True,
    ) -> Self:
        """Manually crop the image. Coordinates are in pixel or float values between 0 and 1 (percentage of image dimensions)
        The coordiantes start in the top/left corner and go down and right.

        Coordinate system:

                0    5    10          x
              0 *=============*------->
                #    .    .   #
              2 #....+~~~~~+  #
                # . .|     |  #
              4 # . .+~~~~~+  #
                *=============*
                |
              y v

        ```python
        img.crop(left=5, top=2, right=10, bottom=4)
        img.crop(left=5, top=2, right=-4, bottom=-2)
        img.crop(left=5, top=2, width=5, height=2)
        img.crop(left=0.3, top=0.42, width=0.5, height=0.4)
        ```

        Args:
            left: Left coordinate of the crop (pixel or relative).
            top: Top coordinate of the crop (pixel or relative).
            right: Right coordinate of the crop (pixel or relative), can be negative.
            bottom: Bottom coordinate of the crop (pixel or relative), can be negative.
            width: Width of the crop (pixel or relative).
            height: Height of the crop (pixel or relative).
            halign: Horizontal alignment of the crop (left, center, right).
            valign: Vertical alignment of the crop (top, middle, bottom).
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
        self.add_filter("cx", crop.left)
        self.add_filter("cy", crop.top)
        self.add_filter("cw", crop.crop_width)
        self.add_filter("ch", crop.crop_height)
        if prcrop:
            self.add_filter("precrop")
        # self.add_filter("fit", "cover")
        return self

    @chain
    def grayscale(self) -> Self:
        """Convert the image to grayscale."""
        self.add_filter("filt", "greyscale")
        return self

    @chain
    def upscale(self, upscale: bool = True) -> Self:
        """upscale the image if fit-in is used

        This only makes sense with `fit-in` or `inside`.

        Args:
            upscale: Whether to upscale the image. Defaults to True."""
        if upscale:
            self.remove("we")
        else:
            self.add_filter("we")
        return self

    @chain
    def rotate(self, angle: int | None = None) -> Self:
        """Rotate the given image by the specified angle after processing.

        This is different from the 'orient' filter which rotates the image before processing.

        Args:
            angle: Rotation angle.
        """
        if angle is None:
            self.add_filter("ro")
        assert angle is not None
        self.add_filter("ro", -angle)
        return self

    @chain
    def background_color(self, color: str) -> Self:
        """The `background_color` filter sets the background layer to the specified color.
        This is specifically useful when converting transparent images (PNG) to JPEG.

        Args:
            color: Background color in hex format without # or 'auto' (e.g., 'FFFFFF', 'aab').
        """
        self.add_filter("bg", color.removeprefix("#").lower())
        return self

    # ===== Filters =====
    @chain
    def blur(self, radius: int | None = None, sigma: int | float | None = None) -> Self:
        """Apply gaussian blur to the image.

        Args:
            radius: Radius of the blur effect (0-150). The bigger the radius, the more blur.
            sigma: Standard deviation of the gaussian kernel, defaults to `radius`. (not supported)
        """
        if radius is None and sigma is None:
            self.add_filter("blur")
        elif sigma is None:
            assert radius is not None, "Radius must be set if sigma is not set"
            sigma = 1 + radius / 2
            self.add_filter("blur", f"{sigma:.2f}")
        else:
            assert radius is None, "Radius must be None if sigma is set"
            self.add_filter("blur", f"{sigma:.2f}")
        return self

    @chain
    def contrast(self, amount: int) -> Self:
        """Adjust contrast of the image.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image contrast.
                     Positive numbers increase contrast and negative numbers decrease contrast.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("con", amount)
        return self

    @chain
    def sharpen(
        self,
        sigma: float | None = None,
        flat: int | None = None,
        jagged: int | None = None,
    ) -> Self:
        """Sharpen the image.

        Args:
            sigma: `0.000001` to `10`. Standard deviation of the gaussian kernel.
            flat: `0` to `1000000`. Flatness of the sharpening effect.
            jagged: `0` to `1000000`. Jaggedness of the sharpening effect.
        """
        if sigma is None:
            self.add_filter("sharp")
        else:
            self.add_filter("sharp", f"{sigma:.6f}")
            if flat is not None:
                self.add_filter("sharpf", flat)
            if jagged is not None:
                self.add_filter("sharpj", jagged)
        return self

    @chain
    def focal(
        self,
        left: int | float | None = None,
        top: int | float | None = None,
        right: int | float | None = None,
        bottom: int | float | None = None,
    ) -> Self:
        """Set the focal point of the image, which is used in later transforms (e.g. `crop`).
        Only a point is supported by wsrv.nl. For this you can use left and top, if right and bottom is used as well
        it calculates the center of the region.

        Args:
            left: Left or x coordinate of the focal region/point, either in pixel or relative (float from 0 to 1).
            top: Top or y coordinate of the focal region/point, either in pixel or relative (float from 0 to 1).
            right: Right coordinate of the focal region, either in pixel or relative (float from 0 to 1).
            bottom: Bottom coordinate of the focal region, either in pixel or relative (float from 0 to 1).

        !!! warning
            [wsrv.nl](https://wsrv.nl/docs/crop.html#focal-point) only supports a point as focal region,
            if right and bottom is specified it calculates the center of the region.
        """
        if right is not None and left is not None:
            left = left + (right - left) / 2
            if isinstance(right, int):
                left = int(left)
        if bottom is not None and top is not None:
            top = top + (bottom - top) / 2
            if isinstance(bottom, int):
                top = int(top)
        if left is not None:
            left_str = f"{left:.3f}" if isinstance(left, float) else str(left)
            self.add_filter("fpx", left_str)
        if top is not None:
            top_str = f"{top:.3f}" if isinstance(top, float) else str(top)
            self.add_filter("fpy", top_str)
        self.add_filter("a", "focal")
        return self

    @chain
    def format(
        self,
        fmt: Literal["jpeg", "jpg", "png", "webp", "tiff"],
        quality: int | None = None,
        filename: str | None = None,
    ) -> Self:
        """Convert the image to the specified format.

        Args:
            fmt: Output format (_jpg_, _png_, _webp_, _tiff_, etc.).
            quality: `1` to `100`. Quality setting for lossy formats (e.g. jpg, does nothing for _png_).
            filename: Output filename, only alphanumeric characters are allowed. Without extension.
        """
        if fmt == "jpeg":
            fmt = "jpg"
        if quality is not None:
            assert 1 <= quality <= 100, "Quality must be between 1 and 100"
            self.add_filter("q", quality)
        if filename:
            self.add_filter("filename", filename)
        self.add_filter("output", fmt)
        return self

    @chain
    def round_corner(
        self,
        rx: int | None = None,
        ry: int | None = None,
        color: str | None | tuple[int, int, int] = None,
    ) -> Self:
        """Add rounded corners to the image, it is not supported by wsrv.nl.

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (not supported at the moment).
            color: Corner color in CSS format (default: "none"), if none is used transparent background is used if possible.
        """
        warnings.warn("wsrv.nl does not support rounded corners.")
        return self

    @chain
    def meta(
        self,
    ) -> Self:
        """Shows meta information of the image."""
        self.add_filter("output", "json")
        return self


if __name__ == "__main__":
    import webbrowser

    from imgora import Signer

    # Example image from Wikipedia
    image_url = (
        "https://raw.githubusercontent.com/cshum/imagor/master/testdata/gopher.png"
    )
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
    signer = Signer(key="my_key", type="sha256")

    # Create an Imagor processor and apply some transformations
    img = WsrvNl(base_url="https://wsrv.nl").with_image(image_url)
    img = (
        img.focal(0.1, 0.6).resize(3000, 4000, upscale=True, method="smart").sharpen(10)
    )
    # img = img.quality(80).fit_in(400, 300)
    # img = img.radius(50, color="fff")
    # img = img.blur(10)
    # img = img.rotate(90)

    url = img.url()
    print(url)
    webbrowser.open(url)
