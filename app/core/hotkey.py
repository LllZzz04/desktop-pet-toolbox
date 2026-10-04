"""Windows RegisterHotKey integration, without keyboard hooks or polling."""
import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal


def parse_hotkey(text):
    tokens = [token.strip().upper() for token in text.split("+")]
    modifiers, key = 0, None
    mapping = {"ALT": 1, "CTRL": 2, "CONTROL": 2, "SHIFT": 4, "WIN": 8}
    for token in tokens:
        if token in mapping:
            if modifiers & mapping[token]:
                raise ValueError("快捷键修饰键重复")
            modifiers |= mapping[token]
        elif key is None and len(token) == 1 and token.isascii() and token.isalnum():
            key = ord(token)
        elif key is None and token.startswith("F") and token[1:].isdigit() and 1 <= int(token[1:]) <= 24:
            key = 0x70 + int(token[1:]) - 1
        else:
            raise ValueError("请输入 Alt+A、Ctrl+Shift+S 或 F8 等快捷键")
    if key is None or (not modifiers and key < 0x70):
        raise ValueError("字母或数字快捷键必须带 Alt / Ctrl / Shift")
    return modifiers | 0x4000, key  # MOD_NOREPEAT


class NativeFilter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == self.owner.hotkey_id:
            self.owner.triggered.emit()
            return True, 0
        return False, 0


class GlobalHotkey(QObject):
    triggered = Signal()

    def __init__(self, app, slot=0):
        super().__init__(app)
        self.app = app
        self.hotkey_id = None
        self.text = ""
        self._ids = (0x5211 + slot * 2, 0x5212 + slot * 2)
        self.filter = NativeFilter(self)
        self.user32 = ctypes.WinDLL("user32", use_last_error=True) if sys.platform == "win32" else None
        if self.user32:
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.RegisterHotKey.restype = wintypes.BOOL
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.UnregisterHotKey.restype = wintypes.BOOL
            app.installNativeEventFilter(self.filter)

    def register(self, text):
        modifiers, key = parse_hotkey(text)
        if self.hotkey_id is not None and parse_hotkey(self.text) == (modifiers, key):
            self.text = text
            return
        if not self.user32:
            raise ValueError("全局快捷键目前只支持 Windows")
        new_id = self._ids[0] if self.hotkey_id != self._ids[0] else self._ids[1]
        if not self.user32.RegisterHotKey(None, new_id, modifiers, key):
            raise ValueError(f"快捷键 {text} 已被其他程序占用或无法注册，请更换快捷键。")
        old_id = self.hotkey_id
        self.hotkey_id, self.text = new_id, text
        if old_id is not None:
            self.user32.UnregisterHotKey(None, old_id)

    def unregister(self):
        if self.user32 and self.hotkey_id is not None:
            self.user32.UnregisterHotKey(None, self.hotkey_id)
        self.hotkey_id, self.text = None, ""

    def close(self):
        self.unregister()
        if self.user32:
            self.app.removeNativeEventFilter(self.filter)


def register_hotkeys(bindings):
    """Replace a small group together, including swaps of keys we already own."""
    parsed = [parse_hotkey(text) for owner, text in bindings if text is not None]
    if len(set(parsed)) != len(parsed):
        raise ValueError("截图和区域取字不能使用相同的快捷键")
    if all((owner.hotkey_id is None and text is None) or
           (owner.hotkey_id is not None and text is not None and
            parse_hotkey(owner.text) == parse_hotkey(text)) for owner, text in bindings):
        for owner, text in bindings:
            owner.text = text or ""
        return
    previous = [(owner, owner.text if owner.hotkey_id is not None else None) for owner, text in bindings]
    for owner, text in bindings:
        owner.unregister()
    try:
        for owner, text in bindings:
            if text is not None:
                owner.register(text)
    except ValueError as original:
        for owner, text in bindings:
            owner.unregister()
        failures = []
        for owner, text in previous:
            if text is not None:
                try:
                    owner.register(text)
                except ValueError as error:
                    failures.append(str(error))
        if failures:
            raise ValueError(str(original) + "\n原快捷键恢复失败：" + "；".join(failures)) from original
        raise
