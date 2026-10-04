from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout

from .answer_view import AnswerView
from .command_input import CommandInput
from .components import ActionButton, ToolButton, card, column, label, page_header, soft_shadow
from .theme import THEME, tool_window


class CommandPanel(QFrame):
    command_submitted = Signal(str)
    screenshot_requested = Signal()
    history_requested = Signal()
    notes_requested = Signal()
    pins_requested = Signal()
    extract_requested = Signal()
    translate_requested = Signal()
    stop_requested = Signal()
    retry_requested = Signal()
    clear_chat_requested = Signal()
    quick_ocr_requested = Signal()
    calculations_requested = Signal()

    def __init__(self):
        # A tool window can own native keyboard/IME focus without the mouse
        # grab of a menu-style Popup interfering with candidate windows.
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self._pet = None
        self._above = True
        self._busy = False
        self._kind = "empty"
        self._can_retry = False
        self._unread_reply = False
        self._waiting_for_reply = False
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._dismiss_if_inactive)
        self.setWindowTitle("桌宠工具面板")
        self.setFixedWidth(368)
        self.setFrameShape(QFrame.Shape.NoFrame)
        tool_window(self, floating=True)
        layout = column(self, 8, 0)
        shell = card(THEME.page_padding, "shell")
        soft_shadow(shell)
        layout.addWidget(shell)
        body = shell.layout()
        body.addWidget(page_header("Luna 工具箱", "随手计算，轻松处理桌面任务"))

        # The answer precedes the shared input and occupies no space until used.
        self.answer_box = card(12)
        answer_layout = self.answer_box.layout()
        answer_layout.setSpacing(8)
        self.result = AnswerView()
        self.result.setProperty("flatEditor", True)
        self.result.height_changed.connect(self._fit)
        answer_layout.addWidget(self.result)
        self.status = label("", "status", True)
        answer_layout.addWidget(self.status)
        actions = QHBoxLayout()
        actions.setSpacing(4)
        self.copy = self._button("复制", "复制完整回答", self._copy_result)
        self.stop = self._button("停止", "停止当前生成，保留已收到的文字", self.stop_requested.emit)
        self.retry = self._button("重试", "重新请求上一条未完成的问题", self.retry_requested.emit)
        self.new_chat = self._button("新对话", "清空本地对话记录和上下文", self.clear_chat_requested.emit)
        self.collapse = self._button("收起", "收起回答，保留对话上下文", self.clear_response)
        for button in (self.copy, self.stop, self.retry, self.new_chat):
            actions.addWidget(button)
        actions.addStretch()
        actions.addWidget(self.collapse)
        answer_layout.addLayout(actions)
        body.addWidget(self.answer_box)
        self.answer_box.hide()
        self.result.hide()

        body.addWidget(label("计算 · 单位换算 · 对话", "section"))
        self.input = CommandInput()
        self.input.setMaxLength(8000)
        self.input.setAccessibleName("计算与对话输入")
        self.input.setPlaceholderText("算式、6GHz 1nH，或直接提问…")
        self.input.setToolTip("Enter 执行 · 自动识别计算、换算、便签或大模型问题")
        self.input.returnPressed.connect(self._submit)
        body.addWidget(self.input)
        body.addWidget(label("Enter 执行   /note 内容：创建便签", "muted"))

        tools = card(12)
        tools.layout().addWidget(label("常用工具", "section"))
        grid = QGridLayout()
        grid.setSpacing(THEME.spacing)
        self.capture = ActionButton("截图 · Alt+A", "primary", "screenshot")
        self.history = ActionButton("最近图片", kind="history")
        self.pins = ActionButton("当前贴图：0", kind="pin")
        self.notes = ActionButton("便签：0", kind="note")
        for widget, signal, row, col in ((self.capture, self.screenshot_requested, 0, 0),
                                        (self.history, self.history_requested, 0, 1),
                                        (self.pins, self.pins_requested, 1, 0),
                                        (self.notes, self.notes_requested, 1, 1)):
            widget.clicked.connect(signal.emit)
            grid.addWidget(widget, row, col)
        self.extract_text = ActionButton("提取文字…", kind="ocr")
        self.translate_image = ActionButton("翻译图片…", kind="translate")
        self.extract_text.clicked.connect(lambda: self.extract_requested.emit())
        self.translate_image.clicked.connect(lambda: self.translate_requested.emit())
        grid.addWidget(self.extract_text, 2, 0)
        grid.addWidget(self.translate_image, 2, 1)
        self.quick_ocr = ActionButton("区域取字", kind="ocr")
        self.quick_ocr.clicked.connect(lambda: self.quick_ocr_requested.emit())
        self.calculations = ActionButton("计算记录", kind="history")
        self.calculations.clicked.connect(lambda: self.calculations_requested.emit())
        grid.addWidget(self.quick_ocr, 3, 0)
        grid.addWidget(self.calculations, 3, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        tools.layout().addLayout(grid)
        body.addWidget(tools)
        self._update_actions()

    @staticmethod
    def _button(text, tooltip, callback):
        button = ToolButton(text)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setAutoRaise(True)
        button.clicked.connect(lambda checked=False: callback())
        return button

    def _submit(self):
        if self.input.is_composing or self.input.confirming_composition:
            return
        self.command_submitted.emit(self.input.text())

    def _copy_result(self):
        if self.result.text():
            QApplication.clipboard().setText(self.result.text())

    def show_near(self, pet):
        self._pet = pet
        if not self._busy and not self._unread_reply:
            self.clear_response()
        area = self._area()
        above = pet.y() - area.top() - 6
        below = area.bottom() - pet.geometry().bottom() - 6
        self._above = above >= below
        self._fit()
        self.show()
        self.raise_()
        self.activateWindow()
        self._fit()
        self._unread_reply = False
        self.input.setFocus()
        self.input.selectAll()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowDeactivate and self.isVisible():
            self._dismiss_timer.start(150)
        elif event.type() == QEvent.Type.WindowActivate:
            self._dismiss_timer.stop()

    def _dismiss_if_inactive(self):
        if not self.isVisible() or QApplication.activeWindow() is self:
            return
        popup = QApplication.activePopupWidget()
        if popup is not None and (popup is self or self.isAncestorOf(popup)):
            self._dismiss_timer.start(150)
            return
        if self.input.is_composing:
            # Native IME candidates may briefly change activation. Do not hide
            # the editor or drop its preedit while the user is selecting text.
            self._dismiss_timer.start(150)
            return
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if not self.input.is_composing:
                self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def _area(self):
        point = self._pet.geometry().center() if self._pet is not None else self.geometry().center()
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        return screen.availableGeometry()

    def _fit(self):
        if self._pet is not None and not self.answer_box.isHidden():
            area = self._area()
            self.layout().activate()
            total = self.layout().totalHeightForWidth(self.width())
            if total < 0:
                total = self.layout().sizeHint().height()
            fixed = total - (0 if self.result.isHidden() else self.result.height())
            space = (self._pet.y() - area.top() - 6 if self._above else
                     area.bottom() - self._pet.geometry().bottom() - 6)
            limit = min(320, int(area.height() * .45), max(28, space - fixed))
            self.result.set_height_limit(limit)
        self.layout().activate()
        self.adjustSize()
        if self._pet is not None:
            area = self._area()
            x = self._pet.geometry().right() - self.width() + 1
            y = self._pet.y() - self.height() - 6 if self._above else self._pet.geometry().bottom() + 6
            x = min(max(area.left(), x), max(area.left(), area.right() - self.width() + 1))
            y = min(max(area.top(), y), max(area.top(), area.bottom() - self.height() + 1))
            self.move(QPoint(x, y))

    def _update_actions(self):
        self.copy.setEnabled(bool(self.result.text()))
        self.stop.setVisible(self._busy)
        self.retry.setVisible(self._kind == "chat" and self._can_retry and not self._busy)
        self.new_chat.setVisible(self._kind == "chat")
        self.new_chat.setEnabled(not self._busy)
        self.collapse.setEnabled(not self._busy)

    def display_result(self, result):
        if result.kind == "empty":
            self.clear_response()
            return
        self._kind = result.kind
        self._can_retry = False
        self._unread_reply = False
        self.result.setPlainText(result.text)
        self.result.show()
        self.result.setToolTip("" if result.ok else "请检查输入格式")
        self.status.setText({"calculation": "本地计算 · 上下键调用历史 · 三角函数使用弧度",
                             "note": "便签", "help": "射频计算用法"}.get(result.kind, "输入有误"))
        self.status.setToolTip("")
        self.answer_box.show()
        self._update_actions()
        self._fit()

    def start_reply(self, question):
        self._kind = "chat"
        self._can_retry = self._unread_reply = False
        self._waiting_for_reply = False
        self.result.clear()
        self.result.setToolTip("大模型回复 · 可选择文字复制")
        self.status.setToolTip(question[:160])
        self.result.hide()
        self.status.setText("大模型 · 等待回复…")
        self.answer_box.show()
        self._update_actions()
        self._fit()

    def append_reply(self, text):
        if self._kind != "chat":
            return
        self.result.append_text(text)
        self.result.show()
        if not self._waiting_for_reply:
            self.status.setText("大模型 · 正在回复…")
        self._update_actions()
        self._fit()

    def finish_reply(self, message, can_retry):
        if self._kind != "chat":
            return
        self._can_retry = can_retry
        self.status.setText(message)
        self._unread_reply = not self.isVisible()
        self._update_actions()
        self._fit()

    def reject_reply(self, message):
        self.start_reply("")
        self.result.setPlainText(message)
        self.result.show()
        self.status.setText("大模型 · 未发送")
        self._update_actions()
        self._fit()

    def set_chat_busy(self, busy):
        self._busy = busy
        self._update_actions()
        self._fit()

    def wait_for_reply(self):
        self._waiting_for_reply = True
        self.status.setText("大模型正在回复；请先点击“停止”，再发送新问题。")
        self._fit()

    def clear_response(self):
        self._kind = "empty"
        self._can_retry = self._unread_reply = False
        self.result.clear()
        self.result.hide()
        self.answer_box.hide()
        self._update_actions()
        self._fit()

    def hideEvent(self, event):
        self._dismiss_timer.stop()
        # Dismissing the popup never reopens it or cancels a background reply.
        if not self._busy:
            self.clear_response()
        super().hideEvent(event)
