"""Thumbor-specific image processing operations and filters.

This module provides the Thumbor class, which implements Thumbor-specific
functionality on top of the base image processing operations.
"""

from __future__ import annotations

from typing import Optional, Tuple

from ._core import BaseImagorThumbor, Operation


class Thumbor(BaseImagorThumbor):
    """Thumbor image processor with Thumbor-specific operations and filters."""

    def brightness_contrast(self, brightness: float, contrast: float) -> "Thumbor":
        """Adjust both brightness and contrast in a single operation.

        Args:
            brightness: Brightness adjustment (-100 to 100).
            contrast: Contrast adjustment (-100 to 100).

        Returns:
            A new instance with the brightness and contrast adjusted.
        """
        new = self._clone()
        new._filters.append(("brightness_contrast", str(brightness), str(contrast)))
        return new

    def equalize(self) -> "Thumbor":
        """Equalize the image histogram.

        Returns:
            A new instance with the equalize filter applied.
        """
        new = self._clone()
        new._filters.append(("equalize",))
        return new

    def curve(
        self,
        channel: str = "all",
        points: Optional[Tuple[Tuple[float, float], ...]] = None,
    ) -> "Thumbor":
        """Apply a curve adjustment to the image.

        Args:
            channel: Channel to adjust ('r', 'g', 'b', 'a', or 'all').
            points: List of (x, y) points defining the curve.

        Returns:
            A new instance with the curve adjustment applied.
        """
        if channel not in ("r", "g", "b", "a", "all"):
            raise ValueError("Channel must be one of: 'r', 'g', 'b', 'a', 'all'")

        new = self._clone()
        if points:
            point_str = ",".join(f"{x}:{y}" for x, y in points)
            new._filters.append(("curve", channel, point_str))
        else:
            new._filters.append(("curve", channel))
        return new

    def enhance(self, factor: float = 1.0) -> "Thumbor":
        """Enhance the image using unsharp masking.

        Args:
            factor: Enhancement factor (0.0 to 10.0).

        Returns:
            A new instance with the enhance filter applied.
        """
        new = self._clone()
        new._filters.append(("enhance", str(factor)))
        return new

    def flip(self) -> "Thumbor":
        """Flip the image vertically.

        Returns:
            A new instance with the flip operation applied.
        """
        new = self._clone()
        new._operations.append(Operation("flip"))
        return new

    def flop(self) -> "Thumbor":
        """Flop the image horizontally.

        Returns:
            A new instance with the flop operation applied.
        """
        new = self._clone()
        new._operations.append(Operation("flop"))
        return new

    def noise(self, amount: float) -> "Thumbor":
        """Add noise to the image.

        Args:
            amount: Amount of noise (0.0 to 100.0).

        Returns:
            A new instance with the noise filter applied.
        """
        new = self._clone()
        new._filters.append(("noise", str(amount)))
        return new

    def rgb(
        self,
        r: Optional[float] = None,
        g: Optional[float] = None,
        b: Optional[float] = None,
    ) -> "Thumbor":
        """Adjust the RGB channels of the image.

        Args:
            r: Red channel multiplier (e.g., 1.5 for 50% more red).
            g: Green channel multiplier.
            b: Blue channel multiplier.

        Returns:
            A new instance with the RGB adjustment applied.
        """
        if r is None and g is None and b is None:
            raise ValueError("At least one channel must be specified")

        parts = []
        if r is not None:
            parts.append(f"r:{r}")
        if g is not None:
            parts.append(f"g:{g}")
        if b is not None:
            parts.append(f"b:{b}")

        new = self._clone()
        new._filters.append(("rgb", ",".join(parts)))
        return new
