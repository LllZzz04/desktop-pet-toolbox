"""Keep the native text menu and add explicit selected-text API actions."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QInputDialog, QMessageBox, QPlainTextEdit


class SelectedTextEdit(QPlainTextEdit):
    assistant_requested = Signal(str, str)

    def contextMenuEvent(self, event):
        text = self.textCursor().selectedText().replace("\u2029", "\n").strip()
        menu = self.createStandardContextMenu()
        if text:
            menu.addSeparator()
            assistant = menu.addMenu("向对话模型提问（使用 API）")
            assistant.addAction("解释选中文字", lambda: self.request("请解释这段内容，说明关键概念。", text))
            assistant.addAction("总结选中文字", lambda: self.request("请简洁总结这段内容，保留重要结论。", text))
            assistant.addAction("关于这段文字提问…", lambda: self.ask(text))
        menu.exec(event.globalPos())
        menu.deleteLater()

    def request(self, question, text):
        if len(text) > 6000:
            QMessageBox.information(self, "选中文字过长", "请缩小选择范围，每次最多 6000 个字符。")
            return
        self.assistant_requested.emit(question, text)

    def ask(self, text):
        question, ok = QInputDialog.getMultiLineText(self, "关于选中文字提问", "你的问题（最多 1000 字符）")
        if ok and question.strip():
            if len(question.strip()) > 1000:
                QMessageBox.information(self, "问题过长", "问题最多 1000 个字符。")
                return
            self.request(question.strip(), text)
