"""Pytest configuration and fixtures for imgora tests."""

from typing import TypedDict

import pytest


class ServiceConfig(TypedDict):
    host: str
    port: int
    base_url: str
    secret: str


@pytest.fixture(scope="session")
def imagor_service() -> ServiceConfig:
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
def thumbor_service() -> ServiceConfig:
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
