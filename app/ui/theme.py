"""Shared light theme. Only marked surfaces receive a background.

Pet, capture and pin windows paint their own pixels; a broad QWidget rule
would break those windows. Keep every visual token and QSS rule here.
"""
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette


@dataclass(frozen=True)
class Theme:
    background: str = "#F7F7F9"
    card: str = "#FFFFFF"
    text: str = "#25252A"
    secondary: str = "#77777F"
    muted: str = "#A0A0A8"
    accent: str = "#D85C68"
    accent_hover: str = "#C94D5A"
    accent_soft: str = "#FBECEF"
    divider: str = "#E8E8EC"
    control_hover: str = "#F0F0F4"
    control_pressed: str = "#E8E8EE"
    focus_border: str = "#C8C8D2"
    scroll_handle: str = "#D2D2DA"
    overlay: str = "#25252A"
    transparent: str = "#00000000"
    shadow: str = "#1225252A"
    font_families: tuple = ("Microsoft YaHei UI", "Segoe UI", "sans-serif")
    body_size: int = 13
    caption_size: int = 12
    title_size: int = 18
    section_size: int = 14
    spacing: int = 8
    page_padding: int = 16
    card_radius: int = 12
    button_radius: int = 8
    input_radius: int = 8
    control_height: int = 36
    compact_height: int = 32
    hover_duration: int = 120
    fade_duration: int = 150


THEME = Theme()


def set_role(widget, name, value):
    """Repolish a changed semantic role, including mode-dependent buttons."""
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
    return widget


def tool_window(widget, floating=False):
    widget.setProperty("uiRoot", True)
    if floating:
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        widget.setProperty("surface", "floating")
    return widget


def stylesheet():
    t = THEME
    icons = (Path(__file__).resolve().parents[2] / "assets" / "ui").as_posix()
    return f"""
    QDialog[uiRoot="true"], QWidget[surface="page"] {{
        background: {t.background}; color: {t.text};
    }}
    QWidget[surface="floating"] {{ background: transparent; border: none; }}
    QFrame[surface="shell"] {{
        background: {t.background}; border: 1px solid {t.divider};
        border-radius: {t.card_radius}px;
    }}
    QFrame[surface="card"] {{
        background: {t.card}; border: 1px solid {t.divider};
        border-radius: {t.card_radius}px;
    }}
    QFrame[surface="soft"] {{
        background: {t.accent_soft}; border: none;
        border-radius: {t.input_radius}px;
    }}
    QWidget[surface="preview"] {{
        background: {t.background}; border: none; border-radius: {t.input_radius}px;
    }}
    QLabel {{ background: transparent; color: {t.text}; border: none; }}
    QLabel[textRole="title"] {{ font-size: {t.title_size}px; font-weight: 600; }}
    QLabel[textRole="section"] {{ font-size: {t.section_size}px; font-weight: 600; }}
    QLabel[textRole="caption"], QLabel[textRole="status"] {{
        color: {t.secondary}; font-size: {t.caption_size}px;
    }}
    QLabel[textRole="muted"] {{ color: {t.muted}; font-size: {t.caption_size}px; }}
    QLabel[textRole="secondary"] {{ color: {t.secondary}; }}
    QLabel[textRole="badge"] {{
        background: {t.accent_soft}; color: {t.accent};
        border-radius: 6px; padding: 4px 8px; font-size: {t.caption_size}px;
    }}
    QLabel[textRole="status"] {{ padding: 4px 0px; }}
    QPushButton, QToolButton {{
        color: {t.text}; background: {t.card}; border: 1px solid {t.divider};
        border-radius: {t.button_radius}px; padding: 0px 12px;
        min-height: {t.control_height - 2}px;
    }}
    QPushButton:hover, QToolButton:hover {{ background: {t.control_hover}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {t.control_pressed}; }}
    QPushButton[buttonRole="primary"], QToolButton[buttonRole="primary"] {{
        background: {t.accent}; border-color: {t.accent}; color: {t.card};
        font-weight: 600;
    }}
    QPushButton[buttonRole="primary"]:hover, QToolButton[buttonRole="primary"]:hover {{
        background: {t.accent_hover}; border-color: {t.accent_hover};
    }}
    QPushButton[buttonRole="ghost"], QToolButton[buttonRole="ghost"] {{
        background: transparent; border-color: transparent; color: {t.secondary};
    }}
    QPushButton[buttonRole="ghost"]:hover, QToolButton[buttonRole="ghost"]:hover {{
        background: {t.control_hover}; color: {t.text};
    }}
    QToolButton[compact="true"], QPushButton[compact="true"] {{
        min-height: {t.compact_height - 2}px; padding: 0px 8px;
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background: {t.background}; color: {t.muted}; border-color: {t.divider};
    }}
    QLineEdit, QKeySequenceEdit, QSpinBox, QComboBox {{
        color: {t.text}; background: {t.card}; border: 1px solid {t.divider};
        border-radius: {t.input_radius}px; padding: 0px 10px;
        min-height: {t.control_height - 2}px;
        selection-background-color: {t.accent_soft}; selection-color: {t.text};
    }}
    QLineEdit:hover, QSpinBox:hover, QComboBox:hover, QKeySequenceEdit:hover {{
        border-color: {t.focus_border};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QKeySequenceEdit:focus {{
        border-color: {t.focus_border};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
        color: {t.muted}; background: {t.background};
    }}
    QKeySequenceEdit QLineEdit, QComboBox QLineEdit {{
        border: none; background: transparent; padding: 0px; min-height: 0px;
    }}
    QComboBox {{ padding-right: 30px; }}
    QComboBox::drop-down {{ width: 28px; border: none; }}
    QComboBox::down-arrow {{ image: url("{icons}/chevron-down.svg"); width: 12px; height: 12px; }}
    QComboBox QAbstractItemView {{
        background: {t.card}; border: 1px solid {t.divider}; padding: 4px;
        selection-background-color: {t.accent_soft}; selection-color: {t.text};
    }}
    QSpinBox {{ padding-right: 24px; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 22px; border: none; }}
    QSpinBox::up-arrow {{ image: url("{icons}/chevron-up.svg"); width: 10px; height: 10px; }}
    QSpinBox::down-arrow {{ image: url("{icons}/chevron-down.svg"); width: 10px; height: 10px; }}
    QTextEdit, QPlainTextEdit {{
        background: {t.card}; color: {t.text}; border: 1px solid {t.divider};
        border-radius: {t.input_radius}px; padding: 8px;
        selection-background-color: {t.accent_soft}; selection-color: {t.text};
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {t.focus_border}; }}
    QTextEdit[flatEditor="true"], QPlainTextEdit[flatEditor="true"] {{
        border: none; background: transparent; padding: 0px;
    }}
    QCheckBox {{ spacing: 8px; color: {t.text}; background: transparent; }}
    QCheckBox:disabled {{ color: {t.muted}; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px; background: {t.card};
        border: 1px solid {t.focus_border}; border-radius: 5px;
    }}
    QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
    QCheckBox::indicator:checked {{
        background: {t.accent}; border-color: {t.accent};
        image: url("{icons}/check.svg");
    }}
    QCheckBox::indicator:disabled {{ background: {t.background}; border-color: {t.divider}; }}
    QListWidget {{
        background: transparent; border: none; outline: none;
        selection-background-color: {t.accent_soft}; selection-color: {t.text};
    }}
    QListWidget::item {{
        background: {t.card}; border: 1px solid {t.divider};
        border-radius: 10px; padding: 8px; color: {t.text};
    }}
    QListWidget::item:hover {{ background: {t.background}; border-color: {t.focus_border}; }}
    QListWidget::item:selected {{ background: {t.accent_soft}; border-color: {t.focus_border}; }}
    QListWidget[listRole="notes"]::item {{
        border: none; background: transparent; padding: 0px;
    }}
    QTabWidget::pane {{ border: none; background: transparent; }}
    QTabBar::tab {{
        background: transparent; color: {t.secondary}; border: none;
        border-bottom: 2px solid transparent; padding: 10px 16px; margin-right: 8px;
    }}
    QTabBar::tab:selected {{ color: {t.text}; border-bottom-color: {t.accent}; font-weight: 600; }}
    QTabBar::tab:hover {{ background: {t.control_hover}; }}
    QSplitter::handle {{ background: transparent; width: 8px; }}
    QSplitter::handle:hover {{ background: {t.divider}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ width: 8px; background: transparent; margin: 2px 0px; }}
    QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 0px 2px; }}
    QScrollBar::handle {{ background: {t.scroll_handle}; border-radius: 4px; }}
    QScrollBar::handle:vertical {{ min-height: 24px; }}
    QScrollBar::handle:horizontal {{ min-width: 24px; }}
    QScrollBar::handle:hover {{ background: {t.muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QMenu {{
        background: {t.card}; color: {t.text}; border: 1px solid {t.divider};
        border-radius: 10px; padding: 8px;
    }}
    QMenu::item {{ padding: 8px 24px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {t.accent_soft}; color: {t.text}; }}
    QMenu::item:disabled {{ color: {t.muted}; }}
    QMenu::separator {{ background: {t.divider}; height: 1px; margin: 4px 8px; }}
    QToolTip {{
        background: {t.card}; color: {t.text}; border: 1px solid {t.divider};
        border-radius: 6px; padding: 6px 8px; font-size: {t.caption_size}px;
    }}
    QFrame[separator="true"] {{ background: {t.divider}; border: none; max-height: 1px; }}
    QFrame[verticalSeparator="true"] {{
        background: {t.divider}; border: none; min-width: 1px; max-width: 1px;
        min-height: 24px;
    }}
    QMessageBox {{ background: {t.background}; }}
    """


def install_theme(app):
    # Fusion supplies consistent control metrics on Windows 10 and 11.
    app.setStyle("Fusion")
    font = QFont()
    font.setFamilies(list(THEME.font_families))
    font.setPixelSize(THEME.body_size)
    app.setFont(font)
    palette = QPalette()
    for role, token in (
        (QPalette.ColorRole.Window, THEME.background),
        (QPalette.ColorRole.WindowText, THEME.text),
        (QPalette.ColorRole.Base, THEME.card),
        (QPalette.ColorRole.AlternateBase, THEME.background),
        (QPalette.ColorRole.Text, THEME.text),
        (QPalette.ColorRole.Button, THEME.card),
        (QPalette.ColorRole.ButtonText, THEME.text),
        (QPalette.ColorRole.Highlight, THEME.accent_soft),
        (QPalette.ColorRole.HighlightedText, THEME.text),
        (QPalette.ColorRole.PlaceholderText, THEME.muted),
        (QPalette.ColorRole.ToolTipBase, THEME.card),
        (QPalette.ColorRole.ToolTipText, THEME.text),
        (QPalette.ColorRole.Link, THEME.accent),
    ):
        palette.setColor(role, QColor(token))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(THEME.muted))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet())
