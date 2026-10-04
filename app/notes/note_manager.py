import uuid
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal

from app.core.storage import read_json, write_json


class NoteManager(QObject):
    changed = Signal(int)

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        self.path = directory / "notes.json"
        self.records = []
        raw = read_json(self.path, {"version": 1, "items": []})
        seen = set()
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            for item in raw["items"]:
                if (isinstance(item, dict) and isinstance(item.get("id"), str)
                    and isinstance(item.get("text"), str) and item["text"].strip()
                    and type(item.get("done")) is bool and isinstance(item.get("created_at"), str)
                    and item["id"] not in seen):
                    self.records.append(item)
                    seen.add(item["id"])

    def _commit(self, records):
        write_json(self.path, {"version": 1, "items": records})
        self.records = records
        self.changed.emit(len(records))

    def add(self, text):
        text = text.strip()
        if not text or len(text) > 2000:
            raise ValueError("便签内容需为 1～2000 个字符")
        record = {"id": uuid.uuid4().hex, "text": text, "done": False,
                  "created_at": datetime.now(timezone.utc).isoformat()}
        self._commit([record] + self.records)
        return record

    def set_done(self, identifier, done):
        records = [dict(record, done=bool(done)) if record["id"] == identifier else record
                   for record in self.records]
        self._commit(records)

    def delete(self, identifier):
        self._commit([record for record in self.records if record["id"] != identifier])
