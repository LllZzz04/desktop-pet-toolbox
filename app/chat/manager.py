"""Coordinate one conversation, async transport, persistence and pet events."""
import logging

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.secrets import ChatCredentials
from app.ui.chat_window import ChatWindow
from .client import ChatClient
from .conversation import Conversation
from .settings import MAX_INPUT_CHARS, validate_api_key, validate_chat_settings


class ChatManager(QObject):
    busy_changed = Signal(bool)
    operation_finished = Signal(bool)
    settings_requested = Signal()
    reply_started = Signal(str)
    reply_text = Signal(str)
    reply_finished = Signal(str, bool)
    reply_rejected = Signal(str)
    conversation_cleared = Signal()

    def __init__(self, config, directory, parent=None):
        super().__init__(parent)
        self.config = config
        self.busy = self.closing = False
        self._reply_source = "window"
        self.credentials = ChatCredentials(directory)
        warning = ""
        try:
            self.api_key = validate_api_key(self.credentials.load())
        except (OSError, ValueError):
            self.api_key = ""
            warning = "无法读取已保存的 API Key，请在对话设置中重新填写。"
            logging.warning("Chat credential could not be loaded")
        try:
            self.conversation = Conversation(directory, config.chat_save_history)
        except OSError:
            self.conversation = Conversation(directory, False)
            warning += "本地对话记录读取失败，当前对话暂不保存。"
            logging.warning("Chat history could not be loaded")
        self.client = ChatClient(self)
        self.client.text_received.connect(self._chunk)
        self.client.completed.connect(self._completed)
        self.client.failed.connect(self._failed)
        self.window = ChatWindow()
        self.window.set_profile(config)
        self.window.render(self.conversation.messages)
        self.window.set_busy(False, self.conversation.can_retry)
        if warning:
            self.window.status.setText(warning)
        self.window.send_requested.connect(self.send)
        self.window.retry_requested.connect(lambda: self.retry(origin="window"))
        self.window.stop_requested.connect(self.stop)
        self.window.clear_requested.connect(self.clear)
        self.window.settings_requested.connect(self.settings_requested.emit)
        self.window.closed.connect(self._window_closed)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save)
        self.paint_timer = QTimer(self)
        self.paint_timer.setSingleShot(True)
        self.paint_timer.timeout.connect(self._paint)
        self.pending_text = []
        self.save_warning = ""

    @property
    def has_api_key(self):
        return bool(self.api_key)

    def configure(self, config, key):
        if config.chat_save_history != self.conversation.persistent:
            self.conversation.set_persistent(config.chat_save_history)
        self.config, self.api_key = config, key
        self.window.set_profile(config)

    def show(self, draft=""):
        if draft and not self.busy:
            self.window.input.setPlainText(draft)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.window.input.setFocus()

    def _window_closed(self):
        if self._reply_source == "window":
            self.stop()

    def send(self, text, *, retry=False, origin="window"):
        if self.busy or self.closing:
            return False
        try:
            url, model = validate_chat_settings(self.config.chat_base_url, self.config.chat_model)
            key = validate_api_key(self.api_key)
            if not key:
                raise ValueError("请先在对话设置中填写 API Key")
            if not retry and (not text.strip() or len(text.strip()) > MAX_INPUT_CHARS):
                raise ValueError(f"消息需为 1～{MAX_INPUT_CHARS} 个字符")
            self.conversation.begin(text, retry=retry)
        except ValueError as error:
            self.window.status.setText(str(error))
            self.reply_rejected.emit(str(error))
            self.operation_finished.emit(False)
            if not self.api_key:
                self.settings_requested.emit()
            return False
        self.save_warning = ""
        self.window.render(self.conversation.messages)
        self.window.set_busy(True, False)
        self.window.status.setText("正在等待回复…")
        if not retry:
            self.window.input.clear()
        self.busy = True
        self._reply_source = origin
        self.busy_changed.emit(True)
        self.reply_started.emit(self.conversation.messages[-2]["content"])
        self._save()
        try:
            self.client.start(self.conversation.context(), url, model, key)
        except (ValueError, RuntimeError):
            self._failed("无法发起对话请求，请检查对话设置")
        return True

    def retry(self, *, origin=None):
        if self.conversation.can_retry:
            self.send("", retry=True, origin=origin or self._reply_source)

    def _chunk(self, text):
        if not self.busy:
            return
        try:
            self.conversation.append(text)
        except ValueError as error:
            self._failed(str(error))
            return
        self.pending_text.append(text)
        if not self.paint_timer.isActive():
            self.paint_timer.start(40)
        if not self.save_timer.isActive():
            self.save_timer.start(1000)
        self.window.status.setText("正在回复… 可点击停止生成")

    def _paint(self):
        self.paint_timer.stop()
        if self.pending_text:
            text = "".join(self.pending_text)
            self.pending_text.clear()
            self.window.append_answer(text)
            self.reply_text.emit(text)
            self.window.update_answer(self.conversation.messages)

    def _save(self):
        self.save_timer.stop()
        try:
            self.conversation.save()
            self.save_warning = ""
        except OSError:
            self.save_warning = " 本地记录保存失败，本次内容仍可复制。"
            logging.warning("Chat history could not be saved")

    def _end(self, status, message):
        self._paint()
        self.conversation.finish(status)
        self._save()
        self.busy = False
        self.window.set_busy(False, self.conversation.can_retry)
        self.window.update_answer(self.conversation.messages)
        self.window.status.setText(message + self.save_warning)
        self.busy_changed.emit(False)
        self.reply_finished.emit(message + self.save_warning, self.conversation.can_retry)

    def _completed(self, reason):
        if not self.busy:
            return
        if not self.conversation.messages[-1]["content"].strip():
            self._failed("模型没有返回文字，请检查模型名称后重试")
        elif reason == "length":
            self._end("partial", "回复达到输出上限，已保留收到的内容；可以缩短问题后重试。")
            self.operation_finished.emit(True)
        elif reason != "stop":
            self._failed("模型未正常完成回复，已保留收到的内容；可以重试上一条。")
        else:
            self._end("complete", "回复完成 · 可复制或继续输入")
            self.operation_finished.emit(True)

    def _failed(self, message):
        if not self.busy:
            return
        self.client.cancel()
        status = "partial" if self.conversation.messages[-1]["content"] else "failed"
        self._end(status, message)
        self.operation_finished.emit(False)
        logging.warning("Chat request failed")

    def stop(self):
        if not self.busy:
            return
        self.client.cancel()
        status = "partial" if self.conversation.messages[-1]["content"] else "failed"
        self._end(status, "已停止生成，保留已收到的内容；可重试上一条。")

    def clear(self):
        if self.busy:
            return
        try:
            self.conversation.clear()
        except OSError:
            self.window.status.setText("无法清空本地记录，请检查数据目录是否可以写入")
            self.reply_rejected.emit("无法清空本地记录，请检查数据目录是否可以写入")
            self.operation_finished.emit(False)
            return
        self.save_warning = ""
        self.window.render([])
        self.window.set_busy(False, False)
        self.window.status.setText("对话已清空，下一条消息会开始新对话")
        self.conversation_cleared.emit()

    def shutdown(self):
        self.closing = True
        self.stop()
        self._save()
        self.client.cancel()
        self.paint_timer.stop()
        self.window.close()
