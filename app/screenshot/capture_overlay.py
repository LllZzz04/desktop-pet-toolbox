from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .selection_geometry import handle_points
from app.ui.theme import THEME


class CaptureOverlay(QWidget):
    def __init__(self, manager, snapshot):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.manager, self.snapshot = manager, snapshot
        self.setWindowTitle("区域截图 — ESC 取消")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.winId()
        self.windowHandle().setScreen(snapshot.screen)
        self.setGeometry(snapshot.logical)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(QRectF(self.rect()), self.snapshot.image)
        shade = QColor(THEME.overlay)
        shade.setAlpha(110)
        painter.fillRect(self.rect(), shade)
        selection = self.manager.selection
        if selection and not selection.isEmpty():
            local = self.snapshot.local_rect(selection)
            painter.setClipRect(local)
            painter.drawImage(QRectF(self.rect()), self.snapshot.image)
            painter.setClipping(False)
            painter.setPen(QPen(QColor(THEME.accent), 1.5))
            painter.drawRect(local)
            if not self.manager.dragging or self.manager.drag_mode != "new":
                painter.setBrush(QColor(THEME.card))
                for point in handle_points(selection).values():
                    handle = self.snapshot.local_point(point)
                    painter.drawRoundedRect(QRectF(handle.x() - 3.5, handle.y() - 3.5, 7, 7), 2, 2)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            label = f"{selection.width()} × {selection.height()} px"
            x = min(max(8, local.x()), max(8, self.width() - 190))
            y = min(max(32, local.y() - 8), self.height() - 18)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(THEME.card))
            painter.drawRoundedRect(QRectF(x - 4, y - 22, 184, 28), 6, 6)
            painter.setPen(QColor(THEME.text))
            painter.drawText(int(x + 4), int(y - 3), label)
            if not self.manager.dragging:
                help_text = "拖动边角调整大小 · 内部拖动移动 · 方向键微调 · Ctrl+方向键调整宽高 · Enter 复制 · ESC 关闭"
                help_width = min(self.width() - 24, painter.fontMetrics().horizontalAdvance(help_text) + 16)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(THEME.card))
                painter.drawRoundedRect(QRectF(12, self.height() - 38, help_width, 26), 6, 6)
                painter.setPen(QColor(THEME.secondary))
                painter.drawText(20, self.height() - 20,
                    painter.fontMetrics().elidedText(help_text, Qt.TextElideMode.ElideRight, help_width - 16))
        else:
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(24, 36, "框选取字 · 松开后复制文字 · ESC 取消"
                             if self.manager.mode == "quick_ocr" else "拖动选择区域 · ESC 取消")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.manager.begin_interaction(self)
        elif event.button() == Qt.MouseButton.RightButton:
            self.manager.cancel()

    def mouseMoveEvent(self, event):
        if self.manager.dragging:
            self.manager.update_selection()
        else:
            self.manager.update_cursor(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.manager.complete_selection()

    def keyPressEvent(self, event):
        if not self.manager.handle_key(event):
            super().keyPressEvent(event)
