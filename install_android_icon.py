"""
install_android_icon.py — Generates all Android mipmap icon resolutions from ratt_app_icon.jpg.
"""
import os
from PIL import Image, ImageDraw

SOURCE_IMAGE = r"C:\Users\State\.gemini\antigravity\scratch\RATT\assets\ratt_app_icon.jpg"
RES_DIR = r"C:\Users\State\.gemini\antigravity\scratch\RATT\ratt\android\app\src\main\res"

SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

def make_round(img: Image.Image) -> Image.Image:
    """Create a circular masked version of the icon for ic_launcher_round."""
    size = img.size
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    round_img = Image.new('RGBA', size, (0, 0, 0, 0))
    round_img.paste(img.convert('RGBA'), (0, 0), mask=mask)
    return round_img

def main():
    print(f"Loading source icon: {SOURCE_IMAGE}")
    src = Image.open(SOURCE_IMAGE).convert("RGBA")
    
    # Also save 512x512 Play Store graphic
    os.makedirs(os.path.join(RES_DIR, "drawable"), exist_ok=True)
    play_icon = src.resize((512, 512), Image.Resampling.LANCZOS)
    play_icon.save(os.path.join(RES_DIR, "drawable", "ic_launcher.png"), "PNG")
    print("Saved 512x512 Play Store icon in res/drawable/ic_launcher.png")

    for folder, dim in SIZES.items():
        out_folder = os.path.join(RES_DIR, folder)
        os.makedirs(out_folder, exist_ok=True)
        
        # Standard Square / Squircle Icon
        resized = src.resize((dim, dim), Image.Resampling.LANCZOS)
        resized.save(os.path.join(out_folder, "ic_launcher.png"), "PNG")
        
        # Circular Icon (for Samsung One UI / Pixel Round Icon)
        rounded = make_round(resized)
        rounded.save(os.path.join(out_folder, "ic_launcher_round.png"), "PNG")
        print(f"Generated {folder}: {dim}x{dim} ic_launcher.png & ic_launcher_round.png")

    print("\nSUCCESS: All Android mipmap icons generated successfully!")

if __name__ == "__main__":
    main()
