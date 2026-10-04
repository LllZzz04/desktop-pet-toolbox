"""Keep selection coordinates in native desktop pixels, including mixed DPI.

Qt's per-screen logical desktop may contain gaps at mixed scale factors. Each
monitor is mapped independently to native Windows monitor bounds. Image crops
therefore never multiply a global desktop coordinate by a single DPI factor.
"""
import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QCursor, QImage, QPainter
from PySide6.QtWidgets import QApplication


def native_monitor_rects():
    if sys.platform != "win32":
        return {}
    user32 = ctypes.WinDLL("user32")

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32)]

    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                       ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                         callback_type, wintypes.LPARAM]
    result = {}

    @callback_type
    def callback(monitor, dc, rect, data):
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            r = info.rcMonitor
            result[info.szDevice] = QRect(r.left, r.top, r.right - r.left, r.bottom - r.top)
        return True

    user32.EnumDisplayMonitors(None, None, callback, 0)
    return result


@dataclass
class ScreenSnapshot:
    screen: object
    logical: QRect
    native: QRect
    image: QImage

    def local_point(self, native_point):
        return QPointF((native_point.x() - self.native.x()) * self.logical.width() / self.native.width(),
                       (native_point.y() - self.native.y()) * self.logical.height() / self.native.height())

    def local_rect(self, native_rect):
        return QRectF((native_rect.x() - self.native.x()) * self.logical.width() / self.native.width(),
                      (native_rect.y() - self.native.y()) * self.logical.height() / self.native.height(),
                      native_rect.width() * self.logical.width() / self.native.width(),
                      native_rect.height() * self.logical.height() / self.native.height())


def capture_screens():
    monitors = native_monitor_rects()
    snapshots = []
    for screen in QApplication.screens():
        image = screen.grabWindow(0).toImage()
        if image.isNull():
            raise RuntimeError(f"无法截取显示器 {screen.name()}")
        image.setDevicePixelRatio(1)
        logical = screen.geometry()
        # Recent Qt builds may expose the friendly monitor name instead of
        # \\.\DISPLAY1. Windows/Qt preserve native monitor origins at mixed DPI.
        native = monitors.get(screen.name())
        if native is None:
            native = next((rect for rect in monitors.values()
                           if rect.topLeft() == logical.topLeft() and rect.size() == image.size()),
                          QRect(logical.topLeft(), image.size()))
        snapshots.append(ScreenSnapshot(screen, logical, native, image))
    if not snapshots:
        raise RuntimeError("没有可用显示器")
    return snapshots


def cursor_native(snapshots):
    if sys.platform == "win32":
        point = wintypes.POINT()
        if ctypes.windll.user32.GetPhysicalCursorPos(ctypes.byref(point)):
            return QPoint(point.x, point.y)
    point = QCursor.pos()
    for snapshot in snapshots:
        if snapshot.logical.contains(point):
            local = point - snapshot.logical.topLeft()
            return snapshot.native.topLeft() + QPoint(
                round(local.x() * snapshot.native.width() / snapshot.logical.width()),
                round(local.y() * snapshot.native.height() / snapshot.logical.height()))
    return point


def selection_rect(start, end):
    # Half-open pixel bounds: dragging 100 -> 200 captures exactly 100 pixels.
    return QRect(min(start.x(), end.x()), min(start.y(), end.y()),
                 abs(end.x() - start.x()), abs(end.y() - start.y()))


def compose_selection(snapshots, selection):
    if selection.width() < 2 or selection.height() < 2:
        raise ValueError("选区太小")
    # Prevent a huge sparse virtual desktop from exhausting memory.
    if selection.width() * selection.height() > 100_000_000:
        raise ValueError("选区过大，请分别截取显示器")
    image = QImage(selection.size(), QImage.Format.Format_RGB32)
    if image.isNull():
        raise MemoryError("截图内存不足")
    image.fill(0xff202020)
    painter = QPainter(image)
    try:
        for snapshot in snapshots:
            intersection = selection.intersected(snapshot.native)
            if intersection.isEmpty():
                continue
            source = QRectF(
                (intersection.x() - snapshot.native.x()) * snapshot.image.width() / snapshot.native.width(),
                (intersection.y() - snapshot.native.y()) * snapshot.image.height() / snapshot.native.height(),
                intersection.width() * snapshot.image.width() / snapshot.native.width(),
                intersection.height() * snapshot.image.height() / snapshot.native.height())
            target = QRectF(intersection.translated(-selection.topLeft()))
            painter.drawImage(target, snapshot.image, source)
    finally:
        painter.end()
    return image
