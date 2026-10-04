"""Connect local OCR, Ollama, image rendering and one reusable result window."""
import logging
import threading

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QFont, QImage, QImageReader
from PySide6.QtWidgets import QApplication, QFileDialog

from app.translation.image_renderer import render_translations
from app.translation.ollama_client import OllamaClient
from app.ui.image_tools_window import ImageToolsWindow
from .engine import ProcessingCancelled, check_cancelled, extract_text


class TaskSignals(QObject):
    completed = Signal(int, str, object, str)


class ImageTask(QRunnable):
    def __init__(self, generation, kind, function, args, signals):
        super().__init__()
        self.generation, self.kind = generation, kind
        self.function, self.args, self.signals = function, args, signals
        self.cancelled = threading.Event()

    def run(self):
        result, error = None, ""
        try:
            check_cancelled(self.cancelled)
            result = self.function(*self.args, self.cancelled)
        except ProcessingCancelled:
            pass
        except Exception as exc:
            logging.exception("Image processing task failed: %s", self.kind)
            error = str(exc)[:500] or "图片处理失败，请检查日志"
        finally:
            self.args = ()
            self.signals.completed.emit(self.generation, self.kind, result, error)


class ImageToolsManager(QObject):
    busy_changed = Signal(bool)
    operation_finished = Signal(bool)
    settings_requested = Signal()
    assistant_requested = Signal(str, str)

    def __init__(self, config, pins, parent=None):
        super().__init__(parent)
        self.config = config
        self.window = ImageToolsWindow()
        self.window.assistant_requested.connect(self.assistant_requested.emit)
        self.window.pin_requested.connect(pins.add)
        self.window.settings_requested.connect(self.settings_requested.emit)
        self.window.import_requested.connect(self.open_file)
        self.window.clipboard_requested.connect(self.open_clipboard)
        self.window.extract_requested.connect(self.extract)
        self.window.translate_requested.connect(self.translate)
        self.window.cancel_requested.connect(self.cancel)
        self.window.closed.connect(lambda: self.cancel(announce=False))
        self.client = OllamaClient(self)
        self.client.batch_completed.connect(self._batch_completed)
        self.client.completed.connect(self._translation_completed)
        self.client.failed.connect(self._error)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.signals = TaskSignals(self)
        self.signals.completed.connect(self._task_completed)
        self._generation = 0
        self._running = self._pending = None
        self._auto_translate = False
        self._closing = False
        self.busy = False

    def show(self, translate=False):
        self.window.set_mode(translate)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self.window, "打开图片", "",
                    "图片 (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff);;所有文件 (*)")
        if not path:
            return
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        size = reader.size()
        if size.width() * size.height() > 64_000_000:
            self.window.status.setText("图片过大，请打开较小的图片或先截取文字区域")
            self.operation_finished.emit(False)
            return
        image = reader.read()
        if image.isNull():
            self.window.status.setText(f"无法打开图片：{reader.errorString()}")
            self.operation_finished.emit(False)
            return
        self.open_image(image, translate=self.window.translation_mode)

    def open_clipboard(self):
        image = QApplication.clipboard().image()
        if image.isNull():
            self.window.status.setText("剪贴板中没有图片，请先复制图片或截图")
            self.operation_finished.emit(False)
            return
        self.open_image(image, translate=self.window.translation_mode)

    def open_image(self, image, translate=False):
        if image is None or image.isNull():
            return
        self.cancel(announce=False)
        self.window.set_mode(translate)
        self.window.set_image(image, self.config.translation_language)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self._auto_translate = bool(translate)
        self.extract(auto_translate=translate)

    def extract(self, auto_translate=False):
        if self.window.image.isNull():
            return
        self.cancel(announce=False)
        self._auto_translate = bool(auto_translate)
        self.window.set_mode(auto_translate)
        self.window.clear_results()
        self.window.status.setText("正在本机提取文字…首次加载 OCR 模型需要几秒")
        self._queue("ocr", extract_text, QImage(self.window.image))

    def _queue(self, kind, function, *args):
        task = ImageTask(self._generation, kind, function, args, self.signals)
        self._set_busy(True)
        if self._running is not None:
            # Keep only the latest request while a canceled CPU call finishes.
            self._pending = task
            self.window.status.setText("正在结束上一次图片处理，随后处理当前图片…")
        else:
            self._running = task
            self.pool.start(task)

    @Slot(int, str, object, str)
    def _task_completed(self, generation, kind, result, error):
        self._running = None
        if self._closing:
            return
        if self._pending is not None:
            self._running, self._pending = self._pending, None
            self.window.status.setText("正在本机提取文字…" if self._running.kind == "ocr" else "正在生成译文图片…")
            self.pool.start(self._running)
        if generation != self._generation:
            return
        if error:
            self._error(error)
            return
        if result is None:
            return
        if kind == "ocr":
            self.window.set_blocks(result.paragraphs)
            if not result.blocks:
                self.window.status.setText("没有识别到文字，请尝试更清晰的图片或更小的截图区域")
                self._finish(False)
            elif self._auto_translate:
                self._auto_translate = False
                self.translate()
            else:
                self.window.status.setText(f"已提取 {len(result.blocks)} 行文字，整理为 {len(result.paragraphs)} 个段落。"
                                           "可自由选中复制，或修改原文后翻译。")
                self._finish(True)
        else:
            self.window.set_translated_image(result.image)
            message = "翻译完成，可在右侧自由选中复制译文；勾选“图片覆盖译文”可查看并导出译文图片。"
            if result.shortened:
                message += f" {result.shortened} 处文字过长或区域太小，完整译文见右侧。"
            self.window.status.setText(message)
            self._finish(True)

    def translate(self):
        self.window.set_mode(True)
        entries = self.window.source_entries()
        if not entries:
            self.window.status.setText("请先提取图片中的文字")
            return
        self.cancel(announce=False)
        self.window.clear_translation()
        self._set_busy(True)
        self.window.status.setText(f"正在连接本地模型 {self.config.translation_model}…")
        try:
            self.client.start(entries, self.config.ollama_url,
                              self.config.translation_model, self.window.language.currentData())
        except (ValueError, RuntimeError) as error:
            self._error(str(error))

    def _batch_completed(self, translations, completed, total):
        self.window.update_translations(translations)
        self.window.status.setText(f"正在本地翻译…{completed} / {total} 批")

    def _translation_completed(self, translations):
        regions = self.window.current_regions()
        if not regions:
            self.window.status.setText("翻译完成，可自由选中复制译文。原文分段已修改，本次未生成覆盖译文图片。")
            self._finish(True)
            return
        self.window.status.setText("正在将译文覆盖到图片…")
        self._queue("render", render_translations, QImage(self.window.image), regions,
                    dict(translations), QFont(QApplication.font()))

    def _set_busy(self, busy):
        self.busy = busy
        self.window.set_busy(busy)
        self.busy_changed.emit(busy)

    def _finish(self, success):
        self._set_busy(False)
        self.operation_finished.emit(success)

    def _error(self, message):
        self.window.status.setText(message)
        self._finish(False)

    def cancel(self, announce=True):
        self._generation += 1
        self._auto_translate = False
        self.client.cancel()
        if self._running is not None:
            self._running.cancelled.set()
        self._pending = None
        self._set_busy(False)
        if announce:
            self.window.status.setText("已取消。正在执行的 OCR 会在当前推理结束后释放资源。")

    def shutdown(self):
        self._closing = True
        self.cancel(announce=False)
        self.window.close()
        self.pool.waitForDone(-1)
