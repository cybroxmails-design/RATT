"""RATT Hardware/OS Abstraction Layer (`ratt/hal/`).

Auto-detects the active operating system (`sys.platform` / `ANDROID_ROOT`) and
instantiates the matching `BasePlatform` driver:
  - Windows (`win32`): `Win32Platform` (`ratt.hal.win32`)
  - macOS (`darwin`): `MacOSPlatform` (`ratt.hal.macos`)
  - Linux (`linux`): `LinuxPlatform` (`ratt.hal.linux`)
  - Android (`ANDROID_ROOT` or `android` bridge): `AndroidBridgePlatform` (`ratt.hal.android_bridge`)
  - iPhone/iPad keyboard (paired over Wi-Fi): `IOSBridgePlatform` (`ratt.hal.ios_bridge`)
"""
import os
import sys
from typing import Optional

from ratt.hal.base import BasePlatform
from ratt.hal.win32 import Win32Platform
from ratt.hal.macos import MacOSPlatform
from ratt.hal.linux import LinuxPlatform
from ratt.hal.android_bridge import AndroidBridgePlatform, check_android_entitlement
from ratt.hal.ios_bridge import IOSBridgePlatform, check_ios_entitlement

_current_hal: Optional[BasePlatform] = None
_android_bridge = None
_ios_bridge = None


def detect_platform(target_os: Optional[str] = None) -> BasePlatform:
    """Instantiate the `BasePlatform` implementation for `target_os` (or auto-detect)."""
    plat = (target_os or sys.platform).lower()
    if plat == "android" or ("ANDROID_ROOT" in os.environ and target_os is None):
        from ratt.hal.android_bridge import AndroidBridgePlatform
        return AndroidBridgePlatform()
    if plat in ("ios", "iphone", "ipados"):
        from ratt.hal.ios_bridge import IOSBridgePlatform
        return IOSBridgePlatform()
    if plat.startswith("win"):
        from ratt.hal.win32 import Win32Platform
        return Win32Platform()
    if plat == "darwin" or plat == "macos":
        from ratt.hal.macos import MacOSPlatform
        return MacOSPlatform()
    if plat.startswith("linux"):
        from ratt.hal.linux import LinuxPlatform
        return LinuxPlatform()
    # Fallback to Windows HAL on unknown desktop environments
    from ratt.hal.win32 import Win32Platform
    return Win32Platform()


def get_platform() -> BasePlatform:
    """Return the singleton `BasePlatform` instance for the current OS."""
    global _current_hal
    if _current_hal is None:
        _current_hal = detect_platform()
    return _current_hal


def get_android_bridge(app_config=None):
    """Return the Android Virtual Keyboard (IME) Bridge singleton instance."""
    global _android_bridge
    if _android_bridge is None:
        _android_bridge = AndroidBridgePlatform(app_config=app_config)
    elif app_config is not None:
        _android_bridge._app_config = app_config
    return _android_bridge


def get_ios_bridge(app_config=None):
    """Return the iPhone keyboard bridge singleton instance."""
    global _ios_bridge
    if _ios_bridge is None:
        _ios_bridge = IOSBridgePlatform(app_config=app_config)
    elif app_config is not None:
        _ios_bridge._config = app_config
    return _ios_bridge


__all__ = [
    "BasePlatform",
    "Win32Platform",
    "MacOSPlatform",
    "LinuxPlatform",
    "AndroidBridgePlatform",
    "check_android_entitlement",
    "IOSBridgePlatform",
    "check_ios_entitlement",
    "get_ios_bridge",
    "detect_platform",
    "get_platform",
    "get_android_bridge",
]
