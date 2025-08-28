"""Pytest configuration and fixtures for pymagor tests."""

import pytest


@pytest.fixture(scope="session")
def imagor_service() -> dict:
    """Get Imagor service configuration from docker-compose.

    Returns:
        dict: Service configuration including host and port.
    """
    return {
        "host": "localhost",
        "port": 8000,
        "base_url": "http://localhost:8000",
        "secret": "test-secret",
    }


@pytest.fixture(scope="session")
def thumbor_service() -> dict:
    """Get Thumbor service configuration from docker-compose.

    Returns:
        dict: Service configuration including host and port.
    """
    return {
        "host": "localhost",
        "port": 8888,
        "base_url": "http://localhost:8888",
        "secret": "test-secret",
    }


@pytest.fixture
def test_image_url() -> str:
    """Return a URL to a test image."""
    return "https://raw.githubusercontent.com/cshum/imagor/develop/testdata/gopher.png"
