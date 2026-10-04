"""Cancelable streaming chat transport. No model SDK or worker thread required."""
import json
from urllib.parse import urlsplit

from PySide6.QtCore import QByteArray, QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .settings import validate_api_key, validate_chat_settings

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_EVENT_BYTES = 1024 * 1024


class ChatClient(QObject):
    text_received = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        self.reply = None
        self.inactivity = QTimer(self)
        self.inactivity.setSingleShot(True)
        self.inactivity.timeout.connect(lambda: self._fail("服务响应超时，请检查网络后重试"))
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(lambda: self._fail("生成时间过长，已停止接收；可以缩短问题后重试"))
        self._reset()

    def _reset(self):
        self.buffer = bytearray()
        self.event = []
        self.event_size = self.received = 0
        self.finish_reason = ""
        self.json_response = False

    def start(self, messages, base_url, model, key):
        base_url, model = validate_chat_settings(base_url, model)
        key = validate_api_key(key)
        if not key:
            raise ValueError("请先在对话设置中填写 API Key")
        self.cancel()
        payload = {"model": model, "messages": messages, "stream": True, "max_tokens": 4096}
        if urlsplit(base_url).hostname == "api.deepseek.com":
            payload["thinking"] = {"type": "disabled"}
        request = QNetworkRequest(QUrl(base_url + "/chat/completions"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(QByteArray(b"Authorization"), QByteArray(("Bearer " + key).encode("ascii")))
        request.setRawHeader(QByteArray(b"Accept"), QByteArray(b"text/event-stream"))
        # Never forward the credential automatically to a redirect target.
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        request.setTransferTimeout(180_000)
        reply = self.network.post(request, QByteArray(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
        self.reply = reply
        reply.setReadBufferSize(MAX_EVENT_BYTES)
        reply.readyRead.connect(lambda r=reply: self._read(r))
        reply.finished.connect(lambda r=reply: self._finished(r))
        self.inactivity.start(180_000)
        self.deadline.start(600_000)

    def _read(self, reply):
        if reply is not self.reply:
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status is None:
            return
        raw = bytes(reply.readAll())
        if not raw:
            return
        self.received += len(raw)
        self.inactivity.start(180_000)
        if self.received > MAX_RESPONSE_BYTES:
            self._fail("服务返回的内容过大，已停止接收")
            return
        if not 200 <= int(status) < 300:
            return  # The HTTP code is enough; never display or log a raw error body.
        self.buffer.extend(raw)
        content_type = str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or "").lower()
        self.json_response = "application/json" in content_type
        if self.json_response:
            if len(self.buffer) > MAX_EVENT_BYTES:
                self._fail("服务返回的内容过大，已停止接收")
            return
        try:
            while reply is self.reply and b"\n" in self.buffer:
                line, _, rest = self.buffer.partition(b"\n")
                self.buffer = bytearray(rest)
                self._line(bytes(line).rstrip(b"\r"))
            if len(self.buffer) + self.event_size > MAX_EVENT_BYTES:
                raise ValueError("服务返回的数据片段过大")
        except (ValueError, UnicodeError):
            self._fail("无法读取服务的流式回复，请检查接口地址与模型")

    def _line(self, line):
        if not line:
            if self.event:
                data = b"\n".join(self.event)
                self.event, self.event_size = [], 0
                self._event(data)
            return
        if len(line) + self.event_size > MAX_EVENT_BYTES:
            raise ValueError("服务返回的数据片段过大")
        if line.startswith(b"data:"):
            value = line[5:]
            if value.startswith(b" "):
                value = value[1:]
            self.event.append(value)
            self.event_size += len(value) + 1
        # SSE comments and other fields are ignored, including keep-alives.

    def _event(self, raw):
        if raw.strip() == b"[DONE]":
            self._complete()
            return
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("error"):
            raise ValueError("服务返回错误")
        choices = payload.get("choices", [])
        if not isinstance(choices, list):
            raise ValueError("无效的回复格式")
        if not choices:
            return  # Optional usage-only chunks have an empty choices list.
        choice = choices[0]
        if not isinstance(choice, dict) or not isinstance(choice.get("delta", {}), dict):
            raise ValueError("无效的回复格式")
        reason = choice.get("finish_reason")
        if reason is not None:
            if not isinstance(reason, str):
                raise ValueError("无效的完成标记")
            self.finish_reason = reason
        content = choice.get("delta", {}).get("content")
        if content is not None:
            if not isinstance(content, str):
                raise ValueError("无效的回复内容")
            if content:
                self.text_received.emit(content)

    @staticmethod
    def _http_error(status):
        messages = {
            400: "请求参数不被支持，请检查模型名称与接口地址",
            401: "API Key 无效或已过期，请在对话设置中重新填写",
            402: "API 账户余额不足，请在服务平台检查余额",
            403: "服务拒绝访问，请检查 API Key 的权限",
            404: "未找到接口或模型，请检查服务地址与模型名称",
            429: "请求过于频繁或额度受限，请稍后重试",
            500: "模型服务暂时出错，请稍后重试",
            502: "模型服务暂时不可用，请稍后重试",
            503: "模型服务繁忙，请稍后重试",
        }
        if status and 300 <= status < 400:
            return "接口发生重定向，请在设置中填写服务的直接地址"
        return messages.get(status, f"服务请求失败（HTTP {status}），请检查服务配置")

    def _finished(self, reply):
        if reply is not self.reply:
            return
        self._read(reply)
        if reply is not self.reply:
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status is not None and not 200 <= int(status) < 300:
            self._fail(self._http_error(int(status)))
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            message = ("安全连接失败，请检查系统时间、证书和网络"
                       if reply.error() == QNetworkReply.NetworkError.SslHandshakeFailedError
                       else "连接中断或无法连接服务，请检查网络后重试")
            self._fail(message)
            return
        try:
            if self.json_response:
                payload = json.loads(self.buffer.decode("utf-8"))
                if not isinstance(payload, dict) or payload.get("error"):
                    raise ValueError
                choice = payload["choices"][0]
                content = choice["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError
                self.finish_reason = choice.get("finish_reason") or "stop"
                if not isinstance(self.finish_reason, str):
                    raise ValueError
                self.text_received.emit(content)
            else:
                if self.buffer:
                    self._line(bytes(self.buffer).rstrip(b"\r"))
                    self.buffer.clear()
                if self.event:
                    self._line(b"")
                if reply is not self.reply:
                    return
                if not self.finish_reason:
                    self._fail("回复未完整结束，已保留收到的内容；可以重试上一条")
                    return
            if reply is self.reply:
                self._complete()
        except (ValueError, UnicodeError, KeyError, TypeError, IndexError):
            self._fail("无法读取服务的回复，请检查接口地址与模型")

    def _complete(self):
        reason = self.finish_reason or "stop"
        self.cancel()
        self.completed.emit(reason)

    def _fail(self, message):
        if self.reply is None:
            return
        self.cancel()
        self.failed.emit(message)

    def cancel(self):
        reply, self.reply = self.reply, None
        self.inactivity.stop()
        self.deadline.stop()
        self._reset()
        if reply is not None:
            if not reply.isFinished():
                reply.abort()
            reply.deleteLater()
