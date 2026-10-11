"""Generate a Windows multi-resolution application icon for Nuitka builds."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "appicon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
SIZE = 256
im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((8, 8, 247, 247), radius=48, fill="#101827")
d.rounded_rectangle((26, 26, 229, 229), radius=36, outline="#4f9cf9", width=7)
# Stylized game-controller silhouette and filesystem blocks.
d.rounded_rectangle((43, 91, 213, 169), radius=33, fill="#eaf2ff")
d.rectangle((79, 109, 94, 148), fill="#142944")
d.rectangle((67, 121, 106, 136), fill="#142944")
d.ellipse((155, 111, 173, 129), fill="#2563eb")
d.ellipse((177, 132, 195, 150), fill="#2563eb")
d.rounded_rectangle((95, 185, 162, 199), radius=6, fill="#4f9cf9")
im.save(OUTPUT, format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f"Icon generated: {OUTPUT}")
