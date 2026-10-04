import logging

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget

from app.core.images import copy_image, save_image
from app.ui.components import ToolButton, card, column, row, separator, soft_shadow
from app.ui.theme import THEME, tool_window
from .capture_overlay import CaptureOverlay
from .screen_capture import capture_screens, compose_selection, cursor_native, selection_rect
from .selection_geometry import clamp_point, hit_test, move_selection, resize_selection
from .toolbar_icons import toolbar_icon
from .annotation_window import AnnotationWindow


class CaptureToolbar(QWidget):
    def __init__(self, manager):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.manager = manager
        self.setWindowTitle("截图操作")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tool_window(self, floating=True)
        outer = column(self, 8, 0)
        shell = card(THEME.page_padding)
        soft_shadow(shell)
        outer.addWidget(shell)
        layout = row()
        shell.layout().addLayout(layout)
        for kind, text, tooltip, action in (
            ("copy", "复制", "复制", manager.copy),
            ("pin", "贴图", "贴图（固定到桌面）", manager.pin),
            ("save", "保存", "保存", manager.save),
            ("annotate", "标注", "标注：箭头、矩形、文字、马赛克", manager.annotate),
            ("ocr", "提取文字", "提取文字", manager.extract_text),
            ("translate", "翻译图片", "翻译图片（本地模型）", manager.translate_image),
            ("cancel", "取消", "取消", manager.cancel),
        ):
            if kind in ("ocr", "cancel"):
                layout.addWidget(separator(vertical=True))
            button = ToolButton(text, "primary" if kind == "copy" else
                                "ghost" if kind == "cancel" else "secondary",
                                kind=kind, icon_only=True, parent=self)
            button.setAccessibleName(text)
            button.setToolTip(tooltip)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setIcon(toolbar_icon(kind))
            button.setIconSize(QSize(20, 20))
            button.setFixedSize(THEME.control_height, THEME.control_height)
            button.setAutoRaise(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            # clicked(bool) must not become cancel(remember=False).
            button.clicked.connect(lambda checked=False, action=action: action())
            button.installEventFilter(self)
            layout.addWidget(button)
        self.adjustSize()
        self.place_near_selection()

    def place_near_selection(self):
        selection = self.manager.selection
        corner = QPoint(selection.x() + selection.width() - 1, selection.y() + selection.height() - 1)
        snapshot = next((s for s in self.manager.snapshots if s.native.contains(corner)), None)
        if snapshot is None:
            cursor = cursor_native(self.manager.snapshots)
            snapshot = next((s for s in self.manager.snapshots if s.native.contains(cursor)), self.manager.snapshots[0])
        self.winId()
        self.windowHandle().setScreen(snapshot.screen)
        local = snapshot.local_rect(selection)
        area = snapshot.screen.availableGeometry()
        left = snapshot.logical.x() + round(local.left())
        right = snapshot.logical.x() + round(local.right())
        top = snapshot.logical.y() + round(local.top())
        bottom = snapshot.logical.y() + round(local.bottom())
        if bottom + 12 + self.height() <= area.y() + area.height():
            y = bottom + 12
        elif top - 12 - self.height() >= area.top():
            y = top - 12 - self.height()
        else:
            y = bottom - self.height() - 12
        x = max(left, right - self.width() - 12)
        self.move(max(area.left(), min(x, area.x() + area.width() - self.width())),
                  max(area.top(), min(y, area.y() + area.height() - self.height())))

    def eventFilter(self, watched, event):
        # Buttons otherwise consume arrow keys for focus navigation.
        if event.type() == QEvent.Type.KeyPress and self.manager.handle_key(event):
            return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if not self.manager.handle_key(event):
            super().keyPressEvent(event)


class ScreenshotManager(QObject):
    started = Signal()
    prepared = Signal()
    overlay_raised = Signal()
    finished = Signal()
    captured = Signal(object)
    finalized = Signal(object)
    pin_requested = Signal(object)
    image_tools_requested = Signal(object, bool)
    failed = Signal(str)
    annotated = Signal(object)
    quick_ocr_requested = Signal(object)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.active = False
        self.snapshots, self.overlays = [], []
        self.start_point = self.selection = self.result = self.toolbar = self.drag_overlay = None
        self.drag_mode = self._drag_origin = self._result_selection = None
        self.desktop = QRect()
        self._committed = False
        self.annotation = None
        self.mode = "image"
        self.prepare_timer = QTimer(self)
        self.prepare_timer.setSingleShot(True)
        self.prepare_timer.timeout.connect(self._prepare)
        self.cursor_timer = QTimer(self)
        self.cursor_timer.setInterval(16)
        self.cursor_timer.timeout.connect(self.update_selection)
        self.refine_timer = QTimer(self)
        self.refine_timer.setSingleShot(True)
        self.refine_timer.setInterval(80)
        self.refine_timer.timeout.connect(self._refresh_after_keys)

    @property
    def dragging(self):
        return self.drag_overlay is not None

    def start(self, mode="image"):
        if self.active:
            return
        self.active = True
        self.mode = "quick_ocr" if mode == "quick_ocr" else "image"
        self._committed = False
        self.started.emit()
        # Let the compositor remove the pet/panel before caching the desktop.
        self.prepare_timer.start(70)

    def _prepare(self):
        try:
            self.snapshots = capture_screens()
            self.desktop = QRect(self.snapshots[0].native)
            for snapshot in self.snapshots[1:]:
                self.desktop = self.desktop.united(snapshot.native)
            for snapshot in self.snapshots:
                overlay = CaptureOverlay(self, snapshot)
                self.overlays.append(overlay)
                overlay.show()
            point = QCursor.pos()
            focus = next((o for o in self.overlays if o.geometry().contains(point)), self.overlays[0])
            focus.raise_()
            focus.activateWindow()
            focus.setFocus()
            self.prepared.emit()
        except Exception as error:
            self._fail(error)

    def begin_selection(self, overlay):
        self._begin_drag(overlay, "new")

    def begin_interaction(self, overlay):
        point = cursor_native(self.snapshots)
        mode = self._hit_test(overlay.snapshot, point) if self.result is not None else "new"
        self._begin_drag(overlay, mode)

    def _hit_test(self, snapshot, point):
        return hit_test(self.selection, point,
                        7 * snapshot.native.width() / snapshot.logical.width(),
                        7 * snapshot.native.height() / snapshot.logical.height())

    def update_cursor(self, overlay):
        mode = self.drag_mode if self.dragging else self._hit_test(overlay.snapshot, cursor_native(self.snapshots))
        cursors = {"nw": Qt.CursorShape.SizeFDiagCursor, "se": Qt.CursorShape.SizeFDiagCursor,
                   "ne": Qt.CursorShape.SizeBDiagCursor, "sw": Qt.CursorShape.SizeBDiagCursor,
                   "n": Qt.CursorShape.SizeVerCursor, "s": Qt.CursorShape.SizeVerCursor,
                   "w": Qt.CursorShape.SizeHorCursor, "e": Qt.CursorShape.SizeHorCursor,
                   "move": Qt.CursorShape.SizeAllCursor}
        overlay.setCursor(cursors.get(mode, Qt.CursorShape.CrossCursor))

    def _begin_drag(self, overlay, mode):
        if not self.active or self.dragging or not self.snapshots:
            return
        self.refine_timer.stop()
        try:
            # Finish pending keyboard edits before starting another mouse drag.
            self._refresh_result()
        except Exception as error:
            self._fail(error)
            return
        self.start_point = cursor_native(self.snapshots)
        self._drag_origin = QRect(self.selection) if self.selection is not None else None
        self.drag_mode = mode
        self.drag_overlay = overlay
        if self.toolbar:
            self.toolbar.hide()
        overlay.raise_()
        overlay.activateWindow()
        overlay.setFocus()
        self.overlay_raised.emit()
        overlay.grabMouse()
        self.update_cursor(overlay)
        self.cursor_timer.start()
        self.update_selection()

    def update_selection(self):
        if not self.dragging:
            return
        point = cursor_native(self.snapshots)
        delta = point - self.start_point
        if self.drag_mode == "new":
            rect = selection_rect(clamp_point(self.start_point, self.desktop), clamp_point(point, self.desktop))
        elif self.drag_mode == "move":
            rect = move_selection(self._drag_origin, delta, self.desktop)
        else:
            rect = resize_selection(self._drag_origin, delta, self.drag_mode, self.desktop)
        if rect == self.selection:
            return
        self.selection = rect
        self._repaint()

    def _repaint(self):
        for overlay in self.overlays:
            overlay.update()

    def complete_selection(self):
        if not self.dragging:
            return
        self.update_selection()
        self.cursor_timer.stop()
        if self.drag_overlay:
            overlay = self.drag_overlay
            overlay.releaseMouse()
            self.drag_overlay = None
        self.start_point = self.drag_mode = self._drag_origin = None
        if self.selection.width() < 2 or self.selection.height() < 2:
            # A click outside an existing selection should not discard it.
            self.selection = QRect(self._result_selection) if self._result_selection is not None else None
        try:
            self._refresh_result()
            self._repaint()
            self.update_cursor(overlay)
            if self.result is not None:
                if self.mode == "quick_ocr":
                    image = self.result
                    self.cancel()
                    self.quick_ocr_requested.emit(image)
                else:
                    self._show_toolbar()
        except Exception as error:
            self._fail(error)

    def _show_toolbar(self):
        if self.toolbar is None:
            self.toolbar = CaptureToolbar(self)
        else:
            self.toolbar.place_near_selection()
        self.toolbar.show()
        self.toolbar.raise_()
        self.toolbar.activateWindow()
        self.overlay_raised.emit()

    def _refresh_result(self, auto_copy=True):
        if not self.active or self.dragging or self.selection is None or self.selection.isEmpty():
            return
        if self.result is not None and self.selection == self._result_selection:
            return
        image = compose_selection(self.snapshots, self.selection)
        if auto_copy and self.config.auto_copy and self.mode == "image":
            copy_image(image)
        self.result = image
        self._result_selection = QRect(self.selection)
        self.captured.emit(image)

    def _refresh_after_keys(self):
        try:
            self._refresh_result()
        except Exception as error:
            self._fail(error)

    def handle_key(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()
            return True
        if not self.active or self.dragging or self.result is None:
            return False
        key, modifiers = event.key(), event.modifiers()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) or (key == Qt.Key.Key_C and modifiers & Qt.KeyboardModifier.ControlModifier):
            self.copy()
            return True
        if modifiers & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier):
            return False
        directions = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
                      Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if key not in directions:
            return False
        step = 10 if modifiers & Qt.KeyboardModifier.ShiftModifier else 1
        x, y = directions[key]
        delta = QPoint(x * step, y * step)
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            rect = resize_selection(self.selection, delta, "e" if x else "s", self.desktop)
        else:
            rect = move_selection(self.selection, delta, self.desktop)
        try:
            if rect != self.selection:
                self.selection = rect
                self._repaint()
                if self.toolbar:
                    self.toolbar.place_near_selection()
                # Debounce keyboard repeats; mouse resizing only recrops on release.
                self.refine_timer.start()
        except Exception as error:
            self._fail(error)
        return True

    def _current_result(self, auto_copy=True):
        self.refine_timer.stop()
        self._refresh_result(auto_copy)
        if self.result is None:
            raise ValueError("请先选择截图区域")
        return self.result

    def copy(self):
        try:
            copy_image(self._current_result(auto_copy=False))
            self.cancel()
        except Exception as error:
            self._fail(error)

    def pin(self):
        try:
            self.pin_requested.emit(self._current_result())
            self.cancel()
        except Exception as error:
            self._fail(error)

    def extract_text(self):
        self._open_image_tool(False)

    def annotate(self):
        try:
            image = self._current_result()
            self.cancel()
            if self.annotation is not None:
                self.annotation.close()
            window = AnnotationWindow(image)
            self.annotation = window
            window.pin_requested.connect(self.pin_requested.emit)
            window.exported.connect(self.annotated.emit)
            window.destroyed.connect(lambda: self._annotation_closed(window))
            window.show()
            window.raise_()
            window.activateWindow()
        except Exception as error:
            self._fail(error)

    def _annotation_closed(self, window):
        if self.annotation is window:
            self.annotation = None

    def shutdown(self):
        self.cancel()
        if self.annotation is not None:
            self.annotation.close()

    def translate_image(self):
        self._open_image_tool(True)

    def _open_image_tool(self, translate):
        try:
            image = self._current_result()
            self.cancel()
            self.image_tools_requested.emit(image, translate)
        except Exception as error:
            self._fail(error)

    def save(self):
        try:
            image = self._current_result()
            self.cancel()  # Remove dimming before the file dialog is shown.
            save_image(image)
        except Exception as error:
            self._fail(error)

    def _fail(self, error):
        logging.exception("Screenshot failed")
        self.cancel(remember=False)
        self.failed.emit(str(error))

    def cancel(self, remember=True):
        was_active = self.active
        error = None
        if was_active and remember:
            try:
                # Commit one final image to history, never every intermediate
                # size. An interrupted mouse drag retains the last release.
                self._refresh_result()
                if self.result is not None and not self._committed:
                    self._committed = True
                    self.finalized.emit(self.result)
            except Exception as exc:
                logging.exception("Cannot finalize screenshot")
                error = str(exc)
        self.prepare_timer.stop()
        self.cursor_timer.stop()
        self.refine_timer.stop()
        if self.drag_overlay:
            self.drag_overlay.releaseMouse()
        for overlay in self.overlays:
            overlay.close()
        if self.toolbar:
            self.toolbar.close()
        self.overlays, self.snapshots = [], []
        self.start_point = self.selection = self.result = self.toolbar = self.drag_overlay = None
        self.drag_mode = self._drag_origin = self._result_selection = None
        self.desktop = QRect()
        self.active = False
        if was_active:
            self.finished.emit()
        if error:
            self.failed.emit(error)
