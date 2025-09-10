import webbrowser

from imgora import WsrvNl

image_url = "https://wsrv.nl/puppy.jpg"

img = (
    # Imagor(base_url="http://localhost:8018", signer=Signer(key="my_key", type="sha256"))
    WsrvNl()
    .with_image(image_url)
    .crop(0.1, 0.2, 0.6, -100)
    .resize(400, 300)
    .blur(3)
    .grayscale()
    .quality(50)
)

# print(img.path()) # path without url
print(img.url())
webbrowser.open(img.url())
