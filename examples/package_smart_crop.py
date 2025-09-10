import webbrowser

# from imgora import Imagor, Signer
from imgora import Imagor, Signer, WsrvNl

image_url = "https://wsrv.nl/puppy.jpg"

img_imagor = Imagor(base_url="http://localhost:8018", signer=Signer(unsafe=True))
img_wsrvnl = WsrvNl()

for img in [img_imagor, img_wsrvnl]:
    img = img.with_image(image_url).resize(100, 400, "fit-in")
    print(img.url())
    webbrowser.open(img.url())
