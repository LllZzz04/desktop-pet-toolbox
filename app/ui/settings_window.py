from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout,
                               QKeySequenceEdit, QLineEdit, QScrollArea,
                               QSpinBox, QTabWidget, QWidget)

from app.chat.settings import MODEL_CHOICES
from app.translation.settings import LANGUAGES
from .components import ActionButton, card, column, label, page_header, page_layout, row


class SettingsWindow(QDialog):
    settings_submitted = Signal(str, int, bool, str, str, str, object)

    def __init__(self, config):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("设置 — 桌宠工具箱")
        self.resize(600, 720)
        self.setMinimumSize(520, 480)
        layout = page_layout(self)
        layout.addWidget(page_header("设置", "让常用工具更贴合你的习惯"))
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        general, general_layout = self.settings_page("常规与本地翻译")
        desktop = card()
        desktop.layout().addWidget(label("桌面与截图", "section"))
        form = self.form()
        self.hotkey = QKeySequenceEdit()
        self.hotkey.setMaximumSequenceLength(1)
        self.quick_hotkey = QKeySequenceEdit()
        self.quick_hotkey.setMaximumSequenceLength(1)
        self.limit = QSpinBox()
        self.limit.setRange(1, 50)
        self.copy = QCheckBox("截图完成后自动复制到剪贴板")
        self.startup = QCheckBox("开机启动（预留）")
        self.startup.setEnabled(False)
        self.restore_pins = QCheckBox("启动时恢复贴图工作区")
        self.fullscreen_dnd = QCheckBox("全屏免打扰（临时隐藏同一显示器上的宠物）")
        form.addRow("截图快捷键", self.hotkey)
        form.addRow("区域取字快捷键", self.quick_hotkey)
        form.addRow("历史最大数量", self.limit)
        form.addRow(self.copy)
        form.addRow(self.startup)
        form.addRow(self.restore_pins)
        form.addRow(self.fullscreen_dnd)
        desktop.layout().addLayout(form)
        general_layout.addWidget(desktop)

        translation = card()
        translation.layout().addWidget(label("本地翻译 · Ollama", "section"))
        translation_form = self.form()
        self.ollama_url = QLineEdit()
        self.ollama_url.setMaxLength(300)
        self.ollama_url.setPlaceholderText("http://127.0.0.1:11434")
        self.model = QLineEdit()
        self.model.setMaxLength(160)
        self.model.setPlaceholderText("qwen2.5:3b")
        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        translation_form.addRow("本机服务地址", self.ollama_url)
        translation_form.addRow("已下载的模型", self.model)
        translation_form.addRow("默认译为", self.language)
        translation.layout().addLayout(translation_form)
        translation.layout().addWidget(label(
            "文字提取可直接使用。翻译需要先安装并启动 Ollama，再下载模型。"
            "图片在本机识别，原文只发送给本机 Ollama。", "caption", True))
        general_layout.addWidget(translation)
        general_layout.addStretch()

        chat_page, chat_layout = self.settings_page("大模型对话")
        connection = card()
        connection.layout().addWidget(label("对话服务", "section"))
        chat_form = self.form()
        self.chat_url = QLineEdit()
        self.chat_url.setMaxLength(500)
        self.chat_url.setPlaceholderText("https://api.deepseek.com")
        self.chat_model = QComboBox()
        self.chat_model.setEditable(True)
        self.chat_model.addItems(MODEL_CHOICES)
        self.chat_model.lineEdit().setMaxLength(160)
        self.chat_key = QLineEdit()
        self.chat_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.chat_key.setMaxLength(4096)
        self.chat_key.setAccessibleName("对话 API Key")
        self.remove_chat_key = QCheckBox("移除已保存的 API Key")
        self.remove_chat_key.toggled.connect(lambda checked: self.chat_key.setEnabled(not checked))
        self.save_chat = QCheckBox("保存对话到本地（关闭后删除本地记录）")
        chat_form.addRow("服务地址", self.chat_url)
        chat_form.addRow("模型", self.chat_model)
        chat_form.addRow("API Key", self.chat_key)
        chat_form.addRow(self.remove_chat_key)
        chat_form.addRow(self.save_chat)
        connection.layout().addLayout(chat_form)
        chat_layout.addWidget(connection)
        explanation = card(12, "soft")
        explanation.layout().addWidget(label(
            "默认连接 DeepSeek。消息会发送到这里配置的服务，费用以服务平台账单为准。"
            "API Key 使用 Windows 加密保存；已有密钥时，输入框留空可保持原密钥。"
            "此配置用于文字对话，图片翻译仍使用本机 Ollama。", "caption", True))
        chat_layout.addWidget(explanation)
        chat_layout.addStretch()

        self.status = label("快捷键冲突时会保留原设置。降低历史数量会移除最旧图片。", "status", True)
        layout.addWidget(self.status)
        footer = row()
        footer.addStretch()
        close = ActionButton("关闭", "ghost")
        close.clicked.connect(self.close)
        apply = ActionButton("保存设置", "primary")
        apply.clicked.connect(self.submit)
        footer.addWidget(close)
        footer.addWidget(apply)
        layout.addLayout(footer)
        self.load(config)

    def settings_page(self, title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        page = QWidget()
        page.setProperty("surface", "page")
        layout = column(page, 0, 16)
        layout.setContentsMargins(0, 16, 8, 0)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, title)
        return page, layout

    @staticmethod
    def form():
        layout = QFormLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return layout

    def load(self, config, has_api_key=False):
        self.hotkey.setKeySequence(QKeySequence(config.screenshot_hotkey))
        self.quick_hotkey.setKeySequence(QKeySequence(config.quick_ocr_hotkey))
        self.limit.setValue(config.history_limit)
        self.copy.setChecked(config.auto_copy)
        self.startup.setChecked(False)
        self.restore_pins.setChecked(config.restore_pins)
        self.fullscreen_dnd.setChecked(config.fullscreen_dnd)
        self.ollama_url.setText(config.ollama_url)
        self.model.setText(config.translation_model)
        index = self.language.findData(config.translation_language)
        self.language.setCurrentIndex(max(0, index))
        self.chat_url.setText(config.chat_base_url)
        self.chat_model.setCurrentText(config.chat_model)
        self.chat_key.clear()
        self.chat_key.setPlaceholderText("已保存（留空保持）" if has_api_key else "粘贴平台提供的 API Key")
        self.remove_chat_key.setChecked(False)
        self.chat_key.setEnabled(True)
        self.save_chat.setChecked(config.chat_save_history)

    def submit(self):
        text = self.hotkey.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        self.settings_submitted.emit(text, self.limit.value(), self.copy.isChecked(),
                                     self.ollama_url.text(), self.model.text(), self.language.currentData(),
                                     {"base_url": self.chat_url.text(), "model": self.chat_model.currentText(),
                                      "save_history": self.save_chat.isChecked(), "key": self.chat_key.text(),
                                      "remove_key": self.remove_chat_key.isChecked(),
                                      "restore_pins": self.restore_pins.isChecked(),
                                      "fullscreen_dnd": self.fullscreen_dnd.isChecked(),
                                      "quick_ocr_hotkey": self.quick_hotkey.keySequence().toString(
                                          QKeySequence.SequenceFormat.PortableText)})
