"""Pixel-coordinate annotations with an inexpensive cached preview."""
import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen

from app.ui.theme import THEME


@dataclass(frozen=True)
class Annotation:
    kind: str
    start: QPointF
    end: QPointF
    color: str = THEME.accent
    width: int = 3
    text: str = ""
    font_size: int = 24


def draw_annotation(painter, image, item, draft=False):
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(item.color), item.width, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    rect = QRectF(item.start, item.end).normalized().intersected(QRectF(image.rect()))
    if item.kind == "arrow":
        painter.drawLine(item.start, item.end)
        angle = math.atan2(item.end.y() - item.start.y(), item.end.x() - item.start.x())
        length = max(12, item.width * 4)
        for offset in (-math.pi / 6, math.pi / 6):
            painter.drawLine(item.end, item.end - QPointF(
                length * math.cos(angle + offset), length * math.sin(angle + offset)))
    elif item.kind == "rect" or (item.kind == "mosaic" and draft):
        painter.drawRect(rect)
    elif item.kind == "mosaic" and not rect.isEmpty():
        region = rect.toAlignedRect().intersected(image.rect())
        small = image.copy(region).scaled(max(1, region.width() // 14),
                                         max(1, region.height() // 14),
                                         Qt.AspectRatioMode.IgnoreAspectRatio,
                                         Qt.TransformationMode.FastTransformation)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(QRectF(region), small)
    elif item.kind == "text":
        font = QFont()
        font.setFamilies(list(THEME.font_families))
        font.setPixelSize(item.font_size)
        painter.setFont(font)
        space = QRectF(item.start.x(), item.start.y(),
                       max(1, image.width() - item.start.x()),
                       max(1, image.height() - item.start.y()))
        height = QFontMetricsF(font).boundingRect(
            space, Qt.TextFlag.TextWordWrap, item.text).height()
        painter.drawText(QRectF(space.x(), space.y(), space.width(), min(space.height(), height + 4)),
                         Qt.TextFlag.TextWordWrap, item.text)
    painter.restore()


def render_annotations(image, items):
    result = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    if result.isNull():
        raise ValueError("无法分配标注图片内存，请使用较小截图")
    result.setDevicePixelRatio(1)
    painter = QPainter(result)
    if not painter.isActive():
        raise ValueError("无法绘制标注图片")
    try:
        for item in items:
            draw_annotation(painter, image, item)
    finally:
        painter.end()
    return result
