"""Integration tests for the Thumbor client."""

from __future__ import annotations

import requests

from pymagor import Thumbor


# Note: These tests are similar to the Imagor tests but use Thumbor-specific features
# In a real-world scenario, you would need a Thumbor server for testing


def test_thumbor_basic_operations(thumbor_service: dict, test_image_url: str) -> None:
    """Test basic Thumbor operations.

    Note: This test uses the Imagor container since it's mostly API-compatible
    for basic operations. In a real project, you'd want a Thumbor container.
    """
    # Create a Thumbor instance with the test container's configuration
    img = (
        Thumbor(key=thumbor_service["secret"])
        .with_base(thumbor_service["base_url"])
        .with_image(test_image_url)
        .resize(200, 300)
        .grayscale()
        .quality(85)
    )

    # Generate the URL
    url = img.url()

    # Verify the URL structure
    assert url.startswith(thumbor_service["base_url"])
    assert "/unsafe/" in url or f"/{thumbor_service['secret']}/" in url
    assert "200x300" in url
    assert "grayscale()" in url.lower()
    assert "quality(85)" in url.lower()

    # Test the URL actually works
    response = requests.get(url, timeout=10)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_chaining(thumbor_service: dict, test_image_url: str) -> None:
    """Test method chaining and operation order."""
    img = (
        Thumbor(key=thumbor_service["secret"])
        .with_base(thumbor_service["base_url"])
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


def test_thumbor_flip_flop(thumbor_service: dict, test_image_url: str) -> None:
    """Test Thumbor's flip and flop operations."""
    img = (
        Thumbor(key=thumbor_service["secret"])
        .with_base(thumbor_service["base_url"])
        .with_image(test_image_url)
        .resize(100, 100)
        .flip()
        .flop()
    )

    url = img.url()
    assert "100x100/flip/flop/" in url

    response = requests.get(url, timeout=10)
    assert response.status_code == 200


def test_thumbor_rgb_adjustment(thumbor_service: dict, test_image_url: str) -> None:
    """Test RGB channel adjustments."""
    img = (
        Thumbor(key=thumbor_service["secret"])
        .with_base(thumbor_service["base_url"])
        .with_image(test_image_url)
        .resize(150, 150)
        .rgb(r=1.2, g=0.9, b=1.1)
    )

    url = img.url()
    assert "filters:rgb(r:1.2,g:0.9,b:1.1)" in url

    response = requests.get(url, timeout=10)
    assert response.status_code == 200


def test_thumbor_noise(thumbor_service: dict, test_image_url: str) -> None:
    """Test adding noise to an image."""
    img = (
        Thumbor(key=thumbor_service["secret"])
        .with_base(thumbor_service["base_url"])
        .with_image(test_image_url)
        .resize(200, 200)
        .noise(30.5)
    )

    url = img.url()
    assert "filters:noise(30.5)" in url

    response = requests.get(url, timeout=10)
    assert response.status_code == 200


def test_unsafe_url(thumbor_service: dict, test_image_url: str) -> None:
    """Test generating an unsafe URL."""
    img = (
        Thumbor()
        .with_base(thumbor_service["base_url"])
        .with_image(test_image_url)
        .resize(400, 400)
    )

    url = img.url()
    assert "/unsafe/" in url

    response = requests.get(url, timeout=10)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
