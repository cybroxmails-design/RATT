"""What RATT does when told to: right-click menu entries, popup choices and hotkey chords.

Everything here starts on the Tk thread (`ActionRunner.run`), hands the slow parts
(clipboard polling, translation, keystrokes, file routing) to a worker thread, and reports
back through `app.notify_async`, which is safe to call from any thread.
"""
import ctypes
import os
import shutil
import threading
import time
from ctypes import wintypes
from typing import List, Optional, Tuple

import pyperclip

from ratt import security_guard, win_clipboard
from ratt.clipboard_manager import SlotAction, SlotContentType
from ratt.config import config, TRANSLATE_LANGUAGES
from ratt.translation import TranslationError

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetForegroundWindow.argtypes = []


def _get_foreground_window() -> int:
    """Return the HWND of the current foreground window."""
    try:
        return int(_user32.GetForegroundWindow() or 0)
    except Exception:
        return 0


def _consume_shell_context(max_age_sec: float = 10.0, path: Optional[str] = None) -> Tuple[Optional[str], List[str]]:
    """Read and remove %APPDATA%\\RATT\\shell_context.txt if recently written by ratt_menu.dll."""
    if path:
        ctx_path = path
    else:
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return None, []
        ctx_path = os.path.join(appdata, "RATT", "shell_context.txt")
    if not os.path.exists(ctx_path):
        return None, []
    try:
        age = time.time() - os.path.getmtime(ctx_path)
        with open(ctx_path, "rb") as f:
            raw_bytes = f.read()
        try:
            os.remove(ctx_path)
        except Exception:
            pass
        if age > max_age_sec or not raw_bytes:
            return None, []

        # Autodetect encoding: UTF-16LE (BOM or NUL interleaved), UTF-8-SIG, or UTF-8
        if raw_bytes.startswith(b"\xff\xfe") or b"\x00" in raw_bytes[:64]:
            text = raw_bytes.decode("utf-16-le", errors="replace")
        elif raw_bytes.startswith(b"\xef\xbb\xbf"):
            text = raw_bytes.decode("utf-8-sig", errors="replace")
        else:
            text = raw_bytes.decode("utf-8", errors="replace")

        lines = text.splitlines()
        folder: Optional[str] = None
        files: List[str] = []
        for line in lines:
            line = line.strip()
            if line.startswith("FOLDER\t"):
                folder = line.split("\t", 1)[1].strip()
            elif line.startswith("FILE\t"):
                fp = line.split("\t", 1)[1].strip()
                if fp:
                    files.append(fp)
        return folder, files
    except Exception:
        return None, []


def _safe_copy_or_move_files(files: List[str], dest_dir: str, is_cut: bool) -> Tuple[bool, str]:
    """Safely copy or move validated inert files into dest_dir without executing anything."""
    ok, safe_files, err = security_guard.validate_file_list(files)
    if not ok:
        return False, err
    if not dest_dir or not os.path.isdir(dest_dir):
        return False, "Destination folder does not exist."
    if dest_dir.startswith("\\\\") or dest_dir.startswith("//"):
        return False, "Security Block: Remote UNC destination folders are prohibited."

    dest_dir = os.path.abspath(os.path.normpath(dest_dir))
    transferred = 0
    try:
        for src in safe_files:
            base = os.path.basename(src)
            stem, ext = os.path.splitext(base)
            target = os.path.join(dest_dir, base)
            # If copying/moving to the exact same path, skip or create a safe copy suffix
            if os.path.abspath(src).lower() == os.path.abspath(target).lower():
                if is_cut:
                    transferred += 1
                    continue
                target = os.path.join(dest_dir, f"{stem} - Copy{ext}")
            counter = 1
            while os.path.exists(target):
                target = os.path.join(dest_dir, f"{stem} ({counter}){ext}")
                counter += 1
            if is_cut:
                shutil.move(src, target)
            else:
                if os.path.isdir(src):
                    shutil.copytree(src, target)
                else:
                    shutil.copy2(src, target)
            transferred += 1
        verb = "Moved" if is_cut else "Copied"
        return True, f"{verb} {transferred} file(s) to {os.path.basename(dest_dir) or dest_dir}"
    except Exception as e:
        return False, f"File transfer failed: {e}"


class ActionRunner:
    def __init__(self, app):
        self.app = app

    def _report_error(self, err: str, fallback: str = "Operation blocked"):
        msg = err or fallback
        if msg.startswith("UPGRADE_REQUIRED:"):
            reason = msg.split(":", 1)[1].strip()
            if hasattr(self.app, "request_upgrade_async"):
                self.app.request_upgrade_async(reason)
            else:
                self.app.notify_async(reason, is_error=True)
        else:
            self.app.notify_async(msg, is_error=True)

    # ---- entry point ----

    def run(self, action, args):
        app = self.app
        if action == "open":
            app.show_main_window()
            return
        if action in ("toggle-enabled", "toggle"):
            if hasattr(app, "toggle_ratt"):
                app.toggle_ratt()
            else:
                config.enabled = not config.enabled
            return
        if not config.enabled:
            return
        if not config.user.is_logged_in:
            app.show_main_window()
            app.show_notification("Sign up to start using RATT", is_error=True)
            return

        if action in ("share", "mirror"):
            self._share_or_mirror(action)
        elif action == "popup":
            app.show_popup()
        elif action in ("copy", "cut", "paste"):
            self._slot_action(action, args)
        elif action in ("hotkey-copy", "hotkey-cut", "hotkey-paste"):
            self._hotkey_action(action.split("-")[1], args)
        elif action in ("android", "android-copy", "android-cut", "android-paste"):
            self._android_action(action, args)
        elif action in ("ios", "ios-copy", "ios-cut", "ios-paste"):
            self._ios_action(action, args)
        elif action == "translate" and args:
            # "translate fr" (from the menu) asks which slot; "translate fr 3" goes straight on
            slot = _number(args, 1)
            if slot is None:
                app.show_translate_picker(args[0])
            else:
                self.translate(args[0], slot)

    def _android_action(self, action, args):
        """Copy, Cut, or Paste with the Android Virtual Keyboard (Premium & Enterprise only)."""
        if not config.is_premium:
            reason = (
                "Copy, Cut & Paste to Android is limited to Premium and Enterprise users. "
                "Please upgrade your plan to unlock Android integration."
            )
            if hasattr(self.app, "request_upgrade"):
                self.app.request_upgrade(reason)
            else:
                self.app.show_main_window()
                self.app.show_notification(reason, is_error=True)
            return
        slot = _number(args, 0) or 1
        manager = self.app.clipboard_manager
        if action == "android-cut":
            ok = manager.cut_to_android(slot)
            if ok:
                self.app.show_notification(f"Cut Slot #{slot} to Android Keyboard")
            else:
                self._report_error(manager.last_error)
        elif action == "android-paste":
            res = manager.paste_from_android(slot)
            if res:
                self.app.show_notification(f"Pasted Slot #{slot} from Android Keyboard")
            else:
                self._report_error(manager.last_error)
        else:
            ok = manager.copy_to_android(slot)
            if ok:
                self.app.show_notification(f"Copied Slot #{slot} to Android Keyboard")
            else:
                self._report_error(manager.last_error)

    def _ios_action(self, action, args):
        """Copy, Cut, or Paste with the iOS (iPhone/iPad) Custom Keyboard (Premium & Enterprise only)."""
        if not config.is_premium:
            reason = (
                "Copy, Cut & Paste to iOS (iPhone/iPad) is limited to Premium and Enterprise users. "
                "Please upgrade your plan to unlock iOS integration."
            )
            if hasattr(self.app, "request_upgrade"):
                self.app.request_upgrade(reason)
            else:
                self.app.show_main_window()
                self.app.show_notification(reason, is_error=True)
            return
        slot = _number(args, 0) or 1
        manager = self.app.clipboard_manager
        if action == "ios-cut":
            ok = manager.cut_to_ios(slot)
            if ok:
                self.app.show_notification(f"Cut Slot #{slot} to iPhone Keyboard (iOS)")
            else:
                self._report_error(manager.last_error)
        elif action == "ios-paste":
            res = manager.paste_from_ios(slot)
            if res:
                self.app.show_notification(f"Pasted Slot #{slot} from iPhone Keyboard (iOS)")
            else:
                self._report_error(manager.last_error)
        else:
            ok = manager.copy_to_ios(slot)
            if ok:
                self.app.show_notification(f"Copied Slot #{slot} to iPhone Keyboard (iOS)")
            else:
                self._report_error(manager.last_error)

    def _share_or_mirror(self, action):
        app = self.app
        if not config.user.is_trial_active:
            app.show_main_window()
            app.show_notification(f"Your 7-day {action} trial has ended - upgrade to continue", is_error=True)
        elif action == "share":
            app.show_share_dialog()
        else:
            app.show_mirror_dialog()

    def _slot_action(self, action, args):
        """Right-click menu: copy / cut / paste with a slot number."""
        slot = _number(args, 0)
        if slot is None or slot > config.max_slots:
            self.app.show_notification("That slot is not available on your plan", is_error=True)
            return
        extra_path = None
        if len(args) > 1:
            candidate = args[1].strip().strip('"')
            if candidate and os.path.exists(candidate):
                extra_path = candidate
        work = self._paste_into_document if action == "paste" else self._grab_to_slot
        threading.Thread(target=work, args=(action, slot, 0.3, extra_path), daemon=True).start()

    def _hotkey_action(self, action, args):
        """Hotkey chord: the helper already sent Ctrl+C / Ctrl+X, or held back Ctrl+V."""
        slot = _number(args, 0)
        if slot is None or slot > config.max_slots:
            self.app.notify_async("That slot is not available on your plan", is_error=True)
            return
        if action == "paste":
            threading.Thread(target=self._paste_into_document, args=(action, slot, 0.05, None), daemon=True).start()
        else:
            threading.Thread(target=self._store_clipboard, args=(action, slot), daemon=True).start()

    # ---- copy / cut / paste ----

    def _store_clipboard(self, action, slot):
        """The document/Explorer just copied or cut: capture the multi-format clipboard into the slot."""
        time.sleep(0.15)
        manager = self.app.clipboard_manager
        store = manager.copy_to_slot if action == "copy" else manager.cut_to_slot
        if store(slot):
            slot_obj = manager.get_slot(slot)
            badge = f"[{slot_obj.type_badge}] " if slot_obj else ""
            self.app.notify_async(f"{'Copied' if action == 'copy' else 'Cut'} {badge}to Slot #{slot}")
        elif manager.last_error:
            self._report_error(manager.last_error)

    def _grab_to_slot(self, action, slot, delay=0.3, direct_file=None):
        """Copy/cut the highlighted text, image, diagram, link, or Explorer files into a slot."""
        manager = self.app.clipboard_manager

        # 1. Direct file path passed as argument (e.g. from fallback registry verb)
        if direct_file and os.path.exists(direct_file):
            if manager.store_files_to_slot(slot, [direct_file], action=action):
                self.app.notify_async(
                    f"{'Copied' if action == 'copy' else 'Cut'} 1 file to Slot #{slot}"
                )
            else:
                self._report_error(manager.last_error, "Blocked unsafe file selection")
            return

        # 2. Check if invoked from Explorer right-click menu with selected files
        _, shell_files = _consume_shell_context()
        if shell_files:
            if manager.store_files_to_slot(slot, shell_files, action=action):
                self.app.notify_async(
                    f"{'Copied' if action == 'copy' else 'Cut'} {len(shell_files)} file(s) to Slot #{slot}"
                )
            else:
                self._report_error(manager.last_error, "Blocked unsafe file selection")
            return

        time.sleep(min(delay, 0.08))           # let context menu/popup dismiss
        hwnd_target = _get_foreground_window() # capture target document window
        if delay > 0.08:
            time.sleep(delay - 0.08)
        if hwnd_target and _get_foreground_window() != hwnd_target:
            self.app.notify_async("Action cancelled: active window changed", is_error=True)
            return

        seq_before = win_clipboard.get_sequence_number()
        self.app.daemon.send_keys("ctrl+c" if action == "copy" else "ctrl+x")

        changed = False
        for _ in range(15):                    # wait up to 1.5 s for the app/Explorer to update clipboard
            time.sleep(0.1)
            if win_clipboard.get_sequence_number() != seq_before:
                changed = True
                break

        if not changed:
            self.app.notify_async("Highlight text, image, or files first", is_error=True)
            return

        store = manager.copy_to_slot if action == "copy" else manager.cut_to_slot
        if store(slot):
            slot_obj = manager.get_slot(slot)
            badge = f"[{slot_obj.type_badge}] " if slot_obj else ""
            self.app.notify_async(f"{'Copied' if action == 'copy' else 'Cut'} {badge}to Slot #{slot}")
        else:
            self._report_error(manager.last_error, "Nothing valid copied")

    def _paste_into_document(self, action, slot, delay=0.3, direct_target=None):
        manager = self.app.clipboard_manager
        slot_obj = manager.get_slot(slot)
        if slot_obj is None or slot_obj.is_empty:
            self.app.notify_async(f"Slot #{slot} is empty", is_error=True)
            return

        if slot_obj.content_type == SlotContentType.FILES and not config.is_premium:
            from ratt.clipboard_manager import UPGRADE_FILES_MSG
            self._report_error(UPGRADE_FILES_MSG)
            return

        # Check if direct folder path was provided or invoked from Explorer right-click menu
        shell_folder, _ = _consume_shell_context()
        dest_folder = None
        if direct_target and os.path.isdir(direct_target):
            dest_folder = direct_target
        elif shell_folder and os.path.isdir(shell_folder):
            dest_folder = shell_folder

        if dest_folder and slot_obj.content_type == SlotContentType.FILES:
            is_cut = slot_obj.action == SlotAction.CUT
            ok, msg = _safe_copy_or_move_files(slot_obj.files, dest_folder, is_cut=is_cut)
            if ok:
                if is_cut:
                    manager.clear_slot(slot)
                self.app.notify_async(f"Slot #{slot}: {msg}")
            else:
                self._report_error(msg)
            return

        time.sleep(min(delay, 0.05))
        hwnd_target = _get_foreground_window() # capture target document window
        if delay > 0.05:
            time.sleep(delay - 0.05)
        if hwnd_target and _get_foreground_window() != hwnd_target:
            self.app.notify_async("Paste cancelled: active window changed", is_error=True)
            return

        if not manager.paste_from_slot(slot):
            self._report_error(manager.last_error, f"Slot #{slot} is empty")
            return

        time.sleep(0.03)
        if hwnd_target and _get_foreground_window() != hwnd_target:
            self.app.notify_async("Paste cancelled: active window changed", is_error=True)
            return

        self.app.daemon.send_keys("ctrl+v")
        badge = f"[{slot_obj.type_badge}] "
        self.app.notify_async(f"Pasted {badge}from Slot #{slot}")

    # ---- translate (Premium / Enterprise) ----

    def translate(self, language, slot, delay=0.3):
        """Translate a slot and paste the result into the document in front."""
        app = self.app
        if not config.is_premium:
            app.show_main_window()
            app.show_notification("Translate is for Premium and Enterprise users", is_error=True)
            return
        content = app.clipboard_manager.get_slot(slot)
        if content is None or content.is_empty:
            app.show_notification(f"Slot #{slot} is empty", is_error=True)
            return
        if content.content_type not in (SlotContentType.TEXT, SlotContentType.LINK):
            app.show_notification(f"Slot #{slot} holds {content.type_badge} (only text can be translated)", is_error=True)
            return
        if not app.translation.ensure_consent(app.root):
            return
        name = dict(TRANSLATE_LANGUAGES).get(language, language)
        app.show_notification(f"Translating Slot #{slot} to {name}...", duration=1500)
        threading.Thread(target=self._translate_and_paste,
                         args=(content.content, language, name, slot, delay), daemon=True).start()

    def _translate_and_paste(self, text, language, name, slot, delay):
        time.sleep(min(delay, 0.08))
        hwnd_target = _get_foreground_window()
        if delay > 0.08:
            time.sleep(delay - 0.08)
        try:
            translated = self.app.translation.translate(text, language)
        except TranslationError as error:
            self.app.notify_async(str(error), is_error=True)
            return
        if hwnd_target and _get_foreground_window() != hwnd_target:
            self.app.notify_async("Paste cancelled: active window changed during translation", is_error=True)
            return
        ok, clean_trans, _, err = security_guard.sanitize_unformatted_text_and_links(translated)
        if not ok:
            self.app.notify_async(err, is_error=True)
            return
        try:
            pyperclip.copy(clean_trans)
        except pyperclip.PyperclipException:
            pass
        time.sleep(0.15)
        if hwnd_target and _get_foreground_window() != hwnd_target:
            self.app.notify_async("Paste cancelled: active window changed", is_error=True)
            return
        self.app.daemon.send_keys("ctrl+v")
        self.app.notify_async(f"Pasted {name} translation of Slot #{slot}")


def _number(args, index):
    """args[index] as an int, or None."""
    return int(args[index]) if len(args) > index and args[index].isdigit() else None
