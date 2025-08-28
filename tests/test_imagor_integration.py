"""Integration tests for the Imagor client."""

from __future__ import annotations

import requests

from pymagor import Imagor


def test_basic_usage(imagor_service: dict, test_image_url: str) -> None:
    """Test basic usage of the Imagor client."""
    # Create a basic image with some operations
    img = (
        Imagor(key=imagor_service["secret"])
        .with_base(imagor_service["base_url"])
        .with_image(test_image_url)
        .resize(200, 300)
        .grayscale()
        .quality(85)
    )

    # Generate the URL
    url = img.url()

    # Verify the URL structure
    assert url.startswith(imagor_service["base_url"])
    assert "/unsafe/" in url or f"/{imagor_service['secret']}/" in url
    assert "200x300" in url
    assert "grayscale()" in url.lower()
    assert "quality(85)" in url.lower()

    # Test the URL actually works
    response = requests.get(url, timeout=10)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_imagor_unsafe_url(imagor_service: dict, test_image_url: str) -> None:
    """Test generating an unsigned URL."""
    img = (
        Imagor()
        .with_base(imagor_service["base_url"])
        .with_image(test_image_url)
        .resize(100, 100)
    )  # No key provided

    # Unsigned URL should still work since we have UNSAFE=1
    url = img.url(unsafe=True)
    response = requests.get(url, timeout=10)
    assert response.status_code == 200


def test_chaining(imagor_service: dict, test_image_url: str) -> None:
    """Test method chaining and operation order."""
    img = (
        Imagor(key=imagor_service["secret"])
        .with_base(imagor_service["base_url"])
        .with_image(test_image_url)
        .resize(100, 100)
        .grayscale()
        .blur(3)
        .quality(90)
    )

    url = img.url()
    assert "/100x100/" in url
    assert "grayscale()" in url.lower()
    assert "blur(3)" in url.lower()
    assert "quality(90)" in url.lower()

    # Verify the order of operations is preserved
    resize_idx = url.find("100x100")
    grayscale_idx = url.lower().find("grayscale()")
    blur_idx = url.lower().find("blur(")
    quality_idx = url.lower().find("quality(")

    assert resize_idx < grayscale_idx < blur_idx < quality_idx


def test_imagor_watermark(imagor_service: dict, test_image_url: str) -> None:
    """Test adding a watermark."""
    watermark_url = "https://example.com/watermark.png"
    img = (
        Imagor(key=imagor_service["secret"])
        .with_base(imagor_service["base_url"])
        .with_image(test_image_url)
        .resize(400, 300)
        .watermark(watermark_url, "center", "middle", 0.5, 0.5, 0.5)
    )

    url = img.url()
    assert "resize/400x300" in url
    assert "filters:watermark" in url

    # The actual watermark won't be applied since the URL is not accessible,
    # but we can verify the URL structure
    assert watermark_url in url


def test_imagor_format_conversion(imagor_service: dict, test_image_url: str) -> None:
    """Test converting the image format."""
    img = (
        Imagor(key=imagor_service["secret"])
        .with_base(imagor_service["base_url"])
        .with_image(test_image_url)
        .resize(200, 200)
        .format("webp")
    )

    url = img.url()
    assert "/format(webp)/" in url

    response = requests.get(url, timeout=10)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
