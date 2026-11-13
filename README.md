# RATT v2 — Rapid Access To Text

[![Publisher](https://img.shields.io/badge/Publisher-Cybrox-blue.svg)](https://github.com/)
[![Version](https://img.shields.io/badge/Version-v2.0.0-00BFFF.svg)](https://github.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-0078D6.svg)](https://microsoft.com)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**RATT v2** (*Rapid Access To Text*) is an enterprise multi-slot clipboard manager, workflow accelerator, and secure file/media routing platform developed by **Cybrox**. RATT replaces the standard single-item clipboard with numbered slots, instant keyboard chords, cascading shell context menus, vector/raster media preservation, non-execution security filters, and cross-platform architecture.

---

## 🚀 Key Features

* **Multi-Slot Clipboard**: from 10 up to 50,000 text slots, each with its own colour.
* **Keyboard chords** that work in any app:
  * `Ctrl + C`, then the slot number &rarr; *Copy to Slot*
  * `Ctrl + X`, then the slot number &rarr; *Cut to Slot*
  * `Ctrl + V`, then the slot number &rarr; *Paste from Slot* (Ctrl+V waits 1 second for the number, then pastes normally)
  * `Ctrl + Shift + R` &rarr; *Quick popup*
* **Right-click menu**: one `RATT` entry with Copy / Cut / Paste per slot, Share, Mirror and Translate → Language → Slot. Slots that hold data show a dot in their colour.
* **Translation**: translate a slot to another language and paste the result into your document (Premium / Enterprise).
* **Share & Mirror**: send clipboard content or mirror it to a colleague (Basic: 7-day trial).
* **Plans**: Basic (free), Premium (USD 0.99 per 10 slots / month) and Enterprise (USD 2.99 / month) with Paystack payments (Mobile Money & card).

---

## 🧩 How it is built (hybrid)

| Part | Language | Job |
|------|----------|-----|
| `ratt/` application | Python / Tkinter | windows, slots, accounts, payments, translation |
| `daemon/ratt_daemon.c` → `assets/ratt_daemon.dll` | C (run by `rundll32.exe`) | global hotkeys (`RegisterHotKey`, no keyboard hook), key injection, instant delivery of right-click actions |
| `shellext/ratt_menu.c` → `assets/ratt_menu.dll` | C | the Explorer right-click menu (a registry menu is capped at 16 entries by Windows) |

The Python app and the helper talk through a hidden window (`WM_COPYDATA`, app → helper) and a per-user named pipe (helper → app). See the comment at the top of `daemon/ratt_daemon.c` for the protocol, and [`RATT_Architecture_Plan.pdf`](RATT_Architecture_Plan.pdf) for diagrams.

> The two DLLs are unsigned. Windows Application Control / Smart App Control may refuse to load an unsigned DLL for a while (or for good). RATT retries automatically and tells you; sign the DLLs before distributing RATT.

---

## 💻 Developer Setup

### Prerequisites
* Windows 10 or 11 (64-bit), Python 3.10+
* MinGW-w64 `gcc` (for example from MSYS2) to build the two DLLs

### Run from source
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python build_native.py        # builds assets\ratt_daemon.dll and assets\ratt_menu.dll
python -m ratt.main
```

### Build the standalone executable
```powershell
.\build.bat
```
The binary is written to `dist/RATT.exe`.

### Remove the right-click menu
```powershell
python -m ratt.context_menu_updater --unregister
```

---

## 📂 Project Structure

```
RATT/
├── assets/                  # icons, logo, the two native DLLs
├── daemon/ratt_daemon.c     # helper: hotkeys, key injection, action relay
├── shellext/ratt_menu.c     # right-click menu shell extension
├── ratt/
│   ├── ui/                  # Tkinter pages, popup, styles
│   ├── actions.py           # what menu / popup / hotkey actions do
│   ├── app.py               # main window and coordinator (RattApp)
│   ├── clipboard_manager.py # thread-safe multi-slot buffer
│   ├── config.py            # plans, prices, preferences, session
│   ├── context_menu_updater.py # installs the menu extension, describes the menu
│   ├── daemon_link.py       # starts the helper, talks to it
│   ├── instance.py          # one RATT at a time
│   ├── main.py              # entry point
│   ├── native.py            # data folder, installing / loading the DLLs
│   ├── payment_gateway.py   # Paystack checkout
│   ├── translation.py       # translation
│   └── tray_icon.py         # system tray icon (pystray)
├── build.bat                # build everything
├── build_native.py          # compile the DLLs with gcc
├── RATT.spec                # PyInstaller specification
└── RATT.vbs                 # silent launcher for running from source
```

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
