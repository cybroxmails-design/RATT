"""One RATT at a time.

The first RATT takes a named mutex and creates a "show yourself" event. A second launch
(double-clicking the logo again) finds the mutex taken, signals the event and exits, so
clicking the logo many times never opens many windows. Both objects are local to the
user's session and carry no data - nothing for another program to talk to.
"""
import ctypes
import os
import threading
from ctypes import wintypes

MUTEX_NAME = "Local\\RATT.App.v2"
SHOW_EVENT_NAME = "Local\\RATT.Show.v2"
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CreateEventW.restype = wintypes.HANDLE
_kernel32.OpenEventW.restype = wintypes.HANDLE
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.FindWindowW.restype = wintypes.HWND
_user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
_user32.FindWindowExW.restype = wintypes.HWND
_user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

_mutex = None
_show_event = None


def _is_ratt_process(pid: int) -> bool:
    """Verify the target PID belongs to a RATT or Python interpreter process."""
    proc = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not proc:
        return False
    try:
        buf = ctypes.create_unicode_buffer(1024)
        sz = wintypes.DWORD(1024)
        if _kernel32.QueryFullProcessImageNameW(proc, 0, buf, ctypes.byref(sz)):
            exe = os.path.basename(buf.value).lower()
            return exe in ("ratt.exe", "python.exe", "pythonw.exe", "rundll32.exe")
        return False
    finally:
        _kernel32.CloseHandle(proc)


def _stop_legacy_instances():
    """Terminate any stale pre-v2 RATT or daemon process left running in the tray."""
    my_pid = os.getpid()
    hwnds = [
        _user32.FindWindowW(None, "RATT \u2014 Rapid Access To Text"),
        _user32.FindWindowW(None, "RATT v2 \u2014 Rapid Access To Text"),
        _user32.FindWindowExW(ctypes.c_void_p(-3), None, "RATTDaemonWnd", None),
    ]
    for hwnd in hwnds:
        if not hwnd:
            continue
        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value and pid.value != my_pid and _is_ratt_process(pid.value):
            proc = _kernel32.OpenProcess(PROCESS_TERMINATE, False, pid.value)
            if proc:
                _kernel32.TerminateProcess(proc, 0)
                _kernel32.CloseHandle(proc)


def acquire():
    """True if this is the first RATT; False if one is already running."""
    global _mutex, _show_event
    _mutex = _kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return False
    # We are the primary v2 instance — ensure no legacy v1 tray process is still running
    try:
        _stop_legacy_instances()
    except Exception:
        pass
    _show_event = _kernel32.CreateEventW(None, False, False, SHOW_EVENT_NAME)   # auto-reset
    return True


def request_show(bring_to_front: bool = True):
    """Ask the running RATT to process pending actions and optionally bring its window to the front."""
    if os.name != "nt":
        return
    event = _kernel32.OpenEventW(EVENT_MODIFY_STATE, False, SHOW_EVENT_NAME)
    if event:
        _kernel32.SetEvent(event)
        _kernel32.CloseHandle(event)
    if bring_to_front:
        for title in ("RATT v2 \u2014 Rapid Access To Text", "RATT \u2014 Rapid Access To Text"):
            hwnd = _user32.FindWindowW(None, title)
            if hwnd:
                _user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                _user32.SetForegroundWindow(hwnd)


def watch_for_show(callback):
    """Call `callback()` (on a worker thread) every time another launch asks to show RATT."""
    if not _show_event:
        return

    def wait():
        while _kernel32.WaitForSingleObject(_show_event, 0xFFFFFFFF) == 0:
            callback()

    threading.Thread(target=wait, daemon=True).start()
