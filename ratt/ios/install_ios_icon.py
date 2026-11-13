"""
install_ios_icon.py — Generates Apple iOS AppIcon.appiconset assets from the master 1024x1024 icon.
Supports iPhone 17 Pro Max (@3x Super Retina), App Store master (1024x1024), and Xcode 15/16.
"""
import os
import json
from PIL import Image

SOURCE_ICON = r"C:\Users\State\.gemini\antigravity\scratch\RATT\assets\ratt_ios_app_icon.png"
FALLBACK_ICON = r"C:\Users\State\.gemini\antigravity\scratch\RATT\assets\ratt_app_icon.jpg"
APP_ASSETS_DIR = r"C:\Users\State\.gemini\antigravity\scratch\RATT\ratt\ios\RattApp\Assets.xcassets\AppIcon.appiconset"

IOS_SIZES = [
    # Universal App Store (Master)
    {"size": "1024x1024", "idiom": "universal", "platform": "ios", "scale": "1x", "filename": "AppIcon-1024.png", "px": 1024},
    # iPhone Home Screen (@3x for iPhone 17 Pro Max, @2x for standard)
    {"size": "60x60", "idiom": "iphone", "scale": "3x", "filename": "AppIcon-60@3x.png", "px": 180},
    {"size": "60x60", "idiom": "iphone", "scale": "2x", "filename": "AppIcon-60@2x.png", "px": 120},
    # iPhone Spotlight Search
    {"size": "40x40", "idiom": "iphone", "scale": "3x", "filename": "AppIcon-40@3x.png", "px": 120},
    {"size": "40x40", "idiom": "iphone", "scale": "2x", "filename": "AppIcon-40@2x.png", "px": 80},
    # iPhone Settings
    {"size": "29x29", "idiom": "iphone", "scale": "3x", "filename": "AppIcon-29@3x.png", "px": 87},
    {"size": "29x29", "idiom": "iphone", "scale": "2x", "filename": "AppIcon-29@2x.png", "px": 58},
    # iPhone Notifications
    {"size": "20x20", "idiom": "iphone", "scale": "3x", "filename": "AppIcon-20@3x.png", "px": 60},
    {"size": "20x20", "idiom": "iphone", "scale": "2x", "filename": "AppIcon-20@2x.png", "px": 40},
]

def install(src_path: str = None):
    chosen = src_path or (SOURCE_ICON if os.path.exists(SOURCE_ICON) else FALLBACK_ICON)
    if not os.path.exists(chosen):
        print(f"Error: Source image not found at {chosen}")
        return False

    print(f"Loading master iOS icon: {chosen}")
    img = Image.open(chosen).convert("RGBA")

    os.makedirs(APP_ASSETS_DIR, exist_ok=True)

    images_meta = []
    for entry in IOS_SIZES:
        dim = entry["px"]
        fn = entry["filename"]
        out_path = os.path.join(APP_ASSETS_DIR, fn)
        resized = img.resize((dim, dim), Image.Resampling.LANCZOS)
        resized.save(out_path, "PNG")
        print(f"Generated {fn}: {dim}x{dim} px")
        
        meta = {
            "idiom": entry["idiom"],
            "size": entry["size"],
            "scale": entry["scale"],
            "filename": fn
        }
        if "platform" in entry:
            meta["platform"] = entry["platform"]
        images_meta.append(meta)

    contents_json = {
        "images": images_meta,
        "info": {
            "author": "xcode",
            "version": 1
        }
    }

    with open(os.path.join(APP_ASSETS_DIR, "Contents.json"), "w", encoding="utf-8") as f:
        json.dump(contents_json, f, indent=2)
    print("Saved Contents.json in AppIcon.appiconset")

    # Also save an Assets.xcassets root Contents.json
    root_contents = {"info": {"author": "xcode", "version": 1}}
    with open(os.path.join(r"C:\Users\State\.gemini\antigravity\scratch\RATT\ratt\ios\RattApp\Assets.xcassets", "Contents.json"), "w", encoding="utf-8") as f:
        json.dump(root_contents, f, indent=2)

    print("\nSUCCESS: All iOS AppIcon assets installed successfully!")
    return True

if __name__ == "__main__":
    import sys
    custom = sys.argv[1] if len(sys.argv) > 1 else None
    install(custom)
