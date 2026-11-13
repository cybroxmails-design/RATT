"""RATT Abstract Hardware/OS Abstraction Layer (HAL) Interface.

Isolates all operating-system-specific routines (clipboard multi-format capture,
file routing, keystroke synthesis, single-instance locking, and in-memory buffer
protection) behind a uniform cross-platform contract (`BasePlatform`).
"""
import abc
from typing import Tuple


class BasePlatform(abc.ABC):
    """Abstract base class for Windows, macOS, Linux, and Android HAL drivers."""

    @property
    @abc.abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform identifier ('Windows', 'macOS', 'Linux', 'Android')."""

    @abc.abstractmethod
    def read_clipboard_bundle(self, default_action: str = "copy") -> dict:
        """Read native OS clipboard and return a security-validated bundle dict
        (kind: 'files' | 'diagram' | 'image' | 'link' | 'text')."""

    @abc.abstractmethod
    def restore_clipboard_bundle(self, bundle: dict) -> bool:
        """Write a validated slot bundle back onto the native OS clipboard."""

    def write_clipboard_bundle(self, bundle: dict) -> Tuple[bool, str]:
        """Write a validated slot bundle and return (success: bool, error_message: str)."""
        ok = self.restore_clipboard_bundle(bundle)
        return (True, "") if ok else (False, "Failed to restore clipboard bundle.")

    @abc.abstractmethod
    def inject_keystrokes(self, combo: str) -> None:
        """Inject synthetic keystroke chord (e.g. 'ctrl+c', 'ctrl+x', 'ctrl+v' or 'cmd+c')."""

    @abc.abstractmethod
    def single_instance_acquire(self) -> bool:
        """Acquire OS-level single-instance lock (Win32 Mutex or POSIX fcntl.flock)."""

    @abc.abstractmethod
    def protect_memory_buffer(self, data: bytes) -> bytes:
        """Encrypt or lock sensitive slot buffer in process RAM (DPAPI / mlock / Keystore)."""

    def unprotect_memory_buffer(self, data: bytes, orig_len: int = 0) -> bytes:
        """Decrypt or unlock a buffer previously protected by `protect_memory_buffer`."""
        return data[:orig_len] if orig_len > 0 else data

    def get_foreground_window(self) -> int:
        """Return an integer identifier for the currently focused window (Focus Guard)."""
        return 0

    def get_sequence_number(self) -> int:
        """Return a monotonic counter that increments when the OS clipboard changes."""
        return 0
