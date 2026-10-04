"""Rounded vector icons shared by every tool window."""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QIconEngine, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from .theme import THEME


class ToolbarIconEngine(QIconEngine):
    def __init__(self, kind, color=None):
        super().__init__()
        self.kind, self.color = kind, color

    def clone(self):
        return ToolbarIconEngine(self.kind, self.color)

    def paint(self, painter, rect, mode, state):
        group = (QPalette.ColorGroup.Disabled if mode == QIcon.Mode.Disabled
                 else QPalette.ColorGroup.Active)
        color = QColor(THEME.muted) if mode == QIcon.Mode.Disabled else (
            QColor(self.color) if self.color else QApplication.palette().color(group, QPalette.ColorRole.ButtonText))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 24, rect.height() / 24)
        painter.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == "screenshot":
            for x, y, dx, dy in ((3, 3, 1, 1), (21, 3, -1, 1), (3, 21, 1, -1), (21, 21, -1, -1)):
                painter.drawLine(x, y, x + 5 * dx, y)
                painter.drawLine(x, y, x, y + 5 * dy)
            painter.drawRoundedRect(7, 7, 10, 10, 2, 2)
        elif self.kind == "history":
            painter.drawRoundedRect(3, 4, 18, 16, 3, 3)
            painter.drawEllipse(7, 7, 3, 3)
            path = QPainterPath()
            path.moveTo(5, 17)
            path.lineTo(11, 11)
            path.lineTo(15, 15)
            path.lineTo(18, 12)
            path.lineTo(21, 15)
            painter.drawPath(path)
        elif self.kind == "note":
            painter.drawRoundedRect(4, 3, 16, 18, 3, 3)
            painter.drawLine(8, 8, 16, 8)
            painter.drawLine(8, 12, 16, 12)
            painter.drawLine(8, 16, 12, 16)
        elif self.kind == "chat":
            painter.drawRoundedRect(3, 3, 18, 14, 4, 4)
            painter.drawLine(7, 17, 7, 21)
            painter.drawLine(7, 21, 12, 17)
            for x in (8, 12, 16):
                painter.drawPoint(x, 10)
        elif self.kind == "add":
            painter.drawLine(12, 5, 12, 19)
            painter.drawLine(5, 12, 19, 12)
        elif self.kind == "settings":
            painter.drawEllipse(4, 4, 16, 16)
            painter.drawEllipse(9, 9, 6, 6)
            for x1, y1, x2, y2 in ((12, 2, 12, 4), (12, 20, 12, 22), (2, 12, 4, 12), (20, 12, 22, 12)):
                painter.drawLine(x1, y1, x2, y2)
        elif self.kind == "annotate":
            path = QPainterPath()
            path.moveTo(4, 16)
            path.lineTo(16, 4)
            path.lineTo(20, 8)
            path.lineTo(8, 20)
            path.lineTo(3, 21)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(13, 7, 17, 11)
        elif self.kind == "copy":
            painter.drawRoundedRect(8, 3, 12, 14, 2, 2)
            path = QPainterPath()
            path.moveTo(5, 7)
            path.lineTo(4, 7)
            path.lineTo(4, 21)
            path.lineTo(16, 21)
            path.lineTo(16, 20)
            painter.drawPath(path)
        elif self.kind == "pin":
            path = QPainterPath()
            path.moveTo(8, 3)
            path.lineTo(16, 3)
            path.lineTo(14, 9)
            path.lineTo(18, 13)
            path.lineTo(6, 13)
            path.lineTo(10, 9)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(12, 13, 12, 21)
        elif self.kind == "save":
            path = QPainterPath()
            path.moveTo(3, 3)
            path.lineTo(18, 3)
            path.lineTo(21, 6)
            path.lineTo(21, 21)
            path.lineTo(3, 21)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawRect(7, 3, 9, 7)
            painter.drawRect(7, 15, 10, 6)
        elif self.kind == "cancel":
            painter.drawLine(6, 6, 18, 18)
            painter.drawLine(6, 18, 18, 6)
        elif self.kind == "ocr":
            painter.drawLine(3, 8, 3, 3)
            painter.drawLine(3, 3, 8, 3)
            painter.drawLine(16, 3, 21, 3)
            painter.drawLine(21, 3, 21, 8)
            painter.drawLine(3, 16, 3, 21)
            painter.drawLine(3, 21, 8, 21)
            painter.drawLine(16, 21, 21, 21)
            painter.drawLine(21, 21, 21, 16)
            for y, end in ((8, 17), (12, 17), (16, 13)):
                painter.drawLine(7, y, end, y)
        elif self.kind == "translate":
            font = QFont(painter.font())
            font.setPixelSize(THEME.body_size)
            painter.setFont(font)
            painter.drawText(QRect(1, 1, 14, 14), Qt.AlignmentFlag.AlignCenter, "文")
            painter.drawText(QRect(11, 10, 12, 14), Qt.AlignmentFlag.AlignCenter, "A")
            painter.drawLine(3, 18, 9, 18)
            painter.drawLine(7, 16, 9, 18)
            painter.drawLine(9, 18, 7, 20)
        painter.restore()

    def pixmap(self, size, mode, state):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRect(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pixmap


def icon(kind, color=None):
    return QIcon(ToolbarIconEngine(kind, color))
