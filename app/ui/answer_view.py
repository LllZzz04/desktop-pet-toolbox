"""A selectable plain-text answer that grows with wrapped content."""
import math

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFrame, QSizePolicy, QTextEdit


class AnswerView(QTextEdit):
    height_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setAccessibleName("回答内容")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().setDocumentMargin(4)
        self._height_limit = 320
        self.setFixedHeight(28)
        self._measure_timer = QTimer(self)
        self._measure_timer.setSingleShot(True)
        self._measure_timer.timeout.connect(self._measure)
        self.document().documentLayout().documentSizeChanged.connect(lambda size: self._schedule())

    def text(self):
        return self.toPlainText()

    def set_height_limit(self, limit):
        limit = max(28, limit)
        if limit != self._height_limit:
            self._height_limit = limit
            self._schedule()

    def _schedule(self):
        if not self._measure_timer.isActive():
            self._measure_timer.start(0)

    def _measure(self):
        height = min(self._height_limit, max(28, math.ceil(self.document().size().height()) + 2))
        if height != self.height():
            self.setFixedHeight(height)
            self.height_changed.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule()

    def append_text(self, text):
        bar = self.verticalScrollBar()
        previous = bar.value()
        selection = self.textCursor()
        selected = selection.hasSelection()
        anchor, position = selection.anchor(), selection.position()
        follow = previous >= bar.maximum() - 8 and not selected
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        if selected:
            selection.setPosition(anchor)
            selection.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(selection)
        bar.setValue(bar.maximum() if follow else previous)
