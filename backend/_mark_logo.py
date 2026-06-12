"""Génère le petit 'mark' Lumenia (luciole + anneau, sans le texte) à partir du logo
détouré, pour la sidebar / cartes / avatars / favicon."""
from PIL import Image, ImageDraw, ImageEnhance

CUT = "static/logo-lumenia-cut.png"          # logo complet détouré (transparent)
MARK = "static/logo-mark.png"                # luciole + anneau, transparent
FAV = "static/logo-favicon.png"              # mark sur pastille sombre, pour le favicon

src = Image.open(CUT).convert("RGBA")
W, H = src.size  # ~1248 x 1254

# --- recadrage sur la luciole + l'anneau (haut-centre du lockup) ---
# valeurs proportionnelles, ajustables
l = int(W * 0.27); r = int(W * 0.73)
t = int(H * 0.06); b = int(H * 0.50)
mark = src.crop((l, t, r, b))

# carré : on pad pour centrer dans un carré transparent
side = max(mark.size)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2), mark)

# éclaircir : la luciole est pâle, sinon trop sombre sur la pastille foncée
r, g, b, a = sq.split()
rgb = ImageEnhance.Brightness(Image.merge("RGB", (r, g, b))).enhance(1.5)
rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
r, g, b = rgb.split()
a = a.point(lambda v: min(255, int(v * 1.3)))
sq = Image.merge("RGBA", (r, g, b, a))

sq.save(MARK)
print(f"mark -> {MARK} {sq.size}")

# --- favicon : pastille violette arrondie + mark centré ---
S = 128
fav = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(fav)
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=30, fill=(34, 22, 56, 255))
m = sq.resize((int(S * 0.82), int(S * 0.82)), Image.LANCZOS)
fav.paste(m, ((S - m.width) // 2, (S - m.height) // 2), m)
fav.save(FAV)
print(f"favicon -> {FAV} {fav.size}")
