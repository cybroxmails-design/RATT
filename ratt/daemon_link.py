"""Link between the Python app and the native helper (assets\ratt_daemon.dll).

The helper is a small DLL run by rundll32.exe. It owns what must be instant and must not
look like a keylogger: the global hotkeys (RegisterHotKey, no keyboard hook), the Ctrl+C /
Ctrl+V sent to the document in front, and the receiving end of the right-click menu.

    app -> helper   WM_COPYDATA text commands: STATE ..., KEYS ctrl+v, ACTION ..., SHOW
    helper -> app   one line per event on the pipe \\\\.\\pipe\\RATT.events.<app pid>

The full protocol is documented at the top of daemon\\ratt_daemon.c.
"""
import ctypes
import json
import os
import socket
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from typing import List, Optional, Tuple

from ratt import hal, native
from ratt.config import config

COPYDATA_MAGIC = 0x52415454            # "RATT"
WINDOW_CLASS = "RATTDaemonWnd"
RETRY_SECONDS = 60                     # how often to retry while Windows refuses the helper

_IS_WIN = os.name == "nt"
_IS_MAC = sys.platform == "darwin"

if _IS_WIN:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.FindWindowExW.restype = wintypes.HWND
    _user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    _user32.CreateWindowExW.restype = wintypes.HWND
    _user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    _user32.SendMessageTimeoutW.restype = wintypes.LPARAM
    _user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                            wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
else:
    _user32 = None

_client_hwnd = None


def _get_client_hwnd():
    """Return a hidden HWND owned by this process so the daemon can verify our PID."""
    global _client_hwnd
    if not _IS_WIN or not _user32:
        return 0
    if not _client_hwnd:
        _client_hwnd = _user32.CreateWindowExW(
            0, "STATIC", "RATTClient", 0, 0, 0, 0, 0, None, None, None, None
        )
    return _client_hwnd or 0


class _CopyData(ctypes.Structure):
    _fields_ = [("dwData", ctypes.c_size_t), ("cbData", wintypes.DWORD), ("lpData", ctypes.c_void_p)]


def _helper_window():
    if not _IS_WIN or not _user32:
        return 0
    return _user32.FindWindowExW(ctypes.c_void_p(-3), None, WINDOW_CLASS, None)   # HWND_MESSAGE


def send_command(text):
    """Deliver a command to the running helper. False if it is not running."""
    if not _IS_WIN or not _user32:
        return False
    window = _helper_window()
    if not window:
        return False
    data = text.encode("utf-8")
    buffer = ctypes.create_string_buffer(data)
    copy = _CopyData(COPYDATA_MAGIC, len(data), ctypes.cast(buffer, ctypes.c_void_p))
    result = ctypes.c_size_t()
    WM_COPYDATA, SMTO_ABORTIFHUNG = 0x4A, 0x2
    sender = _get_client_hwnd()
    return bool(_user32.SendMessageTimeoutW(window, WM_COPYDATA, sender, ctypes.addressof(copy),
                                            SMTO_ABORTIFHUNG, 1500, ctypes.byref(result)))


# ---- keystrokes -------------------------------------------------------------------

_VK = {"ctrl": 0x11, "c": 0x43, "x": 0x58, "v": 0x56}


class _KeyboardInput(ctypes.Structure):
    _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class _MouseInput(ctypes.Structure):               # only here to give INPUT its real size
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class _Input(ctypes.Structure):
    class _Union(ctypes.Union):
        _fields_ = [("ki", _KeyboardInput), ("mi", _MouseInput)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _Union)]


def send_keys_directly(combo):
    """Fallback when the helper is not running: send e.g. 'ctrl+v' with SendInput or macOS Quartz."""
    if _IS_MAC:
        try:
            hal.get_platform().inject_keystrokes(combo)
        except Exception:
            pass
        return
    if not _IS_WIN:
        return
    keys = [_VK[k] for k in combo.split("+") if k in _VK]
    if not keys:
        return
    KEYEVENTF_KEYUP = 2
    events = [(vk, 0) for vk in keys] + [(vk, KEYEVENTF_KEYUP) for vk in reversed(keys)]
    inputs = (_Input * len(events))()
    for slot, (vk, flags) in zip(inputs, events):
        slot.type = 1                               # INPUT_KEYBOARD
        slot.ki = _KeyboardInput(vk, 0, flags, 0, 0)
    ctypes.windll.user32.SendInput(len(events), inputs, ctypes.sizeof(_Input))


# ---- the link ---------------------------------------------------------------------

class FallbackHotkeyEngine:
    """Seamless pure-Python chord hotkey engine used when rundll32/ratt_daemon.dll is restricted."""

    def __init__(self, app):
        self.app = app
        self._running = False
        self._chord_action = None
        self._chord_timer = None
        self._digit_timer = None
        self._digits = ""
        self._lock = threading.RLock()
        self._ignore_until = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        try:
            import keyboard
            keyboard.on_press(self._on_key_press, suppress=False)
            try:
                keyboard.add_hotkey("ctrl+shift+r", lambda: self.app.queue_action("popup", []), suppress=True)
            except Exception:
                pass
            try:
                keyboard.add_hotkey("ctrl+alt+p", lambda: self.app.queue_action("toggle-enabled", []), suppress=True)
            except Exception:
                pass
            native.log("daemon", "Python fallback hotkey engine active")
        except Exception as e:
            native.log("daemon", f"Python fallback hotkey failed: {e}")

    def stop(self):
        self._running = False
        self._cancel_chord()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass

    def ignore_for(self, seconds: float):
        self._ignore_until = time.time() + seconds
        self._cancel_chord()

    def _on_key_press(self, event):
        if not self._running or time.time() < self._ignore_until or not config.enabled:
            return

        name = event.name.lower() if event.name else ""

        # Digits while a chord is active build the slot number
        if self._chord_action and name in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
            self._on_digit(name)
            return

        # Detect Ctrl+C, Ctrl+X, Ctrl+V
        try:
            import keyboard
            ctrl = keyboard.is_pressed('ctrl')
            shift = keyboard.is_pressed('shift')
            alt = keyboard.is_pressed('alt')

            if ctrl and not shift and not alt:
                if name == 'c':
                    self._start_chord('copy')
                elif name == 'x':
                    self._start_chord('cut')
                elif name == 'v':
                    self._start_chord('paste')
        except Exception:
            pass

    def _start_chord(self, action: str):
        with self._lock:
            self._cancel_chord()
            self._chord_action = action
            self._digits = ""
            timeout = config.CHORD_TIMEOUT if action != 'paste' else config.PASTE_SLOT_DELAY
            self._chord_timer = threading.Timer(timeout, self._cancel_chord)
            self._chord_timer.daemon = True
            self._chord_timer.start()

    def _on_digit(self, d: str):
        with self._lock:
            if self._chord_timer:
                self._chord_timer.cancel()
                self._chord_timer = None
            if self._digit_timer:
                self._digit_timer.cancel()
                self._digit_timer = None

            if not self._digits and d == '0':
                self._execute_chord(10)
                return

            self._digits += d
            max_slots = config.max_slots
            try:
                n = int(self._digits)
            except ValueError:
                self._cancel_chord()
                return

            if n < 1 or n > max_slots:
                self._cancel_chord()
                return

            can_grow = (n * 10 <= max_slots) and len(self._digits) < len(str(max_slots))
            if not can_grow:
                self._execute_chord(n)
            else:
                self._digit_timer = threading.Timer(config.DIGIT_GAP, self._finish_digits)
                self._digit_timer.daemon = True
                self._digit_timer.start()

    def _finish_digits(self):
        with self._lock:
            if self._chord_action and self._digits:
                self._execute_chord(int(self._digits))

    def _execute_chord(self, slot_num: int):
        with self._lock:
            action = self._chord_action
            self._cancel_chord()

        if action:
            self.app.queue_action(f"hotkey-{action}", [str(slot_num)])

    def _cancel_chord(self):
        with self._lock:
            self._chord_action = None
            self._digits = ""
            if self._chord_timer:
                self._chord_timer.cancel()
                self._chord_timer = None
            if self._digit_timer:
                self._digit_timer.cancel()
                self._digit_timer = None


class DaemonLink:
    """Starts the helper, keeps it informed about the slots and turns its events into
    app actions. `tick()` is called from the Tk thread every few hundred milliseconds."""

    def __init__(self, app):
        self.app = app
        self._process = None
        self._lib = None
        self._inproc_thread = None
        self._c_callback = None
        self._state_sent = None
        self._next_start = 0.0
        self._told_user = False
        self._fallback = FallbackHotkeyEngine(app)
        self._mac_finder_started = False
        if _IS_MAC:
            self._start_mac_finder_ipc()

    # -- lifecycle --

    def _is_native_active(self) -> bool:
        if _IS_WIN:
            if self._inproc_thread and self._inproc_thread.is_alive() and _helper_window():
                return True
            if self._process is not None and self._process.poll() is None and _helper_window():
                return True
        return False

    def tick(self):
        if self._is_native_active():
            if self._fallback and self._fallback._running:
                self._fallback.stop()
            self._sync_state()
            return

        if time.time() >= self._next_start:
            self._start()

        if not self._is_native_active():
            if self._fallback and not self._fallback._running and config.enabled:
                self._fallback.start()
        else:
            if self._fallback and self._fallback._running:
                self._fallback.stop()
            self._sync_state()

    def _start(self):
        self._next_start = time.time() + RETRY_SECONDS
        if _IS_MAC:
            self._start_mac_finder_ipc()
            return
        if not _IS_WIN:
            return
        try:
            dll = native.install("ratt_daemon.dll")
        except OSError as error:
            native.log("daemon", f"cannot install helper: {error!r}")
            self._fallback.start()
            return
        if not native.can_load(dll):
            native.log("daemon", "Windows refused to load the helper (Application Control) - activating fallback engine")
            self._fallback.start()
            return

        # Primary mode: load ratt_daemon.dll in-process on a dedicated thread via ctypes.
        # Avoids Windows 11 Smart App Control blocking rundll32.exe on unsigned DLLs in %APPDATA%.
        try:
            lib = ctypes.WinDLL(dll)
            if hasattr(lib, "SetEventCallback") and hasattr(lib, "RunDaemonW"):
                CB_TYPE = ctypes.WINFUNCTYPE(None, ctypes.c_char_p)

                def _on_c_event(raw_line):
                    if raw_line:
                        try:
                            self._handle_event(raw_line.decode("utf-8", "replace").strip())
                        except Exception:
                            pass

                self._c_callback = CB_TYPE(_on_c_event)
                lib.SetEventCallback.argtypes = [CB_TYPE]
                lib.SetEventCallback.restype = None
                lib.SetEventCallback(self._c_callback)

                fn = lib.RunDaemonW
                fn.argtypes = [wintypes.HWND, wintypes.HINSTANCE, wintypes.LPWSTR, ctypes.c_int]
                fn.restype = None
                self._lib = lib
                self._state_sent = None
                self._inproc_thread = threading.Thread(
                    target=fn,
                    args=(None, None, f"--parent {os.getpid()}", 0),
                    daemon=True,
                    name="RATTDaemonInProc",
                )
                self._inproc_thread.start()
                for _ in range(15):
                    if _helper_window():
                        break
                    time.sleep(0.02)
                if _helper_window():
                    if self._fallback and self._fallback._running:
                        self._fallback.stop()
                    self._sync_state()
                    native.log("daemon", "In-process native hotkey & shell daemon active")
                    return
        except Exception as e:
            native.log("daemon", f"In-process daemon load failed ({e}), trying rundll32 fallback")

        try:
            self._process = subprocess.Popen(
                ["rundll32.exe", f"{dll},RunDaemonW", "--parent", str(os.getpid())],
                creationflags=subprocess.CREATE_NO_WINDOW)
            self._state_sent = None
            threading.Thread(target=self._read_events, daemon=True).start()
        except Exception as e:
            native.log("daemon", f"rundll32 spawn failed: {e} - activating fallback engine")
            self._fallback.start()

    def _start_mac_finder_ipc(self):
        """Listen on ~/Library/Application Support/RATT/finder_ipc.sock for macOS FinderSync file Copy/Cut/Paste."""
        if not _IS_MAC or self._mac_finder_started:
            return
        self._mac_finder_started = True

        def _server():
            sock_dir = os.path.expanduser("~/Library/Application Support/RATT")
            os.makedirs(sock_dir, mode=0o700, exist_ok=True)
            sock_path = os.path.join(sock_dir, "finder_ipc.sock")
            try:
                if os.path.exists(sock_path):
                    os.unlink(sock_path)
            except Exception:
                pass
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                srv.bind(sock_path)
                os.chmod(sock_path, 0o600)
                srv.listen(8)
                while True:
                    conn, _ = srv.accept()
                    with conn:
                        raw = conn.recv(65536).decode("utf-8", "replace").strip()
                        if not raw:
                            continue
                        for line in raw.splitlines():
                            try:
                                msg = json.loads(line)
                                act = str(msg.get("action", "")).lower()
                                slot = int(msg.get("slot", 1))
                                files = msg.get("files") or []
                                folder = msg.get("folder") or ""
                                if act in ("copy", "cut") and files:
                                    self.app.queue_action(act, [str(slot)] + [str(f) for f in files])
                                elif act == "paste" and folder:
                                    self.app.queue_action("paste", [str(slot), str(folder)])
                            except Exception:
                                pass
            except Exception:
                pass
            finally:
                try:
                    srv.close()
                except Exception:
                    pass

        threading.Thread(target=_server, daemon=True, name="RATTMacFinderIPC").start()

    def query_explorer_context(self, target_hwnd: Optional[int] = None) -> Tuple[Optional[str], List[str]]:
        """Query the active Windows File Explorer (or macOS Finder) window for its current folder and selected files."""
        if _IS_MAC:
            plat = hal.get_platform()
            if hasattr(plat, "get_finder_selection_and_folder"):
                return plat.get_finder_selection_and_folder()
            return None, []
        if not _IS_WIN:
            return None, []
        try:
            lib = self._lib
            if lib is None:
                dll = native.install("ratt_daemon.dll")
                if native.can_load(dll):
                    lib = ctypes.WinDLL(dll)
                    self._lib = lib
            if lib and hasattr(lib, "GetExplorerSelectionW"):
                fn = lib.GetExplorerSelectionW
                fn.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
                fn.restype = ctypes.c_int
                buf = ctypes.create_unicode_buffer(16384)
                hwnd_arg = wintypes.HWND(target_hwnd) if target_hwnd else None
                if fn(hwnd_arg, buf, 16384):
                    folder: Optional[str] = None
                    files: List[str] = []
                    for line in buf.value.splitlines():
                        line = line.strip()
                        if line.startswith("FOLDER\t"):
                            folder = line.split("\t", 1)[1].strip()
                        elif line.startswith("FILE\t"):
                            fp = line.split("\t", 1)[1].strip()
                            if fp:
                                files.append(fp)
                    return folder, files
        except Exception:
            pass
        return None, []

    # -- app -> helper --

    def _sync_state(self):
        """Tell the helper whenever login, enabled toggle, plan or the filled slots change."""
        filled = tuple(sorted(self.app.clipboard_manager.get_all_slots()))
        state = (config.user.is_logged_in, config.enabled, config.max_slots, filled)
        if state == self._state_sent:
            return
        text = (f"STATE login={int(state[0])} enabled={int(state[1])} max={state[2]} "
                f"paste={int(config.PASTE_SLOT_DELAY * 1000)} gap={int(config.DIGIT_GAP * 1000)} "
                f"chord={int(config.CHORD_TIMEOUT * 1000)} filled={','.join(map(str, filled))}")
        if send_command(text):
            self._state_sent = state

    def sync_now(self):
        """Force an immediate STATE sync with the native helper (e.g. on ON/OFF toggle)."""
        self._state_sent = None
        self._sync_state()
        if hasattr(self, "_fallback") and self._fallback:
            if config.enabled and not self._is_native_active():
                self._fallback.start()
            else:
                self._fallback.stop()

    def send_keys(self, combo):
        """Send 'ctrl+c' / 'ctrl+x' / 'ctrl+v' to the document in front."""
        if hasattr(self, "_fallback") and self._fallback:
            self._fallback.ignore_for(0.3)
        if not send_command("KEYS " + combo):
            send_keys_directly(combo)

    # -- helper -> app --

    def _read_events(self):
        pipe = None
        path = rf"\\.\pipe\RATT.events.{os.getpid()}"
        deadline = time.time() + 3
        while pipe is None and time.time() < deadline:
            try:
                pipe = open(path, "rb")
            except OSError:
                time.sleep(0.1)
        if pipe is None:
            native.log("daemon", "helper started but event pipe did not connect - activating fallback engine")
            self._fallback.start()
            return
        with pipe:
            for line in pipe:
                self._handle_event(line.decode("utf-8", "replace").strip())

    def _handle_event(self, line):
        parts = line.split()
        if not parts:
            return
        kind, args = parts[0], parts[1:]
        if kind == "HK" and len(args) == 2:                  # HK copy 3
            self.app.queue_action("hotkey-" + args[0], [args[1]])
        elif kind == "TOGGLE":                                # Emergency hotkey (Ctrl+Alt+P / Win+Shift+Pause)
            self.app.queue_action("toggle-enabled", [])
        elif kind == "POPUP":
            self.app.queue_action("popup", [])
        elif kind == "SHOW":
            self.app.queue_action("open", [])
        elif kind == "ACTION" and args:                       # right-click menu
            self.app.queue_action(args[0], args[1:3])
        elif kind == "ERR" and len(args) == 2:                # ERR hotkey-in-use Ctrl+C
            reason = ("is already used by another program" if args[0] == "hotkey-in-use"
                      else "could not be registered with Windows")
            self.app.notify_async(f"RATT hotkey {args[1]} {reason}", is_error=True)
