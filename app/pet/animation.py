"""Animation clock with transparent Luna frames and a missing-asset fallback."""
import logging
import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from .luna_renderer import LunaRenderer


class GeometricRenderer:
    colors = {"idle": "#7bb7c8", "working": "#d6ac68",
              "success": "#79bd96", "error": "#cf8191"}

    def draw(self, painter: QPainter, bounds: QRectF, state: str, frame: int):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bob = math.sin(frame / 9) * 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawEllipse(QRectF(22, 88, 76, 10))
        painter.setBrush(QColor(self.colors.get(state, self.colors["idle"])))
        painter.drawEllipse(QRectF(22, 22 + bob, 76, 66))
        painter.drawEllipse(QRectF(24, 14 + bob, 25, 28))
        painter.drawEllipse(QRectF(71, 14 + bob, 25, 28))
        painter.setBrush(QColor("#263e4b"))
        if frame % 64 < 3:
            painter.setPen(QPen(QColor("#263e4b"), 3))
            painter.drawLine(44, int(50 + bob), 52, int(50 + bob))
            painter.drawLine(69, int(50 + bob), 77, int(50 + bob))
        else:
            painter.drawEllipse(QRectF(45, 45 + bob, 6, 9))
            painter.drawEllipse(QRectF(70, 45 + bob, 6, 9))
        painter.setPen(QPen(QColor("#263e4b"), 2))
        painter.drawArc(QRectF(54, 53 + bob, 13, 10), 180 * 16, 180 * 16)
        if state == "working":
            painter.drawArc(QRectF(91, 7, 16, 16), frame * 20 * 16, 230 * 16)


class Animation:
    def __init__(self, renderer=None):
        if renderer is None:
            try:
                renderer = LunaRenderer()
            except (OSError, ValueError, KeyError, TypeError) as error:
                logging.warning("Luna assets unavailable, using placeholder: %s", error)
                renderer = GeometricRenderer()
        self.renderer = renderer
        self.is_luna = isinstance(renderer, LunaRenderer)
        self.state = "idle"
        self.clip = "idle_normal"
        self.frame = 0
        self.elapsed = 0.0
        self.gaze = 0.0
        self._gaze_target = 0.0
        self._reverse = False
        self._blend_source = None
        self._blend_elapsed = 0.0
        self._blend_duration = .12

    def set_gaze(self, value):
        self._gaze_target = max(-1.0, min(1.0, value))

    def play(self, clip, state, restart=True):
        if clip == self.clip and not restart:
            return
        if self.is_luna:
            if clip == "attention_loop":
                if self.clip == "attention_enter":
                    # Reverse from the displayed pose when the cursor returns
                    # during the exit. Do not restart the greeting.
                    self._reverse, self.state = False, "attention"
                    return
                self._switch("attention_enter", "attention")
                return
            if clip == "idle_normal" and self.state == "attention":
                same_clip = self.clip == "attention_enter"
                if same_clip:
                    self._reverse, self.state = True, "attention_exit"
                    return
                progress = self._timing("attention_enter")[1]
                self._switch("attention_enter", "attention_exit", elapsed=progress,
                             reverse=True)
                return
            if clip == "working_loop":
                if self.clip == "working_enter":
                    self._reverse, self.state = False, "working"
                else:
                    self._switch("working_enter", "working")
                return
            if clip == "working_exit" and self.clip == "working_enter":
                # A very quick cancellation must not jump to fully raised arms.
                self._reverse, self.state = True, "working_exit"
                return
            if clip.startswith("feedback_") and (self.clip == "working_loop" or
                    (self.clip == "working_exit" and self.elapsed < .06)):
                clip = "working_" + state
        # On normal completion, keep the breathing phase at the end of the
        # authored recovery instead of restarting the neutral pose at frame 0.
        phase = self._base_phase() if clip == "idle_normal" and not restart else 0.0
        self._switch(clip, state, elapsed=phase)

    def _base_phase(self):
        offset = self.renderer.clips[self.clip].get("phase_offset", 0.0) if self.is_luna else 0.0
        return (offset + self.elapsed) % 6.4

    def _switch(self, clip, state, *, elapsed=0.0, reverse=False, blend=True):
        # Snapshot the currently composed pose, including an interrupted blend;
        # this bounds memory and prevents chained input from flashing old poses.
        source = self._image() if self.is_luna and blend else None
        self.clip, self.state, self.elapsed = clip, state, elapsed
        self._reverse = reverse
        self._blend_source = source
        self._blend_elapsed = 0.0
        self._set_frame()

    def _timing(self, name=None):
        name = name or self.clip
        if self.is_luna:
            clip = self.renderer.clips[name]
            return clip["fps"], clip["duration"], clip["loop"]
        lengths = {"idle_normal": 6.4, "idle_look_around": 4.4, "idle_yawn": 3.8,
                   "click_question": .9, "click_annoyed": 1.3, "working_exit": .4,
                   "feedback_success": 1.3, "feedback_error": 1.4,
                   "drag_start": .28, "drag_hold": 2.4, "land": .85}
        loop = name in {"idle_normal", "working_loop", "drag_hold", "attention_loop"}
        return 30, lengths.get(name, 2.0), loop

    def _set_frame(self):
        fps, duration, loop = self._timing()
        count = len(self.renderer.clips[self.clip]["frames"]) if self.is_luna else max(1, round(duration * fps))
        frame = max(0, int(self.elapsed * fps + 1e-7))
        self.frame = frame % count if loop else (count - 1 if self.elapsed >= duration else min(count - 1, frame))

    def tick(self, delta=1 / 30):
        # Follow the cursor continuously instead of changing direction at a
        # threshold. Both timing and smoothing are independent of timer jitter.
        self.gaze += (self._gaze_target - self.gaze) * (1 - math.exp(-delta / .14))
        if abs(self.gaze - self._gaze_target) < .001:
            self.gaze = self._gaze_target
        self._blend_elapsed += delta
        if self._blend_elapsed >= self._blend_duration:
            self._blend_source = None
        self.elapsed = max(0.0, self.elapsed + (-delta if self._reverse else delta))
        self._set_frame()
        _, duration, loop = self._timing()
        if self.is_luna and self.clip in ("attention_enter", "working_enter"):
            if self._reverse and self.elapsed <= 0:
                was_working = self.clip == "working_enter"
                self._switch("idle_normal", "idle", blend=False)
                return was_working
            if not self._reverse and self.elapsed >= duration:
                target = "attention_loop" if self.clip == "attention_enter" else "working_loop"
                self._switch(target, self.state, elapsed=self.elapsed, blend=False)
            return False
        return not loop and self.elapsed >= duration

    def _image(self):
        image = self.renderer.image(self.clip, self.frame, self.gaze)
        if self._blend_source is not None:
            progress = min(1.0, self._blend_elapsed / self._blend_duration)
            image = self.renderer.blend(self._blend_source, image, progress * progress * (3 - 2 * progress))
        return image

    def draw(self, painter, bounds):
        if self.is_luna:
            self.renderer.draw(painter, bounds, self._image())
        else:
            self.renderer.draw(painter, bounds, self.state, int(self.elapsed * 12.5))

    def contains(self, point, bounds):
        return (self.renderer.contains(point, bounds, self._image())
                if self.is_luna else bounds.contains(point))

    def clear(self):
        self._blend_source = None
        if self.is_luna:
            self.renderer.clear()
