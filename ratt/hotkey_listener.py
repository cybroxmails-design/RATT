"""RATT Global Hotkey Listener.

Implements chord-based keyboard shortcuts:
- Ctrl+C, then a slot number: Copy to slot
- Ctrl+X, then a slot number: Cut to slot
- Ctrl+V, then a slot number: Paste from slot
- Ctrl+Shift+R: Open RATT popup

Slot numbers can have several digits (type 1 then 0 for slot 10). A number that
could still grow into a valid slot (e.g. "1" when slot 10+ exist) waits a short
moment for the next digit; otherwise it runs immediately.
"""
import keyboard
import threading
import time
from typing import Callable, Optional
from ratt.config import config

DIGITS = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')
DIGIT_GAP = 0.8   # seconds to wait for another digit of a multi-digit slot number


class HotkeyListener:
    """Listens for global hotkey chords."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._chord_active = False
        self._chord_action: Optional[str] = None  # 'copy', 'cut', 'paste'
        self._chord_timer: Optional[threading.Timer] = None
        self._digits = ""
        self._digit_timer: Optional[threading.Timer] = None
        self._ignore_until = 0.0
        self._lock = threading.RLock()

        # Callbacks
        self.on_copy_to_slot: Optional[Callable[[int], None]] = None
        self.on_cut_to_slot: Optional[Callable[[int], None]] = None
        self.on_paste_from_slot: Optional[Callable[[int], None]] = None
        self.on_popup_requested: Optional[Callable[[], None]] = None

    def start(self):
        """Start listening for hotkeys."""
        if self._running:
            return
        self._running = True

        # We hook into Ctrl+C/X/V AFTER they fire (so normal copy/cut/paste still works)
        # Then listen for slot digits within the chord timeout
        keyboard.on_press(self._on_key_press, suppress=False)

        # Register popup hotkey
        keyboard.add_hotkey(config.POPUP_HOTKEY, self._on_popup_hotkey, suppress=True)

    def stop(self):
        """Stop listening for hotkeys."""
        self._running = False
        self._cancel_chord()
        try:
            keyboard.unhook_all()
        except Exception:
            pass

    def ignore_for(self, seconds: float):
        """Ignore key events for a moment (used while RATT sends its own Ctrl+C/V)."""
        self._ignore_until = time.time() + seconds
        self._cancel_chord()

    def _on_key_press(self, event):
        """Handle key press events."""
        if not self._running or time.time() < self._ignore_until:
            return

        # Digits while a chord is active build the slot number
        if self._chord_active and event.name in DIGITS:
            self._on_digit(event.name)
            return

        # Detect Ctrl+C, Ctrl+X, Ctrl+V
        plain_ctrl = (keyboard.is_pressed('ctrl') and not keyboard.is_pressed('shift')
                      and not keyboard.is_pressed('alt'))
        if event.name == 'c' and plain_ctrl:
            self._start_chord('copy')
        elif event.name == 'x' and plain_ctrl:
            self._start_chord('cut')
        elif event.name == 'v' and plain_ctrl:
            self._start_chord('paste')

    def _start_chord(self, action: str):
        """Start a chord sequence."""
        with self._lock:
            self._cancel_chord()
            self._chord_active = True
            self._chord_action = action
            self._digits = ""

            # Set timeout to cancel chord
            self._chord_timer = threading.Timer(config.CHORD_TIMEOUT, self._cancel_chord)
            self._chord_timer.daemon = True
            self._chord_timer.start()

    def _on_digit(self, d: str):
        """Add a digit to the slot number; run now or wait for more digits."""
        with self._lock:
            # From here on the digit gap timer (not the chord timeout) is in charge
            if self._chord_timer:
                self._chord_timer.cancel()
                self._chord_timer = None
            if self._digit_timer:
                self._digit_timer.cancel()
                self._digit_timer = None

            if not self._digits and d == '0':
                self._execute_chord(10)            # legacy: 0 alone = slot 10
                return

            self._digits += d
            max_slots = config.max_slots
            n = int(self._digits)
            if n < 1 or n > max_slots:
                self._cancel_chord()               # not a valid slot
                return

            can_grow = (n * 10 <= max_slots) and len(self._digits) < len(str(max_slots))
            if not can_grow:
                self._execute_chord(n)
            else:
                self._digit_timer = threading.Timer(DIGIT_GAP, self._finish_digits)
                self._digit_timer.daemon = True
                self._digit_timer.start()

    def _finish_digits(self):
        with self._lock:
            if self._chord_active and self._digits:
                self._execute_chord(int(self._digits))

    def _execute_chord(self, slot_num: int):
        """Execute the chord action."""
        with self._lock:
            action = self._chord_action
            self._cancel_chord()

        if action == 'copy' and self.on_copy_to_slot:
            self.on_copy_to_slot(slot_num)
        elif action == 'cut' and self.on_cut_to_slot:
            self.on_cut_to_slot(slot_num)
        elif action == 'paste' and self.on_paste_from_slot:
            self.on_paste_from_slot(slot_num)

    def _cancel_chord(self):
        """Cancel the current chord sequence."""
        with self._lock:
            self._chord_active = False
            self._chord_action = None
            self._digits = ""
            if self._chord_timer:
                self._chord_timer.cancel()
                self._chord_timer = None
            if self._digit_timer:
                self._digit_timer.cancel()
                self._digit_timer = None

    def _on_popup_hotkey(self):
        """Handle popup hotkey."""
        if self.on_popup_requested:
            self.on_popup_requested()
