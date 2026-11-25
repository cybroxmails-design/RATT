"""Where RATT's files live, and how its native helpers (assets\*.dll) get installed.

The helpers are copied out of the application bundle into %APPDATA%\RATT\native under a
name that contains the file's hash. Two reasons: a PyInstaller bundle is unpacked to a
temporary folder that disappears when RATT exits, and Windows Explorer keeps a loaded
shell extension locked, so a new version must be able to sit next to the old one.
"""
import ctypes
import hashlib
import os
import shutil
import sys


def app_dir():
    """Folder that holds the source tree (or the bundle contents when frozen)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def assets_dir():
    return os.path.join(app_dir(), "assets")


def data_dir():
    """Per-user folder for session, logs and installed helpers."""
    folder = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RATT")
    os.makedirs(folder, exist_ok=True)
    return folder


def log(name, message):
    """Append one line to %APPDATA%\\RATT\\<name>.log (capped at 1 MB); never raises."""
    import time
    try:
        log_path = os.path.join(data_dir(), f"{name}.log")
        mode = "a"
        if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 1024:
            mode = "w"
        with open(log_path, mode, encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def launch_command():
    """(program, argument prefix) that starts RATT - used by the right-click menu when
    RATT is not running yet."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    native_exe = os.path.join(data_dir(), "native", "RATT.exe")
    dist_exe = os.path.join(app_dir(), "dist", "RATT.exe")
    if os.path.exists(dist_exe):
        try:
            os.makedirs(os.path.dirname(native_exe), exist_ok=True)
            if not os.path.exists(native_exe):
                shutil.copyfile(dist_exe, native_exe)
        except OSError:
            pass
    return native_exe, ""


def _file_sha256(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def install(name):
    """Return the installed Program Files path when present, or copy `assets\\<name>`
    into the per-user native directory."""
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf_candidate = os.path.join(prog_files, "RATT", name)
    if os.path.exists(pf_candidate):
        return pf_candidate
    if getattr(sys, "frozen", False):
        exe_candidate = os.path.join(os.path.dirname(sys.executable), name)
        if os.path.exists(exe_candidate):
            return exe_candidate

    source = os.path.join(assets_dir(), name)
    with open(source, "rb") as f:
        data = f.read()
    expected_sha256 = hashlib.sha256(data).hexdigest()
    stem, ext = os.path.splitext(name)
    folder = os.path.join(data_dir(), "native")
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, f"{stem}_{hashlib.sha1(data).hexdigest()[:8]}{ext}")
    try:
        if not os.path.exists(target) or _file_sha256(target) != expected_sha256:
            shutil.copyfile(source, target)
        for other in os.listdir(folder):               # remove older versions (best effort)
            path = os.path.join(folder, other)
            if other.startswith(stem + "_") and other.endswith(ext) and path != target:
                try:
                    os.remove(path)
                except OSError:
                    pass
    except OSError:
        if os.path.exists(source):
            return source
    if not can_load(target) and can_load(source):
        return source
    return target


def can_load(path):
    """True if Windows lets this process load the DLL. An unsigned file can be refused
    by an Application Control policy (and accepted again later), so callers retry.
    SEM_FAILCRITICALERRORS suppresses the system 'Bad Image' (0xc0e90002) modal popup."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        SEM_FAILCRITICALERRORS = 0x0001
        old_mode = kernel32.SetErrorMode(SEM_FAILCRITICALERRORS)
        try:
            kernel32.LoadLibraryW.argtypes = [ctypes.c_wchar_p]
            kernel32.LoadLibraryW.restype = ctypes.c_void_p
            kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]
            handle = kernel32.LoadLibraryW(path)
            if not handle:
                return False
            kernel32.FreeLibrary(handle)
            return True
        finally:
            kernel32.SetErrorMode(old_mode)
    except (OSError, Exception):
        return False
