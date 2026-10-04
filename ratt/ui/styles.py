"""RATT UI Styles and Theme Constants."""
import colorsys

# Color palette
BG_PRIMARY = "#1E1E1E"
BG_SECONDARY = "#2D2D2D"
BG_HOVER = "#3D3D3D"
BG_ACTIVE = "#4D4D4D"
ACCENT = "#FF6B00"
ACCENT_HOVER = "#FF8533"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B0B0B0"
TEXT_MUTED = "#707070"
BORDER = "#404040"
SUCCESS = "#4CAF50"
WARNING = "#FFC107"
ERROR = "#F44336"


def generate_slot_color(slot_num: int) -> str:
    """Generate a unique, vibrant color for any slot number.
    
    Uses the golden angle (137.5 degrees) to evenly distribute hues
    so every slot gets a visually distinct color, even with 50,000 slots.
    """
    golden_angle = 137.508
    hue = ((slot_num - 1) * golden_angle) % 360 / 360.0
    saturation = 0.7 + (((slot_num * 7) % 3) * 0.1)  # 0.7-0.9
    lightness = 0.55 + (((slot_num * 13) % 3) * 0.08)  # 0.55-0.71
    
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"


# Pre-generate first 50 colors for quick access, rest generated on demand
SLOT_COLORS = [generate_slot_color(i) for i in range(1, 51)]


def get_slot_color(slot_num: int) -> str:
    """Get color for any slot number (1-based)."""
    if slot_num <= len(SLOT_COLORS):
        return SLOT_COLORS[slot_num - 1]
    return generate_slot_color(slot_num)


# Fonts
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 16, "bold")
FONT_HEADING = (FONT_FAMILY, 12, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_MONO = ("Consolas", 10)

def apply_dark_theme(widget):
    """Apply dark theme to a tkinter widget recursively."""
    try:
        widget.configure(bg=BG_PRIMARY)
    except Exception:
        pass
    for child in widget.winfo_children():
        apply_dark_theme(child)


# RATT logo colours (sampled from the official logo)
LOGO_CYAN = "#00D5FE"
LOGO_BLUE = "#01AEFD"
LOGO_NAVY = "#16335D"
LOGO_DARK = "#04152B"   # dark text for use on LOGO_BLUE / LOGO_CYAN

