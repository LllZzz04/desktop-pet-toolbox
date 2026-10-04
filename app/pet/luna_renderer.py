"""Lazy, bounded playback of transparent frames built from Luna_Final."""
import json
import logging
import math
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter


ASSET_DIRECTORY = Path(__file__).resolve().parents[2] / "assets" / "luna"
REQUIRED_CLIPS = {
    "idle_normal", "idle_look_around", "idle_yawn",
    "attention_enter", "attention_loop", "working_enter",
    "click_question", "click_annoyed", "click_angry_head",
    "click_angry_chest", "click_angry_legs", "working_loop", "working_exit",
    "feedback_success", "feedback_error", "working_success", "working_error",
    "drag_start", "drag_hold", "land",
}


class LunaRenderer:
    def __init__(self, directory=ASSET_DIRECTORY):
        self.directory = Path(directory).resolve()
        manifest = json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))
        self.clips = manifest["clips"]
        if manifest.get("version") != 2 or not REQUIRED_CLIPS.issubset(self.clips):
            raise ValueError("Luna 动画目录不完整，请重新导出素材")
        self.directional = manifest["directional"]
        for family in ("attention_enter", "attention_loop"):
            names = self.directional.get(family, [])
            if len(names) != 9 or names[4] != family or not set(names).issubset(self.clips):
                raise ValueError("Luna 鼠标朝向素材不完整")
            timing = self.clips[family]
            if any(any(self.clips[name][key] != timing[key] for key in ("fps", "duration", "loop"))
                   or len(self.clips[name]["frames"]) != len(timing["frames"]) for name in names):
                raise ValueError("Luna 鼠标朝向的时间轴不一致")
        self.paths = {}
        for name, clip in self.clips.items():
            if not 1 <= clip["fps"] <= 60 or not clip["frames"] or not 0 < clip["duration"] <= 60:
                raise ValueError(f"Luna 动画参数无效：{name}")
            paths = []
            for filename in clip["frames"]:
                path = (self.directory / filename).resolve()
                path.relative_to(self.directory)
                paths.append(path)
            if not paths[0].is_file():
                raise FileNotFoundError(paths[0])
            self.paths[name] = tuple(paths)
        # About 7 MiB at 384 × 576 RGBA; do not decode entire clips up front.
        self.cache = OrderedDict()
        self.last_image = QImage()
        self.failed_paths = set()
        self._sample_key = None
        self._sample_image = QImage()

    def frame_image(self, clip, frame):
        path = self.paths[clip][frame % len(self.paths[clip])]
        if path in self.cache:
            self.cache.move_to_end(path)
            return self.cache[path]
        if path in self.failed_paths:
            return self.last_image
        image = QImage(str(path))
        if image.isNull():
            logging.error("Cannot read Luna animation frame: %s", path)
            self.failed_paths.add(path)
            return self.last_image
        image.setDevicePixelRatio(1)
        image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        self.cache[path] = image
        self.last_image = image
        while len(self.cache) > 8:
            self.cache.popitem(last=False)
        return image

    @staticmethod
    def blend(first, second, amount):
        """Interpolate premultiplied color AND alpha with complementary weights."""
        if amount <= 0 or second.isNull():
            return first
        if amount >= 1 or first.isNull():
            return second
        # Frame images and prior blend results are already premultiplied.
        # Copy before painting so the cached source stays unchanged.
        result = first.copy()
        painter = QPainter(result)
        # Source with constant opacity performs (1 - t) * first + t * second
        # on all four channels, including transparent pixels. Plus saturates
        # the sum BEFORE applying painter opacity, causing brightness/alpha
        # shifts; SourceOver would apply the source alpha a second time.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.setOpacity(amount)
        painter.drawImage(0, 0, second)
        painter.end()
        return result

    def image(self, clip, frame, gaze=0.0):
        key = clip, frame, round(gaze, 3)
        if key == self._sample_key:
            return self._sample_image
        names = self.directional.get(clip)
        if names:
            position = (max(-1.0, min(1.0, gaze)) + 1) * (len(names) - 1) / 2
            left = math.floor(position)
            right = min(left + 1, len(names) - 1)
            first = self.frame_image(names[left], frame)
            image = (first if right == left or position == left else
                     self.blend(first, self.frame_image(names[right], frame), position - left))
        else:
            image = self.frame_image(clip, frame)
        # The short suspended loop includes breathing with a different period.
        # Ease its last four frame intervals back to its first frame.
        if clip == "drag_hold":
            start = len(self.paths[clip]) - 5
            if frame >= start:
                progress = (frame - start) / 4
                image = self.blend(image, self.frame_image(clip, 0), progress * progress * (3 - 2 * progress))
        self._sample_key, self._sample_image = key, image
        return image

    @staticmethod
    def draw(painter, bounds, image):
        if not image.isNull():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(QRectF(bounds), image)

    @staticmethod
    def contains(point, bounds, image):
        if not bounds.contains(point):
            return False
        if image.isNull():
            return False
        x = min(image.width() - 1, max(0, int((point.x() - bounds.x()) * image.width() / bounds.width())))
        y = min(image.height() - 1, max(0, int((point.y() - bounds.y()) * image.height() / bounds.height())))
        return image.pixelColor(x, y).alpha() >= 24

    def clear(self):
        self.cache.clear()
        self.last_image = QImage()
        self.failed_paths.clear()
        self._sample_key = None
        self._sample_image = QImage()
