from dataclasses import dataclass


@dataclass(frozen=True)
class TextBlock:
    id: int
    text: str
    confidence: float
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class TextRegion:
    """A translation paragraph, retaining the OCR lines used to erase text."""
    id: int
    text: str
    confidence: float
    points: tuple[tuple[float, float], ...]
    lines: tuple[TextBlock, ...]


@dataclass(frozen=True)
class OcrResult:
    blocks: tuple[TextBlock, ...]
    paragraphs: tuple[TextRegion, ...] = ()

    @property
    def text(self):
        return "\n".join(block.text for block in self.blocks)
