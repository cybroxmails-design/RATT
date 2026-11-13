"""Right-click menu: one "RATT" entry with everything cascading under it.

    RATT >  Open RATT
            Copy to Slot  > Slot 1 ... Slot N        (N = slots on the user's plan)
            Cut to Slot   > Slot 1 ... Slot N
            Paste from Slot > slots that hold data
            Share / Mirror                            (Basic: 7-day trial, then greyed out)
            Translate > Language > Slot               (Premium / Enterprise)

A slot that holds data gets a dot in the same colour it has in the RATT window; the dot
disappears when the slot is cleared.

How it works: Windows limits a menu made of registry entries to 16 entries in total, far
too few. So the menu is drawn by a small shell extension (assets\ratt_menu.dll, source in
shellext\ratt_menu.c) that reads %APPDATA%\RATT\menu_state.txt. This module installs the
extension once and rewrites that text file whenever the slots or the plan change.

    python -m ratt.context_menu_updater --unregister      removes the menu again
"""
import os
import sys
import threading
import winreg

from ratt import native

CLSID = "{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}"
HANDLER_KEYS = [
    r"Software\Classes\*\shellex\ContextMenuHandlers\RATT",
    r"Software\Classes\Directory\shellex\ContextMenuHandlers\RATT",
    r"Software\Classes\Directory\Background\shellex\ContextMenuHandlers\RATT",
]
# Registry-only menus written by earlier versions of RATT; removed so they don't show twice.
OLD_MENU_KEYS = [
    rf"Software\Classes\{place}\shell\{name}"
    for place in ("*", "Directory", r"Directory\Background")
    for name in ("RATT", "RATT_02_copy", "RATT_03_cut", "RATT_04_translate")
]

MENU_CAP = 40              # slots listed per submenu, then "More slots..."
RETRY_SECONDS = 60         # while Windows refuses to load the (unsigned) extension

_lock = threading.Lock()
_last_state = None


# ---- state -------------------------------------------------------------------------

def build_state(config, clipboard_manager=None):
    """Everything the menu depends on, as plain comparable values."""
    from ratt.config import TRANSLATE_LANGUAGES
    user = config.user
    filled = tuple(sorted(clipboard_manager.get_all_slots())) if clipboard_manager else ()
    return {
        "enabled": bool(getattr(config, "enabled", True)),
        "num_slots": int(config.max_slots),
        "filled": filled,
        "premium": bool(config.is_premium),
        "trial_active": bool(user.is_trial_active),
        "trial_days": int(user.trial_days_remaining),
        "languages": tuple(TRANSLATE_LANGUAGES),
    }


def update_context_menu(config, clipboard_manager):
    """Called by the app whenever slots or plan change. The snapshot is taken on the
    caller's thread; the file and registry work happens in the background."""
    try:
        state = build_state(config, clipboard_manager)
    except Exception as error:
        native.log("menu", f"snapshot failed: {error!r}")
        return
    threading.Thread(target=_apply, args=(state,), daemon=True).start()


def _apply(state):
    global _last_state
    with _lock:
        if state == _last_state:
            return
        try:
            _write_state_file(state)
            dll = native.install("ratt_menu.dll")
            _register(dll)
            if native.can_load(dll):
                _remove_old_menus()
                _last_state = state
            else:
                if state.get("enabled", True):
                    _register_fallback_menus(state)
                else:
                    _remove_old_menus()
                raise OSError("Windows refused to load the menu extension (Application Control); using registry menu fallback")
        except Exception as error:
            native.log("menu", f"menu not updated, retrying: {error!r}")
            timer = threading.Timer(RETRY_SECONDS, _apply, args=(state,))
            timer.daemon = True
            timer.start()


# ---- the menu description read by the extension --------------------------------------

def _logo_file():
    """64x64 premultiplied BGRA copy of the RATT logo (the extension scales it)."""
    import struct
    from PIL import Image
    path = os.path.join(native.data_dir(), "ratt_menu_logo.raw")
    if not os.path.exists(path):
        image = Image.open(os.path.join(native.assets_dir(), "ratt_icon.png")).convert("RGBA").resize((64, 64))
        data = bytearray(struct.pack("<II", 64, 64))
        for r, g, b, a in image.getdata():
            data += bytes((b * a // 255, g * a // 255, r * a // 255, a))
        with open(path, "wb") as f:
            f.write(data)
    return path


def _write_state_file(state):
    """Line format (tab separated) is documented at the top of shellext\\ratt_menu.c."""
    path = os.path.join(native.data_dir(), "menu_state.txt")
    if not state.get("enabled", True):
        with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            f.write("DISABLED\n")
        os.replace(path + ".tmp", path)
        return

    from ratt.ui.styles import get_slot_color
    filled = list(state["filled"])
    all_slots = list(range(1, state["num_slots"] + 1))
    program, prefix = native.launch_command()
    lines = [f"LAUNCH\t{program}\t{prefix}", f"LOGO\t{_logo_file()}"]

    def add(depth, kind, label, args="-", dot="-"):
        """kind: M = submenu, I = item, D = disabled item"""
        lines.append(f"ITEM\t{depth}\t{kind}\t{dot}\t{args}\t{label}")

    def add_slots(depth, numbers, action, language=None):
        for n in numbers[:MENU_CAP]:
            args = f"{action} {language} {n}" if language else f"{action} {n}"
            add(depth, "I", f"Slot {n}", args, get_slot_color(n).lstrip("#") if n in filled else "-")
        if len(numbers) > MENU_CAP:
            add(depth, "I", "More slots... (open RATT)", "popup")

    add(0, "I", "Open RATT", "open")
    add(0, "M", "Copy to Slot")
    add_slots(1, all_slots, "copy")
    add(0, "M", "Cut to Slot")
    add_slots(1, all_slots, "cut")
    add(0, "M", "Paste from Slot")
    if filled:
        add_slots(1, filled, "paste")
    else:
        add(1, "D", "(no slot has data yet)")

    for name, action in (("Share", "share"), ("Mirror", "mirror")):
        days = state["trial_days"]
        if state["premium"]:
            add(0, "I", name, action)
        elif state["trial_active"]:
            add(0, "I", f"{name} ({days} day{'s' if days != 1 else ''} left)", action)
        else:
            add(0, "D", f"{name} (trial ended)")

    if state["premium"]:
        add(0, "M", "Translate")
        for code, language in state["languages"]:
            add(1, "M", language)
            if filled:
                add_slots(2, filled, "translate", code)
            else:
                add(2, "D", "(no slot has data yet)")
        add(0, "M", "Android Keyboard (IME)")
        add_slots(1, all_slots, "android-copy")
        add(0, "M", "iOS Keyboard (iPhone)")
        add_slots(1, all_slots, "ios-copy")
    else:
        add(0, "D", "Translate (Premium / Enterprise)")
        add(0, "I", "Android Keyboard (Premium / Enterprise)", "android")
        add(0, "I", "iOS Keyboard (Premium / Enterprise)", "ios")

    path = os.path.join(native.data_dir(), "menu_state.txt")
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(path + ".tmp", path)


# ---- registry ----------------------------------------------------------------------

def _set(path, **values):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
        for name, value in values.items():
            winreg.SetValueEx(key, "" if name == "default" else name, 0, winreg.REG_SZ, value)


def _delete_tree(path):
    try:
        with winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
            children = []
            while True:
                try:
                    children.append(winreg.EnumKey(key, len(children)))
                except OSError:
                    break
        for child in children:
            _delete_tree(path + "\\" + child)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def _should_register_hkcu() -> bool:
    """Skip HKCU registration when a system-wide Program Files installation already owns the CLSID."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"Software\Classes\CLSID\{CLSID}\InProcServer32") as k:
            val, _ = winreg.QueryValueEx(k, "")
            if isinstance(val, str) and "program files" in val.lower():
                return False
    except OSError:
        pass
    return True


def _register(dll):
    """Point Explorer's context-menu handlers (files, folders, folder background) at the DLL."""
    if not _should_register_hkcu():
        return
    _set(rf"Software\Classes\CLSID\{CLSID}", default="RATT right-click menu")
    _set(rf"Software\Classes\CLSID\{CLSID}\InProcServer32", default=dll, ThreadingModel="Apartment")
    for key in HANDLER_KEYS:
        _set(key, default=CLSID)


def _remove_old_menus():
    for key in OLD_MENU_KEYS:
        _delete_tree(key)


def _register_fallback_menus(state):
    """Fallback Windows Registry cascading menu if Smart App Control blocks the COM DLL."""
    program, prefix = native.launch_command()
    icon = os.path.join(native.assets_dir(), "ratt_icon.ico")
    cmd_base = f'"{program}" {prefix}'.strip()
    for place in ("*", "Directory", r"Directory\Background"):
        root = rf"Software\Classes\{place}\shell\RATT"
        _set(root, MUIVerb="RATT", Icon=icon, SubCommands="")
        _set(rf"{root}\shell\01_open", MUIVerb="Open RATT", Icon=icon)
        _set(rf"{root}\shell\01_open\command", default=f"{cmd_base} open")
        _set(rf"{root}\shell\02_popup", MUIVerb="RATT Slots Menu (Copy / Cut / Paste)")
        _set(rf"{root}\shell\02_popup\command", default=f"{cmd_base} popup")
        for idx in range(1, min(state["num_slots"], 10) + 1):
            _set(rf"{root}\shell\1{idx:02d}_copy", MUIVerb=f"Copy to Slot {idx}")
            cmd = f'{cmd_base} copy {idx} "%1"' if place != r"Directory\Background" else f"{cmd_base} copy {idx}"
            _set(rf"{root}\shell\1{idx:02d}_copy\command", default=cmd)
        for idx in list(state["filled"])[:5]:
            _set(rf"{root}\shell\2{idx:02d}_paste", MUIVerb=f"Paste from Slot {idx}")
            cmd = f'{cmd_base} paste {idx} "%1"' if place != r"Directory\Background" else f"{cmd_base} paste {idx}"
            _set(rf"{root}\shell\2{idx:02d}_paste\command", default=cmd)


def unregister():
    """Remove RATT from the right-click menu completely."""
    for key in HANDLER_KEYS:
        _delete_tree(key)
    _delete_tree(rf"Software\Classes\CLSID\{CLSID}")
    _remove_old_menus()


if __name__ == "__main__":
    if "--unregister" in sys.argv:
        unregister()
        print("RATT removed from the right-click menu.")
    else:
        print(__doc__)
