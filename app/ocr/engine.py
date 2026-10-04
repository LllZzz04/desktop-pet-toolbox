"""RapidOCR CPU adapter. No network requests and no eager model loading."""
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

from .models import OcrResult, TextBlock
from .layout import group_paragraphs


class ProcessingCancelled(Exception):
    pass


def check_cancelled(cancelled):
    if cancelled.is_set():
        raise ProcessingCancelled()


def extract_text(image, cancelled):
    check_cancelled(cancelled)
    if image.isNull():
        raise ValueError("图片为空")
    if image.width() * image.height() > 64_000_000:
        raise ValueError("图片过大，请截取更小的文字区域后重试")
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise ValueError("尚未安装文字提取依赖，请按 README 安装 requirements.txt") from error

    # Bound OCR working memory while retaining coordinates in the original image.
    scaled = image.scaled(3200, 3200, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation) if max(image.width(), image.height()) > 3200 else image
    rgb = QImage(scaled.size(), QImage.Format.Format_RGB888)
    rgb.fill(Qt.GlobalColor.white)
    painter = QPainter(rgb)
    try:
        painter.drawImage(0, 0, scaled)
    finally:
        painter.end()
    pixels = np.frombuffer(rgb.constBits(), dtype=np.uint8,
                           count=rgb.height() * rgb.bytesPerLine()).reshape(rgb.height(), rgb.bytesPerLine())
    pixels = pixels[:, :rgb.width() * 3].reshape(rgb.height(), rgb.width(), 3)
    bgr = np.ascontiguousarray(pixels[:, :, ::-1])
    check_cancelled(cancelled)
    # A task owns its sessions; they are released after extraction, rather than
    # keeping OCR models resident for the entire lifetime of the desktop pet.
    engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1,
                      det_use_cuda=False, rec_use_cuda=False, cls_use_cuda=False,
                      det_use_dml=False, rec_use_dml=False, cls_use_dml=False,
                      max_side_len=3200, det_limit_side_len=1536, det_limit_type="max")
    try:
        check_cancelled(cancelled)
        raw, _ = engine(bgr, use_det=True, use_cls=True, use_rec=True)
        check_cancelled(cancelled)
    finally:
        del engine
    scale_x, scale_y = image.width() / rgb.width(), image.height() / rgb.height()
    blocks = []
    for points, text, confidence, *unused in raw or []:
        text = str(text).strip()
        if not text or len(points) != 4:
            continue
        mapped = tuple((min(image.width() - 1, max(0, float(x) * scale_x)),
                        min(image.height() - 1, max(0, float(y) * scale_y))) for x, y in points)
        score = float(confidence)
        if not math.isfinite(score) or any(not math.isfinite(v) for point in mapped for v in point):
            continue
        blocks.append(TextBlock(len(blocks), text, score, mapped))
    blocks = tuple(blocks)
    paragraphs = group_paragraphs(blocks, check=lambda: check_cancelled(cancelled))
    check_cancelled(cancelled)
    return OcrResult(blocks, paragraphs)
