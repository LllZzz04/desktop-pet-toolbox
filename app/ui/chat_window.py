"""Selectable text conversation UI; streaming does not replace the document."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit

from app.chat.settings import MAX_INPUT_CHARS
from .components import ActionButton, card, label, page_header, page_layout, row


class MessageInput(QPlainTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and event.modifiers() in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ControlModifier)):
            if not event.isAutoRepeat() and not self.isReadOnly():
                self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChatWindow(QDialog):
    send_requested = Signal(str)
    retry_requested = Signal()
    stop_requested = Signal()
    clear_requested = Signal()
    settings_requested = Signal()
    closed = Signal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("对话记录 — 桌宠工具箱")
        self.resize(680, 600)
        self.setMinimumSize(480, 420)
        self._busy = False
        self._can_retry = False
        self._last_answer = ""
        self.finished.connect(lambda result: self.closed.emit())
        layout = page_layout(self)
        settings = ActionButton("对话设置", "ghost", "settings", compact=True)
        settings.clicked.connect(lambda: self.settings_requested.emit())
        layout.addWidget(page_header("对话记录", "随时回看，也可以继续提问", settings))
        conversation = card()
        self.profile = label("", "caption", True)
        conversation.layout().addWidget(self.profile)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setProperty("flatEditor", True)
        self.transcript.setPlaceholderText("填写 API Key 后，在下方输入消息。回复和对话记录可以自由选择复制。")
        self.transcript.setAccessibleName("对话记录")
        conversation.layout().addWidget(self.transcript, 1)
        actions = row()
        self.copy_answer = ActionButton("复制上一条回复", "ghost", "copy", compact=True)
        self.copy_answer.clicked.connect(self._copy_answer)
        self.retry = ActionButton("重试上一条", "ghost", compact=True)
        self.retry.clicked.connect(lambda: self.retry_requested.emit())
        self.clear = ActionButton("清空对话", "ghost", compact=True)
        self.clear.clicked.connect(lambda: self.clear_requested.emit())
        actions.addWidget(self.copy_answer)
        actions.addWidget(self.retry)
        actions.addStretch()
        actions.addWidget(self.clear)
        conversation.layout().addLayout(actions)
        layout.addWidget(conversation, 1)

        composer = card(12)
        self.status = label("Enter 发送 · Shift+Enter 换行", "status", True)
        composer.layout().addWidget(self.status)
        self.input = MessageInput()
        self.input.setPlaceholderText("输入消息…")
        self.input.setAccessibleName("消息输入")
        self.input.setProperty("flatEditor", True)
        self.input.setFixedHeight(88)
        self.input.submitted.connect(self._send)
        composer.layout().addWidget(self.input)
        bottom = row()
        self.count = label("", "muted")
        self.input.textChanged.connect(self._update_count)
        bottom.addWidget(self.count)
        bottom.addStretch()
        self.stop = ActionButton("停止生成", "secondary")
        self.stop.clicked.connect(lambda: self.stop_requested.emit())
        self.send = ActionButton("发送", "primary", "chat")
        self.send.clicked.connect(self._send)
        bottom.addWidget(self.stop)
        bottom.addWidget(self.send)
        composer.layout().addLayout(bottom)
        layout.addWidget(composer)
        self.set_busy(False)
        self._update_count()

    def _send(self):
        if not self._busy:
            self.send_requested.emit(self.input.toPlainText())

    def _update_count(self):
        self.count.setText(f"{len(self.input.toPlainText())} / {MAX_INPUT_CHARS}")

    def set_profile(self, config):
        self.profile.setText(f"{config.chat_model} · " +
                             ("对话保存在本机" if config.chat_save_history else "仅保留本次对话"))
        self.profile.setToolTip(config.chat_base_url)

    def set_busy(self, busy, can_retry=None):
        self._busy = busy
        if can_retry is not None:
            self._can_retry = can_retry
        self.send.setEnabled(not busy)
        self.input.setReadOnly(busy)
        self.stop.setEnabled(busy)
        self.retry.setEnabled(not busy and self._can_retry)
        self.clear.setEnabled(not busy)

    def render(self, messages):
        parts = []
        for message in messages:
            if message["role"] == "user":
                header = "你"
            else:
                header = "助手"
                if message["status"] in ("partial", "failed"):
                    header += "（未完成）"
            parts.append(header + "\n" + message["content"])
        self.transcript.setPlainText("\n\n".join(parts))
        self.transcript.verticalScrollBar().setValue(self.transcript.verticalScrollBar().maximum())
        self.update_answer(messages)

    def append_answer(self, text):
        bar = self.transcript.verticalScrollBar()
        previous = bar.value()
        selection = self.transcript.textCursor()
        selected = selection.hasSelection()
        anchor, position = selection.anchor(), selection.position()
        follow = previous >= bar.maximum() - 8 and not selected
        cursor = QTextCursor(self.transcript.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        if selected:
            # An end-of-document selection must not grow as new tokens arrive.
            selection.setPosition(anchor)
            selection.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
            self.transcript.setTextCursor(selection)
        bar.setValue(bar.maximum() if follow else previous)

    def update_answer(self, messages):
        self._last_answer = next((m["content"] for m in reversed(messages)
                                  if m["role"] == "assistant" and m["content"]), "")
        self.copy_answer.setEnabled(bool(self._last_answer))

    def _copy_answer(self):
        if self._last_answer:
            QApplication.clipboard().setText(self._last_answer)

