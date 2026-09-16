"""
Clean up the logo.png so the background is fully transparent.

The current logo has semi-transparent white/gray halos around the letters.
We keep only pixels that clearly belong to the logo (navy blue text
"Ergo" or gold text "Fit / INTELLIGENCE / lines"), and make everything
else fully transparent. Logo pixels get their alpha boosted to 255.
"""

from PIL import Image
from pathlib import Path

HERE = Path(__file__).parent
SRC  = HERE / "logo.png"
BAK  = HERE / "logo_original_backup.png"
DST  = HERE / "logo.png"

# Reference logo colors (roughly)
NAVY = (35, 40, 90)      # "Ergo"
GOLD = (180, 145, 55)    # "Fit", "INTELLIGENCE", separator lines


def color_distance(c1, c2):
    return ((c1[0] - c2[0]) ** 2
          + (c1[1] - c2[1]) ** 2
          + (c1[2] - c2[2]) ** 2) ** 0.5


def is_logo_pixel(r, g, b):
    """Return True if the pixel is clearly a logo color."""
    d_navy = color_distance((r, g, b), NAVY)
    d_gold = color_distance((r, g, b), GOLD)
    # Tolerance chosen empirically: tight enough to reject grays/whites,
    # loose enough to catch antialiased edges.
    return d_navy < 110 or d_gold < 110


def main():
    if not SRC.exists():
        print(f"[ERROR] {SRC} not found.")
        return

    # Back up the original once
    if not BAK.exists():
        Image.open(SRC).save(BAK)
        print(f"Backup saved to {BAK.name}")

    img = Image.open(SRC).convert("RGBA")
    px  = img.load()
    w, h = img.size

    kept = removed = boosted = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue  # already transparent
            if is_logo_pixel(r, g, b):
                # Boost alpha so the logo is crisp
                if a < 255:
                    px[x, y] = (r, g, b, 255)
                    boosted += 1
                kept += 1
            else:
                px[x, y] = (0, 0, 0, 0)  # fully transparent
                removed += 1

    img.save(DST, "PNG")
    print(f"Done. Kept: {kept}, Removed: {removed}, Alpha-boosted: {boosted}")
    print(f"Cleaned logo saved to {DST.name}")


if __name__ == "__main__":
    main()
