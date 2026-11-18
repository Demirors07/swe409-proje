import os
import numpy as np
from PIL import Image, ImageDraw

os.makedirs("samples", exist_ok=True)

# 1. Düz / Yumuşak Görsel (Smooth - 256x256)
smooth_data = np.linspace(0, 255, 256*256, dtype=np.uint8).reshape(256, 256)
smooth_img = Image.fromarray(smooth_data).convert("RGB")
smooth_img.save("samples/smooth_256.png")

# 2. Dokulu / Gürültülü Görsel (Textured - 512x512)
noise_data = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
textured_img = Image.fromarray(noise_data, "RGB")
textured_img.save("samples/textured_512.png")

# 3. Karma Görsel (Geometrik / Mixed - 512x512)
mixed_img = Image.new("RGB", (512, 512), color="white")
draw = ImageDraw.Draw(mixed_img)
draw.rectangle([100, 100, 400, 400], fill="blue")
draw.ellipse([200, 200, 350, 350], fill="red")
mixed_img.save("samples/mixed_512.png")

print("Test görselleri başarıyla oluşturuldu!")