"""RATT v2 Comprehensive Help & User Guide across Windows, macOS, Android, and iOS."""
import tkinter as tk
from tkinter import scrolledtext
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.config import config, open_cybrox_web
from ratt.ui.styles import *


class HelpDialog:
    """In-window comprehensive help and user guide for RATT v2."""

    def __init__(self, root: tk.Tk, app: "RattApp"):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None

    def show(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus_force()
            return

        self.dialog = self.app.new_window("help", scroll=False)
        self.dialog.title(f"RATT v{config.VERSION} \u2014 Help & Platform Guide")
        self.dialog.configure(bg=BG_PRIMARY)

        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=10, padx=16)
        header.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            header, text=f"\u2753 RATT v{config.VERSION} Platform & User Guide", font=FONT_TITLE,
            fg="#2196F3", bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text=f"{config.APP_NAME} v{config.VERSION} ({config.VERSION_FULL}) by {config.PUBLISHER} \u2014 Universal Cross-Platform Edition",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(2, 0))

        btn_bar = tk.Frame(self.dialog, bg=BG_PRIMARY)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=16, pady=(4, 12))
        tk.Button(
            btn_bar, text="Open Cybrox Account Website", font=FONT_BODY,
            fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
            relief=tk.FLAT, pady=7, padx=14, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_ACCOUNT_URL)
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(
            btn_bar, text="Got it!", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg="#2196F3", activebackground="#1976D2",
            relief=tk.FLAT, pady=7, padx=14, cursor="hand2",
            command=self.dismiss
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        content_frame = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=16, pady=6)
        content_frame.pack(fill=tk.BOTH, expand=True)

        text = scrolledtext.ScrolledText(
            content_frame, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            padx=16, pady=16, wrap=tk.WORD, cursor="arrow"
        )
        text.pack(fill=tk.BOTH, expand=True)

        text.tag_configure("title", font=(FONT_FAMILY, 14, "bold"), foreground=LOGO_CYAN)
        text.tag_configure("heading", font=(FONT_FAMILY, 11, "bold"), foreground="#2196F3")
        text.tag_configure("subheading", font=(FONT_FAMILY, 10, "bold"), foreground="#00BFFF")
        text.tag_configure("tier_basic", font=(FONT_FAMILY, 10, "bold"), foreground="#94A3B8")
        text.tag_configure("tier_premium", font=(FONT_FAMILY, 10, "bold"), foreground="#4CAF50")
        text.tag_configure("tier_enterprise", font=(FONT_FAMILY, 10, "bold"), foreground="#CE93D8")
        text.tag_configure("key", font=("Consolas", 10, "bold"), foreground="#4CAF50")
        text.tag_configure("alert", font=("Consolas", 10, "bold"), foreground="#F59E0B")
        text.tag_configure("note", font=(FONT_FAMILY, 9, "italic"), foreground=TEXT_MUTED)
        text.tag_configure("body", font=FONT_BODY, foreground=TEXT_PRIMARY)
        text.tag_configure("bullet", font=FONT_BODY, foreground=TEXT_SECONDARY, lmargin1=18, lmargin2=32)

        text.insert(tk.END, f"Welcome to RATT v{config.VERSION} Universal Edition!\n", "title")
        text.insert(tk.END, "Rapid Access To Text, Rich Media & Files across Windows, macOS, Android & iOS\n\n", "note")

        # 1. Cybrox Website Account & Profile Management
        text.insert(tk.END, "1. CYBROX ACCOUNT & PROFILE MANAGEMENT (WEBSITE)\n", "heading")
        text.insert(tk.END, "All account credentials and profile settings are managed securely on the official Cybrox website (", "body")
        text.insert(tk.END, "https://cybrox.com", "key")
        text.insert(tk.END, "):\n", "body")
        text.insert(tk.END, "\u2022 Sign-Up & Sign-In: Visit ", "bullet")
        text.insert(tk.END, "cybrox.com/signup", "key")
        text.insert(tk.END, " or ", "bullet")
        text.insert(tk.END, "cybrox.com/signin", "key")
        text.insert(tk.END, " to manage your account and activate RATT.\n", "bullet")
        text.insert(tk.END, "\u2022 Change Password: Visit ", "bullet")
        text.insert(tk.END, "cybrox.com/account/password", "key")
        text.insert(tk.END, " (or click \"Change Password\" in Settings).\n", "bullet")
        text.insert(tk.END, "\u2022 Change Profile Name: Visit ", "bullet")
        text.insert(tk.END, "cybrox.com/account/profile", "key")
        text.insert(tk.END, " (or click \"Change Profile Name\" in Settings).\n\n", "bullet")

        # 2. ON / OFF Toggle
        text.insert(tk.END, "2. ON / OFF TOGGLE (RELEASE NATIVE KEYBOARD & MOUSE)\n", "heading")
        text.insert(tk.END, "Need standard OS shortcuts or playing full-screen games? Pause RATT anytime to completely release native keyboard hooks and Explorer context menus:\n", "body")
        text.insert(tk.END, "\u2022 Header Switch: Click ", "bullet")
        text.insert(tk.END, "[ \u25cf ON  ]", "key")
        text.insert(tk.END, " (Cyan glow) to switch to ", "bullet")
        text.insert(tk.END, "[   OFF \u25cf]", "key")
        text.insert(tk.END, " (Muted slate-grey).\n", "bullet")
        text.insert(tk.END, "\u2022 System Tray Menu: Right-click the tray icon and toggle ", "bullet")
        text.insert(tk.END, "\"Pause RATT (Release Keyboard)\"", "key")
        text.insert(tk.END, " / ", "bullet")
        text.insert(tk.END, "\"Resume RATT\"", "key")
        text.insert(tk.END, ".\n", "bullet")
        text.insert(tk.END, "\u2022 Universal Emergency Hotkey: Press ", "bullet")
        text.insert(tk.END, "Ctrl+Alt+P", "key")
        text.insert(tk.END, " (or ", "bullet")
        text.insert(tk.END, "Win+Shift+Pause", "key")
        text.insert(tk.END, ") from anywhere to toggle RATT without opening the window.\n\n", "bullet")

        # 3. Windows PC Guide
        text.insert(tk.END, "3. WINDOWS PC INSTRUCTIONS\n", "heading")
        text.insert(tk.END, "\u2022 Copy to Slot: Press ", "bullet")
        text.insert(tk.END, "Ctrl+C", "key")
        text.insert(tk.END, ", then within 2 seconds press a slot number (", "bullet")
        text.insert(tk.END, "1-9", "key")
        text.insert(tk.END, ", or ", "bullet")
        text.insert(tk.END, "0", "key")
        text.insert(tk.END, " for slot 10).\n", "bullet")
        text.insert(tk.END, "\u2022 Cut to Slot: Press ", "bullet")
        text.insert(tk.END, "Ctrl+X", "key")
        text.insert(tk.END, ", then within 2 seconds press the slot number.\n", "bullet")
        text.insert(tk.END, "\u2022 Paste from Slot: Press ", "bullet")
        text.insert(tk.END, "Ctrl+V", "key")
        text.insert(tk.END, ", then within 1 second press the slot number.\n", "bullet")
        text.insert(tk.END, "\u2022 File Extension Badges: Slots clearly identify file payloads with exact extension badges (e.g. ", "bullet")
        text.insert(tk.END, "[PDF]", "key")
        text.insert(tk.END, ", ", "bullet")
        text.insert(tk.END, "[DOCX]", "key")
        text.insert(tk.END, ", ", "bullet")
        text.insert(tk.END, "[PNG]", "key")
        text.insert(tk.END, ") and file count metadata.\n", "bullet")
        text.insert(tk.END, "\u2022 Responsive Display: Slot cards automatically adapt to your window size — expanding to full width in minimized/compact mode and arranging into dual columns on wide or maximized displays.\n", "bullet")
        text.insert(tk.END, "\u2022 Right-Click Menu: Right-click any file in Windows Explorer to find the RATT context menu.\n", "bullet")
        text.insert(tk.END, "\u2022 Floating Quick Popup: Press ", "bullet")
        text.insert(tk.END, "Ctrl+Shift+R", "key")
        text.insert(tk.END, " anywhere to open the borderless cursor palette.\n", "bullet")
        text.insert(tk.END, "\u2022 Encrypted Local Vault: Your history is sealed with Windows DPAPI + AES-256-GCM. Sensitive data (passwords, tokens, credit cards) are automatically masked.\n\n", "bullet")

        # 4. macOS Guide
        text.insert(tk.END, "4. macOS INSTRUCTIONS\n", "heading")
        text.insert(tk.END, "\u2022 Global Shortcuts: Use ", "bullet")
        text.insert(tk.END, "Cmd+C", "key")
        text.insert(tk.END, ", ", "bullet")
        text.insert(tk.END, "Cmd+X", "key")
        text.insert(tk.END, ", and ", "bullet")
        text.insert(tk.END, "Cmd+V", "key")
        text.insert(tk.END, " followed by a slot number (1-9, 0).\n", "bullet")
        text.insert(tk.END, "\u2022 NSPasteboard Drivers: Fully integrates with macOS Pasteboard for unformatted text, PNG images (`public.png`), and file URLs (`public.file-url`).\n", "bullet")
        text.insert(tk.END, "\u2022 Required Permissions: Open ", "bullet")
        text.insert(tk.END, "System Settings \u2794 Privacy & Security \u2794 Accessibility", "key")
        text.insert(tk.END, " and ensure RATT is checked to allow global hotkeys and paste injection.\n\n", "bullet")

        # 5. Android Guide
        text.insert(tk.END, "5. ANDROID INSTRUCTIONS\n", "heading")
        text.insert(tk.END, "\u2022 Floating Assist Overlay: Keep your favorite keyboard (Samsung Keyboard or Gboard) active! RATT displays a compact magnetic assist bubble whenever an editable text field is focused.\n", "bullet")
        text.insert(tk.END, "\u2022 Universal \"Share to RATT\": In any Android app (Gallery, Files, WhatsApp, Chrome), tap ", "bullet")
        text.insert(tk.END, "Share \u2794 RATT", "key")
        text.insert(tk.END, " to instantly send images, documents, or links to your PC clipboard.\n", "bullet")
        text.insert(tk.END, "\u2022 Local Wi-Fi Sync: Connect both devices to the same Wi-Fi. The PC listens on port 49211 and the phone syncs in < 100ms.\n", "bullet")
        text.insert(tk.END, "\u2022 Pairing: In RATT on PC, click \"Android Sync\" to display your 6-digit rolling PIN or QR code, then enter it on your Android device.\n\n", "bullet")

        # 6. iOS (iPhone & iPad) Guide
        text.insert(tk.END, "6. iOS (iPHONE & iPAD) INSTRUCTIONS\n", "heading")
        text.insert(tk.END, "\u2022 RATT Custom Keyboard: Type normally on the Apple Keyboard. Tap the ", "bullet")
        text.insert(tk.END, "Globe (\U0001F310) icon", "key")
        text.insert(tk.END, " to expand the RATT 10-Slot Palette.\n", "bullet")
        text.insert(tk.END, "\u2022 Tap-to-Copy Rich Media: Tapping an image card (", "bullet")
        text.insert(tk.END, "\U0001F5BC\ufe0f", "key")
        text.insert(tk.END, ") copies the high-resolution image directly to iOS ", "bullet")
        text.insert(tk.END, "UIPasteboard", "key")
        text.insert(tk.END, " with haptic feedback. Long-press in WhatsApp, Messages, or Slack and tap Paste!\n", "bullet")
        text.insert(tk.END, "\u2022 Native \"Share to RATT\" Extension: In Apple Photos or the Files app, tap ", "bullet")
        text.insert(tk.END, "Share \u2794 RATT", "key")
        text.insert(tk.END, " to push photos or files straight into your Windows PC clipboard!\n", "bullet")
        text.insert(tk.END, "\u2022 Enabling on iOS: Go to ", "bullet")
        text.insert(tk.END, "Settings \u2794 General \u2794 Keyboard \u2794 Keyboards \u2794 Add New Keyboard... \u2794 RATT", "key")
        text.insert(tk.END, ", then tap RATT and enable ", "bullet")
        text.insert(tk.END, "\"Allow Full Access\"", "alert")
        text.insert(tk.END, " so RATT can communicate with your PC.\n\n", "bullet")

        # 7. Method 3: Cross-Network E2EE Cloud Relay
        text.insert(tk.END, "7. CROSS-NETWORK E2EE CLOUD RELAY (METHOD 3)\n", "heading")
        text.insert(tk.END, "Not on the same Wi-Fi? Working from an office or coffee shop on cellular data?\n", "body")
        text.insert(tk.END, "\u2022 Zero-Knowledge Relay: Devices on different networks sync through Cybrox's ephemeral relay mailbox.\n", "bullet")
        text.insert(tk.END, "\u2022 Double Cryptographic Seal: Payloads are compressed with zlib and encrypted with Curve25519 ECDH + AES-256-GCM. The cloud relay sees only blind ciphertext and cannot read your data.\n", "bullet")
        text.insert(tk.END, "\u2022 Dynamic Failover: RATT automatically uses fast local Wi-Fi when available and seamlessly fails over to Cloud Relay when on different networks.\n\n", "bullet")

        # 8. Packages: Basic vs Premium vs Enterprise
        text.insert(tk.END, "8. RATT PACKAGES (BASIC, PREMIUM & ENTERPRISE)\n", "heading")

        text.insert(tk.END, "\u25a0 BASIC PACKAGE (Free Forever)\n", "tier_basic")
        text.insert(tk.END, "\u2022 10 High-Speed Clipboard Slots (Slots 1\u201310)\n", "bullet")
        text.insert(tk.END, "\u2022 Rich Media: Unformatted Text, Unformatted Links, Images (PNG/DIB), Vector Diagrams (SVG)\n", "bullet")
        text.insert(tk.END, "\u2022 ON / OFF Native Release Toggle (Header switch, Tray menu, Ctrl+Alt+P)\n", "bullet")
        text.insert(tk.END, "\u2022 7-Day Free Trial of Share & Mirror\n", "bullet")
        text.insert(tk.END, "\u2022 Zero-Execution Anti-Malware Security Shield\n\n", "bullet")

        text.insert(tk.END, "\u25a0 PREMIUM PACKAGE (USD 0.99 / 10 slots / month)\n", "tier_premium")
        text.insert(tk.END, "\u2022 Custom Slots: From 10 up to 50,000 slots\n", "bullet")
        text.insert(tk.END, "\u2022 Document & Media File Copy/Paste (.docx, .pdf, .xlsx, .pptx, .mp4, .zip, etc.)\n", "bullet")
        text.insert(tk.END, "\u2022 Android Integration (Floating Assist Overlay + Share Target + Virtual Keyboard)\n", "bullet")
        text.insert(tk.END, "\u2022 iOS Integration (RATT Keyboard Slot Palette + Share Extension + Pasteboard)\n", "bullet")
        text.insert(tk.END, "\u2022 macOS Desktop Integration with Global Cmd+C/X/V\n", "bullet")
        text.insert(tk.END, "\u2022 Instant 9-Language Translation\n", "bullet")
        text.insert(tk.END, "\u2022 Unlimited Cross-Network Cloud Relay, Share & Mirror\n\n", "bullet")

        text.insert(tk.END, "\u25a0 ENTERPRISE PACKAGE (USD 2.99 / month flat)\n", "tier_enterprise")
        text.insert(tk.END, "\u2022 50 Slots included out-of-the-box\n", "bullet")
        text.insert(tk.END, "\u2022 Manage 1 to 3,000 organization workers under one centralized tenant\n", "bullet")
        text.insert(tk.END, "\u2022 All Premium features included (Files, Images, Android, iOS, macOS, Relay, Translation)\n", "bullet")
        text.insert(tk.END, "\u2022 Team-wide Secure Share, Mirror & Centralized Admin Audit Logging\n\n", "bullet")

        # 9. Keyboard Shortcuts Quick Reference
        text.insert(tk.END, "9. KEYBOARD SHORTCUTS QUICK REFERENCE\n", "heading")
        text.insert(tk.END, "Ctrl+C, then 1-9/0", "key")
        text.insert(tk.END, "       Copy text, image, diagram, or file to slot\n", "body")
        text.insert(tk.END, "Ctrl+X, then 1-9/0", "key")
        text.insert(tk.END, "       Cut text, image, diagram, or file to slot\n", "body")
        text.insert(tk.END, "Ctrl+V, then 1-9/0", "key")
        text.insert(tk.END, "       Paste from slot\n", "body")
        text.insert(tk.END, "Ctrl+Shift+R", "key")
        text.insert(tk.END, "             Open floating cursor popup menu\n", "body")
        text.insert(tk.END, "Ctrl+Alt+P", "key")
        text.insert(tk.END, "               Emergency Pause/Resume RATT (Release Keyboard & Mouse)\n", "body")
        text.insert(tk.END, "Win+Shift+Pause", "key")
        text.insert(tk.END, "          Alternate Emergency Toggle ON / OFF\n", "body")
        text.insert(tk.END, "Cmd+C/X/V, then 1-9/0", "key")
        text.insert(tk.END, "    macOS global slot copy, cut, and paste\n\n", "body")

        # 10. Security & Hygiene
        text.insert(tk.END, "10. SECURITY & DATA HYGIENE PROTOCOL\n", "heading")
        text.insert(tk.END, "\u2022 Zero-Execution Guarantee: RATT processes clipboard buffers strictly as inert bytes. Executables (.exe, .bat, .cmd, .ps1, .vbs, macros) and malicious schemes are blocked.\n", "bullet")
        text.insert(tk.END, "\u2022 Instant Global Deletion (< 100ms): Clearing a slot on your PC instantly zeroes local RAM and transmits signed tombstones to purge the slot across all paired Android and iOS devices.\n", "bullet")
        text.insert(tk.END, "\u2022 End-to-End Encryption: All transmissions use Curve25519 ECDH + AES-256-GCM with CSPRNG IVs.\n\n", "bullet")

        text.insert(tk.END, f"\u00a9 2026 {config.PUBLISHER}. All rights reserved.\n", "note")
        text.config(state=tk.DISABLED)

    def dismiss(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
