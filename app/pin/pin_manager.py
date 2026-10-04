import uuid

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from .pin_window import PinWindow
from .workspace import WorkspaceStore


class PinManager(QObject):
    changed = Signal(int)
    image_tools_requested = Signal(object, bool)
    failed = Signal(str)
    workspace_saved = Signal(int)

    def __init__(self, parent=None, directory=None):
        super().__init__(parent)
        self.windows = []
        self.hidden = False
        self._closing = self._restoring = self._announce_save = False
        self._touched = False
        self.workspace = WorkspaceStore(directory, self) if directory is not None else None
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(600)
        self.save_timer.timeout.connect(self.save_workspace)
        if self.workspace:
            self.workspace.loaded.connect(self._restore_loaded)
            self.workspace.failed.connect(self.failed.emit)
            self.workspace.saved.connect(self._saved)

    def add(self, image, point=None, state=None):
        if image is None or image.isNull():
            raise ValueError("图片为空")
        window = PinWindow(image, point)
        window.workspace_id = state["id"] if state else uuid.uuid4().hex
        if state:
            window.restore_state(state)
        window.closed.connect(self._remove)
        window.image_tools_requested.connect(self.image_tools_requested.emit)
        window.state_changed.connect(self._schedule_save)
        self.windows.append(window)
        if not self.hidden:
            window.show()
        self.changed.emit(len(self.windows))
        if not self._restoring or state is None:
            self._schedule_save()
        return window

    def _remove(self, window):
        if window in self.windows:
            self.windows.remove(window)
        self.changed.emit(len(self.windows))
        self._schedule_save()

    def hide_all(self):
        self.hidden = True
        for window in self.windows:
            window.hide()
        self._schedule_save()

    def restore_all(self):
        self.hidden = False
        for window in self.windows:
            window.show()
        self._schedule_save()

    def close_all(self):
        for window in self.windows[:]:
            window.close()

    def restore_interaction(self):
        for window in self.windows:
            window.set_click_through(False)
            window.set_locked(False)
        self.restore_all()

    def _schedule_save(self):
        if not self._closing:
            self._touched = True
        if self.workspace and not self._closing and not self._restoring:
            self.save_timer.start()

    def snapshot(self):
        return [({"id": w.workspace_id, "file": w.workspace_id + ".png",
                  "x": w.x(), "y": w.y(), "width": w.width(), "height": w.height(),
                  "opacity": w.windowOpacity(), "locked": w.locked,
                  "click_through": w.click_through}, QImage(w.image)) for w in self.windows], self.hidden

    def save_workspace(self, announce=False):
        if self.workspace and not self._closing and not self._restoring:
            self.save_timer.stop()
            self._touched = True
            self._announce_save |= bool(announce)
            self.workspace.save(self.snapshot())

    def _saved(self, count):
        if self._announce_save:
            self._announce_save = False
            self.workspace_saved.emit(count)

    def restore_workspace(self):
        if self.workspace and not self.windows and not self._restoring:
            self._restoring = True
            self.workspace.load()

    def _restore_loaded(self, entries, hidden):
        if not self._touched:
            self.hidden = hidden
        try:
            for record, image in entries:
                try:
                    self.add(image, state=record)
                except Exception as error:
                    self.failed.emit(f"无法恢复贴图：{error}")
        finally:
            self._restoring = False
        if self._touched:
            self._schedule_save()

    def shutdown(self):
        self.save_timer.stop()
        self._closing = True
        if self.workspace:
            self.workspace.shutdown(self.snapshot() if self._touched else None,
                                    merge_loading=self._restoring)
        self.close_all()
