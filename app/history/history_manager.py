import logging
import queue
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QImage

from app.core.storage import read_json, write_json


class ImageWriter(QRunnable):
    def __init__(self, image, directory, record, completed, notify):
        super().__init__()
        self.image = image.copy()
        self.directory, self.record = directory, record
        self.completed, self.notify = completed, notify

    def run(self):
        error = None
        path = self.directory / self.record["file"]
        thumbnail = self.directory / self.record["thumbnail"]
        temporary = path.with_suffix(".tmp")
        try:
            if not self.image.save(str(temporary), "PNG"):
                raise OSError("无法保存截图历史，请检查磁盘空间")
            temporary.replace(path)
            small = self.image.scaled(160, 110, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
            if not small.save(str(thumbnail), "PNG"):
                raise OSError("无法写入缩略图")
        except Exception as exc:
            logging.exception("History image write failed")
            error = str(exc)
            path.unlink(missing_ok=True)
            thumbnail.unlink(missing_ok=True)
        finally:
            temporary.unlink(missing_ok=True)
            self.image = QImage()
            self.completed.put((self.record, error))
            self.notify.emit()


class HistoryManager(QObject):
    changed = Signal()
    failed = Signal(str)
    ready = Signal()

    def __init__(self, directory: Path, limit=50, parent=None):
        super().__init__(parent)
        self.directory = directory / "history"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.index = self.directory / "index.json"
        self.limit = max(1, min(50, limit))
        self.records = []
        raw = read_json(self.index, {"version": 1, "items": []})
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            seen = set()
            for item in raw["items"]:
                if not isinstance(item, dict):
                    continue
                identifier = item.get("id", "")
                if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
                    continue
                if identifier in seen or not isinstance(item.get("created_at"), str):
                    continue
                if item.get("source") not in ("screenshot", "clipboard", "imported"):
                    continue
                if item.get("file") != identifier + ".png" or item.get("thumbnail") != identifier + ".thumb.png":
                    continue
                if not (self.directory / item["file"]).is_file():
                    continue
                seen.add(identifier)
                self.records.append(item)
        self.records.sort(key=lambda item: item["created_at"], reverse=True)
        self.completed = queue.Queue()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.ready.connect(self._drain)
        self.set_limit(self.limit)

    def add(self, image, source="screenshot"):
        if source not in ("screenshot", "clipboard", "imported"):
            raise ValueError("未知图片来源")
        if image.isNull():
            raise ValueError("图片为空")
        identifier = uuid.uuid4().hex
        record = {"id": identifier, "file": identifier + ".png",
                  "thumbnail": identifier + ".thumb.png",
                  "created_at": datetime.now(timezone.utc).isoformat(), "source": source,
                  "width": image.width(), "height": image.height()}
        self.pool.start(ImageWriter(image, self.directory, record, self.completed, self.ready))

    def _drain(self):
        while not self.completed.empty():
            record, error = self.completed.get_nowait()
            if error:
                self.failed.emit(error)
                continue
            self.records.insert(0, record)
            self.records.sort(key=lambda item: item["created_at"], reverse=True)
            try:
                self.set_limit(self.limit)
            except OSError as exc:
                logging.exception("Cannot commit history index")
                self.failed.emit(str(exc))
        self.changed.emit()

    def _persist(self, records):
        write_json(self.index, {"version": 1, "items": records})

    def _delete_files(self, records):
        for record in records:
            for field in ("file", "thumbnail"):
                try:
                    (self.directory / record[field]).unlink(missing_ok=True)
                except OSError:
                    logging.exception("Cannot remove history file")

    def set_limit(self, limit):
        limit = max(1, min(50, limit))
        retained, removed = self.records[:limit], self.records[limit:]
        self._persist(retained)
        self.limit, self.records = limit, retained
        self._delete_files(removed)
        self.changed.emit()

    def delete(self, identifier):
        removed = [record for record in self.records if record["id"] == identifier]
        retained = [record for record in self.records if record["id"] != identifier]
        self._persist(retained)
        self.records = retained
        self._delete_files(removed)
        self.changed.emit()

    def load_image(self, record):
        image = QImage(str(self.directory / record["file"]))
        if image.isNull():
            raise ValueError("图片文件无法读取，可能已被移动或损坏")
        return image

    def shutdown(self):
        # Finish local writes and commit their metadata even when quitting immediately.
        self.pool.waitForDone(-1)
        self._drain()
