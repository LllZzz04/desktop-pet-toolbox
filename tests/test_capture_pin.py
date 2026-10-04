import unittest

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QContextMenuEvent, QCursor, QImage, QWheelEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from app.core.config import Config
from app.core.hotkey import GlobalHotkey
from app.pin.pin_manager import PinManager
from app.pet.pet_window import PetWindow
from app.screenshot.screen_capture import ScreenSnapshot, compose_selection, selection_rect
from app.screenshot.screenshot_manager import ScreenshotManager

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def solid(width, height, color):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    return image


class CapturePinTests(unittest.TestCase):
    def test_lossless_cross_monitor_negative_origin_mixed_dpi(self):
        first = ScreenSnapshot(None, QRect(-200, 0, 200, 100), QRect(-300, 0, 300, 150),
                               solid(300, 150, "red"))
        second = ScreenSnapshot(None, QRect(0, 0, 200, 100), QRect(0, 0, 200, 100),
                                solid(200, 100, "blue"))
        image = compose_selection([first, second], QRect(-50, 10, 100, 60))
        self.assertEqual((image.width(), image.height()), (100, 60))
        self.assertEqual(image.pixelColor(49, 0), QColor("red"))
        self.assertEqual(image.pixelColor(50, 0), QColor("blue"))
        self.assertAlmostEqual(first.local_rect(QRect(-150, 0, 150, 150)).x(), 100)
        self.assertEqual(selection_rect(QPoint(200, 100), QPoint(100, 0)), QRect(100, 0, 100, 100))

    def test_sparse_desktop_gap_and_guard(self):
        snapshot = ScreenSnapshot(None, QRect(0, 0, 20, 20), QRect(0, 0, 20, 20), solid(20, 20, "red"))
        image = compose_selection([snapshot], QRect(10, 10, 30, 30))
        self.assertEqual(image.pixelColor(0, 0), QColor("red"))
        self.assertEqual(image.pixelColor(29, 29), QColor("#202020"))
        with self.assertRaises(ValueError):
            compose_selection([snapshot], QRect(0, 0, 100_000, 100_000))

    def test_real_screen_clipboard_pin_and_cleanup(self):
        manager = ScreenshotManager(Config())
        errors, captures = [], []
        manager.failed.connect(errors.append)
        manager.captured.connect(captures.append)
        manager.start()
        QTest.qWait(180)
        self.assertFalse(errors, errors)
        self.assertTrue(manager.overlays)
        overlay = manager.overlays[0]
        QCursor.setPos(overlay.mapToGlobal(QPoint(100, 100)))
        manager.begin_selection(overlay)
        QCursor.setPos(overlay.mapToGlobal(QPoint(300, 240)))
        manager.complete_selection()
        self.assertEqual(len(captures), 1)
        captured = captures[0]
        self.assertEqual(APP.clipboard().image().size(), captured.size())
        self.assertGreaterEqual(captured.width(), 200)
        pins = PinManager()
        manager.pin_requested.connect(pins.add)
        manager.pin()
        self.assertFalse(manager.active)
        self.assertFalse(manager.snapshots)
        self.assertEqual(len(pins.windows), 1)
        window = pins.windows[0]
        old_width = window.width()
        wheel = QWheelEvent(QPointF(20, 20), QPointF(window.mapToGlobal(QPoint(20, 20))),
                            QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        APP.sendEvent(window, wheel)
        self.assertGreater(window.width(), old_width)
        self.assertAlmostEqual(window.width() / window.height(), captured.width() / captured.height(), delta=.02)
        position = window.pos()
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(15, 15))
        QTest.mouseMove(window, QPoint(55, 45), delay=20)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(15, 15))
        self.assertGreater((window.pos() - position).manhattanLength(), 20)

        def choose_opacity():
            menu = APP.activePopupWidget()
            action = next(action for action in menu.actions() if action.text() == "透明度")
            preset = next(action for action in action.menu().actions() if action.text() == "60%")
            preset.trigger()
            menu.close()

        QTimer.singleShot(30, choose_opacity)
        menu_event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(20, 20),
                                       window.mapToGlobal(QPoint(20, 20)))
        APP.sendEvent(window, menu_event)
        self.assertAlmostEqual(window.windowOpacity(), .6, delta=.01)
        pins.hide_all()
        self.assertEqual(len(pins.windows), 1)
        self.assertFalse(window.isVisible())
        pins.restore_all()
        self.assertTrue(window.isVisible())
        QTest.mouseDClick(window, Qt.MouseButton.LeftButton)
        self.assertEqual(len(pins.windows), 0)
        QTest.qWait(10)

    def test_pet_click_drag_state_and_restored_position(self):
        pet = PetWindow()
        pet.show()
        QTest.qWait(20)
        clicks, moves = QSignalSpy(pet.clicked), QSignalSpy(pet.moved)
        QTest.mouseClick(pet, Qt.MouseButton.LeftButton, pos=QPoint(50, 50))
        self.assertEqual(clicks.count(), 1)
        position = pet.pos()
        QTest.mousePress(pet, Qt.MouseButton.LeftButton, pos=QPoint(50, 50))
        QTest.mouseMove(pet, QPoint(10, 10), delay=20)
        QTest.mouseRelease(pet, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        self.assertEqual(clicks.count(), 1)
        self.assertEqual(moves.count(), 1)
        self.assertNotEqual(pet.pos(), position)
        restored = PetWindow([pet.x(), pet.y()])
        self.assertEqual(restored.pos(), pet.pos())
        for state in ("working", "success", "error", "idle"):
            pet.set_state(state)
            self.assertEqual(pet.animation.state, state)
        pet.hide()
        self.assertFalse(pet.timer.isActive())
        pet.close()
        restored.close()

    def test_auto_copy_disabled_and_repeated_cancel(self):
        previous = solid(10, 10, "green")
        APP.clipboard().setImage(previous)
        manager = ScreenshotManager(Config(auto_copy=False))
        manager.start()
        QTest.qWait(150)
        overlay = manager.overlays[0]
        QCursor.setPos(overlay.mapToGlobal(QPoint(100, 100)))
        manager.begin_selection(overlay)
        QCursor.setPos(overlay.mapToGlobal(QPoint(200, 200)))
        manager.complete_selection()
        self.assertEqual(APP.clipboard().image().size(), previous.size())
        manager.copy()
        self.assertGreater(APP.clipboard().image().width(), 10)
        manager.cancel()
        self.assertFalse(manager.active)

    def test_escape_cancel(self):
        manager = ScreenshotManager(Config())
        manager.start()
        QTest.qWait(150)
        QTest.keyClick(manager.overlays[0], Qt.Key.Key_Escape)
        self.assertFalse(manager.active)
        self.assertFalse(manager.overlays)

    def test_native_hotkey_conflict_preserves_previous_registration(self):
        first, second = GlobalHotkey(APP), GlobalHotkey(APP)
        try:
            first.register("Ctrl+Alt+F22")
            second.register("Ctrl+Alt+F23")
            with self.assertRaises(ValueError):
                second.register("Ctrl+Alt+F22")
            self.assertEqual(second.text, "Ctrl+Alt+F23")
        finally:
            first.close()
            second.close()
        released = GlobalHotkey(APP)
        released.register("Ctrl+Alt+F22")
        released.close()


if __name__ == "__main__":
    unittest.main()
