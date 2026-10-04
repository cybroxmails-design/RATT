# RATT — Rapid Access To Text

[![Publisher](https://img.shields.io/badge/Publisher-Cybrox.Inc-blue.svg)](https://github.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**RATT** (*Rapid Access To Text*) is a high-performance multi-slot clipboard manager and workflow acceleration utility for Windows. Developed by **Cybrox.Inc**, RATT replaces the limitation of standard single-item clipboards with multi-slot memory buffers, sequential global keyboard chording, dynamic Windows Explorer context menu integration, inline translation, and real-time screen sharing/mirroring.

---

## 🚀 Key Features

* **Multi-Slot Clipboard Engine**: Manage from 2 up to 50,000 text slots with instant visual feedback and sub-10ms response times.
* **Global Keyboard Chording**: Perform actions without leaving your active app:
  * `Ctrl + C`, then type slot number &rarr; *Copy to Slot*
  * `Ctrl + X`, then type slot number &rarr; *Cut to Slot*
  * `Ctrl + V`, then type slot number &rarr; *Paste from Slot*
  * `Ctrl + Shift + R` &rarr; *Quick HUD Popup*
* **Dynamic Windows Shell Menu**: Cascading right-click menu in Windows Explorer dynamically reflects which slots hold data with colored dot indicators.
* **Zero Cold-Storage Privacy**: Clipboard buffers live strictly in system RAM protected by ephemeral AES-256 Fernet session keys that are purged on exit.
* **Translation Engine**: Translate copied text to 50+ languages using Google Cloud / Web endpoints.
* **Peer-to-Peer Mirror & Share**: Share clipboard contents or mirror text directly to a colleague's screen.
* **Tiered Commercial Engine**: Basic (Free), Premium, and Enterprise plans with integrated Paystack payment processing (Mobile Money & Card).

---

## 🛠️ Architecture & Documentation

* Detailed Architecture Plan: See [`RATT_Architecture_Plan.pdf`](RATT_Architecture_Plan.pdf) for layered diagrams, sequence flows, IPC models, and security breakdowns.

---

## 💻 Developer Setup & Contributing

### Prerequisites
* Windows 10 or 11 (64-bit)
* Python 3.10 or higher
* Git (or GitHub Desktop)

### Step 1: Clone the Repository
```powershell
git clone https://github.com/<your-username>/RATT.git
cd RATT
```

### Step 2: Create a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application Locally
```powershell
python -m ratt.main
```

### Step 5: (Optional) Register Windows Context Menu
To enable the cascading right-click menu in Windows Explorer:
```powershell
python -m ratt.register_context_menu
```

### Step 6: Build Standalone Executable
To package the app into a standalone `.exe` using PyInstaller:
```powershell
.\build.bat
```
The compiled binary will be placed in `dist/RATT.exe`.

---

## 📂 Project Structure

```
RATT/
├── assets/                  # Icons, graphics, dynamic dot indicators
├── ratt/                    # Main application package
│   ├── ui/                  # Tkinter UI pages, HUD popup, styles
│   ├── app.py               # Central coordinator (RattApp)
│   ├── clipboard_manager.py # Thread-safe multi-slot buffer
│   ├── config.py            # User tiers, preferences, sessions
│   ├── context_menu_updater.py # Registry sync daemon
│   ├── encryption.py        # Ephemeral AES-256 crypto layer
│   ├── hotkey_listener.py   # Global keyboard chord state machine
│   ├── main.py              # Entry point & loopback socket IPC
│   ├── payment_gateway.py   # Paystack checkout integration
│   ├── register_context_menu.py # Windows registry setup
│   ├── sync.py              # Cross-device synchronization stub
│   ├── translation.py       # Cloud translation integration
│   └── tray_icon.py         # System tray daemon (pystray)
├── build.bat                # PyInstaller packaging script
├── generate_icon.py         # Asset generator script
├── requirements.txt         # Python package dependencies
├── RATT.spec                # PyInstaller specification
└── RATT.vbs                 # Silent background shell runner
```

---

## 🤝 Contributing

Contributions from the developer community are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, branching conventions, and pull request procedures.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
