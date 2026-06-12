"""Détoure le logo Lumenia : fond sombre -> transparent, en gardant les lueurs douces.
Technique = luminance keying (idéal pour un logo lumineux sur fond noir)."""
from PIL import Image

SRC = "static/logo-lumenia.png"
DST = "static/logo-lumenia-cut.png"

THRESHOLD = 24   # en dessous = fond -> transparent
SCALE = 1.7      # pente de montée de l'alpha

img = Image.open(SRC).convert("RGB")
lum = img.convert("L")
alpha = lum.point(lambda v: 0 if v < THRESHOLD else min(255, int((v - THRESHOLD) * SCALE)))

out = img.convert("RGBA")
out.putalpha(alpha)

# recadre sur le contenu visible (enlève les marges transparentes)
bbox = alpha.getbbox()
if bbox:
    # petite marge de respiration autour
    pad = 16
    l, t, r, b = bbox
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(out.width, r + pad); b = min(out.height, b + pad)
    out = out.crop((l, t, r, b))

out.save(DST)
print(f"OK -> {DST}  taille {out.size}")
