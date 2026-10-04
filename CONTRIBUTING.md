# Contributing to RATT

Thank you for your interest in contributing to **RATT (Rapid Access To Text)**! 

---

## 🧭 Getting Started

1. **Fork the Repository** on GitHub to your personal account.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<your-username>/RATT.git
   cd RATT
   ```
3. Set up a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

---

## 🌿 Branching Strategy

* Create feature or bugfix branches off of `main`:
  * `feature/your-feature-name` (for new capabilities or enhancements)
  * `bugfix/issue-description` (for bug fixes)
  * `docs/documentation-update` (for documentation improvements)

---

## 💻 Development Guidelines

* **Code Style**: Follow PEP 8 standards. Use clear docstrings and meaningful type annotations where applicable.
* **Thread Safety**: Any code interacting with `ClipboardManager` must respect thread locks since hotkey hooks and UI timers operate asynchronously.
* **Windows API Safety**:
  * Registry modifications in `context_menu_updater.py` must stay within `HKEY_CURRENT_USER`.
  * Never require Administrator / elevated privileges for standard clipboard features.
* **Security & Secrets**:
  * Never hardcode API keys or credentials in code.
  * Secrets belong in `%APPDATA%\RATT\services.json`.

---

## 🚀 Submitting a Pull Request (PR)

1. Commit your changes with descriptive commit messages:
   ```bash
   git commit -m "feat(clipboard): add search filter to popup HUD"
   ```
2. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
3. Open a Pull Request against the `main` branch of the upstream repository.
4. Provide a clear description of the problem solved, testing steps taken, and screenshots if UI changes were made.
