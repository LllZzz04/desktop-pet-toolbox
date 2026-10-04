from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox)

from app.core.images import copy_image, save_image
from app.ui.components import ActionButton, card, empty_state, label, page_header, page_layout, row


class PreviewWindow(QDialog):
    image_tools_requested = Signal(object, bool)

    def __init__(self, image, pins, parent):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.resize(820, 580)
        self.setMinimumSize(720, 400)
        self.image = image
        self.label = QLabel()
        self.label.setMinimumSize(100, 100)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = page_layout(self)
        layout.addWidget(page_header("图片预览", f"{image.width()} × {image.height()} px"))
        picture = card()
        self.label.setProperty("surface", "preview")
        picture.layout().addWidget(self.label, 1)
        layout.addWidget(picture, 1)
        buttons = row()
        for text, action in (("复制", lambda: copy_image(self.image)),
                             ("重新贴图", lambda: pins.add(self.image)),
                             ("保存", lambda: save_image(self.image, self)),
                             ("提取文字", lambda: self.image_tools_requested.emit(self.image, False)),
                             ("翻译图片", lambda: self.image_tools_requested.emit(self.image, True)),
                             ("关闭", self.close)):
            button = ActionButton(text, "primary" if text == "重新贴图" else
                                  "ghost" if text == "关闭" else "secondary")
            button.clicked.connect(action)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.label.setPixmap(QPixmap.fromImage(self.image).scaled(
            self.label.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))


class HistoryWindow(QDialog):
    image_tools_requested = Signal(object, bool)

    def __init__(self, manager, pins):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.manager, self.pins = manager, pins
        self.preview = None
        self.setWindowTitle("最近图片 — 桌宠工具箱")
        self.resize(760, 540)
        self.setMinimumSize(660, 400)
        layout = page_layout(self)
        self.total = label("", "badge")
        layout.addWidget(page_header("最近图片", "截图留在本机，需要时随手找回", self.total))
        collection = card()
        self.description = label("", "caption")
        collection.layout().addWidget(self.description)
        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setMovement(QListWidget.Movement.Static)
        self.grid.setIconSize(QSize(150, 100))
        self.grid.setGridSize(QSize(182, 156))
        self.grid.setSpacing(4)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.context_menu)
        self.grid.itemClicked.connect(lambda item: self.act("preview", item))
        collection.layout().addWidget(self.grid, 1)
        self.empty = empty_state("还没有图片", "使用截图快捷键后，图片会自动出现在这里")
        collection.layout().addWidget(self.empty, 1)
        layout.addWidget(collection, 1)
        actions = card(12)
        toolbar = row()
        for title, action in (("预览", "preview"), ("复制", "copy"), ("重新贴图", "pin"),
                              ("保存", "save"), ("删除", "delete")):
            button = ActionButton(title, "primary" if action == "pin" else
                                  "ghost" if action == "delete" else "secondary")
            button.clicked.connect(lambda checked=False, a=action: self.act(a))
            toolbar.addWidget(button)
        actions.layout().addLayout(toolbar)
        tools = row()
        for title, action in (("提取文字", "extract"), ("翻译图片", "translate")):
            button = ActionButton(title, "ghost", "ocr" if action == "extract" else "translate")
            button.clicked.connect(lambda checked=False, a=action: self.act(a))
            tools.addWidget(button)
        tools.addStretch()
        actions.layout().addLayout(tools)
        layout.addWidget(actions)
        manager.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.grid.clear()
        self.total.setText(f"{len(self.manager.records)} 张")
        self.empty.setVisible(not self.manager.records)
        self.grid.setVisible(bool(self.manager.records))
        self.description.setText(f"最近 {len(self.manager.records)} 张 · 单击预览，右键操作")
        for record in self.manager.records:
            try:
                date = datetime.fromisoformat(record["created_at"]).astimezone().strftime("%m-%d %H:%M:%S")
            except ValueError:
                date = record["created_at"]
            item = QListWidgetItem(QIcon(str(self.manager.directory / record["thumbnail"])),
                                   f"{date}\n{record.get('width', '?')} × {record.get('height', '?')}")
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.grid.addItem(item)

    def context_menu(self, point):
        item = self.grid.itemAt(point)
        if item is None:
            return
        self.grid.setCurrentItem(item)
        menu = QMenu(self)
        for title, action in (("预览", "preview"), ("复制", "copy"), ("重新贴图", "pin"),
                              ("保存", "save"), ("提取文字", "extract"),
                              ("翻译图片", "translate"), ("删除", "delete")):
            menu.addAction(title, lambda checked=False, a=action: self.act(a))
        menu.exec(self.grid.mapToGlobal(point))

    def act(self, action, item=None):
        item = item or self.grid.currentItem()
        if item is None:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        try:
            if action == "delete":
                self.manager.delete(record["id"])
                return
            image = self.manager.load_image(record)
            if action == "copy":
                copy_image(image)
            elif action == "pin":
                self.pins.add(image)
            elif action == "save":
                save_image(image, self)
            elif action in ("extract", "translate"):
                self.image_tools_requested.emit(image, action == "translate")
            elif action == "preview":
                if self.preview is not None:
                    self.preview.close()
                self.preview = PreviewWindow(image, self.pins, self)
                self.preview.image_tools_requested.connect(self.image_tools_requested.emit)
                preview = self.preview
                preview.destroyed.connect(lambda: self._preview_destroyed(preview))
                self.preview.show()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "操作失败", str(error))

    def _preview_destroyed(self, preview):
        if self.preview is preview:
            self.preview = None
