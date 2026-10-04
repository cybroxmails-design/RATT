"""RATT Cross-Device Sync (Phase 2 Stub).

This module defines the interface for cross-device clipboard synchronization.
In Phase 2, this would connect to a cloud server via WebSocket for real-time sync.
"""
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SyncStatus(Enum):
    """Sync connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class SyncEvent:
    """A sync event from another device."""
    event_type: str  # "copy", "cut", "clear"
    slot_num: int
    content: str = ""
    source_device: str = ""


class SyncManager:
    """Manages cross-device clipboard synchronization.
    
    Phase 2 Implementation Notes:
    - Use WebSocket connection to a relay server
    - All data encrypted with Signal Protocol before transmission
    - Server never sees plaintext clipboard data
    - Support for multiple simultaneous device connections
    """
    
    def __init__(self):
        self._status = SyncStatus.DISCONNECTED
        self._device_id: str = ""
        self._on_sync_event: Optional[Callable[[SyncEvent], None]] = None
    
    @property
    def status(self) -> SyncStatus:
        """Get current sync status."""
        return self._status
    
    @property
    def is_connected(self) -> bool:
        return self._status == SyncStatus.CONNECTED
    
    def connect(self, user_token: str) -> bool:
        """Connect to sync server. (Stub)"""
        print(f"[Sync Stub] Would connect with token: {user_token[:8]}...")
        self._status = SyncStatus.DISCONNECTED
        return False
    
    def disconnect(self):
        """Disconnect from sync server. (Stub)"""
        self._status = SyncStatus.DISCONNECTED
    
    def push_slot(self, slot_num: int, content: str, action: str) -> bool:
        """Push a slot update to other devices. (Stub)"""
        print(f"[Sync Stub] Would push slot {slot_num} ({action})")
        return False
    
    def set_sync_listener(self, callback: Callable[[SyncEvent], None]):
        """Set callback for incoming sync events. (Stub)"""
        self._on_sync_event = callback
    
    def get_status_text(self) -> str:
        """Get human-readable status text."""
        status_map = {
            SyncStatus.DISCONNECTED: "Not connected (Phase 2)",
            SyncStatus.CONNECTING: "Connecting...",
            SyncStatus.CONNECTED: "Connected",
            SyncStatus.ERROR: "Connection error",
        }
        return status_map.get(self._status, "Unknown")
