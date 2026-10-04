"""Generate RATT application icon."""
import os
from PIL import Image, ImageDraw, ImageFont


def create_icon():
    """Create the RATT icon in multiple sizes."""
    os.makedirs('assets', exist_ok=True)
    
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background circle - orange
        margin = max(1, size // 32)
        draw.ellipse(
            [margin, margin, size - margin - 1, size - margin - 1],
            fill='#FF6B00'
        )
        
        # Draw "R" letter
        try:
            font_size = int(size * 0.55)
            font = ImageFont.truetype("arial.ttf", size=font_size)
        except (IOError, OSError):
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()
        
        text = "R"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) // 2
        y = (size - text_h) // 2 - bbox[1]
        
        draw.text((x, y), text, fill='white', font=font)
        images.append(img)
    
    # Save as .ico
    ico_path = 'assets/ratt_icon.ico'
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"[OK] Icon saved to {ico_path}")
    
    # Also save as PNG (for fallback)
    png_path = 'assets/ratt_icon.png'
    images[-1].save(png_path, format='PNG')  # Save largest size
    print(f"[OK] PNG saved to {png_path}")


if __name__ == '__main__':
    create_icon()
