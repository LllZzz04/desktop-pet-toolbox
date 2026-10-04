"""Small presentation-only building blocks; callbacks stay in each window."""
from PySide6.QtCore import QEvent, QRect, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QPushButton, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

from .icons import icon
from .theme import THEME, set_role, tool_window


def column(parent=None, padding=0, spacing=None):
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(THEME.spacing if spacing is None else spacing)
    return layout


def row(parent=None, padding=0, spacing=None):
    layout = QHBoxLayout(parent)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(THEME.spacing if spacing is None else spacing)
    return layout


def page_layout(window):
    tool_window(window)
    return column(window, THEME.page_padding, 16)


def label(text="", role="caption", wrap=False):
    widget = QLabel(text)
    widget.setProperty("textRole", role)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    return widget


def card(padding=None, surface="card"):
    frame = QFrame()
    frame.setProperty("surface", surface)
    frame.setFrameShape(QFrame.Shape.NoFrame)
    column(frame, THEME.page_padding if padding is None else padding, 12)
    return frame


def page_header(title, subtitle="", trailing=None):
    frame = QWidget()
    layout = row(frame)
    dot = label("●", "badge")
    dot.setFixedSize(28, 28)
    dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
    text = column(spacing=4)
    text.addWidget(title if isinstance(title, QLabel) else label(title, "title"))
    if subtitle:
        text.addWidget(label(subtitle, "caption", True))
    layout.addLayout(text, 1)
    if trailing is not None:
        layout.addWidget(trailing, 0, Qt.AlignmentFlag.AlignTop)
    return frame


def empty_state(title, description, kind="history"):
    frame = QWidget()
    layout = column(frame, 24, 8)
    glyph = QLabel()
    glyph.setPixmap(icon(kind, THEME.accent).pixmap(QSize(32, 32)))
    glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addStretch()
    layout.addWidget(glyph)
    for text, role in ((title, "section"), (description, "caption")):
        text_label = label(text, role, True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)
    layout.addStretch()
    return frame


def soft_shadow(widget):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(12)
    effect.setOffset(0, 2)
    effect.setColor(QColor(THEME.shadow))
    widget.setGraphicsEffect(effect)


def separator(vertical=False):
    frame = QFrame()
    frame.setProperty("verticalSeparator" if vertical else "separator", True)
    return frame


def _mix(first, second, amount):
    a, b = QColor(first), QColor(second)
    return QColor(*(round(x + (y - x) * amount) for x, y in (
        (a.red(), b.red()), (a.green(), b.green()),
        (a.blue(), b.blue()), (a.alpha(), b.alpha()))))


class _ButtonVisual:
    """Animate paint only. Native focus, click, keyboard and signals remain Qt's."""

    def _init_visual(self, variant, kind, compact):
        self._hover = 0.0
        self._icon_kind = kind
        self._motion = QVariantAnimation(self)
        self._motion.setDuration(THEME.hover_duration)
        self._motion.valueChanged.connect(self._hover_changed)
        self.setProperty("buttonRole", variant)
        self.setProperty("compact", compact)
        self.setMinimumHeight(THEME.compact_height if compact else THEME.control_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        if kind:
            self.setIcon(icon(kind))
            self.setIconSize(QSize(18, 18))

    def set_variant(self, variant):
        set_role(self, "buttonRole", variant)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(min(80, hint.width()), hint.height())

    def _hover_changed(self, value):
        self._hover = float(value)
        self.update()

    def event(self, event):
        if hasattr(self, "_motion"):
            if event.type() in (QEvent.Type.Enter, QEvent.Type.Leave):
                self._motion.stop()
                self._motion.setStartValue(self._hover)
                self._motion.setEndValue(1.0 if event.type() == QEvent.Type.Enter else 0.0)
                self._motion.start()
            elif event.type() in (QEvent.Type.Hide, QEvent.Type.EnabledChange):
                self._motion.stop()
                self._hover = 0.0
        return super().event(event)

    def paintEvent(self, event):
        t = THEME
        variant = self.property("buttonRole")
        if not self.isEnabled():
            background, border, foreground = (
                (t.transparent, t.transparent, t.muted) if variant == "ghost" else
                (t.background, t.divider, t.muted))
        elif variant == "primary":
            background = _mix(t.accent, t.accent_hover, 1.0 if self.isDown() else self._hover)
            border, foreground = background, t.card
        elif variant == "ghost":
            background = QColor(t.control_hover)
            background.setAlpha(round(255 * self._hover))
            border, foreground = t.transparent, t.secondary
            if self.isDown():
                background = t.control_pressed
        else:
            background = _mix(t.card, t.control_hover, self._hover)
            border, foreground = t.divider, t.text
            if self.isDown():
                background = t.control_pressed
        if self.hasFocus() and self.isEnabled():
            border = t.focus_border
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5),
                                t.button_radius, t.button_radius)
        painter.setFont(self.font())
        painter.setPen(QColor(foreground))
        icon_only = isinstance(self, QToolButton) and self.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
        text = "" if icon_only else self.text()
        icon_width = self.iconSize().width() if self._icon_kind else 0
        gap = 8 if icon_width and text else 0
        available = max(0, self.width() - 16 - icon_width - gap)
        text = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, available)
        text_width = painter.fontMetrics().horizontalAdvance(text)
        left = (self.width() - icon_width - gap - text_width) // 2
        if self._icon_kind:
            icon(self._icon_kind, QColor(foreground).name()).paint(
                painter, QRect(left, (self.height() - icon_width) // 2, icon_width, icon_width),
                Qt.AlignmentFlag.AlignCenter)
        if text:
            painter.drawText(QRect(left + icon_width + gap, 0, text_width, self.height()),
                             Qt.AlignmentFlag.AlignCenter, text)


class ActionButton(_ButtonVisual, QPushButton):
    def __init__(self, text, variant="secondary", kind=None, compact=False, parent=None):
        super().__init__(text, parent)
        self._init_visual(variant, kind, compact)


class ToolButton(_ButtonVisual, QToolButton):
    def __init__(self, text, variant="ghost", kind=None, icon_only=False, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setAccessibleName(text)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly if icon_only else
                                Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._init_visual(variant, kind, True)
        if icon_only:
            self.setFixedSize(THEME.control_height, THEME.control_height)
