"""A small annotation editor; export stays in full-resolution image pixels."""
import logging

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (QColorDialog, QDialog, QInputDialog, QMessageBox,
                               QSpinBox, QWidget)

from app.core.images import copy_image, save_image
from app.ui.components import ActionButton, card, label, page_header, page_layout, row
from app.ui.theme import THEME
from .annotation import Annotation, draw_annotation, render_annotations


class AnnotationCanvas(QWidget):
    changed = Signal()

    def __init__(self, image):
        super().__init__()
        self.image = QImage(image)
        self.image.setDevicePixelRatio(1)
        self.rendered = QImage(self.image)
        self.items, self.redo_items = [], []
        self.kind, self.color, self.pen_width, self.font_size = "arrow", THEME.accent, 3, 24
        self._start = self._end = None
        self.setMinimumSize(320, 200)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def target(self):
        available = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        scale = min(available.width() / self.image.width(), available.height() / self.image.height())
        return QRectF(available.center().x() - self.image.width() * scale / 2,
                      available.center().y() - self.image.height() * scale / 2,
                      self.image.width() * scale, self.image.height() * scale)

    def image_point(self, point):
        target = self.target()
        return QPointF(min(self.image.width() - 1, max(0, (point.x() - target.x()) * self.image.width() / target.width())),
                       min(self.image.height() - 1, max(0, (point.y() - target.y()) * self.image.height() / target.height())))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(THEME.background))
        target = self.target()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target, self.rendered)
        if self._start is not None:
            painter.setClipRect(target)
            painter.translate(target.topLeft())
            painter.scale(target.width() / self.image.width(), target.height() / self.image.height())
            draw_annotation(painter, self.image, self._draft(), draft=True)

    def _draft(self):
        return Annotation(self.kind, self._start, self._end, self.color, self.pen_width,
                          font_size=self.font_size)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.target().contains(event.position()):
            return
        point = self.image_point(event.position())
        if self.kind == "text":
            text, ok = QInputDialog.getMultiLineText(self, "添加文字", "文字内容（最多 2000 字符）")
            if ok and text.strip():
                self.commit(Annotation("text", point, point, self.color, self.pen_width,
                                       text[:2000], self.font_size))
        else:
            self._start = self._end = point
            self.update()

    def mouseMoveEvent(self, event):
        if self._start is not None:
            self._end = self.image_point(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if self._start is not None and event.button() == Qt.MouseButton.LeftButton:
            self._end = self.image_point(event.position())
            if (self._end - self._start).manhattanLength() >= 3:
                self.commit(self._draft())
            self._start = self._end = None
            self.update()

    def commit(self, item):
        if len(self.items) >= 100:
            QMessageBox.information(self, "标注数量", "每张图片最多 100 个标注。")
            return
        self.rebuild(self.items + [item], [])

    def rebuild(self, items, redo_items):
        try:
            rendered = render_annotations(self.image, items)
            self.rendered, self.items, self.redo_items = rendered, items, redo_items
            self.changed.emit()
            self.update()
        except Exception as error:
            logging.exception("Annotation rendering failed")
            QMessageBox.warning(self, "标注失败", str(error))

    def undo(self):
        if self.items:
            self.rebuild(self.items[:-1], self.redo_items + [self.items[-1]])

    def redo(self):
        if self.redo_items:
            self.rebuild(self.items + [self.redo_items[-1]], self.redo_items[:-1])


class AnnotationWindow(QDialog):
    exported = Signal(object)
    pin_requested = Signal(object)

    def __init__(self, image):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("截图标注 — Luna 工具箱")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(940, 640)
        layout = page_layout(self)
        layout.addWidget(page_header("截图标注", "拖动绘制 · 文字工具单击添加 · 导出保留原始像素"))
        tools = row()
        self.canvas = AnnotationCanvas(image)
        self.tool_buttons = {}
        for kind, title in (("arrow", "箭头"), ("rect", "矩形"), ("text", "文字"), ("mosaic", "马赛克")):
            button = ActionButton(title)
            button.clicked.connect(lambda checked=False, kind=kind: self.set_tool(kind))
            self.tool_buttons[kind] = button
            tools.addWidget(button)
        color = ActionButton("颜色", "ghost")
        color.clicked.connect(self.choose_color)
        tools.addWidget(color)
        tools.addWidget(label("线宽", "caption"))
        width = QSpinBox()
        width.setRange(1, 12)
        width.setValue(3)
        width.valueChanged.connect(lambda value: setattr(self.canvas, "pen_width", value))
        tools.addWidget(width)
        tools.addWidget(label("字号", "caption"))
        size = QSpinBox()
        size.setRange(10, 100)
        size.setValue(24)
        size.valueChanged.connect(lambda value: setattr(self.canvas, "font_size", value))
        tools.addWidget(size)
        layout.addLayout(tools)
        picture = card(8)
        picture.layout().addWidget(self.canvas, 1)
        layout.addWidget(picture, 1)
        footer = row()
        self.undo = ActionButton("撤销", "ghost")
        self.undo.clicked.connect(self.canvas.undo)
        self.redo = ActionButton("重做", "ghost")
        self.redo.clicked.connect(self.canvas.redo)
        footer.addWidget(self.undo)
        footer.addWidget(self.redo)
        footer.addStretch()
        for title, kind, action in (("复制", "copy", "copy"), ("贴图", "pin", "pin"), ("保存", "save", "save")):
            button = ActionButton(title, "primary" if action == "copy" else "secondary", kind)
            button.clicked.connect(lambda checked=False, action=action: self.export(action))
            footer.addWidget(button)
        close = ActionButton("关闭", "ghost")
        close.clicked.connect(self.close)
        footer.addWidget(close)
        layout.addLayout(footer)
        self.canvas.changed.connect(self.update_actions)
        self.set_tool("arrow")
        self.update_actions()

    def set_tool(self, kind):
        self.canvas.kind = kind
        for name, button in self.tool_buttons.items():
            button.set_variant("primary" if name == kind else "secondary")

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.canvas.color), self, "标注颜色")
        if color.isValid():
            self.canvas.color = color.name()

    def update_actions(self):
        self.undo.setEnabled(bool(self.canvas.items))
        self.redo.setEnabled(bool(self.canvas.redo_items))

    def export(self, action):
        try:
            image = QImage(self.canvas.rendered)
            if action == "copy":
                copy_image(image)
            elif action == "pin":
                self.pin_requested.emit(image)
            elif not save_image(image, self):
                return
            if self.canvas.items:
                self.exported.emit(image)
            self.close()
        except Exception as error:
            logging.exception("Annotation export failed")
            QMessageBox.warning(self, "标注失败", str(error))
