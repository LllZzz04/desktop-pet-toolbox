"""Atomic, bounded local pin snapshots; image encoding runs off the UI thread."""
import logging
import math
import re

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QImage, QImageReader

from app.core.storage import read_json, write_json

ID = re.compile(r"[0-9a-f]{32}")
MAX_PINS = 50
MAX_PIXELS = 128_000_000


class WorkspaceSignals(QObject):
    done = Signal(str, object, str)


class WorkspaceTask(QRunnable):
    def __init__(self, kind, directory, payload, signals):
        super().__init__()
        self.kind, self.directory, self.payload, self.signals = kind, directory, payload, signals
        self.result = None

    def run(self):
        result, error = None, ""
        try:
            result = self.load() if self.kind == "load" else self.save()
            if self.kind == "load":
                self.result = result
        except Exception as exc:
            logging.exception("Pin workspace %s failed", self.kind)
            error = str(exc)
        finally:
            self.payload = None
            self.signals.done.emit(self.kind, result, error)

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        entries, hidden = self.payload
        retained, pixels = [], 0
        for record, image in entries[-MAX_PINS:]:
            pixels += image.width() * image.height()
            if pixels > MAX_PIXELS:
                raise ValueError("贴图工作区超过 1.28 亿总像素；请关闭部分贴图后保存")
            path = self.directory / record["file"]
            if not path.is_file():
                temporary = path.with_suffix(".tmp")
                try:
                    if not image.save(str(temporary), "PNG"):
                        raise OSError("无法保存贴图工作区图片，请检查磁盘空间")
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
            retained.append(record)
        if len(entries) > MAX_PINS:
            raise ValueError("贴图工作区最多保存 50 张；请关闭部分贴图后保存")
        write_json(self.directory / "index.json",
                   {"version": 1, "hidden": hidden, "items": retained})
        names = {record["file"] for record in retained}
        for path in self.directory.glob("*.png"):
            if ID.fullmatch(path.stem) and path.name not in names:
                try:
                    path.unlink()
                except OSError:
                    logging.warning("Cannot remove obsolete pin image")
        return len(retained)

    def load(self):
        raw = read_json(self.directory / "index.json", {})
        if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
            return [], False, ""
        entries, seen, pixels, skipped = [], set(), 0, 0
        for record in raw["items"][:MAX_PINS]:
            if not isinstance(record, dict):
                skipped += 1
                continue
            identifier = record.get("id")
            if not isinstance(identifier, str) or not ID.fullmatch(identifier) or identifier in seen:
                skipped += 1
                continue
            if record.get("file") != identifier + ".png":
                skipped += 1
                continue
            if any(type(record.get(field)) is not int for field in ("x", "y", "width")):
                skipped += 1
                continue
            if not 1 <= record["width"] <= 8192 or any(abs(record[k]) > 1_000_000 for k in ("x", "y")):
                skipped += 1
                continue
            opacity = record.get("opacity", 1)
            if type(opacity) not in (float, int) or not math.isfinite(opacity) or not .1 <= opacity <= 1:
                skipped += 1
                continue
            reader = QImageReader(str(self.directory / record["file"]))
            size = reader.size()
            area = size.width() * size.height()
            if not size.isValid() or area > 64_000_000 or pixels + area > MAX_PIXELS:
                skipped += 1
                continue
            image = reader.read()
            if image.isNull():
                skipped += 1
                continue
            seen.add(identifier)
            pixels += area
            entries.append((record, image))
        warning = f"{skipped} 张工作区图片缺失、损坏或超出限制，已跳过" if skipped else ""
        return entries, raw.get("hidden") is True, warning


class WorkspaceStore(QObject):
    loaded = Signal(object, bool)
    saved = Signal(int)
    failed = Signal(str)

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        self.directory = directory / "pin_workspace"
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.signals = WorkspaceSignals(self)
        self.signals.done.connect(self._done)
        self._saving = False
        self._pending = None
        self._closing = False
        self._load_task = None

    def load(self):
        self._load_task = WorkspaceTask("load", self.directory, None, self.signals)
        self.pool.start(self._load_task)

    def save(self, payload):
        if self._saving:
            self._pending = payload
        else:
            self._saving = True
            self.pool.start(WorkspaceTask("save", self.directory, payload, self.signals))

    def _done(self, kind, result, error):
        if self._closing:
            return
        if error:
            self.failed.emit(error)
        if kind == "load":
            self._load_task = None
            if result is not None:
                entries, hidden, warning = result
                self.loaded.emit(entries, hidden)
                if warning:
                    self.failed.emit(warning)
            else:
                self.loaded.emit([], False)
        else:
            self._saving = False
            if self._pending is not None:
                payload, self._pending = self._pending, None
                self.save(payload)
            elif not error:
                self.saved.emit(result)

    def shutdown(self, payload=None, merge_loading=False):
        # Save the final snapshot after the existing worker has drained. Never
        # let closing the on-screen windows erase the just-saved layout.
        self._closing = True
        self.pool.waitForDone(-1)
        self._pending = None
        if merge_loading and payload is not None and self._load_task is not None:
            # An immediate quit must preserve pins still loading, including
            # those not yet delivered to the GUI, alongside newly created pins.
            loaded = self._load_task.result
            if loaded is not None:
                existing, hidden, warning = loaded
                current, current_hidden = payload
                identifiers = {record["id"] for record, image in current}
                payload = ([item for item in existing if item[0]["id"] not in identifiers] + current,
                           current_hidden)
        self._load_task = None
        if payload is not None:
            self.pool.start(WorkspaceTask("save", self.directory, payload, self.signals))
            self.pool.waitForDone(-1)
