"""RATT Multi-Slot Clipboard Manager."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Callable, List
import pyperclip
import threading


class SlotAction(Enum):
    """Type of clipboard action."""
    COPY = "copy"
    CUT = "cut"


@dataclass
class ClipboardSlot:
    """A single clipboard slot storing copied/cut data."""
    content: str = ""
    timestamp: Optional[datetime] = None
    action: SlotAction = SlotAction.COPY
    source_app: str = ""
    
    @property
    def preview(self) -> str:
        """Get a short preview of the content (first 50 chars)."""
        if not self.content:
            return "(empty)"
        text = self.content.replace('\n', ' ').strip()
        if len(text) > 50:
            return text[:47] + "..."
        return text
    
    @property
    def is_empty(self) -> bool:
        return not self.content
    
    @property
    def char_count(self) -> int:
        return len(self.content)


class ClipboardManager:
    """Manages multiple clipboard slots for RATT."""
    
    def __init__(self, config):
        """Initialize with app config."""
        self.config = config
        self._slots: Dict[int, ClipboardSlot] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        self.last_used_slot: Optional[int] = None   # most recent slot copied/cut/pasted
    
    def add_listener(self, callback: Callable):
        """Add a listener that gets called when slots change."""
        self._listeners.append(callback)
    
    def _notify_listeners(self):
        """Notify all listeners of a slot change."""
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                pass
    
    def copy_to_slot(self, slot_num: int, text: Optional[str] = None) -> bool:
        """Copy text to a numbered slot. If text is None, reads from system clipboard."""
        if not self._is_valid_slot(slot_num):
            return False
        if text is None:
            try:
                text = pyperclip.paste()
            except Exception:
                return False
        if not text:
            return False
        with self._lock:
            self._slots[slot_num] = ClipboardSlot(
                content=text,
                timestamp=datetime.now(),
                action=SlotAction.COPY
            )
            self.last_used_slot = slot_num
        self._notify_listeners()
        return True
    
    def cut_to_slot(self, slot_num: int, text: Optional[str] = None) -> bool:
        """Cut text to a numbered slot. If text is None, reads from system clipboard."""
        if not self._is_valid_slot(slot_num):
            return False
        if text is None:
            try:
                text = pyperclip.paste()
            except Exception:
                return False
        if not text:
            return False
        with self._lock:
            self._slots[slot_num] = ClipboardSlot(
                content=text,
                timestamp=datetime.now(),
                action=SlotAction.CUT
            )
            self.last_used_slot = slot_num
        self._notify_listeners()
        return True
    
    def paste_from_slot(self, slot_num: int) -> Optional[str]:
        """Paste from a numbered slot. Copies content to system clipboard and returns it."""
        with self._lock:
            slot = self._slots.get(slot_num)
        if slot is None or slot.is_empty:
            return None
        changed = self.last_used_slot != slot_num
        self.last_used_slot = slot_num
        try:
            pyperclip.copy(slot.content)
        except Exception:
            pass
        if changed:
            self._notify_listeners()   # menu label 'Translate Slot N' follows the active slot
        return slot.content
    
    def get_slot(self, slot_num: int) -> Optional[ClipboardSlot]:
        """Get a specific slot."""
        with self._lock:
            return self._slots.get(slot_num)
    
    def active_slot(self) -> Optional[int]:
        """Slot that translate acts on: the last slot used, else the lowest filled slot."""
        with self._lock:
            s = self._slots.get(self.last_used_slot) if self.last_used_slot else None
            if s is not None and not s.is_empty:
                return self.last_used_slot
            filled = sorted(k for k, v in self._slots.items() if not v.is_empty)
            return filled[0] if filled else None

    def get_all_slots(self) -> Dict[int, ClipboardSlot]:
        """Get all non-empty slots."""
        with self._lock:
            return {k: v for k, v in self._slots.items() if not v.is_empty}
    
    def clear_slot(self, slot_num: int):
        """Clear a specific slot."""
        with self._lock:
            self._slots.pop(slot_num, None)
        self._notify_listeners()
    
    def clear_all(self):
        """Clear all slots. Called on app exit per requirement #11."""
        with self._lock:
            self._slots.clear()
        self._notify_listeners()
    
    def get_available_slot_numbers(self) -> List[int]:
        """Get list of available slot numbers based on user tier."""
        return list(range(1, self.config.max_slots + 1))
    
    def _is_valid_slot(self, slot_num: int) -> bool:
        """Check if slot number is valid for current user tier."""
        return 1 <= slot_num <= self.config.max_slots
