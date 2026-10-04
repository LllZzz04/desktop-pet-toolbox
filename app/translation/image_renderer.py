"""Render translated text into a new image, preserving the original pixels."""
import math
from dataclasses import dataclass
from statistics import median

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QTextLayout, QTextOption

from app.ocr.engine import check_cancelled
from app.ocr.layout import join_texts, line_height


@dataclass(frozen=True)
class RenderResult:
    image: QImage
    shortened: int


def background_color(image, points):
    left, right = min(p[0] for p in points), max(p[0] for p in points)
    top, bottom = min(p[1] for p in points), max(p[1] for p in points)
    middle_x, middle_y = (left + right) / 2, (top + bottom) / 2
    samples = [(left - 3, top - 3), (middle_x, top - 3), (right + 3, top - 3),
               (left - 3, middle_y), (right + 3, middle_y),
               (left - 3, bottom + 3), (middle_x, bottom + 3), (right + 3, bottom + 3)]
    colors = [image.pixelColor(min(image.width() - 1, max(0, round(x))),
                              min(image.height() - 1, max(0, round(y)))) for x, y in samples]
    return QColor(*(int(median(getattr(color, channel)() for color in colors))
                    for channel in ("red", "green", "blue")))


def layout_text(text, font, width):
    layout = QTextLayout(text, font)
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    layout.setTextOption(option)
    height, overflow = 0, False
    layout.beginLayout()
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(max(1, width))
        overflow = overflow or line.naturalTextWidth() > max(1, width) + .1
        line.setPosition(QPointF(0, height))
        height += line.height()
    layout.endLayout()
    return layout, height, overflow


def fit_text(text, base_font, width, height, maximum_size=None):
    minimum, maximum = 6, max(6, min(96, round(height), maximum_size or 96))
    selected, selected_height = None, 0
    while minimum <= maximum:
        size = (minimum + maximum) // 2
        font = QFont(base_font)
        font.setPixelSize(size)
        layout, measured, overflow = layout_text(text, font, width)
        if measured <= height and not overflow:
            selected, selected_height = layout, measured
            minimum = size + 1
        else:
            maximum = size - 1
    if selected is not None:
        return selected, selected_height, False
    font = QFont(base_font)
    font.setPixelSize(6)
    shortened = QFontMetricsF(font).elidedText(text.replace("\n", " "), Qt.TextElideMode.ElideRight, max(1, width))
    layout, measured, _ = layout_text(shortened, font, width)
    return layout, measured, True


def render_translations(image, blocks, translations, base_font, cancelled):
    check_cancelled(cancelled)
    output = image.convertToFormat(QImage.Format.Format_ARGB32).copy()
    output.setDevicePixelRatio(1)
    if output.isNull():
        raise MemoryError("无法分配译文图片，请缩小图片区域")
    painter = QPainter(output)
    shortened = 0
    try:
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        for block in blocks:
            check_cancelled(cancelled)
            text = translations.get(block.id)
            lines = getattr(block, "lines", (block,))
            if not text or text == join_texts(line.text for line in lines):
                continue
            p0, p1, p2, p3 = block.points
            width = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            height = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
            if width < 4 or height < 4:
                shortened += 1
                continue
            # Clear original line polygons individually; preserve paragraph
            # margins and gaps rather than painting a large solid rectangle.
            for line in lines:
                check_cancelled(cancelled)
                q0, q1, q2, q3 = line.points
                painter.save()
                try:
                    painter.translate(q0[0], q0[1])
                    painter.rotate(math.degrees(math.atan2(q1[1] - q0[1], q1[0] - q0[0])))
                    painter.fillRect(QRectF(-1, -1, math.dist(q0, q1) + 2, math.dist(q0, q3) + 2),
                                     background_color(image, line.points))
                finally:
                    painter.restore()
            background = background_color(image, block.points)
            luminance = .2126 * background.red() + .7152 * background.green() + .0722 * background.blue()
            painter.save()
            try:
                painter.translate(p0[0], p0[1])
                painter.rotate(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])))
                painter.setPen(QColor("#111111") if luminance > 140 else QColor("#ffffff"))
                target = QRectF(1, 0, max(1, width - 2), height)
                painter.setClipRect(target)
                maximum_size = max(6, round(median(line_height(line) for line in lines)))
                layout, text_height, clipped = fit_text(text, base_font, target.width(), target.height(), maximum_size)
                shortened += int(clipped)
                # Prose stays aligned at the paragraph's top, independent of
                # how many lines the target language needs.
                y = max(0, (height - text_height) / 2) if len(lines) == 1 else 0
                layout.draw(painter, QPointF(target.x(), y))
            finally:
                painter.restore()
    finally:
        painter.end()
    return RenderResult(output, shortened)
