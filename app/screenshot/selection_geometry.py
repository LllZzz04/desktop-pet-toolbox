"""Selection hit testing and edits, all using half-open native pixel bounds."""
from PySide6.QtCore import QPointF, QRect

MINIMUM_SIZE = 2


def handle_points(rect):
    left, top = rect.x(), rect.y()
    right, bottom = left + rect.width(), top + rect.height()
    middle_x, middle_y = (left + right) / 2, (top + bottom) / 2
    return {"nw": QPointF(left, top), "n": QPointF(middle_x, top),
            "ne": QPointF(right, top), "e": QPointF(right, middle_y),
            "se": QPointF(right, bottom), "s": QPointF(middle_x, bottom),
            "sw": QPointF(left, bottom), "w": QPointF(left, middle_y)}


def hit_test(rect, point, tolerance_x, tolerance_y):
    if rect is None or rect.isEmpty():
        return "new"
    left, top = rect.x(), rect.y()
    right, bottom = left + rect.width(), top + rect.height()
    x, y = point.x(), point.y()
    if not left - tolerance_x <= x <= right + tolerance_x or not top - tolerance_y <= y <= bottom + tolerance_y:
        return "new"
    horizontal = min(((abs(x - left), "w"), (abs(x - right), "e")))
    vertical = min(((abs(y - top), "n"), (abs(y - bottom), "s")))
    side_x = horizontal[1] if horizontal[0] <= tolerance_x else ""
    side_y = vertical[1] if vertical[0] <= tolerance_y else ""
    if side_x or side_y:
        return side_y + side_x
    return "move" if left <= x < right and top <= y < bottom else "new"


def clamp_point(point, desktop):
    # Edges may lie on the exclusive desktop boundary, even though the last
    # visible cursor pixel is one pixel inside it.
    return type(point)(max(desktop.x(), min(point.x(), desktop.x() + desktop.width())),
                       max(desktop.y(), min(point.y(), desktop.y() + desktop.height())))


def move_selection(origin, delta, desktop):
    x = max(desktop.x(), min(origin.x() + delta.x(), desktop.x() + desktop.width() - origin.width()))
    y = max(desktop.y(), min(origin.y() + delta.y(), desktop.y() + desktop.height() - origin.height()))
    return QRect(x, y, origin.width(), origin.height())


def resize_selection(origin, delta, edges, desktop):
    left, top = origin.x(), origin.y()
    right, bottom = left + origin.width(), top + origin.height()
    if "w" in edges:
        left = max(desktop.x(), min(left + delta.x(), right - MINIMUM_SIZE))
    if "e" in edges:
        right = min(desktop.x() + desktop.width(), max(right + delta.x(), left + MINIMUM_SIZE))
    if "n" in edges:
        top = max(desktop.y(), min(top + delta.y(), bottom - MINIMUM_SIZE))
    if "s" in edges:
        bottom = min(desktop.y() + desktop.height(), max(bottom + delta.y(), top + MINIMUM_SIZE))
    return QRect(left, top, right - left, bottom - top)
