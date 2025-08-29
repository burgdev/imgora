"""Thumbor-specific image processing operations and filters.

This module provides the Thumbor class, which implements Thumbor-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

from typing import List, Literal, Self

from pymagor._converter import color_html_to_rgb
from pymagor._core import BaseImagorThumbor, filter, operation


class Thumbor(BaseImagorThumbor):
    """Thumbor image processor with Thumbor-specific operations and filters.

    Filter documentation: https://thumbor.readthedocs.io/en/latest/filters.html"""

    # ===== Operations =====
    # compared to imagor it adds method as well.
    @operation
    def fit_in(
        self, width: int, height: int, method: Literal["full", "adaptive"] | None = None
    ) -> Self:
        """Fit the image within the specified dimensions while preserving aspect ratio.

        Fit-in means that the generated image should not be auto-cropped and otherwise just fit in an imaginary box specified by `ExF`.
        If a `full` fit-in is specified, then the largest size is used for cropping (width instead of height, or the other way around).
        If `adaptive` fit-in is specified, it inverts requested width and height if it would get a better image definition;

        Args:
            width: Maximum width in pixels.
            height: Maximum height in pixels.
            method: Method to use for fit-in ('full', 'adaptive' or None).
        """
        assert "stretch" not in (
            a.name for a in self._get_operations()
        ), "Use either 'fit-in' or 'stretch'"
        if method:
            self.add_operation(f"{method}-fit-in")
        else:
            self.add_operation("fit-in")
        self.add_operation("resize", f"{width}x{height}")

    # ===== Filters =====
    @filter
    def auto_jpg(self) -> Self:
        """Automatically convert to JPEG (overwrite `AUTO_PNG_TO_JPG` variable)."""
        self.add_filter("autojpg")

    @filter
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

    @filter
    def cover(self) -> Self:
        """This filter is used in GIFs to extract their first frame as the image to be used as cover."""
        self.add_filter("cover")

    @filter
    def equalize(self) -> Self:
        """This filter equalizes the color distribution in the image."""
        self.add_filter("equalize")

    @filter
    def extract_focal(self) -> Self:
        """Extract the focal points from the image.

        [More information](https://thumbor.readthedocs.io/en/latest/extract_focal_points.html)"""
        self.add_filter("extract_focal")

    @filter
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

    @filter
    def format(
        self,
        fmt: Literal["jpeg", "jpg", "png", "webp", "gif"],
        quality: int | None = None,
    ) -> Self:
        """Convert the image to the specified format.

        Args:
            fmt: Output format (_jpeg_, _jpg_, _png_, _webp_, _gif_, etc.).
            quality: `1` to `100`. Quality setting for lossy formats (e.g. jpg, does nothing for _png_).
        """
        if fmt == "jpg":
            fmt = "jpeg"
        if quality is not None:
            assert 1 <= quality <= 100, "Quality must be between 1 and 100"
            self.add_filter("quality", quality)
        self.add_filter("format", fmt)

    @filter
    def noise(self, amount: int) -> Self:
        """Add noise to the image.

        Args:
            amount: `0` to `100`. Amount of noise in %.
        """
        assert 0 <= amount <= 100, "Amount must be between 0 and 100"
        self.add_filter("noise", str(amount))

    @filter
    def quality(self, amount: int) -> Self:
        """Set the quality of the output image.

        Args:
            amount: `1` to `100`. Quality setting for lossy formats (e.g. jpg, does nothing for _png_).
        """
        assert 1 <= amount <= 100, "Quality must be between 1 and 100"
        self.add_filter("quality", amount)

    @filter
    def red_eye(self) -> Self:
        """Automatically detect and correct red-eye in photos."""
        self.add_filter("redeye")

    @filter
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
            color = color_html_to_rgb(color)

        if ry is not None and rx != ry:
            radius = f"{rx}|{ry}"
            raise ValueError("'ry' not supported at the moment")
        else:
            radius = rx
        self.add_filter("round_corner", radius, *color, transparent)

    @filter
    def saturation(self, amount: float) -> Self:
        """Adjust the image saturation.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image saturation.
                    Positive numbers increase saturation and negative numbers decrease saturation.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("saturation", str(amount))

    @filter
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

    @filter
    def stretch(self) -> Self:
        """This filter stretches the image until it fits the required width and height, instead of cropping the image."""
        self.add_filter("stretch")

    @filter
    def strip_metadata(self) -> Self:
        """Remove all metadata from the image."""
        self.add_filter("strip_exif")
        self.add_filter("strip_icc")

    @filter
    def upscale(self) -> Self:
        """Enable upscaling of the image beyond its original dimensions.
        This only makes sense with `fit-in` or `adaptive-fit-in`.

        [More information](https://thumbor.readthedocs.io/en/latest/upscale.html)"""
        self.add_filter("upscale")


if __name__ == "__main__":
    import webbrowser

    from pymagor import Signer

    # Example image from Wikipedia
    image_url = (
        "https://raw.githubusercontent.com/cshum/imagor/master/testdata/gopher.png"
    )
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
    signer = Signer(key="my_key")

    # Create an Imagor processor and apply some transformations
    img = Thumbor(base_url="http://localhost:8019", signer=signer).with_image(image_url)
    img = img.quality(80).fit_in(400, 300)
    img = img.radius(50, color="fff")
    # img = img.blur(10)
    img = img.rotate(90)

    url = img.url()
    print(url)
    webbrowser.open(url)
