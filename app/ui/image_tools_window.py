from dataclasses import replace

from PySide6.QtCore import QRectF, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QPlainTextEdit, QPushButton, QSplitter, QWidget)

from app.core.images import copy_image, save_image
from app.ocr.layout import can_merge_regions, join_texts, make_region
from app.translation.settings import LANGUAGES
from .components import ActionButton, card, label, page_header, page_layout, row
from .icons import icon
from .theme import THEME
from .selected_text_edit import SelectedTextEdit


class ImageView(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.setMinimumSize(260, 180)

    def set_image(self, image):
        self.image = QImage(image)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(THEME.background))
        painter.drawRoundedRect(QRectF(self.rect()), THEME.input_radius, THEME.input_radius)
        if not self.image.isNull():
            scale = min(self.width() / self.image.width(), self.height() / self.image.height())
            width, height = self.image.width() * scale, self.image.height() * scale
            target = QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(target, self.image)
        else:
            center = self.rect().center()
            icon("history", THEME.muted).paint(painter, center.x() - 20, center.y() - 48, 40, 40)
            painter.setPen(QColor(THEME.secondary))
            painter.drawText(self.rect().adjusted(16, 0, -16, 0),
                             Qt.AlignmentFlag.AlignCenter, "打开图片，或从剪贴板读取")


class ImageToolsWindow(QDialog):
    extract_requested = Signal()
    translate_requested = Signal()
    cancel_requested = Signal()
    settings_requested = Signal()
    import_requested = Signal()
    clipboard_requested = Signal()
    pin_requested = Signal(object)
    closed = Signal()
    assistant_requested = Signal(str, str)

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(1080, 640)
        self.image, self.translated_image = QImage(), QImage()
        self.blocks, self.translations = (), {}
        self._geometry_valid = False
        self.translation_mode = False
        self._busy = False
        layout = page_layout(self)
        settings = ActionButton("设置", "ghost", "settings", compact=True)
        settings.clicked.connect(lambda checked=False: self.settings_requested.emit())
        self.heading = label("提取文字", "title")
        layout.addWidget(page_header(self.heading, "图片与文字并排浏览，可自由选择任意内容复制", settings))

        command_card = card(12)
        inputs = row()
        open_image = ActionButton("打开图片…", kind="history")
        open_image.clicked.connect(lambda checked=False: self.import_requested.emit())
        clipboard = ActionButton("剪贴板图片", kind="copy")
        clipboard.clicked.connect(lambda checked=False: self.clipboard_requested.emit())
        inputs.addWidget(open_image)
        inputs.addWidget(clipboard)
        inputs.addStretch()
        self.extract = ActionButton("提取文字", "primary", "ocr")
        self.extract.clicked.connect(lambda checked=False: self.extract_requested.emit())
        self.translate = ActionButton("翻译图片", kind="translate")
        self.translate.clicked.connect(lambda checked=False: self.translate_requested.emit())
        self.cancel = ActionButton("取消处理", "ghost")
        self.cancel.clicked.connect(lambda checked=False: self.cancel_requested.emit())
        for widget in (self.extract, self.translate, self.cancel):
            inputs.addWidget(widget)
        command_card.layout().addLayout(inputs)
        self.options = QWidget()
        options = row(self.options)
        self.language_label = label("译为", "caption")
        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        self.show_translation = QCheckBox("图片覆盖译文")
        self.show_translation.setEnabled(False)
        self.show_translation.toggled.connect(self.update_preview)
        options.addWidget(self.language_label)
        options.addWidget(self.language)
        options.addSpacing(8)
        options.addWidget(self.show_translation)
        options.addStretch()
        command_card.layout().addWidget(self.options)
        layout.addWidget(command_card)

        self.status = label("打开图片或读取剪贴板，提取的各段文字之间用空行分隔，可自由选中复制。",
                            "status", True)
        layout.addWidget(self.status)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(THEME.spacing)
        self.splitter.setChildrenCollapsible(False)
        self.preview = ImageView()
        picture_pane = card()
        picture_layout = picture_pane.layout()
        picture_layout.addWidget(label("图片", "section"))
        picture_layout.addWidget(self.preview, 1)
        picture_layout.addWidget(label("原始图片 / 覆盖译文预览", "muted"))
        self.splitter.addWidget(picture_pane)

        self.source_editor = SelectedTextEdit()
        self.source_editor.assistant_requested.connect(self.assistant_requested.emit)
        self.source_editor.setAccessibleName("提取原文")
        self.source_editor.setPlaceholderText("提取出的文字会显示在这里。\n可拖动选择任意文字，按 Ctrl+C 复制。")
        self.copy_source = ActionButton("复制全部", "ghost", compact=True)
        self.copy_source.setAccessibleName("复制全部原文")
        self.copy_source.clicked.connect(lambda: QApplication.clipboard().setText(self.source_text()))
        self.source_pane = self.text_pane("原文", self.source_editor, self.copy_source)
        paragraphs = row(spacing=4)
        self.merge = ActionButton("合并选中段落", "ghost", compact=True)
        self.merge.setToolTip("在原文中拖选同一栏的相邻段落后合并，再重新翻译")
        self.merge.clicked.connect(self.merge_selected)
        self.split_paragraph = ActionButton("按原行拆分", "ghost", compact=True)
        self.split_paragraph.setToolTip("选中段落或将光标放在段落中，还原未修改的 OCR 原行")
        self.split_paragraph.clicked.connect(self.split_selected)
        paragraphs.addWidget(self.merge)
        paragraphs.addWidget(self.split_paragraph)
        paragraphs.addStretch()
        self.source_pane.layout().addLayout(paragraphs)
        self.splitter.addWidget(self.source_pane)

        self.translation_editor = SelectedTextEdit()
        self.translation_editor.assistant_requested.connect(self.assistant_requested.emit)
        self.translation_editor.setAccessibleName("译文")
        self.translation_editor.setReadOnly(True)
        self.translation_editor.setPlaceholderText("翻译结果会显示在这里。\n可跨段选择任意文字，按 Ctrl+C 复制。")
        self.copy_translation = ActionButton("复制全部", "ghost", compact=True)
        self.copy_translation.setAccessibleName("复制全部译文")
        self.copy_translation.clicked.connect(lambda: QApplication.clipboard().setText(self.translated_text()))
        self.translation_pane = self.text_pane("译文", self.translation_editor, self.copy_translation)
        self.splitter.addWidget(self.translation_pane)
        for index in range(3):
            self.splitter.setStretchFactor(index, 1)
        layout.addWidget(self.splitter, 1)
        self.source_editor.textChanged.connect(self.source_changed)
        self.source_editor.selectionChanged.connect(self.update_structure_buttons)
        self.source_editor.cursorPositionChanged.connect(self.update_structure_buttons)

        buttons = row()
        self.copy_picture = ActionButton("复制图片", kind="copy")
        self.copy_picture.clicked.connect(lambda: copy_image(self.export_image()))
        self.pin = ActionButton("贴图", kind="pin")
        self.pin.clicked.connect(lambda: self.pin_requested.emit(self.export_image()))
        self.save = ActionButton("保存图片", kind="save")
        self.save.clicked.connect(lambda: save_image(self.export_image(), self))
        close = ActionButton("关闭", "ghost")
        close.clicked.connect(self.close)
        for button in (self.copy_picture, self.pin, self.save):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.set_mode(False)
        self.set_busy(False)

    @staticmethod
    def text_pane(title, editor, copy_button):
        pane = card()
        pane.setMinimumWidth(280)
        layout = pane.layout()
        header = row()
        header.addWidget(label(title, "section"))
        header.addStretch()
        header.addWidget(copy_button)
        layout.addLayout(header)
        editor.setProperty("flatEditor", True)
        editor.document().setDocumentMargin(4)
        layout.addWidget(editor, 1)
        return pane

    def set_mode(self, translate):
        changed = self.translation_mode != bool(translate)
        self.translation_mode = bool(translate)
        self.heading.setText("图片翻译" if translate else "提取文字")
        self.extract.set_variant("secondary" if translate else "primary")
        self.translate.set_variant("primary" if translate else "secondary")
        self.options.setVisible(bool(translate))
        self.setWindowTitle(("图片翻译" if translate else "提取文字") + " — 桌宠工具箱")
        self.translation_pane.setVisible(bool(translate))
        for widget in (self.language_label, self.language, self.show_translation):
            widget.setVisible(bool(translate))
        if not translate:
            self.show_translation.setChecked(False)
        if changed or not self.isVisible():
            self.splitter.setSizes([360, 360, 360] if translate else [520, 520, 0])

    def set_image(self, image, language):
        self.image = QImage(image)
        self.image.setDevicePixelRatio(1)
        index = self.language.findData(language)
        self.language.setCurrentIndex(max(0, index))
        self.clear_results()
        self.set_busy(False)

    def clear_results(self):
        self.blocks = ()
        self._geometry_valid = False
        blocker = QSignalBlocker(self.source_editor)
        self.source_editor.clear()
        blocker.unblock()
        self.clear_translation()
        self.set_busy(self._busy)

    def clear_translation(self):
        self.translations = {}
        self.translation_editor.clear()
        self.translated_image = QImage()
        self.show_translation.setChecked(False)
        self.show_translation.setEnabled(False)
        self.copy_translation.setEnabled(False)
        self.update_preview()

    def set_blocks(self, blocks):
        self.clear_translation()
        self.blocks = tuple(replace(block, id=i, text=join_texts(block.text.splitlines()))
                            for i, block in enumerate(blocks))
        self._geometry_valid = True
        blocker = QSignalBlocker(self.source_editor)
        self.source_editor.setPlainText("\n\n".join(block.text for block in self.blocks))
        blocker.unblock()
        self.set_busy(self._busy)

    def source_paragraphs(self):
        # QTextBlock positions use Qt's UTF-16 offsets, including emoji. Keep
        # selection offsets in that same coordinate space instead of len(str).
        paragraphs = []
        block = self.source_editor.document().firstBlock()
        while block.isValid():
            text = block.text().strip()
            if text:
                paragraphs.append((text, block.position(), block.position() + block.length() - 1))
            block = block.next()
        return paragraphs

    def source_changed(self):
        paragraphs = self.source_paragraphs()
        if len(paragraphs) != len(self.blocks):
            self._geometry_valid = False
        elif tuple(p[0] for p in paragraphs) == tuple(block.text for block in self.blocks):
            self._geometry_valid = True
        self.clear_translation()
        self.set_busy(self._busy)
        if self.source_text().strip():
            self.status.setText("原文已修改，点击“翻译图片”更新译文。Enter 换段，Ctrl+C 复制选中文字。")

    def selected_rows(self):
        cursor = self.source_editor.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if cursor.hasSelection():
            return [i for i, (_, a, b) in enumerate(self.source_paragraphs()) if a < end and b > start]
        return [i for i, (_, a, b) in enumerate(self.source_paragraphs()) if a <= start <= b]

    def current_regions(self):
        paragraphs = self.source_paragraphs()
        if not self._geometry_valid or not self.blocks or len(paragraphs) != len(self.blocks):
            # Free text remains translatable after arbitrary edits. Without
            # matching paragraph geometry, do not cover the wrong image area.
            return ()
        return tuple(replace(block, text=paragraph[0])
                     for block, paragraph in zip(self.blocks, paragraphs))

    def can_split_row(self, row, regions=None):
        regions = self.current_regions() if regions is None else regions
        return (row < len(regions) and len(regions[row].lines) > 1
                and regions[row].text == join_texts(line.text for line in regions[row].lines))

    def update_structure_buttons(self):
        selected = self.selected_rows()
        regions = self.current_regions()
        chosen = [regions[row] for row in selected if row < len(regions)]
        self.merge.setEnabled(not self._busy and len(chosen) > 1 and can_merge_regions(chosen))
        self.split_paragraph.setEnabled(not self._busy and bool(regions)
                                       and any(self.can_split_row(row, regions) for row in selected))

    def merge_selected(self):
        selected = self.selected_rows()
        regions = self.current_regions()
        if self._busy or len(selected) < 2 or not regions:
            return
        chosen = [regions[row] for row in selected]
        if not can_merge_regions(chosen):
            self.status.setText("请只选择同一栏的相邻段落，避免把不同栏覆盖在一起")
            return
        merged = make_region(0, (line for region in chosen for line in region.lines),
                             join_texts(region.text for region in chosen))
        first, last = selected[0], selected[-1]
        self.set_blocks(regions[:first] + (merged,) + regions[last + 1:])
        _, start, end = self.source_paragraphs()[first]
        cursor = self.source_editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.source_editor.setTextCursor(cursor)
        self.status.setText(f"已合并 {len(selected)} 个段落，原文修改已保留。请重新翻译图片。")

    def split_selected(self):
        selected = set(self.selected_rows())
        current = self.current_regions()
        if self._busy or not selected or not current:
            return
        regions, count, edited = [], 0, 0
        for row, region in enumerate(current):
            if row in selected and len(region.lines) > 1:
                if self.can_split_row(row, current):
                    regions.extend(make_region(0, (line,)) for line in region.lines)
                    count += 1
                    continue
                edited += 1
            regions.append(region)
        if count:
            self.set_blocks(regions)
        message = f"已拆分 {count} 个段落。可拖选相邻原行重新合并，再翻译图片。"
        if edited:
            message += f" {edited} 个已修改的段落保留原文；需要拆分时可先重新提取文字。"
        self.status.setText(message)

    def update_translations(self, translations):
        self.translations.update(translations)
        text = "\n\n".join(self.translations.get(entry["id"], "") for entry in self.source_entries())
        # New batches must not reset a selection being copied, or scroll the
        # user away from the paragraph currently being read.
        cursor = self.translation_editor.textCursor()
        anchor, position = cursor.anchor(), cursor.position()
        scroll = self.translation_editor.verticalScrollBar().value()
        self.translation_editor.setPlainText(text)
        limit = self.translation_editor.document().characterCount() - 1
        cursor = self.translation_editor.textCursor()
        cursor.setPosition(min(anchor, limit))
        cursor.setPosition(min(position, limit), QTextCursor.MoveMode.KeepAnchor)
        self.translation_editor.setTextCursor(cursor)
        self.translation_editor.verticalScrollBar().setValue(scroll)
        self.copy_translation.setEnabled(bool(text.strip()))

    def set_translated_image(self, image):
        self.translated_image = QImage(image)
        self.show_translation.setEnabled(True)
        # Text columns are the default view; image overlay stays optional.
        self.update_preview()

    def update_preview(self, checked=None):
        self.preview.set_image(self.export_image())

    def export_image(self):
        if self.show_translation.isChecked() and not self.translated_image.isNull():
            return self.translated_image
        return self.image

    def source_entries(self):
        return [{"id": i, "text": paragraph[0]} for i, paragraph in enumerate(self.source_paragraphs())]

    def source_text(self):
        return self.source_editor.toPlainText()

    def translated_text(self):
        return self.translation_editor.toPlainText()

    def set_busy(self, busy):
        self._busy = busy
        has_image = not self.image.isNull()
        has_text = bool(self.source_text().strip())
        self.extract.setEnabled(has_image and not busy)
        self.translate.setEnabled(has_image and has_text and not busy)
        self.language.setEnabled(not busy)
        self.cancel.setEnabled(busy)
        self.source_editor.setReadOnly(busy or not has_image)
        self.copy_source.setEnabled(has_text)
        self.copy_translation.setEnabled(bool(self.translated_text().strip()))
        for button in (self.copy_picture, self.pin, self.save):
            button.setEnabled(has_image)
        self.update_structure_buttons()

    def closeEvent(self, event):
        self.closed.emit()
        self.image, self.translated_image = QImage(), QImage()
        self.clear_results()
        self.set_busy(False)
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)
