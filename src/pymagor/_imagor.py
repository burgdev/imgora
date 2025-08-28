"""Imagor-specific image processing operations and filters.

This module provides the Imagor class, which implements Imagor-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

from typing import Optional, Union

from ._core import BaseImagorThumbor, Operation


class Imagor(BaseImagorThumbor):
    """Imagor image processor with Imagor-specific operations and filters."""

    def stretch(self, width: int, height: int) -> "Imagor":
        """Stretch the image to the exact dimensions without preserving aspect ratio.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.

        Returns:
            A new instance with the stretch operation applied.
        """
        new = self._clone()
        new._operations.append(Operation("stretch", (width, height)))
        return new

    def focal(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        original_width: Optional[int] = None,
        original_height: Optional[int] = None,
    ) -> "Imagor":
        """Set the focal point of the image.

        Args:
            left: Left coordinate of the focal point.
            top: Top coordinate of the focal point.
            right: Right coordinate of the focal point.
            bottom: Bottom coordinate of the focal point.
            original_width: Original width of the image (optional).
            original_height: Original height of the image (optional).

        Returns:
            A new instance with the focal point set.
        """
        new = self._clone()
        args = [str(left), str(top), str(right), str(bottom)]
        if original_width is not None and original_height is not None:
            args.extend([str(original_width), str(original_height)])
        new._operations.append(Operation("focal", tuple(args)))
        return new

    def upscale(self) -> "Imagor":
        """Enable upscaling of the image beyond its original dimensions.

        Returns:
            A new instance with upscaling enabled.
        """
        new = self._clone()
        new._operations.append(Operation("upscale"))
        return new

    def page(self, num: int) -> "Imagor":
        """Select a specific page from a multi-page document.

        Args:
            num: Page number (1-based index).

        Returns:
            A new instance with the specified page selected.
        """
        new = self._clone()
        new._operations.append(Operation("page", (num,)))
        return new

    def dpi(self, dpi: int) -> "Imagor":
        """Set the DPI for vector images.

        Args:
            dpi: Dots per inch.

        Returns:
            A new instance with the DPI set.
        """
        new = self._clone()
        new._operations.append(Operation("dpi", (dpi,)))
        return new

    def proportion(self, percentage: float) -> "Imagor":
        """Scale the image by a percentage.

        Args:
            percentage: Scale percentage (e.g., 50 for 50%).

        Returns:
            A new instance with the scale applied.
        """
        new = self._clone()
        new._operations.append(Operation("proportion", (percentage,)))
        return new

    def format(self, fmt: str) -> "Imagor":
        """Convert the image to the specified format.

        Args:
            fmt: Output format (e.g., 'jpg', 'png', 'webp').

        Returns:
            A new instance with the output format set.
        """
        new = self._clone()
        new._operations.append(Operation("format", (fmt,)))
        return new

    def watermark(
        self,
        image: str,
        x: Union[int, str],
        y: Union[int, str],
        alpha: float,
        w_ratio: Optional[float] = None,
        h_ratio: Optional[float] = None,
    ) -> "Imagor":
        """Add a watermark to the image.

        Args:
            image: Path or URL of the watermark image.
            x: X position of the watermark (can be number or 'left', 'center', 'right').
            y: Y position of the watermark (can be number or 'top', 'middle', 'bottom').
            alpha: Opacity of the watermark (0.0 to 1.0).
            w_ratio: Width ratio of the watermark relative to the base image.
            h_ratio: Height ratio of the watermark relative to the base image.

        Returns:
            A new instance with the watermark applied.
        """
        new = self._clone()
        args = [image, str(x), str(y), str(alpha)]
        if w_ratio is not None and h_ratio is not None:
            args.extend([str(w_ratio), str(h_ratio)])
        new._filters.append(("watermark", *args))
        return new

    def label(
        self,
        text: str,
        x: Union[int, str],
        y: Union[int, str],
        size: int,
        color: str,
        alpha: Optional[float] = None,
        font: Optional[str] = None,
    ) -> "Imagor":
        """Add a text label to the image.

        Args:
            text: Text to display.
            x: X position (can be number or 'left', 'center', 'right').
            y: Y position (can be number or 'top', 'middle', 'bottom').
            size: Font size in points.
            color: Text color in CSS format.
            alpha: Text opacity (0.0 to 1.0).
            font: Font family to use.

        Returns:
            A new instance with the label applied.
        """
        new = self._clone()
        args = [text, str(x), str(y), str(size), color]
        if alpha is not None:
            args.append(str(alpha))
        if font is not None:
            args.append(font)
        new._filters.append(("label", *args))
        return new

    def background_color(self, color: str) -> "Imagor":
        """Set the background color for transparent images.

        Args:
            color: Background color in CSS format.

        Returns:
            A new instance with the background color set.
        """
        new = self._clone()
        new._filters.append(("background_color", color))
        return new

    def fill(self, color: str) -> "Imagor":
        """Fill the image with a solid color.

        Args:
            color: Fill color in CSS format.

        Returns:
            A new instance with the fill applied.
        """
        new = self._clone()
        new._filters.append(("fill", color))
        return new

    def max_bytes(self, amount: int) -> "Imagor":
        """Set the maximum file size in bytes for the output image.

        Args:
            amount: Maximum file size in bytes.

        Returns:
            A new instance with the maximum file size set.
        """
        new = self._clone()
        new._filters.append(("max_bytes", str(amount)))
        return new

    def max_frames(self, n: int) -> "Imagor":
        """Limit the number of frames in an animated image.

        Args:
            n: Maximum number of frames to keep.

        Returns:
            A new instance with the frame limit applied.
        """
        new = self._clone()
        new._filters.append(("max_frames", str(n)))
        return new
