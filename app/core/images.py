from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox


def copy_image(image):
    if image.isNull():
        raise ValueError("图片为空")
    copied = image.copy()
    copied.setDevicePixelRatio(1)
    QApplication.clipboard().setImage(copied)


def save_image(image, parent=None):
    path, _ = QFileDialog.getSaveFileName(parent, "保存图片", "截图.png",
                                         "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg)")
    if not path:
        return False
    if not Path(path).suffix:
        path += ".png"
    if not image.save(path):
        QMessageBox.warning(parent, "保存失败", "无法写入图片，请检查目标路径和磁盘空间。")
        return False
    return True
