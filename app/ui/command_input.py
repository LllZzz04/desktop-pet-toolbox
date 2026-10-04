"""Standard line editing with an IME composition guard for command submission."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit


class CommandInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_composing = False
        self.confirming_composition = False
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self._history = []
        self._history_index = -1
        self._history_draft = ""
        self.textEdited.connect(lambda text: self._reset_history())
        self.setInputMethodHints(Qt.InputMethodHint.ImhNone)

    def inputMethodEvent(self, event):
        self.is_composing = bool(event.preeditString())
        super().inputMethodEvent(event)

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and not self.is_composing
                and event.modifiers() == Qt.KeyboardModifier.NoModifier and self._history):
            if self._history_index == -1:
                if event.key() == Qt.Key.Key_Down:
                    return super().keyPressEvent(event)
                self._history_draft = self.text()
            step = 1 if event.key() == Qt.Key.Key_Up else -1
            self._history_index = min(len(self._history) - 1, max(-1, self._history_index + step))
            self.setText(self._history[self._history_index] if self._history_index >= 0 else self._history_draft)
            self.setCursorPosition(len(self.text()))
            event.accept()
            return
        # Some IMEs commit their preedit while QLineEdit handles the same key.
        # Keep the guard active until that entire key event has returned.
        self.confirming_composition = (self.is_composing and event.key() in
                                      (Qt.Key.Key_Return, Qt.Key.Key_Enter))
        try:
            super().keyPressEvent(event)
        finally:
            self.confirming_composition = False

    def hideEvent(self, event):
        super().hideEvent(event)
        self.is_composing = self.confirming_composition = False

    def set_history(self, expressions):
        self._history = list(dict.fromkeys(expressions))[:100]
        self._reset_history()

    def _reset_history(self):
        self._history_index = -1
