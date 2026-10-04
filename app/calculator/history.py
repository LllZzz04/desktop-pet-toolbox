"""Local calculator records and named reusable expressions, bounded on disk."""
import uuid
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal

from app.core.storage import read_json, write_json


class CalculatorStore(QObject):
    changed = Signal()

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        self.path = directory / "calculations.json"
        raw = read_json(self.path, {})
        raw = raw if isinstance(raw, dict) else {}
        self.history = self._load(raw.get("history"), 100)
        self.favorites = self._load(raw.get("favorites"), 50, favorite=True)

    @staticmethod
    def _load(items, limit, favorite=False):
        result = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if any(not isinstance(item.get(key), str) for key in ("id", "expression", "answer", "created_at")):
                    continue
                if not 1 <= len(item["expression"]) <= 8000 or len(item["answer"]) > 16000:
                    continue
                if favorite and (not isinstance(item.get("name"), str) or not 1 <= len(item["name"]) <= 80):
                    continue
                result.append(item)
                if len(result) >= limit:
                    break
        return result

    def _commit(self, history, favorites):
        write_json(self.path, {"version": 1, "history": history, "favorites": favorites})
        self.history, self.favorites = history, favorites
        self.changed.emit()

    def record(self, expression, answer):
        expression = expression.strip()
        if self.history and self.history[0]["expression"] == expression and self.history[0]["answer"] == answer:
            return
        entry = {"id": uuid.uuid4().hex, "expression": expression, "answer": answer,
                 "created_at": datetime.now(timezone.utc).isoformat()}
        self._commit(([entry] + self.history)[:100], self.favorites)

    def favorite(self, entry, name):
        name = name.strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("收藏名称需为 1～80 字符")
        retained = [item for item in self.favorites if item["expression"] != entry["expression"]]
        if len(retained) >= 50:
            raise ValueError("最多收藏 50 个表达式，请先删除部分收藏")
        item = dict(entry, id=uuid.uuid4().hex, name=name)
        self._commit(self.history, [item] + retained)

    def delete(self, identifier, favorite=False):
        if favorite:
            self._commit(self.history, [item for item in self.favorites if item["id"] != identifier])
        else:
            self._commit([item for item in self.history if item["id"] != identifier], self.favorites)

    def clear_history(self):
        self._commit([], self.favorites)
