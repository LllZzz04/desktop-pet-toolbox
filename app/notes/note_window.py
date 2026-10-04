from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QDialog, QLineEdit, QListWidget, QListWidgetItem

from app.ui.components import ActionButton, card, empty_state, label, page_header, page_layout, row


class NoteWindow(QDialog):
    operation_finished = Signal(bool)

    def __init__(self, manager):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.manager = manager
        self.setWindowTitle("便签 — 桌宠工具箱")
        self.resize(500, 480)
        self.setMinimumSize(420, 360)
        layout = page_layout(self)
        self.total = label("", "badge")
        layout.addWidget(page_header("便签", "记下小事，完成后轻轻勾选", self.total))
        composer = card(12)
        composer.layout().addWidget(label("新便签", "section"))
        input_row = row()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入便签内容")
        self.input.setMaxLength(2000)
        self.input.returnPressed.connect(self.add)
        input_row.addWidget(self.input, 1)
        add = ActionButton("添加", "primary", "add")
        add.clicked.connect(self.add)
        input_row.addWidget(add)
        composer.layout().addLayout(input_row)
        layout.addWidget(composer)
        collection = card(12)
        self.list = QListWidget()
        self.list.setProperty("listRole", "notes")
        self.list.setSpacing(4)
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.timeout.connect(self._resize_rows)
        self.list.viewport().installEventFilter(self)
        collection.layout().addWidget(self.list, 1)
        self.empty = empty_state("还没有便签", "在上方输入内容，或使用 /note 命令", "note")
        collection.layout().addWidget(self.empty, 1)
        layout.addWidget(collection, 1)
        self.status = label("勾选表示完成 · 内容自动保存在本地", "status", True)
        layout.addWidget(self.status)
        manager.changed.connect(self.refresh)
        self.refresh()

    def refresh(self, count=None):
        self.list.clear()
        self.total.setText(f"{len(self.manager.records)} 条")
        self.empty.setVisible(not self.manager.records)
        self.list.setVisible(bool(self.manager.records))
        for record in self.manager.records:
            widget = card(12)
            item_row = row()
            widget.layout().addLayout(item_row)
            checkbox = QCheckBox()
            checkbox.setAccessibleName("完成：" + record["text"])
            checkbox.setChecked(record["done"])
            checkbox.toggled.connect(lambda done, identifier=record["id"]: self.toggle(identifier, done))
            item_row.addWidget(checkbox)
            text = label(record["text"], "muted" if record["done"] else "body", True)
            text.setTextFormat(Qt.TextFormat.PlainText)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            font = text.font()
            font.setStrikeOut(record["done"])
            text.setFont(font)
            item_row.addWidget(text, 1)
            delete = ActionButton("删除", "ghost", compact=True)
            delete.setFixedWidth(56)
            delete.clicked.connect(lambda checked=False, identifier=record["id"]: self.delete(identifier))
            item_row.addWidget(delete)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)
        self._resize_rows()
        self._reflow_timer.start(0)

    def _resize_rows(self):
        # Reflow presentation when the window width changes; note data stays
        # untouched and long notes remain selectable inside their own cards.
        width = max(220, self.list.viewport().width() - 16)
        for index in range(self.list.count()):
            item = self.list.item(index)
            widget = self.list.itemWidget(item)
            if widget is not None:
                height = widget.layout().totalHeightForWidth(width)
                if height < 0:
                    height = widget.sizeHint().height()
                item.setSizeHint(QSize(width, max(60, height)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_reflow_timer"):
            self._reflow_timer.start(0)

    def eventFilter(self, watched, event):
        if watched is self.list.viewport() and event.type() == QEvent.Type.Resize:
            self._reflow_timer.start(0)
        return super().eventFilter(watched, event)

    def add(self):
        try:
            self.manager.add(self.input.text())
            self.input.clear()
            self.status.setText("已添加便签")
            self.operation_finished.emit(True)
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
            self.operation_finished.emit(False)

    def toggle(self, identifier, done):
        try:
            self.manager.set_done(identifier, done)
            self.status.setText("已完成便签" if done else "便签已恢复为未完成")
            self.operation_finished.emit(True)
        except (OSError, ValueError) as error:
            self.status.setText(f"保存失败：{error}")
            self.refresh()
            self.operation_finished.emit(False)

    def delete(self, identifier):
        try:
            self.manager.delete(identifier)
            self.status.setText("已删除便签")
            self.operation_finished.emit(True)
        except (OSError, ValueError) as error:
            self.status.setText(f"保存失败：{error}")
            self.operation_finished.emit(False)
