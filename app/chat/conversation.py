"""One bounded, local conversation; incomplete turns never enter API context."""
from datetime import datetime, timezone

from app.core.storage import read_json, write_json
from .settings import (MAX_ANSWER_CHARS, MAX_CONTEXT_CHARS, MAX_CONTEXT_TURNS,
                       MAX_HISTORY_CHARS, MAX_HISTORY_TURNS, MAX_INPUT_CHARS)


class Conversation:
    def __init__(self, directory, persistent=True):
        self.path = directory / "chat.json"
        self.persistent = persistent
        self.messages = []
        if not persistent:
            return
        if self.path.exists() and self.path.stat().st_size > 4_000_000:
            raise OSError("本地对话记录过大，请先备份并移走 chat.json")
        raw = read_json(self.path, {"version": 1, "messages": []})
        items = raw.get("messages", []) if isinstance(raw, dict) and raw.get("version") == 1 else []
        if isinstance(items, list):
            # Keep user/assistant pairs together, including interrupted turns.
            for index in range(0, len(items) - 1, 2):
                user, assistant = items[index:index + 2]
                if not self._valid(user, "user") or not self._valid(assistant, "assistant"):
                    continue
                assistant = dict(assistant)
                if assistant["status"] == "pending":
                    assistant["status"] = "partial" if assistant["content"] else "failed"
                self.messages.extend([dict(user), assistant])
        self._prune()

    @staticmethod
    def _valid(item, role):
        return (isinstance(item, dict) and item.get("role") == role
                and isinstance(item.get("content"), str)
                and len(item["content"]) <= (MAX_INPUT_CHARS if role == "user" else MAX_ANSWER_CHARS)
                and item.get("status") in ("complete", "pending", "partial", "failed")
                and isinstance(item.get("created_at"), str))

    def _prune(self):
        size = sum(len(item["content"]) for item in self.messages)
        while len(self.messages) > 2 and (len(self.messages) > MAX_HISTORY_TURNS * 2 or size > MAX_HISTORY_CHARS):
            size -= sum(len(item["content"]) for item in self.messages[:2])
            del self.messages[:2]

    def begin(self, text, *, retry=False):
        if retry:
            if not self.can_retry:
                raise ValueError("没有可以重试的消息")
            self.messages[-1]["content"] = ""
            self.messages[-1]["status"] = "pending"
        else:
            text = text.strip()
            if not text or len(text) > MAX_INPUT_CHARS:
                raise ValueError(f"消息需为 1～{MAX_INPUT_CHARS} 个字符")
            created_at = datetime.now(timezone.utc).isoformat()
            self.messages.extend([
                {"role": "user", "content": text, "status": "complete", "created_at": created_at},
                {"role": "assistant", "content": "", "status": "pending", "created_at": created_at},
            ])
        self._prune()

    @property
    def can_retry(self):
        return bool(self.messages and self.messages[-1]["status"] in ("partial", "failed"))

    def context(self):
        turns, size = [], len(self.messages[-2]["content"])
        for index in range(len(self.messages) - 4, -1, -2):
            pair = self.messages[index:index + 2]
            if pair[1]["status"] != "complete":
                continue
            length = sum(len(item["content"]) for item in pair)
            if len(turns) >= MAX_CONTEXT_TURNS or size + length > MAX_CONTEXT_CHARS:
                break
            turns.append(pair)
            size += length
        result = [{"role": "system", "content": "你是一个桌面聊天助手，请用用户使用的语言清晰回答。"}]
        for pair in reversed(turns):
            result.extend({"role": item["role"], "content": item["content"]} for item in pair)
        result.append({"role": "user", "content": self.messages[-2]["content"]})
        return result

    def append(self, text):
        current = self.messages[-1]
        if len(current["content"]) + len(text) > MAX_ANSWER_CHARS:
            raise ValueError("回复过长，已停止接收；可以分成更小的问题继续询问")
        current["content"] += text

    def finish(self, status):
        if self.messages and self.messages[-1]["status"] == "pending":
            self.messages[-1]["status"] = status
        self._prune()

    def save(self):
        if self.persistent:
            write_json(self.path, {"version": 1, "messages": self.messages})

    def set_persistent(self, enabled):
        if enabled:
            write_json(self.path, {"version": 1, "messages": self.messages})
        else:
            self.path.unlink(missing_ok=True)
        self.persistent = enabled

    def clear(self):
        if self.persistent:
            write_json(self.path, {"version": 1, "messages": []})
        self.messages.clear()
