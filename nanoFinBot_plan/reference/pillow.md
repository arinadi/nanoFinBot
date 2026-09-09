# Pillow 10.x — reference (image preprocessing)

Pin major 10. Use for downscaling/deskewing photos before the vision call.

```python
from PIL import Image
import io

img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
img.thumbnail((768, 768))                     # keeps aspect ratio, caps at 768px
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=85)      # keep payload < ~500KB
img_bytes = buf.getvalue()
```

Why 768px (from Phase 0 research): Gemini vision tiles images on a 768px grid; an image
≤768px on both sides is a single 258-token tile. Crossing 768px adds a whole extra tile,
so capping there minimizes token cost without hurting legibility.

`thumbnail` never upscales; small photos pass through unchanged. Convert to RGB so
RGBA/PNG screenshots don't error on JPEG save.
