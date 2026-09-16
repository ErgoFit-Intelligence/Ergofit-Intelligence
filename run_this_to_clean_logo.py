"""
Double-click this file to clean the logo transparency.

If double-click doesn't work, right-click -> Open with -> Python.
Or open Command Prompt in this folder and run:
    py run_this_to_clean_logo.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

# --- ensure Pillow ---------------------------------------------------
try:
    from PIL import Image
except ImportError:
    print("Installing Pillow ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

# --- constants -------------------------------------------------------
SRC = HERE / "logo.png"
BAK = HERE / "logo_original_backup.png"

NAVY = (35, 40, 90)
GOLD = (180, 145, 55)

def color_distance(c1, c2):
    return ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2) ** 0.5

def is_logo(r, g, b):
    return color_distance((r,g,b), NAVY) < 110 or color_distance((r,g,b), GOLD) < 110

# --- main ------------------------------------------------------------
def main():
    if not SRC.exists():
        print(f"[ERROR] {SRC} not found.")
        return

    if not BAK.exists():
        Image.open(SRC).save(BAK)
        print(f"Backup saved: {BAK.name}")

    img = Image.open(SRC).convert("RGBA")
    px = img.load()
    w, h = img.size
    kept = removed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if is_logo(r, g, b):
                px[x, y] = (r, g, b, 255)
                kept += 1
            else:
                px[x, y] = (0, 0, 0, 0)
                removed += 1

    img.save(SRC, "PNG")
    print(f"Done. Kept {kept} logo pixels, removed {removed} background pixels.")
    print(f"Saved cleaned logo to: {SRC}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
    input("\nPress Enter to close...")
