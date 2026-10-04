"""Dynamic right-click menu updater.

Keeps the Windows "RATT >" menu in sync with the app and makes every entry do something:

  * Copy / Cut to Slot  - one entry per slot of the user's plan
  * Paste from Slot     - only slots that currently hold data
  * Share / Mirror      - 7-day trial countdown for Basic, greyed out afterwards
  * Translate           - Premium/Enterprise: pick a language, RATT translates the
                          active slot (last slot used) and pastes it into the document
  * a coloured dot icon marks every slot that has data (same colour as in RATT);
    it disappears when the slot is cleared

Each entry launches RATT.vbs with an action ("copy 3", "translate fr", ...). The running
RATT instance receives it and performs the action.

Windows limits a cascading menu to about 16 entries, so plans with more slots list the
first 15 plus "More slots..." (opens the RATT popup, which lists every slot).
"""
import os
import sys
import threading
import time
import winreg

_lock = threading.Lock()
_last_state = None

MAX_ENTRIES = 16
_LOCATIONS = [
    r"Software\Classes\*\shell\RATT",
    r"Software\Classes\Directory\Background\shell\RATT",
    r"Software\Classes\Directory\shell\RATT",
]


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _log(msg):
    try:
        folder = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RATT")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "menu.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except Exception:
        pass


def update_context_menu(config, clipboard_manager):
    """Snapshot state on the caller's thread, then rewrite the registry in the background."""
    try:
        from ratt.config import TRANSLATE_LANGUAGES
        user = config.user
        state = {
            "num_slots": int(config.max_slots),
            "filled": tuple(sorted(clipboard_manager.get_all_slots().keys())),
            "active": clipboard_manager.active_slot(),
            "premium": bool(config.is_premium),
            "trial_active": bool(user.is_trial_active),
            "trial_days": int(user.trial_days_remaining),
            "languages": tuple(TRANSLATE_LANGUAGES),
        }
    except Exception as e:
        _log(f"snapshot failed: {e!r}")
        return
    threading.Thread(target=_do_update, args=(state,), daemon=True).start()


def _make_dot_icon(color_hex):
    """Create (once) a small round dot .ico in the given colour and return its path."""
    from PIL import Image, ImageDraw
    folder = os.path.join(_app_dir(), "assets", "dots")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"dot_{color_hex.lstrip('#').lower()}.ico")
    if os.path.exists(path):
        return path
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(S * 0.18)
    d.ellipse([pad, pad, S - pad, S - pad], fill=color_hex)
    img.save(path, format="ICO", sizes=[(16, 16), (20, 20), (24, 24), (32, 32)])
    return path


def _delete_tree(base, path):
    try:
        with winreg.OpenKeyEx(base, path, 0, winreg.KEY_READ) as k:
            subs, i = [], 0
            while True:
                try:
                    subs.append(winreg.EnumKey(k, i))
                    i += 1
                except OSError:
                    break
        for s in subs:
            _delete_tree(base, path + "\\" + s)
        winreg.DeleteKey(base, path)
    except FileNotFoundError:
        pass


def _del_value(base, path, name):
    try:
        with winreg.OpenKeyEx(base, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except (FileNotFoundError, OSError):
        pass


def _set_values(base, path, **vals):
    with winreg.CreateKeyEx(base, path, 0, winreg.KEY_WRITE) as k:
        for name, v in vals.items():
            if isinstance(v, int):
                winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, v)
            else:
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, v)


def _entry(base, parent_shell, key, label, cmd, icon=None, disabled=False):
    path = f"{parent_shell}\\{key}"
    _set_values(base, path, MUIVerb=label)
    if icon:
        _set_values(base, path, Icon=icon)
    else:
        _del_value(base, path, "Icon")
    if disabled:
        _set_values(base, path, LegacyDisable="")
    else:
        _del_value(base, path, "LegacyDisable")
    _set_values(base, path + "\\command", **{"": cmd})


def _rebuild_slot_menu(base, menu_key, action, numbers, filled, icons, C, placeholder=None):
    """(Re)create a Slot submenu. An EMPTY cascading menu makes Windows drop it (and
    can swallow the entries after it), so we always leave at least one entry."""
    shell_path = menu_key + "\\shell"
    _delete_tree(base, shell_path)
    _set_values(base, menu_key, SubCommands="")
    numbers = list(numbers)
    more = len(numbers) > MAX_ENTRIES
    shown = numbers[:MAX_ENTRIES - 1] if more else numbers
    for n in shown:
        _entry(base, shell_path, f"slot{n:05d}", f"Slot {n}", C(action, n),
               icon=icons.get(n) if n in filled else None)
    if more:
        _entry(base, shell_path, "zz_more", "More slots... (open RATT)", C("popup"))
    if not shown and placeholder:
        _entry(base, shell_path, "slot00000", placeholder, C("open"), disabled=True)


def _do_update(state):
    global _last_state
    with _lock:
        comparable = {k: v for k, v in state.items() if k != "_retry"}
        if comparable == _last_state:
            return
        errors = []
        base = winreg.HKEY_CURRENT_USER
        vbs = os.path.join(_app_dir(), "RATT.vbs")

        def C(*args):
            return f'wscript.exe "{vbs}" ' + " ".join(str(a) for a in args)

        def step(_what, fn, *a, **k):
            try:
                fn(*a, **k)
            except Exception as e:  # keep going: one failure must not hide the other entries
                errors.append(f"{_what}: {e!r}")

        filled = set(state["filled"])
        from ratt.ui.styles import get_slot_color
        icons = {}
        for n in filled:
            try:
                icons[n] = _make_dot_icon(get_slot_color(n))
            except Exception as e:
                errors.append(f"icon {n}: {e!r}")

        copy_nums = list(range(1, state["num_slots"] + 1))
        paste_nums = sorted(filled)
        active = state["active"]

        for loc in _LOCATIONS:
            shell = loc + "\\shell"

            step("open", _entry_leaf, base, shell + "\\01_open", C("open"))
            step("copy", _rebuild_slot_menu, base, shell + "\\02_copy", "copy", copy_nums, filled, icons, C)
            step("cut", _rebuild_slot_menu, base, shell + "\\03_cut", "cut", copy_nums, filled, icons, C)
            step("paste", _rebuild_slot_menu, base, shell + "\\04_paste", "paste", paste_nums, filled, icons, C,
                 placeholder="(no slot has data yet)")

            # Share / Mirror: Basic = 7-day trial countdown, then greyed out
            for key, name, action in (("05_share", "Share", "share"), ("06_mirror", "Mirror", "mirror")):
                if state["premium"]:
                    label, disabled = name, False
                elif state["trial_active"]:
                    d = state["trial_days"]
                    label, disabled = f"{name} ({d} day{'s' if d != 1 else ''} left)", False
                else:
                    label, disabled = f"{name} (trial ended)", True
                step(name, _entry_leaf, base, shell + "\\" + key, C(action), label=label, disabled=disabled)

            # Translate: Premium / Enterprise, acts on the active slot
            step("translate", _build_translate, base, shell + "\\07_translate", state, active, C)

        if errors:
            _log("update errors: " + " | ".join(errors))
            if not state.get("_retry"):
                t = threading.Timer(3.0, _do_update, args=(dict(state, _retry=True),))
                t.daemon = True
                t.start()
            return
        _last_state = comparable


def _entry_leaf(base, path, cmd, label=None, disabled=False):
    """A plain (non-cascading) menu entry with a command."""
    if label:
        _set_values(base, path, MUIVerb=label)
    if disabled:
        _set_values(base, path, LegacyDisable="")
    else:
        _del_value(base, path, "LegacyDisable")
    _set_values(base, path + "\\command", **{"": cmd})


def _build_translate(base, tpath, state, active, C):
    if state["premium"] and active is not None:
        _delete_tree(base, tpath + "\\command")      # a cascading entry has no command of its own
        _delete_tree(base, tpath + "\\shell")
        _set_values(base, tpath, MUIVerb=f"Translate Slot {active}", SubCommands="")
        _del_value(base, tpath, "LegacyDisable")
        for code, lang in state["languages"]:
            _entry(base, tpath + "\\shell", code, lang, C("translate", code))
    else:
        _delete_tree(base, tpath + "\\shell")
        _del_value(base, tpath, "SubCommands")
        label = ("Translate (Premium / Enterprise)" if not state["premium"]
                 else "Translate (no slot has data yet)")
        _set_values(base, tpath, MUIVerb=label, LegacyDisable="")
        _set_values(base, tpath + "\\command", **{"": C("open")})
