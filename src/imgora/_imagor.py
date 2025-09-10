"""[Imagor](https://github.com/cshum/imagor)-specific image processing operations and filters.

This module provides the Imagor class, which implements Imagor-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

from typing import Literal, Optional, Self
from urllib.parse import quote

from imgora._core import BaseImagorThumbor, chain


class Imagor(BaseImagorThumbor):
    """[Imagor](https://github.com/cshum/imagor) image processor with Imagor-specific operations and filters."""

    # ===== Operations =====

    # ===== Filters =====
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
        if right is None and bottom is None:
            x = f"{left:.3f}" if isinstance(left, float) else str(left)
            y = f"{top:.3f}" if isinstance(top, float) else str(top)
            self.add_filter("focal", f"{x}x{y}")
        elif (
            left is not None
            and top is not None
            and right is not None
            and bottom is not None
        ):
            left_str = f"{left:.3f}" if isinstance(left, float) else str(left)
            top_str = f"{top:.3f}" if isinstance(top, float) else str(top)
            right_str = f"{right:.3f}" if isinstance(right, float) else str(right)
            bottom_str = f"{bottom:.3f}" if isinstance(bottom, float) else str(bottom)
            self.add_filter("focal", f"{left_str}x{top_str}:{right_str}x{bottom_str}")
        else:
            raise ValueError(
                "'left', 'top' or 'left', 'top', 'right', 'bottom' must be specified"
            )
        self.add_operation("smart")
        self.remove("fit-in")
        return self

    @chain
    def page(self, num: int) -> Self:
        """Select a specific page from a multi-page document.

        Args:
            num: Page number (1-based index).
        """
        self.add_filter("page", num)
        return self

    @chain
    def dpi(self, dpi: int) -> Self:
        """Set the DPI for vector images like PDF or SVG.

        Args:
            dpi: Dots per inch.
        """
        self.add_filter("dpi", dpi)
        return self

    @chain
    def orient(self, angle: int) -> Self:
        """Rotate the image before resizing and cropping.

        This is different from the 'rotate' filter which rotates the image after processing.

        Args:
            angle: `0`, `90`, `180`, `270`. Rotation angle.
        """
        if angle % 90 != 0:
            raise ValueError("Rotation angle must be a multiple of 90 degrees")
        self.add_operation("orient", str(angle))
        return self

    @chain
    def fill(self, color: str | Literal["blur", "auto", "none"] | None = None) -> Self:
        """Fill the missing area or transparent image with the specified color.

        Args:
            color: Color in hex format or 'blur', 'auto', or 'none' (transparent). Default is transparent.
        """
        if color is None:
            color = "none"
        self.add_filter("fill", color)
        return self

    @chain
    def hue(self, angle: int) -> Self:
        """Adjust the hue of the image.

        Args:
            angle: `0` to `359`. Hue rotation angle in degrees.
        """
        assert 0 <= angle <= 359, "Angle must be between 0 and 359"
        self.add_filter("hue", angle)
        return self

    @chain
    def round_corner(
        self, rx: int, ry: int | None = None, color: str | None = None
    ) -> Self:
        """Add rounded corners to the image.

        Args:
            rx: Horizontal radius of the corners.
            ry: Vertical radius of the corners (defaults to rx if not specified).
            color: Corner color in hex format (default: '000000').
        """
        if ry is None:
            ry = rx
        color = "ffffff" if color is None or color == "none" else color.lstrip("#")
        self.add_filter("round_corner", f"{rx},{ry},{color}")
        return self

    @chain
    def watermark(
        self,
        image: str,
        x: int | str = "center",
        y: int | str = "middle",
        alpha: int = 0,
        w_ratio: Optional[float] = None,
        h_ratio: Optional[float] = None,
    ) -> Self:
        """Add a watermark to the image.

        Args:
            image: Watermark image URI.
            x: Horizontal position (e.g., `left`, `center`, `right`, `repeat`, or pixel value from left. Number with `p` suffix for percentage (e.g. `20p`)).
            y: Vertical position (e.g., `top`, `middle`, `bottom`, `repeat`, or pixel value from top. Number with `p` suffix for percentage).
            alpha: `0` to `100`. Watermark transparency.
            w_ratio: `0` to `100`. Width ratio of the watermark relative to the image.
            h_ratio: `0` to `100`. Height ratio of the watermark relative to the image.
        """
        image = quote(image, safe="")
        self.add_filter("watermark", image, x, y, alpha, w_ratio, h_ratio)
        return self

    @chain
    def label(
        self,
        text: str,
        x: int | str,
        y: int | str,
        size: int,
        color: str,
        alpha: Optional[float] = None,
        font: Optional[str] = None,
    ) -> Self:
        """Add a text label to the image.

        Args:
            text: Text to display (URL-encoded if needed).
            x: X position (can be number, percentage like `20p`, or `left`, `center`, `right`).
            y: Y position (can be number, percentage like `20p`, or `top`, `middle`, `bottom`).
            size: Font size in points.
            color: Text color in hex format (without #).
            alpha: Text transparency (0.0 to 1.0).
            font: Font family to use.
        """
        args = [text, str(x), str(y), str(size), color]
        if alpha is not None:
            args.append(str(alpha))
        if font is not None:
            args.append(font)
        self.add_filter("label", ",".join(args))
        return self

    @chain
    def strip_metadata(self) -> Self:
        """Remove all metadata from the image."""
        self.add_filter("strip_metadata")
        return self

    @chain
    def max_frames(self, n: int) -> Self:
        """Limit the number of frames in an animated image.

        Args:
            n: Maximum number of frames to keep.
        """
        self.add_operation("max_frames", str(n))
        return self

    @chain
    def sharpen(self, sigma: float, amount: float = 1.0) -> Self:
        """Sharpen the image.

        Args:
            sigma: Standard deviation of the gaussian kernel.
            amount: Strength of the sharpening effect.
        """
        self.add_filter("sharpen", f"{sigma},{amount}")
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
    img = Imagor(base_url="http://localhost:8018", signer=signer).with_image(image_url)
    img = img.quality(80).focal(0.1, 0.5, 0.4, 1).resize(200, 400)

    url = img.url()
    print(url)
    webbrowser.open(url)
