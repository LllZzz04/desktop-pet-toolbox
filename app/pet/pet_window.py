"""Desktop interaction and animation priorities for the Luna character."""
import math
import random
import time
from collections import deque

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .animation import Animation


class PetWindow(QWidget):
    ATTENTION_ENTER_DISTANCE = 200  # Qt logical pixels, independent of DPI
    ATTENTION_EXIT_DISTANCE = 240   # Hysteresis avoids toggling at the boundary

    clicked = Signal()
    moved = Signal(QPoint)
    menu_requested = Signal(QMenu)

    def __init__(self, position=None):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Luna — 桌宠工具箱")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.animation = Animation()
        if self.animation.is_luna:
            self.setFixedSize(216, 324)
        else:
            self.setFixedSize(120, 108)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.menu_timer = QTimer(self)
        self.menu_timer.setSingleShot(True)
        self.menu_timer.setInterval(450)
        self.menu_timer.timeout.connect(self._open_panel)
        self._last_tick = None
        self._press = None
        self._dragging = False
        self._input_passthrough = False
        self._work_sources = set()
        self._pending_feedback = None
        self._near = False
        self._mouse_local = QPoint()
        self._idle_remaining = random.uniform(12, 30)
        self._last_variant = None
        self._click_times = deque()
        self._click_region = None
        self._angry_until = 0.0
        self._pending_panel = False
        available = QApplication.primaryScreen().availableGeometry()
        self.move(available.x() + available.width() - self.width() - 24,
                  available.y() + available.height() - self.height() - 20)
        if position:
            self.move(QPoint(*position))
        self._keep_on_screen()

    def _keep_on_screen(self):
        screens = QApplication.screens()
        area = next((s.availableGeometry() for s in screens
                     if s.availableGeometry().intersects(self.geometry())),
                    QApplication.primaryScreen().availableGeometry())
        self.move(max(area.left(), min(self.x(), area.x() + area.width() - self.width())),
                  max(area.top(), min(self.y(), area.y() + area.height() - self.height())))

    def set_input_passthrough(self, enabled):
        enabled = bool(enabled)
        if self._input_passthrough == enabled:
            return
        self._input_passthrough = enabled
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        if visible:
            self.show()

    def set_working(self, reason, enabled):
        if enabled:
            self._work_sources.add(reason)
        else:
            self._work_sources.discard(reason)
        state = self.animation.state
        if state in ("success", "error", "drag", "land"):
            return
        if self._work_sources:
            self._play("working_loop", "working", restart=False)
        elif state == "working":
            self._play("working_exit", "working_exit")

    def set_state(self, state):
        # Keep the existing controller API; distinct long-running operations
        # use set_working(reason, bool), so one cannot clear another's state.
        if state == "working":
            self.set_working("legacy", True)
        elif state == "idle":
            self._work_sources.discard("legacy")
            if self.animation.state not in ("success", "error", "drag", "land"):
                if self.animation.state == "working" and not self._work_sources:
                    self._play("working_exit", "working_exit")
                else:
                    self._resume()
        elif state in ("success", "error"):
            if self.animation.state == state:
                return
            if self.animation.state in ("drag", "land"):
                if self._pending_feedback != "error":
                    self._pending_feedback = state
            elif state == "success" and self.animation.state == "error":
                self._pending_feedback = state
            else:
                self._play("feedback_" + state, state)

    def _play(self, clip, state, restart=True):
        self.animation.play(clip, state, restart=restart)
        self.update()

    def _resume(self):
        self._idle_remaining = random.uniform(12, 30)
        if self._pending_feedback:
            state, self._pending_feedback = self._pending_feedback, None
            self._play("feedback_" + state, state)
        elif self._work_sources:
            self._play("working_loop", "working", restart=False)
        elif self._near and not self._input_passthrough:
            self._play("attention_loop", "attention", restart=False)
        else:
            self._play("idle_normal", "idle", restart=False)

    def _update_proximity(self):
        self._mouse_local = self.mapFromGlobal(QCursor.pos())
        # Distance from the visible body gives rounded corners to the range.
        # A separate exit radius prevents enter/exit chatter from hand jitter.
        body = QRectF(self.rect()).adjusted(self.width() * .10, self.height() * .04,
                                           -self.width() * .10, -self.height() * .04)
        dx = max(body.left() - self._mouse_local.x(), 0, self._mouse_local.x() - body.right())
        dy = max(body.top() - self._mouse_local.y(), 0, self._mouse_local.y() - body.bottom())
        radius = self.ATTENTION_EXIT_DISTANCE if self._near else self.ATTENTION_ENTER_DISTANCE
        self._near = math.hypot(dx, dy) <= radius
        if self._near:
            span = body.width() / 2 + self.ATTENTION_ENTER_DISTANCE
            self.animation.set_gaze((self._mouse_local.x() - body.center().x()) / span)
        if self._input_passthrough or self._work_sources or self._press is not None:
            return
        if self._near and self.animation.state in ("idle", "idle_variant", "attention", "attention_exit"):
            self._play("attention_loop", "attention", restart=False)
        elif not self._near and self.animation.state == "attention":
            self._resume()

    def _tick(self):
        now = time.monotonic()
        delta = min(.1, now - self._last_tick) if self._last_tick is not None else 1 / 30
        self._last_tick = now
        self._update_proximity()
        if self.animation.tick(delta):
            if self.animation.clip == "drag_start" and self._dragging:
                self._play("drag_hold", "drag")
            else:
                self._resume()
        if self.animation.state == "idle" and not self._near and self._press is None:
            self._idle_remaining -= delta
            if self._idle_remaining <= 0:
                choices = [name for name in ("idle_look_around", "idle_yawn") if name != self._last_variant]
                self._last_variant = random.choice(choices)
                self._play(self._last_variant, "idle_variant")
        self.update()

    def showEvent(self, event):
        self._last_tick = None
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        self.menu_timer.stop()
        self._pending_panel = False
        self._last_tick = None
        self._press = None
        self._dragging = False
        self._near = False
        if self.animation.state == "drag":
            self._resume()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        self.animation.draw(painter, QRectF(self.rect()))

    def _hit(self, position):
        return self.animation.contains(position, QRectF(self.rect()))

    def mousePressEvent(self, event):
        if self._input_passthrough:
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._hit(event.position()):
            self.menu_timer.stop()
            self._press = event.globalPosition().toPoint()
            self._origin = self.pos()
            self._dragging = False
            event.accept()
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        # Qt sends a double-click event instead of the second press; count its
        # release too, so rapid clicks can reach the original three/six levels.
        self.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is not None:
            delta = event.globalPosition().toPoint() - self._press
            if not self._dragging and delta.manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
                self._pending_panel = False
                self._click_times.clear()
                self._play("drag_start", "drag")
            if self._dragging:
                self.move(self._origin + delta)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        dragged = self._dragging
        self._press = None
        self._dragging = False
        if dragged:
            self._keep_on_screen()
            self._play("land", "land")
            self.moved.emit(self.pos())
        elif self._hit(event.position()):
            self._notify_click(event.position())

    def _notify_click(self, position):
        now = time.monotonic()
        y = position.y() * 2304 / self.height()
        region = "head" if y < 900 else "chest" if y < 1440 else "legs"
        if region != self._click_region:
            self._click_times.clear()
            self._click_region = region
        while self._click_times and now - self._click_times[0] > 2:
            self._click_times.popleft()
        self._click_times.append(now)
        recent = sum(now - stamp <= 1 for stamp in self._click_times)
        # Wait briefly for a click sequence. A burst animates the pet without
        # opening a popup that would intercept all subsequent mouse clicks.
        self._pending_panel = recent < 3 and len(self._click_times) < 6
        if self._pending_panel:
            self.menu_timer.start()
        else:
            self.menu_timer.stop()
        if self.animation.state in ("working", "working_exit", "success", "error", "drag", "land"):
            return
        if now < self._angry_until:
            return
        if len(self._click_times) >= 6:
            clip, rank = "click_angry_" + region, 3
            self._angry_until = now + 2
        elif recent >= 3:
            clip, rank = "click_annoyed", 2
        else:
            clip, rank = "click_question", 1
        current_rank = (3 if self.animation.clip.startswith("click_angry_")
                        else 2 if self.animation.clip == "click_annoyed" else 1)
        if self.animation.state != "click" or rank > current_rank:
            self._play(clip, "click")

    def _open_panel(self):
        if self._pending_panel and self.isVisible() and not self._input_passthrough and not self._dragging:
            self._pending_panel = False
            self.clicked.emit()

    def contextMenuEvent(self, event):
        self.menu_timer.stop()
        self._pending_panel = False
        if self._input_passthrough:
            return
        menu = QMenu(self)
        self.menu_requested.emit(menu)
        menu.exec(event.globalPos())

    def closeEvent(self, event):
        self.timer.stop()
        self.menu_timer.stop()
        self.animation.clear()
        super().closeEvent(event)
