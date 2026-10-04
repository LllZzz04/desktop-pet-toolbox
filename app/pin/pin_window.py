from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QCursor, QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from app.core.images import copy_image, save_image
from app.ui.theme import THEME


class PinWindow(QWidget):
    closed = Signal(object)
    image_tools_requested = Signal(object, bool)
    state_changed = Signal()

    def __init__(self, image, point=None):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("贴图 — 双击关闭")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.image = image.copy()
        self.image.setDevicePixelRatio(1)
        self._press = None
        self.locked = False
        self.click_through = False
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        point = point or QCursor.pos()
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.scale = min(1 / screen.devicePixelRatio(),
                         area.width() * .7 / self.image.width(),
                         area.height() * .7 / self.image.height())
        self._resize()
        self.move(max(area.left(), min(point.x(), area.right() - self.width())),
                  max(area.top(), min(point.y(), area.bottom() - self.height())))

    def _resize(self):
        self.resize(max(1, round(self.image.width() * self.scale)),
                    max(1, round(self.image.height() * self.scale)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF(self.rect()), self.image)
        painter.setPen(QPen(QColor(THEME.divider), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.locked:
            self._press = event.globalPosition().toPoint()
            self._origin = self.pos()

    def mouseMoveEvent(self, event):
        if self._press is not None:
            self.move(self._origin + event.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, event):
        if self._press is not None:
            self.state_changed.emit()
        self._press = None

    def wheelEvent(self, event):
        if self.locked:
            event.accept()
            return
        if event.angleDelta().y() == 0:
            return
        old = self.size()
        maximum = max(self.image.width(), self.image.height())
        self.scale = min(8, 8192 / maximum,
                         max(min(32 / maximum, 1), self.scale * 1.15 ** (event.angleDelta().y() / 120)))
        self._resize()
        anchor = event.position()
        self.move(self.pos() + QPoint(round(anchor.x() * (1 - self.width() / old.width())),
                                     round(anchor.y() * (1 - self.height() / old.height()))))
        event.accept()
        self.state_changed.emit()

    def set_locked(self, enabled):
        self.locked = bool(enabled)
        self._press = None
        self.setCursor(Qt.CursorShape.ArrowCursor if self.locked else Qt.CursorShape.SizeAllCursor)
        self.state_changed.emit()

    def set_click_through(self, enabled):
        enabled = bool(enabled)
        if enabled == self.click_through:
            return
        self.click_through = enabled
        self._press = None
        visible = self.isVisible()
        geometry, opacity = self.geometry(), self.windowOpacity()
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        self.setGeometry(geometry)
        self.setWindowOpacity(opacity)
        if visible:
            self.show()
        self.state_changed.emit()

    def set_opacity(self, value):
        self.setWindowOpacity(value)
        self.state_changed.emit()

    def restore_state(self, record):
        self.scale = min(8, 8192 / max(self.image.width(), self.image.height()),
                         max(1 / self.image.width(), record["width"] / self.image.width()))
        self._resize()
        self.move(record["x"], record["y"])
        screen = next((s for s in QApplication.screens()
                       if s.availableGeometry().intersects(self.geometry())), QApplication.primaryScreen())
        area = screen.availableGeometry()
        self.move(max(area.left(), min(self.x(), area.right() - min(self.width(), area.width()) + 1)),
                  max(area.top(), min(self.y(), area.bottom() - min(self.height(), area.height()) + 1)))
        self.set_opacity(record.get("opacity", 1))
        self.set_locked(record.get("locked") is True)
        self.set_click_through(record.get("click_through") is True)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("复制", lambda: copy_image(self.image))
        menu.addAction("保存", lambda: save_image(self.image, self))
        menu.addAction("提取文字", lambda: self.image_tools_requested.emit(self.image, False))
        menu.addAction("翻译图片", lambda: self.image_tools_requested.emit(self.image, True))
        menu.addSeparator()
        lock = menu.addAction("锁定位置与大小")
        lock.setCheckable(True)
        lock.setChecked(self.locked)
        lock.triggered.connect(self.set_locked)
        through = menu.addAction("鼠标穿透（从宠物菜单恢复）")
        through.setCheckable(True)
        through.setChecked(self.click_through)
        through.triggered.connect(self.set_click_through)
        opacity = menu.addMenu("透明度")
        for percent in (100, 80, 60, 40):
            action = opacity.addAction(f"{percent}%")
            action.setCheckable(True)
            action.setChecked(abs(self.windowOpacity() - percent / 100) < .02)
            action.triggered.connect(lambda checked=False, p=percent: self.set_opacity(p / 100))
        menu.addSeparator()
        menu.addAction("关闭", self.close)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)
