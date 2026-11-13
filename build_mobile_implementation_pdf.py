"""
build_mobile_implementation_pdf.py — Generates mobile_implimentation.pdf
Step-by-Step Instructions for Gemini 4 Argon for Android & iPhone Commercial Launch.
"""
import os
import sys
import zlib
import shutil

SCRATCH_DIR = r"C:\Users\State\.gemini\antigravity\scratch\RATT"
ARTIFACT_DIR = r"C:\Users\State\.gemini\antigravity\brain\d0dba156-f5d2-41ce-8268-31cfed4e189e"
PDF_NAME = "mobile_implimentation.pdf"
PDF_ALT_NAME = "mobile_implementation.pdf"

PAGE_W = 595.28
PAGE_H = 841.89
MARGIN_L = 36.0
MARGIN_R = 36.0
MARGIN_T = 36.0
MARGIN_B = 36.0
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R  # 523.28 pt


class PageStream:
    def __init__(self, page_num):
        self.stream = bytearray()
        self.page_num = page_num
        self.y = PAGE_H - MARGIN_T

    def op(self, s):
        self.stream.extend(s.encode('latin1') + b'\n')

    def set_fill(self, r, g, b):
        self.op(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def set_stroke(self, r, g, b):
        self.op(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def set_line_width(self, w):
        self.op(f"{w:.2f} w")

    def rect(self, x, y, w, h, fill=True, stroke=False):
        mode = "B" if (fill and stroke) else ("f" if fill else "s")
        self.op(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {mode}")

    def line(self, x1, y1, x2, y2):
        self.op(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l s")

    def text(self, x, y, text, font="/F1", size=8.5):
        clean = (text.replace('\u2022', '-')
                     .replace('\u2014', '--')
                     .replace('\u2013', '-')
                     .replace('\u2026', '...')
                     .replace('\u2018', "'")
                     .replace('\u2019', "'")
                     .replace('\u201c', '"')
                     .replace('\u201d', '"')
                     .replace('⚡', '[!]')
                     .replace('✓', '[YES]')
                     .replace('✗', '[NO]')
                     .replace('→', '->')
                     .replace('🛡', '[SEC]')
                     .replace('⚠️', '[WARN]')
                     .replace('🌐', '[GLOBE]')
                     .replace('⚙️', '[SETTINGS]')
                     .replace('📋', '[CLIP]')
                     .replace('🔒', '[LOCK]'))
        clean = clean.encode('ascii', errors='replace').decode('latin1')
        safe = clean.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        self.op("BT")
        self.op(f"{font} {size} Tf")
        self.op(f"{x:.2f} {y:.2f} Td")
        self.op(f"({safe}) Tj")
        self.op("ET")


def wrap_text(text, max_chars):
    words = text.split()
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + (1 if cur else 0) <= max_chars:
            cur.append(w)
            cur_len += len(w) + (1 if len(cur) > 1 else 0)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


class ReportBuilder:
    def __init__(self):
        self.pages = []
        self.current_page = None
        self.new_page()

    def new_page(self):
        p_num = len(self.pages) + 1
        p = PageStream(p_num)
        self.pages.append(p)
        self.current_page = p
        self._draw_page_chrome(p)

    def _draw_page_chrome(self, p):
        if p.page_num > 1:
            p.set_fill(0.35, 0.40, 0.48)
            p.text(MARGIN_L, PAGE_H - 22, "RATT COMMERCIAL LAUNCH -- MOBILE IMPLEMENTATION GUIDE", "/F2", 7.5)
            p.text(PAGE_W - MARGIN_R - 165, PAGE_H - 22, "INSTRUCTIONS FOR GEMINI 4 ARGON", "/F1", 7.5)
            p.set_stroke(0.85, 0.88, 0.92)
            p.set_line_width(0.75)
            p.line(MARGIN_L, PAGE_H - 26, PAGE_W - MARGIN_R, PAGE_H - 26)

        p.set_stroke(0.85, 0.88, 0.92)
        p.set_line_width(0.75)
        p.line(MARGIN_L, MARGIN_B + 14, PAGE_W - MARGIN_R, MARGIN_B + 14)
        p.set_fill(0.35, 0.40, 0.48)
        p.text(MARGIN_L, MARGIN_B + 4, "CYBROX ARCHITECTURE BLUEPRINT -- COMMERCIAL PRODUCTION", "/F2", 7.5)
        p.text(MARGIN_L + 235, MARGIN_B + 4, "DOC: MOBILE_IMPLEMENTATION_V1", "/F1", 7.5)
        p.text(PAGE_W - MARGIN_R - 55, MARGIN_B + 4, f"PAGE {p.page_num}", "/F2", 7.5)

    def check_space(self, needed_pt):
        if self.current_page.y - needed_pt < MARGIN_B + 20:
            self.new_page()

    def draw_cover_header(self):
        p = self.current_page
        p.set_fill(0.01, 0.65, 0.98)
        p.rect(MARGIN_L, p.y - 4, USABLE_W, 4, fill=True, stroke=False)
        p.y -= 15

        p.set_fill(0.01, 0.65, 0.98)
        p.rect(MARGIN_L, p.y - 14, 305, 15, fill=True, stroke=False)
        p.set_fill(1.0, 1.0, 1.0)
        p.text(MARGIN_L + 6, p.y - 11, "GEMINI 4 ARGON INSTRUCTIONS: MOBILE IMPLEMENTATION", "/F2", 7.5)

        p.set_fill(0.12, 0.16, 0.22)
        p.text(PAGE_W - MARGIN_R - 175, p.y - 2, "Document: mobile_implimentation.pdf", "/F2", 7.8)
        p.text(PAGE_W - MARGIN_R - 175, p.y - 12, "AI Target: Gemini 4 Argon", "/F1", 7.8)
        p.text(PAGE_W - MARGIN_R - 175, p.y - 22, "Security Standard: High-Grade Commercial", "/F1", 7.8)
        p.text(PAGE_W - MARGIN_R - 175, p.y - 32, "Scope: Android & iPhone Commercial Launch", "/F1", 7.8)

        p.y -= 26
        p.set_fill(0.06, 0.09, 0.16)
        p.text(MARGIN_L, p.y, "RATT MOBILE IMPLEMENTATION SPECIFICATION", "/F2", 13.5)
        p.y -= 12
        p.set_fill(0.28, 0.33, 0.41)
        p.text(MARGIN_L, p.y, "Step-by-Step Instructions for Gemini 4 Argon: High Security, Cross-Platform Deletion & Production UX", "/F1", 8.2)
        p.y -= 12

        p.set_stroke(0.85, 0.88, 0.92)
        p.set_line_width(1.0)
        p.line(MARGIN_L, p.y, PAGE_W - MARGIN_R, p.y)
        p.y -= 11

    def draw_section_heading(self, title):
        self.check_space(30)
        p = self.current_page
        p.y -= 5
        p.set_fill(0.01, 0.65, 0.98)
        p.rect(MARGIN_L, p.y - 9, 3.5, 11, fill=True, stroke=False)
        p.set_fill(0.06, 0.09, 0.16)
        p.text(MARGIN_L + 8, p.y - 8, title.upper(), "/F2", 9.0)
        p.y -= 13

    def draw_paragraph(self, text, max_chars=106, font="/F1", size=8.0, leading=10.2):
        lines = wrap_text(text, max_chars)
        needed = len(lines) * leading + 3
        self.check_space(needed)
        p = self.current_page
        p.set_fill(0.12, 0.16, 0.23)
        for line in lines:
            p.text(MARGIN_L, p.y, line, font, size)
            p.y -= leading
        p.y -= 2

    def draw_callout(self, title, text, style="info"):
        lines = wrap_text(text, 98)
        box_h = 16 + len(lines) * 9.8
        self.check_space(box_h + 8)
        p = self.current_page

        if style == "alert":
            bg = (0.99, 0.94, 0.94)
            border = (0.85, 0.2, 0.2)
            title_color = (0.75, 0.1, 0.1)
        elif style == "success":
            bg = (0.94, 0.98, 0.95)
            border = (0.15, 0.65, 0.3)
            title_color = (0.1, 0.5, 0.2)
        else:
            bg = (0.95, 0.97, 1.0)
            border = (0.01, 0.65, 0.98)
            title_color = (0.0, 0.42, 0.72)

        p.set_fill(*bg)
        p.rect(MARGIN_L, p.y - box_h, USABLE_W, box_h, fill=True, stroke=False)
        p.set_fill(*border)
        p.rect(MARGIN_L, p.y - box_h, 3.5, box_h, fill=True, stroke=False)

        p.set_fill(*title_color)
        p.text(MARGIN_L + 9, p.y - 10, title.upper(), "/F2", 7.8)

        p.set_fill(0.15, 0.2, 0.25)
        cur_y = p.y - 19
        for line in lines:
            p.text(MARGIN_L + 9, cur_y, line, "/F1", 7.5)
            cur_y -= 9.8
        p.y -= (box_h + 5)

    def draw_table(self, headers, rows, col_widths):
        total_w = sum(col_widths)
        scale = USABLE_W / total_w
        widths = [w * scale for w in col_widths]
        header_h = 14
        row_h = 13.0
        total_needed = header_h + len(rows) * row_h + 6
        self.check_space(total_needed)
        p = self.current_page

        p.set_fill(0.08, 0.12, 0.18)
        p.rect(MARGIN_L, p.y - header_h, USABLE_W, header_h, fill=True, stroke=False)

        p.set_fill(1.0, 1.0, 1.0)
        cur_x = MARGIN_L
        for i, h in enumerate(headers):
            p.text(cur_x + 5, p.y - 10, h, "/F2", 7.0)
            cur_x += widths[i]
        p.y -= header_h

        for r_idx, row in enumerate(rows):
            bg = (0.98, 0.98, 0.99) if r_idx % 2 == 0 else (1.0, 1.0, 1.0)
            p.set_fill(*bg)
            p.rect(MARGIN_L, p.y - row_h, USABLE_W, row_h, fill=True, stroke=False)
            p.set_stroke(0.9, 0.92, 0.94)
            p.set_line_width(0.5)
            p.line(MARGIN_L, p.y - row_h, MARGIN_L + USABLE_W, p.y - row_h)

            cur_x = MARGIN_L
            for c_idx, cell in enumerate(row):
                if cell in ("FEASIBLE", "WINNER", "GOLD STANDARD", "ENTERPRISE GRADE", "INSTANT (<100MS)", "ACTIVE"):
                    p.set_fill(0.1, 0.55, 0.2)
                    font = "/F2"
                elif cell in ("IMPOSSIBLE (BLOCKED BY OS)", "HIGH (UNACCEPTABLE)", "POOR", "VULNERABLE", "BLOCKED"):
                    p.set_fill(0.85, 0.1, 0.1)
                    font = "/F2"
                elif cell in ("PARTIAL", "OPTIONAL", "REQUIRES PRIV", "REJECTED (No 3rd-party API)", "REJECTED FOR MOBILE"):
                    p.set_fill(0.85, 0.45, 0.0)
                    font = "/F2"
                elif c_idx == 0:
                    p.set_fill(0.1, 0.15, 0.2)
                    font = "/F2"
                else:
                    p.set_fill(0.2, 0.25, 0.3)
                    font = "/F1"
                p.text(cur_x + 5, p.y - 9.0, str(cell), font, 6.8)
                cur_x += widths[c_idx]
            p.y -= row_h
        p.y -= 5

    def draw_code_box(self, filename, code_lines):
        line_h = 8.8
        box_h = 15 + len(code_lines) * line_h
        self.check_space(box_h + 8)
        p = self.current_page

        p.set_fill(0.1, 0.14, 0.2)
        p.rect(MARGIN_L, p.y - 11, USABLE_W, 11, fill=True, stroke=False)
        p.set_fill(0.01, 0.65, 0.98)
        p.text(MARGIN_L + 6, p.y - 8.5, f"SPECIFICATION / CODE BLOCK: {filename}", "/F2", 6.8)

        p.set_fill(0.96, 0.97, 0.98)
        p.rect(MARGIN_L, p.y - box_h, USABLE_W, box_h - 11, fill=True, stroke=False)
        p.set_stroke(0.85, 0.88, 0.92)
        p.set_line_width(0.5)
        p.rect(MARGIN_L, p.y - box_h, USABLE_W, box_h, fill=False, stroke=True)

        cur_y = p.y - 19
        for cl in code_lines:
            if cl.strip().startswith("//") or cl.strip().startswith("#"):
                p.set_fill(0.45, 0.5, 0.55)
            elif any(k in cl for k in ["class ", "func ", "val ", "override ", "import ", "struct "]):
                p.set_fill(0.05, 0.3, 0.65)
            else:
                p.set_fill(0.12, 0.16, 0.2)
            p.text(MARGIN_L + 8, cur_y, cl, "/F3", 6.6)
            cur_y -= line_h
        p.y -= (box_h + 5)


def build_pdf_document():
    b = ReportBuilder()

    # ==================== PAGE 1 ====================
    b.draw_cover_header()

    b.draw_section_heading("1. Commercial Launch Objectives & Architecture Summary")
    b.draw_paragraph(
        "This document provides the definitive implementation manual for Gemini 4 Argon to construct the production "
        "mobile clients for RATT (Real-time Adaptive Text Transfer). To guarantee commercial success, the application must: "
        "(1) Eliminate user friction by keeping the user's primary keyboard active (Samsung Keyboard or Gboard on Android, "
        "Apple Keyboard on iOS); (2) Deliver commercial enterprise-grade security with AES-256-GCM encryption; and (3) Enforce "
        "instantaneous global slot clearance across all platforms whenever the host PC clears a slot."
    )

    t1_headers = ["PLATFORM UX MODEL", "NATIVE KEYBOARD PRESERVED", "TYPING FRICTION", "OS FEASIBILITY", "COMMERCIAL STATUS"]
    t1_rows = [
        ["Option 1: In-Keyboard Toolbar", "Yes", "None", "IMPOSSIBLE (BLOCKED BY OS)", "REJECTED (No 3rd-party API)"],
        ["Option 2: Floating Assist Overlay (Android)", "Yes (Keep Samsung/Gboard)", "Zero Friction", "FEASIBLE", "WINNER FOR ANDROID"],
        ["Custom Full Keyboard (Current RattIME)", "No (User loses Samsung/Gboard)", "HIGH (UNACCEPTABLE)", "FEASIBLE", "REJECTED FOR MOBILE"],
        ["iOS Slot Palette Extension (iPhone)", "Yes (Tap Globe icon to view slots)", "Extremely Low", "FEASIBLE", "GOLD STANDARD FOR iOS"]
    ]
    b.draw_table(t1_headers, t1_rows, [140, 115, 95, 105, 68])

    b.draw_section_heading("2. High Security Standards (Enterprise Specification)")
    b.draw_callout("CRYPTOGRAPHIC REQUIREMENTS: ZERO PLAINTEXT & HARDWARE-BACKED KEYS",
                   "All data transmitted across local Wi-Fi or networks must be encrypted with AES-256-GCM using a 96-bit CSPRNG "
                   "initialization vector and a 128-bit authentication tag. Pairing requires an out-of-band ECDH exchange over Curve25519, "
                   "authenticated via a dynamic 6-digit rolling PIN or QR code. Encryption keys must reside exclusively within the "
                   "hardware-backed Android Keystore (StrongBox/TEE) and iOS Keychain Services with Secure Enclave backing.",
                   style="info")

    sec_headers = ["SECURITY LAYER", "ANDROID IMPLEMENTATION", "iOS (IPHONE) IMPLEMENTATION", "PROTECTION LEVEL"]
    sec_rows = [
        ["Transit Cipher", "AES-256-GCM with 96-bit CSPRNG IV", "AES-256-GCM with Apple CryptoKit", "ENTERPRISE GRADE"],
        ["Device Pairing", "ECDH + SHA-256 HKDF Key Derivation", "ECDH + HKDF via Secure Enclave", "TAMPER-PROOF"],
        ["At-Rest Storage", "Android Keystore + EncryptedSharedPrefs", "iOS Keychain Services (App Group Shared)", "HARDWARE-BACKED"],
        ["Memory Sanitization", "Arrays.fill() zeroing on slot eviction", "memset_s() zeroing upon deletion", "ZERO MEMORY LEAK"],
    ]
    b.draw_table(sec_headers, sec_rows, [110, 150, 150, 113])

    # ==================== PAGE 2 ====================
    b.new_page()
    b.draw_section_heading("3. Phase 1: Real-Time Global Slot Deletion Protocol")
    b.draw_paragraph(
        "Commercial compliance requires that when the host PC clears a slot (or executes a total wipe), that deletion "
        "is immediately propagated across all paired mobile endpoints. Once received, the device must purge the slot from memory and "
        "local encrypted storage, updating the active UI in less than 100 milliseconds."
    )

    deletion_protocol = [
        "// Global Real-time Deletion Packet Schema (Encrypted Payload)",
        "{",
        '  "action": "CLEAR_SLOT",            // or "CLEAR_ALL"',
        '  "slot_id": 5,                       // Slot index 1 to 10 (omitted on CLEAR_ALL)',
        '  "timestamp": 1794157320,            // Epoch UTC timestamp',
        '  "nonce": "a7b8c9d0e1f2",            // 12-byte CSPRNG replay protection token',
        '  "source_device": "PC-WIN11-HOST"    // Originating node ID',
        "}"
    ]
    b.draw_code_box("Protocol: Real-time Slot Deletion Payload", deletion_protocol)

    b.draw_section_heading("4. Verification & QA Test Matrix")
    b.draw_paragraph(
        "Gemini 4 Argon must ensure that the generated code passes all five verification test criteria prior to release:"
    )

    qa_headers = ["TEST IDENTIFIER", "VERIFICATION CRITERIA", "TARGET SLA", "AUDIT METHOD", "STATUS"]
    qa_rows = [
        ["SEC-001 (Zero Cleartext)", "Wireshark packet capture on port 49210", "Zero plaintext bytes", "Network packet sniff", "ACTIVE"],
        ["DEL-002 (Host Deletion SLA)", "Time from PC 'Clear Slot 5' to Mobile UI", "< 100 milliseconds", "High-speed screen timer", "ACTIVE"],
        ["MEM-003 (RAM Sanitization)", "Memory heap dump after slot eviction", "Zero leftover plaintext", "Android Studio Profiler", "ACTIVE"],
        ["PERF-004 (Battery Overhead)", "24-hour background socket listener", "< 1.5% battery drain", "Battery Historian report", "ACTIVE"],
        ["UI-005 (Samsung/Gboard Parity)", "Overlay appears on editable focus", "100% field detection", "One UI 5/6 & Pixel tests", "ACTIVE"]
    ]
    b.draw_table(qa_headers, qa_rows, [115, 145, 95, 105, 63])

    # ==================== PAGE 3 ====================
    b.new_page()
    b.draw_section_heading("5. Phase 2: Android Implementation Guide (Option 2: Floating Assist Overlay)")
    b.draw_paragraph(
        "On Android, RATT operates as a background service rendering a small floating assist bubble "
        "(WindowManager TYPE_APPLICATION_OVERLAY) whenever an editable input field receives focus. The user keeps "
        "Samsung Keyboard or Gboard active at all times, retaining full autocorrect, swipe gestures, and voice dictation."
    )

    android_code = [
        "// Android FloatingAssistService.kt - Magnetic Floating Bubble & Direct Injection",
        "class FloatingAssistService : Service() {",
        "    private lateinit var windowManager: WindowManager",
        "    private lateinit var bubbleView: View",
        "    ",
        "    fun showRattTrayMenu() {",
        "        // Inflates 10-slot grid with PC clipboard previews and Clear status",
        "        val menu = RattOverlayMenuView(this, SlotRepository.liveSlots)",
        "        menu.onSlotSelected = { slot ->",
        "            RattAccessibilityService.injectText(slot.content)",
        "            collapseToEdge()",
        "        }",
        "    }",
        "    ",
        "    fun onSlotClearedBroadcast(slotId: Int) {",
        "        SlotRepository.clear(slotId) // Zeroes memory array immediately",
        "        bubbleView.updateBadgeState() // Repaints UI to [Empty]",
        "    }",
        "}"
    ]
    b.draw_code_box("Android: FloatingAssistService.kt", android_code)

    android_acc_code = [
        "// Android RattAccessibilityService.kt - Focus Detection & Injection",
        "class RattAccessibilityService : AccessibilityService() {",
        "    override fun onAccessibilityEvent(event: AccessibilityEvent?) {",
        "        if (event?.eventType == AccessibilityEvent.TYPE_VIEW_FOCUSED) {",
        "            val node = event.source ?: return",
        "            if (node.isEditable) {",
        "                FloatingAssistService.revealBubble()",
        "            }",
        "        }",
        "    }",
        "    fun injectText(text: String) {",
        "        val root = rootInActiveWindow ?: return",
        "        val focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return",
        "        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text) }",
        "        focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)",
        "    }",
        "}"
    ]
    b.draw_code_box("Android: RattAccessibilityService.kt", android_acc_code)

    # ==================== PAGE 4 ====================
    b.new_page()
    b.draw_section_heading("6. Phase 3: iPhone (iOS) Implementation Guide (Slot Palette Extension)")
    b.draw_paragraph(
        "Because iOS strictly prohibits floating pop-ups over third-party apps, RATT for iPhone utilizes Apple's "
        "official UIInputViewController. The user stays on their standard Apple keyboard for typing; tapping the Globe (🌐) "
        "icon expands the RATT Slot Palette showing 10 cards synced from the desktop."
    )

    ios_code = [
        "// iOS RattKeyboardViewController.swift - Slot Palette & Deletion Handling",
        "import UIKit",
        "",
        "class RattKeyboardViewController: UIInputViewController {",
        "    override func viewDidLoad() {",
        "        super.viewDidLoad()",
        "        setupSlotPaletteGrid()",
        "        observeDarwinDeletionNotification()",
        "    }",
        "    ",
        "    func didSelectSlot(_ slot: RattSlot) {",
        "        self.textDocumentProxy.insertText(slot.content)",
        "    }",
        "    ",
        "    func observeDarwinDeletionNotification() {",
        "        CFNotificationCenterAddObserver(CFNotificationCenterGetDarwinNotifyCenter(),",
        "            nil, { _, _, _, _, _ in NotificationCenter.default.post(name: .slotCleared, object: nil) },",
        "            \"com.cybrox.ratt.slotCleared\" as CFString, nil, .deliverImmediately)",
        "    }",
        "}"
    ]
    b.draw_code_box("iOS: RattKeyboardViewController.swift", ios_code)

    ios_appgroup_code = [
        "// iOS AppGroupDataManager.swift - Shared Secure Container & Notification",
        "import Foundation",
        "import Security",
        "",
        "class AppGroupDataManager {",
        "    static let shared = AppGroupDataManager()",
        "    private let groupURL = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: \"group.com.cybrox.ratt\")!",
        "    ",
        "    func clearSlot(id: Int) {",
        "        // Purges slot payload from shared container",
        "        let slotFile = groupURL.appendingPathComponent(\"slot_\\(id).enc\")",
        "        try? FileManager.default.removeItem(at: slotFile)",
        "        // Dispatches cross-process Darwin notification to Keyboard Extension",
        "        let name = CFNotificationName(\"com.cybrox.ratt.slotCleared\" as CFString)",
        "        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)",
        "    }",
        "}"
    ]
    b.draw_code_box("iOS: AppGroupDataManager.swift", ios_appgroup_code)

    # ==================== PAGE 5 ====================
    b.new_page()
    b.draw_section_heading("7. Phase 4: Master Execution Instructions for Gemini 4 Argon")
    b.draw_paragraph(
        "Copy and paste the following operational instruction block into Gemini 4 Argon to execute the full "
        "commercial code implementation for Android and iOS:"
    )

    prompt_box = [
        "========================= START GEMINI 4 ARGON PROMPT =========================",
        "ACT AS: Senior Mobile & Security Architect for RATT Commercial Launch.",
        "GOAL: Implement production Android and iOS clients with high-grade security & slot sync.",
        "",
        "1. SECURITY REQUIREMENTS (COMMERCIAL GRADE):",
        "   - End-to-End Transit: AES-256-GCM cipher, 96-bit CSPRNG IVs, zero plaintext on LAN.",
        "   - Pairing: ECDH (Curve25519) + SHA-256 HKDF session key exchange via dynamic QR / 6-digit PIN.",
        "   - Local Storage: Android Keystore + EncryptedSharedPreferences; iOS Keychain Services.",
        "   - Sanitization: Arrays.fill() / memset_s() memory zeroing on slot clearance.",
        "",
        "2. GLOBAL DELETION PROTOCOL:",
        "   - When host clears a slot, emit signed CLEAR_SLOT packet; on wipe emit CLEAR_ALL.",
        "   - Mobile devices must flush memory and repaint active UI to [Empty] in < 100ms.",
        "",
        "3. ANDROID IMPLEMENTATION (OPTION 2: FLOATING ASSIST OVERLAY):",
        "   - FloatingAssistService (TYPE_APPLICATION_OVERLAY) with magnetic border docking.",
        "   - RattAccessibilityService monitors focus (isEditable) and injects text via ACTION_SET_TEXT.",
        "   - User keeps Samsung Keyboard / Gboard active at all times with full predictive text.",
        "",
        "4. IPHONE (iOS) IMPLEMENTATION (SLOT PALETTE KEYBOARD EXTENSION):",
        "   - UIInputViewController custom keyboard extension shared via App Group (group.com.cybrox.ratt).",
        "   - Tapping Globe (🌐) displays 10-slot preview cards; tap slot injects text via insertText().",
        "   - Real-time tombstone propagation using Darwin Notification Center across processes.",
        "",
        "DELIVERABLES:",
        "Complete, buildable Kotlin and Swift source files, AndroidManifest, Entitlements, and QA tests.",
        "========================== END GEMINI 4 ARGON PROMPT =========================="
    ]
    b.draw_code_box("Ready-To-Run Gemini 4 Argon Master Prompt", prompt_box)

    # ==================== FINALIZE PDF OBJECTS ====================
    objects = []

    def add_object(data):
        objects.append(data)
        return len(objects)

    f1_num = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    f2_num = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    f3_num = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    page_nums = []
    pages_root_num = len(objects) + len(b.pages) + 1

    for p in b.pages:
        comp_stream = zlib.compress(bytes(p.stream))
        stream_len = len(comp_stream)
        stream_dict = f"<< /Length {stream_len} /Filter /FlateDecode >>\nstream\n".encode('latin1')
        stream_bytes = stream_dict + comp_stream + b"\nendstream"
        contents_num = add_object(stream_bytes)

        page_dict = (
            f"<< /Type /Page /Parent {pages_root_num} 0 R "
            f"/MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
            f"/Contents {contents_num} 0 R "
            f"/Resources << /Font << /F1 {f1_num} 0 R /F2 {f2_num} 0 R /F3 {f3_num} 0 R >> >> >>"
        ).encode('latin1')
        page_nums.append(add_object(page_dict))

    kids_str = " ".join(f"{pn} 0 R" for pn in page_nums)
    pages_root_bytes = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_nums)} >>".encode('latin1')
    add_object(pages_root_bytes)

    catalog_bytes = f"<< /Type /Catalog /Pages {pages_root_num} 0 R >>".encode('latin1')
    catalog_num = add_object(catalog_bytes)

    out = bytearray()
    out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []

    for i, obj in enumerate(objects):
        num = i + 1
        offsets.append(len(out))
        out.extend(f"{num} 0 obj\n".encode('latin1'))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    num_objs = len(objects) + 1
    out.extend(f"xref\n0 {num_objs}\n".encode('latin1'))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode('latin1'))

    out.extend(f"trailer\n<< /Size {num_objs} /Root {catalog_num} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode('latin1'))
    return bytes(out)


def main():
    print("Compiling mobile_implimentation.pdf...")
    pdf_bytes = build_pdf_document()

    os.makedirs(SCRATCH_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    # Save as mobile_implimentation.pdf (requested name)
    p1 = os.path.join(SCRATCH_DIR, PDF_NAME)
    with open(p1, "wb") as f:
        f.write(pdf_bytes)
    a1 = os.path.join(ARTIFACT_DIR, PDF_NAME)
    shutil.copyfile(p1, a1)
    print(f"SUCCESS: Saved {a1} ({len(pdf_bytes)} bytes)")

    # Save as mobile_implementation.pdf (standard spelling alias)
    p2 = os.path.join(SCRATCH_DIR, PDF_ALT_NAME)
    with open(p2, "wb") as f:
        f.write(pdf_bytes)
    a2 = os.path.join(ARTIFACT_DIR, PDF_ALT_NAME)
    shutil.copyfile(p2, a2)
    print(f"SUCCESS: Saved {a2} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
