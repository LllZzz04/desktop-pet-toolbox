"""Recover prose paragraphs from OCR line geometry without loading more models.

Grouping is deliberately conservative: adjacent lines of similar size and
alignment can continue a paragraph; headings, list starts, gaps and columns
keep their own regions. Retain every original box for image rendering and
manual corrections. These rules cannot infer every document's semantics.
"""
import math
import re
from dataclasses import dataclass
from statistics import median

from .models import TextRegion

LIST_START = re.compile(
    r"^(?:[•●▪◦‣–—*]\s*|-\s+|\d{1,3}[.)、](?=\D)|"
    r"[A-Za-z][.)]\s+|[（(](?:\d+|[一二三四五六七八九十]+)[）)]\s*|"
    r"[一二三四五六七八九十]+[、.]\s*)"
)
SENTENCE_END = re.compile(r"[.!?。！？][\"'”’）)]*$")


def bounds(points):
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def line_height(block):
    p0, p1, p2, p3 = block.points
    return max(1, (math.dist(p0, p3) + math.dist(p1, p2)) / 2)


def is_cjk(character):
    return ("\u3400" <= character <= "\u9fff" or "\u3040" <= character <= "\u30ff"
            or "\uac00" <= character <= "\ud7af")


def join_texts(texts):
    """Join soft line wraps without inserting spaces between Chinese glyphs.

    Preserve hyphens in technical names. The translator can repair a word
    broken with a discretionary hyphen using its surrounding context.
    """
    result = ""
    for text in texts:
        text = text.strip()
        if not text:
            continue
        if not result:
            result = text
            continue
        end, start = result[-1], text[0]
        no_space = (end in "-（([“‘，。；：！？、" or start in ",.;:!?，。；：！？、）)]”’"
                    or (is_cjk(end) and is_cjk(start)))
        result += ("" if no_space else " ") + text
    return result


def make_region(identifier, lines, text=None):
    lines = tuple(lines)
    if not lines:
        raise ValueError("段落没有文字区域")
    if len(lines) == 1:
        points = lines[0].points
    else:
        boxes = [bounds(line.points) for line in lines]
        left, top = min(b[0] for b in boxes), min(b[1] for b in boxes)
        right, bottom = max(b[2] for b in boxes), max(b[3] for b in boxes)
        points = ((left, top), (right, top), (right, bottom), (left, bottom))
    weight = sum(max(1, len(line.text)) for line in lines)
    confidence = sum(line.confidence * max(1, len(line.text)) for line in lines) / weight
    return TextRegion(identifier, join_texts(line.text for line in lines) if text is None else text,
                      confidence, points, lines)


@dataclass(frozen=True)
class LineGeometry:
    block: object
    box: tuple[float, float, float, float]
    height: float
    angle: float

    @property
    def width(self):
        return self.box[2] - self.box[0]

    @property
    def center_y(self):
        return (self.box[1] + self.box[3]) / 2


def geometry(block):
    first, second = block.points[:2]
    angle = math.degrees(math.atan2(second[1] - first[1], second[0] - first[0]))
    return LineGeometry(block, bounds(block.points), line_height(block), angle)


def looks_like_label(line):
    text = line.block.text.strip()
    if re.fullmatch(r"[\d\s.,:%+\-−/()]+", text):
        return True
    if SENTENCE_END.search(text) or line.width > 7 * line.height:
        return False
    if any(is_cjk(c) for c in text):
        return len(text) <= 5
    return len(text) <= 12 and len(text.split()) <= 2


def continuation_score(first, second):
    if (abs(first.angle) > 8 or abs(second.angle) > 8
        or abs(first.angle - second.angle) > 3
        or max(first.height, second.height) / min(first.height, second.height) > 1.3):
        return None
    height = (first.height + second.height) / 2
    gap = second.box[1] - first.box[3]
    if second.center_y - first.center_y < .65 * height or not -.3 * height <= gap <= .85 * height:
        return None
    overlap = min(first.box[2], second.box[2]) - max(first.box[0], second.box[0])
    if overlap < .65 * min(first.width, second.width):
        return None
    indent = second.box[0] - first.box[0]
    if abs(indent) > max(4, 2.2 * height):
        return None
    if LIST_START.match(second.block.text):
        return None
    # A new indent usually begins a paragraph; a bullet's hanging indent is
    # allowed to continue. A first-line indent may return to the column edge.
    if indent > .7 * height and not LIST_START.match(first.block.text):
        return None
    if first.width < .6 * second.width:
        return None  # Short heading or the previous paragraph's final line.
    if SENTENCE_END.search(first.block.text) and first.width < .9 * second.width:
        return None
    if looks_like_label(first) and looks_like_label(second):
        return None
    return abs(gap) / height + .2 * abs(indent) / height


def spans_column_peers(first, second, peers):
    """A full-width heading above two columns must not join the left column."""
    if first.width <= 1.4 * second.width:
        return False
    for peer in peers:
        if peer is second or abs(peer.center_y - second.center_y) > .35 * second.height:
            continue
        gap = max(second.box[0], peer.box[0]) - min(second.box[2], peer.box[2])
        if (gap > .5 * second.height and peer.box[0] >= first.box[0] - second.height * .3
            and peer.box[2] <= first.box[2] + second.height * .3):
            return True
    return False


def _interval_gap(regions, axis):
    """Find a whitespace cut; prefer balanced cuts when gaps have equal size."""
    intervals = sorted((bounds(region.points)[axis], bounds(region.points)[axis + 2])
                       for region in regions)
    end, gaps = intervals[0][1], []
    for start, stop in intervals[1:]:
        if start > end:
            gaps.append((start - end, (start + end) / 2))
        end = max(end, stop)
    if not gaps:
        return None
    middle = (intervals[0][0] + end) / 2
    return max(gaps, key=lambda gap: (gap[0], -abs(gap[1] - middle)))


def reading_order(regions, depth=0):
    """Order columns independently, using horizontal cuts around headings."""
    if len(regions) < 2:
        return list(regions)
    if depth >= 32:
        return sorted(regions, key=lambda region: (bounds(region.points)[1], bounds(region.points)[0]))
    height = median(line_height(line) for region in regions for line in region.lines)
    for axis, minimum in ((0, max(8, height)), (1, max(2, height * .15))):
        gap = _interval_gap(regions, axis)
        if gap is None or gap[0] <= minimum:
            continue
        before = [region for region in regions if bounds(region.points)[axis + 2] < gap[1]]
        after = [region for region in regions if bounds(region.points)[axis] > gap[1]]
        if before and after and len(before) + len(after) == len(regions):
            return reading_order(before, depth + 1) + reading_order(after, depth + 1)
    return sorted(regions, key=lambda region: (bounds(region.points)[1], bounds(region.points)[0]))


def group_paragraphs(blocks, check=None):
    if not blocks:
        return ()
    lines = sorted((geometry(block) for block in blocks),
                   key=lambda line: (line.center_y, line.box[0]))
    successors, predecessors = {}, {}
    for i, first in enumerate(lines):
        if check:
            check()
        for j in range(i + 1, len(lines)):
            second = lines[j]
            if second.center_y - first.center_y > 2.4 * first.height:
                break
            score = continuation_score(first, second)
            if score is None or spans_column_peers(first, second, lines[max(0, j - 8):j + 9]):
                continue
            candidate = (score, j)
            if i not in successors or candidate < successors[i]:
                successors[i] = candidate
            candidate = (score, i)
            if j not in predecessors or candidate < predecessors[j]:
                predecessors[j] = candidate
    # Mutual nearest continuation avoids a short line jumping between columns.
    links = {i: candidate[1] for i, candidate in successors.items()
             if predecessors[candidate[1]][1] == i}
    incoming = set(links.values())
    regions = []
    for i in range(len(lines)):
        if i in incoming:
            continue
        paragraph = [lines[i].block]
        while i in links:
            i = links[i]
            paragraph.append(lines[i].block)
        regions.append(make_region(len(regions), paragraph))
    ordered = reading_order(regions)
    return tuple(make_region(i, region.lines, region.text) for i, region in enumerate(ordered))


def can_merge_regions(regions):
    """Manual override may bridge paragraph gaps, but never a column gutter."""
    if len(regions) < 2:
        return False
    for first, second in zip(regions, regions[1:]):
        a, b = bounds(first.points), bounds(second.points)
        overlap = min(a[2], b[2]) - max(a[0], b[0])
        if overlap < .5 * min(a[2] - a[0], b[2] - b[0]):
            return False
        if any(abs(geometry(line).angle) > 8 for region in (first, second) for line in region.lines):
            return False
    return True
