"""Register RATT cascading submenu in Windows right-click context menu.

Creates nested submenus:
  RATT >
    Open RATT
    Copy to Slot  > Slot 1, Slot 2
    Cut to Slot   > Slot 1, Slot 2
    Paste from Slot > Slot 1, Slot 2
    Share
    Mirror
    Translate (Premium)
"""
import winreg
import os
import sys


def get_paths():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return {
        'app_dir': app_dir,
        'icon': os.path.join(app_dir, 'assets', 'ratt_icon.ico'),
        'vbs': os.path.join(app_dir, 'RATT.vbs'),
    }


def _delete_tree(base, path):
    try:
        with winreg.OpenKeyEx(base, path, 0, winreg.KEY_READ) as k:
            subs = []
            i = 0
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


def register_context_menu():
    paths = get_paths()
    base = winreg.HKEY_CURRENT_USER
    cmd = f'wscript.exe "{paths["vbs"]}"'
    
    unregister_context_menu(silent=True)
    
    locations = [
        r"Software\Classes\*\shell\RATT",
        r"Software\Classes\Directory\Background\shell\RATT",
        r"Software\Classes\Directory\shell\RATT",
    ]
    
    for loc in locations:
        # Parent: RATT with flyout
        with winreg.CreateKeyEx(base, loc, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "RATT")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, paths['icon'])
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
        
        shell = loc + "\\shell"
        
        # === Open RATT ===
        k = shell + "\\01_open"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Open RATT")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, paths['icon'])
        with winreg.CreateKeyEx(base, k + "\\command", 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
        
        # === Copy to Slot (nested submenu) ===
        k = shell + "\\02_copy"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Copy to Slot")
            winreg.SetValueEx(key, "CommandFlags", 0, winreg.REG_DWORD, 0x20)
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
        for i in range(1, 3):  # Basic: 2 slots shown in Explorer
            sk = k + f"\\shell\\slot{i}"
            with winreg.CreateKeyEx(base, sk, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, f"Slot {i}")
            with winreg.CreateKeyEx(base, sk + "\\command", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
        
        # === Cut to Slot (nested submenu) ===
        k = shell + "\\03_cut"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Cut to Slot")
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
        for i in range(1, 3):
            sk = k + f"\\shell\\slot{i}"
            with winreg.CreateKeyEx(base, sk, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, f"Slot {i}")
            with winreg.CreateKeyEx(base, sk + "\\command", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
        
        # === Paste from Slot (nested submenu) ===
        k = shell + "\\04_paste"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Paste from Slot")
            winreg.SetValueEx(key, "CommandFlags", 0, winreg.REG_DWORD, 0x20)
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
        for i in range(1, 3):
            sk = k + f"\\shell\\slot{i}"
            with winreg.CreateKeyEx(base, sk, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, f"Slot {i}")
            with winreg.CreateKeyEx(base, sk + "\\command", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
        
        # === Share ===
        k = shell + "\\05_share"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Share")
            winreg.SetValueEx(key, "CommandFlags", 0, winreg.REG_DWORD, 0x20)
        with winreg.CreateKeyEx(base, k + "\\command", 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
        
        # === Mirror ===
        k = shell + "\\06_mirror"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Mirror")
        with winreg.CreateKeyEx(base, k + "\\command", 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
        
        # === Translate ===
        k = shell + "\\07_translate"
        with winreg.CreateKeyEx(base, k, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Translate")
            winreg.SetValueEx(key, "CommandFlags", 0, winreg.REG_DWORD, 0x20)
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
        for code, name in [("en","English"),("fr","French"),("es","Spanish"),
                           ("de","German"),("ru","Russian"),("zh","Chinese"),
                           ("ar","Arabic"),("ja","Japanese"),("hi","Hindi")]:
            sk = k + f"\\shell\\{code}"
            with winreg.CreateKeyEx(base, sk, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, name)
            with winreg.CreateKeyEx(base, sk + "\\command", 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
    
    print("[OK] RATT nested submenu registered!")
    print()
    print("  RATT >")
    print("    Open RATT")
    print("    ----------")
    print("    Copy to Slot  > Slot 1, Slot 2")
    print("    Cut to Slot   > Slot 1, Slot 2")
    print("    ----------")
    print("    Paste from Slot > Slot 1, Slot 2")
    print("    ----------")
    print("    Share")
    print("    Mirror")
    print("    ----------")
    print("    Translate > English, French, ...")


def unregister_context_menu(silent=False):
    base = winreg.HKEY_CURRENT_USER
    for k in [
        r"Software\Classes\*\shell\RATT",
        r"Software\Classes\Directory\Background\shell\RATT",
        r"Software\Classes\Directory\shell\RATT",
    ]:
        _delete_tree(base, k)
    if not silent:
        print("[OK] RATT removed from right-click context menu.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unregister":
        unregister_context_menu()
    else:
        register_context_menu()
