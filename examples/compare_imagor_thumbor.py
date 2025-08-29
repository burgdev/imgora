import os
import tempfile
import webbrowser
from pathlib import Path

from pymagor import Imagor, Signer, Thumbor, WsrvNl

# Configuration
BASE_URL_IMAGOR = "http://localhost:8018"
BASE_URL_THUMBOR = "http://localhost:8019"
BASE_URL_WSRVN = "http://wsrv.nl"
SIGNER_IMAGOR = Signer(key="my_key", type="sha256")
SIGNER_THUMBOR = Signer(key="my_key", type="sha1")

# Example image from Wikipedia
IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/800px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
# IMAGE_URL = "https://raw.githubusercontent.com/cshum/imagor/master/testdata/gopher.png"

# Create output directory
output_dir = Path(tempfile.gettempdir()) / "pymagor_comparison"
os.makedirs(output_dir, exist_ok=True)

# HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Imagor vs Thumbor Comparison</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .comparison {{ margin-bottom: 40px; }}
        h2 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        .image-container {{ margin: 10px 0; }}
        .caption {{ font-size: 14px; color: #666; margin: 5px 0; }}
        img {{ max-width: 100%; border: 1px solid #ddd; }}
        .original {{ grid-column: 1 / -1; }}
    </style>
</head>
<body>
    <h1>Imagor vs Thumbor Comparison</h1>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""


def create_image_grid(transformations):
    """Generate HTML content for the image grid."""
    rows = []

    # Add original image
    rows.append(
        f'<div class="original">'
        f"<h2>Original Image</h2>"
        f'<div class="image-container">'
        f'<img src="{IMAGE_URL}" alt="Original">'
        f'<div class="caption">Source: {IMAGE_URL}</div>'
        f"</div>"
        f"</div>"
    )

    # Add transformed images
    for name, imagor_url, thumbor_url, wsrvnl_url in transformations:
        rows.append(
            f'<div class="comparison">'
            f"<h2>{name}</h2>"
            '<div style="display: flex; gap: 20px;">'
            f'<div class="image-container" style="flex: 1;">'
            f'<img src="{imagor_url}" alt="Imagor">'
            f'<div class="caption">Imagor</div>'
            f"</div>"
            f'<div class="image-container" style="flex: 1;">'
            f'<img src="{thumbor_url}" alt="Thumbor">'
            f'<div class="caption">Thumbor</div>'
            f"</div>"
            f'<div class="image-container" style="flex: 1;">'
            f'<img src="{wsrvnl_url}" alt="Wsrv.nl">'
            f'<div class="caption">Wsrv.nl</div>'
            f"</div>"
            "</div>"
            f"</div>"
        )

    return HTML_TEMPLATE.format(content="\n".join(rows))


def save_html(content, filename="comparison.html"):
    """Save HTML content to a file and open it in the browser."""
    filepath = output_dir / filename
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


def main():
    # Define transformations to compare
    imagor_image = Imagor(BASE_URL_IMAGOR, signer=SIGNER_IMAGOR).with_image(IMAGE_URL)
    thumbor_image = Thumbor(BASE_URL_THUMBOR, signer=SIGNER_THUMBOR).with_image(
        IMAGE_URL
    )
    wsrvnl_image = WsrvNl(BASE_URL_WSRVN).with_image(IMAGE_URL)
    images = imagor_image, thumbor_image, wsrvnl_image
    transformations = [
        (
            "Resize and Crop",
            *(img.crop(100, 100, 500, 400).resize(400, 300).url() for img in images),
        ),
        (
            "Blur",
            *(img.resize(400, 300).blur(3).url() for img in images),
        ),
        (
            "Rounded Corners",
            *(
                img.resize(300, 200).round_corner(50, color="#ff0000").url()
                for img in images
            ),
        ),
        (
            "Fit in with Background",
            *(img.fit_in(300, 300).background_color("#0000ff").url() for img in images),
        ),
    ]

    # Generate and save HTML
    html_content = create_image_grid(transformations)
    output_file = save_html(html_content)

    # Open in browser
    print(f"Opening comparison in browser: {output_file}")
    webbrowser.open(f"file://{output_file}")


if __name__ == "__main__":
    main()
