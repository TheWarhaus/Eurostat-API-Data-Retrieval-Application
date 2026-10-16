from PIL import Image
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
Image.open(os.path.join(BASE_DIR, "icon.png")).save(
    os.path.join(BASE_DIR, "src", "icons", "app.ico"),
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("app.ico written to icons\\")