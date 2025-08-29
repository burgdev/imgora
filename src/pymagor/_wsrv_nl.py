"""Imagor-specific image processing operations and filters.

This module provides the Imagor class, which implements Imagor-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

from typing import Literal, Self

from pymagor._core import BaseImage
from pymagor.decorator import operation


class WsrvNl(BaseImage):
    """weserve.nl image processor with weserve-specific operations and filters."""

    def path(
        self,
        unsafe: bool = False,
        with_image: str | None = None,
        encode_image: bool = True,
        signer: Signer | None = None,
    ) -> str:
        with_image = (with_image or "" if self._image is None else self._image).strip(
            "/"
        )
        if encode_image:
            with_image = self.encode_image_path(with_image)
        filters = self._filters
        if filters:
            filters_query = "&" + "&".join(
                f"{f.name}={f.args[0]}" if len(f.args) == 1 else f.name for f in filters
            )
        else:
            filters_query = ""
        return f"?url={with_image}{filters_query}"

    # ===== Filters =====
    @operation
    def resize(
        self, width: int, height: int, method: Literal["fit-in", "stretch"] = "fit-in"
    ) -> Self:
        """Resize the image to the exact dimensions.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
        """
        self.add_filter("w", width)
        self.add_filter("h", height)

    @operation
    def crop(
        self,
        # width: int,
        # height: int,
        # align: Literal[
        #    "center",
        #    "left",
        #    "right",
        #    "top",
        #    "bottom",
        #    "top-left",
        #    "top-right",
        #    "bottom-left",
        #    "bottom-right",
        #    "entropy",
        #    "attention",
        # ] = "center",
        # fit: Literal["cover", "contain"] = "cover",
        left: int | float,
        top: int | float,
        right: int | float,
        bottom: int | float,
        # halign: Literal["left", "center", "right"] | None = None,
        # valign: Literal["top", "middle", "bottom"] | None = None,
    ) -> Self:
        """Crop the image. Coordinates are in pixel or float values between 0 and 1 (percentage of image dimensions)

        Args:
            left: Left coordinate of the crop (pixel or relative).
            top: Top coordinate of the crop (pixel or relative).
            right: Right coordinate of the crop (pixel or relative).
            bottom: Bottom coordinate of the crop (pixel or relative).
            halign: Horizontal alignment of the crop (left, center, right).
            valign: Vertical alignment of the crop (top, middle, bottom).
        """
        self.add_filter("cx", right)
        self.add_filter("cy", bottom)
        self.add_filter("cw", right - left)
        self.add_filter("ch", bottom - top)
        # self.add_filter("fit", "cover")

    @operation
    def fit_in(
        self,
        width: int,
        height: int,
        fit: Literal["cover", "contain", "fill", "inside", "outside"] = "cover",
        upscale: bool = True,
    ) -> Self:
        """Fit the image within the specified dimensions while preserving aspect ratio.

        Args:
            width: Maximum width in pixels.
            height: Maximum height in pixels.
        """
        self.add_filter("w", width)
        self.add_filter("h", height)
        self.add_filter("fit", fit)
        if not upscale:
            self.add_filter("we")

    @operation
    def upscale(self) -> Self:
        """upscale the image if fit-in is used"""
        self.remove("we")

    @operation
    def no_upscale(self) -> Self:
        """do not upscale the image if fit-in is used"""
        self.add_filter("we")

    @operation
    def rotate(self, angle: int | None = None) -> Self:
        """Rotate the given image by the specified angle after processing.

        This is different from the 'orient' filter which rotates the image before processing.

        Args:
            angle: Rotation angle.
        """
        if angle is None:
            self.add_filter("ro")
        self.add_filter("ro", angle)

    @operation
    def background_color(self, color: str) -> Self:
        """The `background_color` filter sets the background layer to the specified color.
        This is specifically useful when converting transparent images (PNG) to JPEG.

        Args:
            color: Background color in hex format without # or 'auto' (e.g., 'FFFFFF', 'aab').
        """
        self.add_filter("bg", color.removeprefix("#").lower())

    # ===== Filters =====
    @operation
    def blur(self, radius: int | None = None, sigma: int | None = None) -> Self:
        """Apply gaussian blur to the image.

        Args:
            radius: Radius of the blur effect (0-150). The bigger the radius, the more blur.
            sigma: Standard deviation of the gaussian kernel, defaults to `radius`. (not supported)
        """
        if radius is None and sigma is None:
            self.add_filter("blur")
        elif sigma is None:
            sigma = 1 + radius / 2
            self.add_filter("blur", f"{sigma:.2f}")
        else:
            assert radius is None, "Radius must be None if sigma is set"
            self.add_filter("blur", f"{sigma:.2f}")

    @operation
    def contrast(self, amount: int) -> Self:
        """Adjust contrast of the image.

        Args:
            amount: `-100` to `100`. The amount (in %) to change the image contrast.
                     Positive numbers increase contrast and negative numbers decrease contrast.
        """
        assert -100 <= amount <= 100, "Amount must be between -100 and 100"
        self.add_filter("con", amount)

    @operation
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

    @operation
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

    @operation
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
        pass

    @operation
    def meta(
        self,
    ) -> Self:
        """Shows meta information of the image."""
        self.add_filter("output", "json")


if __name__ == "__main__":
    import webbrowser

    from pymagor import Signer

    # Example image from Wikipedia
    image_url = (
        "https://raw.githubusercontent.com/cshum/imagor/master/testdata/gopher.png"
    )
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
    signer = Signer(key="my_key", type="sha256")

    # Create an Imagor processor and apply some transformations
    img = WsrvNl(base_url="https://wsrv.nl").with_image(image_url)
    img = img.fit_in(300, 400, "inside", upscale=False).sharpen(10)
    # img = img.quality(80).fit_in(400, 300)
    # img = img.radius(50, color="fff")
    # img = img.blur(10)
    # img = img.rotate(90)

    url = img.url()
    print(url)
    webbrowser.open(url)
