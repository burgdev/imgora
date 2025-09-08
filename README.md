<h3 align="center"><b>Imgora</b></h3>
<p align="center">
  <a href="https://burgdev.github.io/imgora"><img src="https://via.placeholder.com/80" alt="Imgora" width="80" /></a>
</p>
<p align="center">
    <em>Chainable Python client for Imagor and Thumbor image processing servers</em>
</p>
<p align="center">
    <b><a href="https://burgdev.github.io/imgora/docu/">Documentation</a></b>
    | <b><a href="https://pypi.org/project/imgora/">PyPI</a></b>
</p>

---

**Imgora** provides a clean, chainable interface for generating image URLs for [Imagor](https://github.com/cshum/imagor), [Thumbor](https://github.com/thumbor/thumbor) and [Wsrv.nl](https://wsrv.nl) image processing servers. It supports all standard operations and filters with full type hints and documentation.

## Features

- **[Imagor](https://github.com/cshum/imagor), [Thumbor](https://github.com/thumbor/thumbor) & [Wsrv.nl](https://wsrv.nl) Support**: Compatible with Imagor, Thumbor and Wsrv.nl servers
- **URL Signing**: Built-in support for secure URL signing
- **Chainable API**: Fluent interface for building complex image processing pipelines
- **Comprehensive Filter Support**: Implements all standard filters and operations
- **Fully Typed**: Built with Python's type hints for better IDE support and code quality

## Installation

Using [uv](https://github.com/astral-sh/uv) (recommended):
```bash
uv pip install imgora
```

Or with pip:
```bash
pip install imgora
```

## Quick Start

```python
from imgora import Imagor

# Create and configure an image processor
img = (
    Imagor(key="your-secret-key")
    .with_base("https://your-imagor-server.com")
    .with_image("path/to/image.jpg")
    .fit_in(300, 300)
    .blur(3)
)

# Generate the URL
url = img.url()
print(f"Generated URL: {url}")
```

## Documentation

For complete documentation, including API reference and advanced usage, please visit the [documentation site](https://burgdev.github.io/imgora/docu/).

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/burgdev/imgora.git
cd imgora

# Install development dependencies
make
uv run invoke install # install 'dev' and 'test' dependencies per default, use --all to install all dependencies
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT - See [LICENSE](LICENSE) for details.
