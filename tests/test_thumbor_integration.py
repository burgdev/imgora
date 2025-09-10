"""Integration tests for the Thumbor client."""

from __future__ import annotations

from imgora import Signer, Thumbor

from .conftest import ServiceConfig

# Note: These tests are similar to the Imagor tests but use Thumbor-specific features
# In a real-world scenario, you would need a Thumbor server for testing


def test_thumbor_basic_operations(
    thumbor_service: ServiceConfig, test_image_url: str
) -> None:
    """Test basic Thumbor operations.

    Note: This test uses the Imagor container since it's mostly API-compatible
    for basic operations. In a real project, you'd want a Thumbor container.
    """
    # Create a Thumbor instance with the test container's configuration
    img = (
        Thumbor(signer=Signer(key=thumbor_service["secret"]))
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
    assert "/unsafe/" not in url
    assert "200x300" in url
    assert "grayscale()" in url.lower()
    assert "quality(85)" in url.lower()

    # Test the URL actually works
    # response = requests.get(url, timeout=10)
    # assert response.status_code == 200
    # assert response.headers["content-type"].startswith("image/")
