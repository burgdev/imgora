"""[Thumbor](https://www.thumbor.org)-specific image processing operations and filters.

This module provides the Thumbor class, which implements Thumbor-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

from typing import List, Literal, Self

import requests
from imgora._converter import color_html_to_rgb
from imgora._core import BaseImagorThumbor, ImageFormats, chain


class Thumbor(BaseImagorThumbor):
    """[Thumbor](https://www.thumbor.org) image processor with Thumbor-specific operations and filters.

    Filter documentation: https://thumbor.readthedocs.io/en/latest/filters.html"""

    def get_size(self, original: bool = False) -> tuple[int, int]:
        """Returns the image size."""
        if original:
            other = self._clone()
            other.remove_operations()
            other.remove_filters()
            _url = other.meta().url()
        else:
            _url = self.meta().url()
        img = requests.get(_url)
        info = img.json().get("thumbor", {}).get("source", {})
        _width = info.get("width")
        _height = info.get("height")
        assert _width is not None, f"Could not get width from '{self.meta().url()}'"
        assert _height is not None, f"Could not get height from '{self.meta().url()}'"
        return int(_width), int(_height)

    # ===== Operations =====
    # compared to imagor it adds method as well.
    @chain
    def resize(
        self,
        width: int,
        height: int,
        method: Literal["fit-in", "stretch", "smart", "focal"] | None = None,
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
        focal_point = self.get_filter("focal")
        if focal_point:
            method_default = "focal"
        method = method or method_default
        if method == "focal":
            method = "smart"
        if method == "stretch":
            self.add_filter("stretch")
        else:
            self.add_operation(method)
        self.add_operation("resize", f"{width}x{height}")
        if upscale:
            self.remove("no_upscale")
            self.add_filter("upscale")
        else:
            self.remove("upscale")
        return self

    # ===== Filters =====
    @chain
    def auto_jpg(self) -> Self:
        """Automatically convert to JPEG (overwrite `AUTO_PNG_TO_JPG` variable)."""
        self.add_filter("autojpg")
        return self

    @chain
    def convolution(
        self,
        matrix: List[List[float]],
        normalize: bool = True,
    ) -> Self:
        """This filter runs a convolution matrix (or kernel) on the image.
        See [Kernel (image processing)](https://en.wikipedia.org/wiki/Kernel_(image_processing)) for details on the process.
        Edge pixels are always extended outside the image area.

        Args:
            matrix: 2D convolution matrix (NxN).
            normalize: Whether to normalize the matrix.
        """
        rows = []
        for row in matrix:
            rows.append(";".join(str(x) for x in row))
        matrix_str = ";".join(rows)
        number_of_columns = len(matrix[0])
        self.add_filter(
            "convolution", matrix_str, str(number_of_columns), str(normalize).lower()
        )
        return self

    @chain
    def cover(self) -> Self:
        """This filter is used in GIFs to extract their first frame as the image to be used as cover."""
        self.add_filter("cover")
        return self

    @chain
    def equalize(self) -> Self:
        """This filter equalizes the color distribution in the image."""
        self.add_filter("equalize")
        return self

    @chain
    def extract_focal(self) -> Self:
        """Extract the focal points from the image.

        [More information](https://thumbor.readthedocs.io/en/latest/extract_focal_points.html)"""
        self.add_filter("extract_focal")
        return self

    @chain
    def fill(
        self,
        color: str,
        fill_transparent: bool = False,
    ) -> Self:
        """This filter returns an image sized exactly as requested independently of its ratio.
        It will fill the missing area with the specified color.
        It is usually combined with the `fit-in` or `adaptive-fit-in` options.

        [More information](https://thumbor.readthedocs.io/en/latest/fill.html)

        Args:
            color: Fill color in hex format without `#` (e.g., 'FFFFFF', 'aab').
            fill_transparent: Whether to fill transparent areas.
        """
        self.add_filter(
            "fill", color.removeprefix("#").lower(), str(fill_transparent).lower()
        )
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

        The coordinates are either in pixel of float values between 0 and 1 (percentage of image dimensions)

        Coordinated by a region of left-top point AxB and right-bottom point CxD, or a point X,Y.

        Args:
            left: Left or x coordinate of the focal region/point, either in pixel or relative (float from 0 to 1).
            top: Top or y coordinate of the focal region/point, either in pixel or relative (float from 0 to 1).
            right: Right coordinate of the focal region, either in pixel or relative (float from 0 to 1).
            bottom: Bottom coordinate of the focal region, either in pixel or relative (float from 0 to 1).
        """
        left = left or 0.5
        top = top or 0.5

        if right is None and bottom is None:
            # point is not supported, create a very small area
            right = left + 0.01 if isinstance(left, float) else left + 1
            bottom = top + 0.01 if isinstance(top, float) else top + 1
        if right is not None and bottom is not None:
            # percent is not supported by thumbor, but we can calculate it
            if (
                isinstance(left, float)
                or isinstance(top, float)
                or isinstance(right, float)
                or isinstance(bottom, float)
            ):
                w, h = self.get_size(original=True)
                left = int(left * w) if isinstance(left, float) else left
                top = int(top * h) if isinstance(top, float) else top
                right = int(right * w) if isinstance(right, float) else right
                bottom = int(bottom * h) if isinstance(bottom, float) else bottom
            self.add_filter("focal", f"{left}x{top}:{right}x{bottom}")
        else:
            raise ValueError(
                "'left', 'top' or 'left', 'top', 'right', 'bottom' must be specified"
            )
        self.add_operation("smart")
        self.remove("fit-in")
        return self

    @chain
    def format(
        self,
        fmt: ImageFormats,
        quality: int | None = None,
    ) -> Self:
        """Convert the image to the specified format.

        Args:
            fmt: Output format (_jpeg_, _jpg_, _png_, _webp_, _gif_, etc.).
            quality: `1` to `100`. Quality setting for lossy formats (e.g. jpg, does nothing for _png_).
        """
        fmt_str = fmt
        if fmt == "jpg":
            fmt_str = "jpeg"
        if quality is not None:
            assert 1 <= quality <= 100, "Quality must be between 1 and 100"
            self.add_filter("quality", quality)
        self.add_filter("format", fmt_str)
        return self

    @chain
    def noise(self, amount: int) -> Self:
        """Add noise to the image.

        Args:
            amount: `0` to `100`. Amount of noise in %.
        """
        assert 0 <= amount <= 100, "Amount must be between 0 and 100"
        self.add_filter("noise", str(amount))
        return self

    @chain
    def quality(self, amount: int) -> Self:
        """Set the quality of the output image.

        Args:
            amount: `1` to `100`. Quality setting for lossy formats (e.g. jpg, does nothing for _png_).
        """
        assert 1 <= amount <= 100, "Quality must be between 1 and 100"
        self.add_filter("quality", amount)
        return self

    @chain
    def red_eye(self) -> Self:
        """Automatically detect and correct red-eye in photos."""
        self.add_filter("redeye")
        return self

    @chain
    def round_corner(
        self,
        rx: int,
        ry: int | None = None,
        color: str | None | tuple[int, int, int] = None,
    ) -> Self:
        """Add rounded corners to the image.

        Args:
            rx: X radius of the corners in pixels.
            ry: Y radius of the corners in pixels (not supported at the moment).
            color: Corner color in CSS format (default: "none"), if none is used transparent background is used if possible.

        Raises:
            ValueError: If 'ry' is used.
        """
        transparent = 0
        if color in [None, "none"]:
            color = (255, 255, 255)  # white
            transparent = 1
        elif not isinstance(color, tuple):
            assert color is not None
            color = color_html_to_rgb(color)

        if ry is not None and rx != ry:
            radius = f"{rx}|{ry}"
            raise ValueError("'ry' not supported at the moment")
        else:
            radius = rx
        self.add_filter("round_corner", radius, *color, transparent)
        return self

    @chain
    def saturation(self, amount: float) -> Self:
        """Adjust the image saturation.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image saturation.
                    Positive numbers increase saturation and negative numbers decrease saturation.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("saturation", str(amount))
        return self

    @chain
    def sharpen(
        self, amount: float, radius: float = 1.0, luminance_only: bool = True
    ) -> Self:
        """Sharpen the image.

        Args:
            amount: `0.0` to around `10.0`. Sharpening amount.
            radius: `0.0` to around `2.0`. Sharpening radius.
            luminance_only: Whether to only sharpen the luminance channel.
        """
        self.add_filter("sharpen", amount, radius, str(luminance_only).lower())
        return self

    @chain
    def stretch(self) -> Self:
        """This filter stretches the image until it fits the required width and height, instead of cropping the image."""
        self.add_filter("stretch")
        return self

    @chain
    def strip_metadata(self) -> Self:
        """Remove all metadata from the image."""
        self.add_filter("strip_exif")
        self.add_filter("strip_icc")
        return self

    @chain
    def upscale(self, upscale: bool = True) -> Self:
        """Enable upscaling of the image beyond its original dimensions.
        This only makes sense with `fit-in` or `adaptive-fit-in`.

        [More information](https://thumbor.readthedocs.io/en/latest/upscale.html)"""
        if upscale:
            self.remove("no_upscale")
            self.add_filter("upscale")
        else:
            self.remove("no_upscale")
            self.add_filter("no_upscale")
        return self


if __name__ == "__main__":
    import webbrowser

    from imgora import Signer

    # Example image from Wikipedia
    image_url = (
        "https://raw.githubusercontent.com/cshum/imagor/master/testdata/gopher.png"
    )
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
    signer = Signer(key="my_key")

    # Create an Imagor processor and apply some transformations
    img = Thumbor(base_url="http://localhost:8019", signer=signer).with_image(image_url)
    img = img.quality(80).focal(0.1, 0.8).resize(200, 600)
    # img = img.radius(50, color=None)
    # img = img.blur(10)
    # img = img.rotate(90).format("png")

    url = img.url()
    print(url)
    webbrowser.open(url)
