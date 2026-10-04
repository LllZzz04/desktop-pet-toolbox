"""Native hotkey / cross-process clipboard QA. Not part of the shipped UI.

python -m tests.manual_probe            production controller + test canvas
python -m tests.manual_probe --receiver separate clipboard paste receiver
"""
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QCursor, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from app.core.storage import data_directory, setup_logging, write_json
from app.main import ApplicationController


class Probe(QWidget):
    def __init__(self, app, receiver=False):
        super().__init__()
        self.app, self.receiver = app, receiver
        self.setWindowTitle("剪贴板粘贴验证" if receiver else "桌宠 v0.1 验证画布")
        self.resize(460, 490)
        self.move(400 if receiver else 80, 100)
        layout = QVBoxLayout(self)
        self.status = QLabel("按 Ctrl+V 粘贴图片" if receiver else "按 Alt+A 验证全局热键（测试模式自动框选画布）")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.canvas = QLabel("V0.1\nSCREEN CAPTURE\n220 × 140 TEST REGION")
        self.canvas.setMinimumHeight(220)
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet("background: #285c70; color: #ffffff; font-size: 20px;")
        layout.addWidget(self.canvas, 1)
        if receiver:
            self.shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
            self.shortcut.activated.connect(self.paste)
        else:
            self.directory = data_directory()
            setup_logging(self.directory)
            self.controller = ApplicationController(app, self.directory)
            self.controller.screenshots.started.connect(self.prepare_selection)
            self.controller.screenshots.captured.connect(self.captured)
            for title, action in (("工具面板", self.controller.toggle_panel),
                                   ("最近图片", self.controller.show_history),
                                   ("便签", self.controller.show_notes),
                                   ("设置", self.controller.show_settings)):
                button = QPushButton(title)
                button.clicked.connect(action)
                layout.addWidget(button)
        quit_button = QPushButton("退出验证")
        quit_button.clicked.connect(app.quit)
        layout.addWidget(quit_button)

    def prepare_selection(self):
        QTimer.singleShot(250, self.select_region)

    def select_region(self):
        manager = self.controller.screenshots
        if not manager.overlays:
            self.status.setText("截图准备失败")
            return
        start = self.canvas.mapToGlobal(QPoint(18, 18))
        overlay = next(o for o in manager.overlays if o.snapshot.logical.contains(start))
        QCursor.setPos(start)
        manager.begin_selection(overlay)
        QCursor.setPos(self.canvas.mapToGlobal(QPoint(238, 158)))
        manager.complete_selection()
        QTimer.singleShot(250, manager.cancel)

    def captured(self, image):
        self.status.setText(f"原生热键触发成功 · 已自动复制 {image.width()} × {image.height()} px")
        write_json(self.directory / "native-result.json",
                   {"native_hotkey": True, "width": image.width(), "height": image.height(),
                    "clipboard": QApplication.clipboard().image().size() == image.size()})

    def paste(self):
        image = QApplication.clipboard().image()
        if image.isNull():
            self.status.setText("剪贴板没有图片")
            return
        self.status.setText(f"跨进程粘贴成功 · {image.width()} × {image.height()} px")
        self.canvas.setPixmap(QPixmap.fromImage(image).scaled(
            self.canvas.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        write_json(data_directory() / "paste-result.json", {"pasted": True,
                   "width": image.width(), "height": image.height()})

    def closeEvent(self, event):
        self.app.quit()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopPetToolboxQA")
    app.setOrganizationName("DesktopPetToolbox")
    app.setQuitOnLastWindowClosed(False)
    probe = Probe(app, "--receiver" in sys.argv)
    probe.show()
    app.exec()


if __name__ == "__main__":
    main()
