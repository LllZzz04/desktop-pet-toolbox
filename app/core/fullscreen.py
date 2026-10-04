"""Low-frequency Windows foreground/monitor checks for pet visibility only."""
import ctypes
import logging
import os
import sys
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal


class MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


class WindowsFullscreen:
    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.dwm = ctypes.WinDLL("dwmapi")
        signatures = {
            "GetForegroundWindow": ([], wintypes.HWND),
            "GetWindowThreadProcessId": ([wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            "IsWindowVisible": ([wintypes.HWND], wintypes.BOOL),
            "IsIconic": ([wintypes.HWND], wintypes.BOOL),
            "IsZoomed": ([wintypes.HWND], wintypes.BOOL),
            "GetClassNameW": ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            "GetWindowLongW": ([wintypes.HWND, ctypes.c_int], wintypes.LONG),
            "MonitorFromWindow": ([wintypes.HWND, wintypes.DWORD], wintypes.HANDLE),
            "GetMonitorInfoW": ([wintypes.HANDLE, ctypes.POINTER(MonitorInfo)], wintypes.BOOL),
            "GetWindowRect": ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.user32, name)
            function.argtypes, function.restype = arguments, result
        self.dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                 ctypes.c_void_p, wintypes.DWORD]
        self.dwm.DwmGetWindowAttribute.restype = wintypes.LONG

    def check(self, pet_handle):
        foreground = self.user32.GetForegroundWindow()
        if not foreground:
            return None  # A transient focus change should not flash the pet.
        process = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(foreground, ctypes.byref(process))
        if process.value == os.getpid():
            return None  # Keep the prior state while our tools/capture are active.
        if not self.user32.IsWindowVisible(foreground) or self.user32.IsIconic(foreground):
            return False
        window_class = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(foreground, window_class, len(window_class))
        if window_class.value in {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}:
            return False
        monitor = self.user32.MonitorFromWindow(foreground, 2)  # MONITOR_DEFAULTTONEAREST
        if not monitor or monitor != self.user32.MonitorFromWindow(pet_handle, 2):
            return False
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if not self.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        cloaked = wintypes.DWORD()
        if (self.dwm.DwmGetWindowAttribute(foreground, 14, ctypes.byref(cloaked),
                                           ctypes.sizeof(cloaked)) == 0 and cloaked.value):
            return False
        bounds = wintypes.RECT()
        # DWM bounds omit invisible resize borders and use physical pixels.
        if self.dwm.DwmGetWindowAttribute(foreground, 9, ctypes.byref(bounds), ctypes.sizeof(bounds)) != 0:
            if not self.user32.GetWindowRect(foreground, ctypes.byref(bounds)):
                return None
        screen = info.rcMonitor
        covers = all(abs(a - b) <= 2 for a, b in zip(
            (bounds.left, bounds.top, bounds.right, bounds.bottom),
            (screen.left, screen.top, screen.right, screen.bottom)))
        # An ordinary maximized window with an auto-hidden taskbar can also
        # cover the monitor. A visible native caption keeps it out of DND.
        caption = self.user32.GetWindowLongW(foreground, -16) & 0x00C00000
        return covers and not (self.user32.IsZoomed(foreground) and caption)


class FullscreenWatcher(QObject):
    changed = Signal(bool)

    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet, self.active = pet, False
        self.native = None
        if sys.platform == "win32":
            try:
                self.native = WindowsFullscreen()
            except OSError:
                logging.exception("Fullscreen detection unavailable")
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check)
        self._error_logged = False

    def set_enabled(self, enabled):
        if enabled and self.native:
            self.timer.start()
            self.check()
        else:
            self.timer.stop()
            self._set_active(False)

    def _set_active(self, active):
        if active != self.active:
            self.active = active
            self.changed.emit(active)

    def check(self):
        try:
            active = self.native.check(int(self.pet.winId()))
            if active is not None:
                self._set_active(active)
        except (OSError, ValueError, ctypes.ArgumentError):
            if not self._error_logged:
                logging.exception("Fullscreen detection failed")
                self._error_logged = True
            self._set_active(False)

    def shutdown(self):
        self.timer.stop()
