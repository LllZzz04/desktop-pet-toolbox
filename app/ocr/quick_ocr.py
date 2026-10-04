"""Region OCR to clipboard, using the same local engine without a result window."""
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from .engine import extract_text
from .image_tools_manager import ImageTask, TaskSignals


class QuickOcrManager(QObject):
    busy_changed = Signal(bool)
    operation_finished = Signal(bool)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.signals = TaskSignals(self)
        self.signals.completed.connect(self._done)
        self._generation = 0
        self._running = self._pending = None
        self._closing = False

    def start(self, image):
        if self._closing:
            return
        self._generation += 1
        if self._running is not None:
            self._running.cancelled.set()
        task = ImageTask(self._generation, "quick_ocr", extract_text,
                         (QImage(image),), self.signals)
        self.busy_changed.emit(True)
        if self._running is None:
            self._running = task
            self.pool.start(task)
        else:
            self._pending = task

    @Slot(int, str, object, str)
    def _done(self, generation, kind, result, error):
        self._running = None
        if self._closing:
            return
        if self._pending is not None:
            self._running, self._pending = self._pending, None
            self.pool.start(self._running)
        if generation != self._generation:
            return
        if not error and result is not None:
            text = "\n\n".join(block.text for block in result.paragraphs) or result.text
            if text.strip():
                QApplication.clipboard().setText(text)
                self.busy_changed.emit(False)
                self.operation_finished.emit(True)
                self.completed.emit(text)
                return
            error = "没有识别到文字，请尝试更清晰的文字区域"
        self.busy_changed.emit(False)
        self.operation_finished.emit(False)
        self.failed.emit(error or "文字提取已取消")

    def shutdown(self):
        self._closing = True
        self._generation += 1
        if self._running is not None:
            self._running.cancelled.set()
        self._pending = None
        self.pool.waitForDone(-1)
