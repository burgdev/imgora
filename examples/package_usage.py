import webbrowser

from imgora import Imagor, Signer

# Example image from Wikipedia
image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"

# Create an Imagor processor and apply some transformations
img = (
    Imagor(base_url="http://localhost:8018", signer=Signer(key="my_key", type="sha256"))
    .with_image(image_url)
    .crop(100, 100, 200, 200)
    .resize(800, 600)  # Resize to 800x600
    .blur(3)  # Apply blur with radius 3
    .grayscale()  # Convert to grayscale
    .quality(85)  # Set quality to 85%
)

# Get and print the processed URL
print(img.path())
print(img.url())
webbrowser.open(img.url())
