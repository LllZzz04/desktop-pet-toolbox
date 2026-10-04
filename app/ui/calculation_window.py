"""Select, copy, favorite or reuse a local calculation without auto-execution."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QDialog, QInputDialog, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QTabWidget)

from .components import ActionButton, card, empty_state, label, page_header, page_layout, row


class CalculationWindow(QDialog):
    expression_requested = Signal(str)

    def __init__(self, store):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.store = store
        self.setWindowTitle("计算记录 — Luna 工具箱")
        self.resize(620, 570)
        layout = page_layout(self)
        layout.addWidget(page_header("计算记录", "上下方向键调用历史 · 收藏表达式，下次继续使用"))
        self.tabs = QTabWidget()
        self.history = QListWidget()
        self.favorites = QListWidget()
        for view, title in ((self.history, "最近计算"), (self.favorites, "公式收藏")):
            view.setSpacing(4)
            view.currentItemChanged.connect(self.select)
            view.itemDoubleClicked.connect(lambda item: self.load_selected())
            self.tabs.addTab(view, title)
        self.tabs.currentChanged.connect(lambda index: self.select())
        collection = card(12)
        collection.layout().addWidget(self.tabs, 1)
        self.empty = empty_state("暂无记录", "先在宠物输入框执行一次计算，再收藏常用表达式", "note")
        collection.layout().addWidget(self.empty)
        layout.addWidget(collection, 1)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setFixedHeight(100)
        self.details.setPlaceholderText("选择记录，查看并复制完整表达式和结果")
        layout.addWidget(self.details)
        actions = row()
        self.load = ActionButton("载入输入框", "primary")
        self.load.clicked.connect(self.load_selected)
        self.copy = ActionButton("复制结果", kind="copy")
        self.copy.clicked.connect(self.copy_selected)
        self.star = ActionButton("收藏 / 改名", "ghost")
        self.star.clicked.connect(self.favorite_selected)
        self.delete = ActionButton("删除", "ghost")
        self.delete.clicked.connect(self.delete_selected)
        for button in (self.load, self.copy, self.star, self.delete):
            actions.addWidget(button)
        layout.addLayout(actions)
        footer = row()
        self.status = label("只记录本机计算，不记录对话消息", "status", True)
        footer.addWidget(self.status, 1)
        clear = ActionButton("清空计算记录", "ghost", compact=True)
        clear.clicked.connect(lambda: self.perform(self.store.clear_history))
        footer.addWidget(clear)
        layout.addLayout(footer)
        store.changed.connect(self.refresh)
        self.refresh()

    def current(self):
        view = self.favorites if self.tabs.currentIndex() == 1 else self.history
        item = view.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def refresh(self):
        for view, entries in ((self.history, self.store.history), (self.favorites, self.store.favorites)):
            view.clear()
            for entry in entries:
                heading = entry.get("name", entry["expression"])
                item = QListWidgetItem(heading[:100] + "\n" + entry["answer"][:180].replace("\n", " · "))
                item.setData(Qt.ItemDataRole.UserRole, entry)
                item.setToolTip(entry["expression"])
                view.addItem(item)
        self.select()

    def select(self, current=None, previous=None):
        entry = self.current()
        self.empty.setVisible(not (self.store.favorites if self.tabs.currentIndex() == 1 else self.store.history))
        self.details.setPlainText(entry["expression"] + "\n\n" + entry["answer"] if entry else "")
        for button in (self.load, self.copy, self.star, self.delete):
            button.setEnabled(entry is not None)

    def load_selected(self):
        entry = self.current()
        if entry:
            self.hide()
            self.expression_requested.emit(entry["expression"])

    def copy_selected(self):
        entry = self.current()
        if entry:
            QApplication.clipboard().setText(entry["answer"])

    def favorite_selected(self):
        entry = self.current()
        if entry:
            name, ok = QInputDialog.getText(self, "收藏表达式", "名称", text=entry.get("name", entry["expression"][:80]))
            if ok:
                self.perform(lambda: self.store.favorite(entry, name))

    def delete_selected(self):
        entry = self.current()
        if entry:
            favorite = self.tabs.currentIndex() == 1
            self.perform(lambda: self.store.delete(entry["id"], favorite))

    def perform(self, callback):
        try:
            callback()
            self.status.setText("已保存到本地")
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
