import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.history.history_manager import HistoryManager
from app.history.history_window import HistoryWindow
from app.pin.pin_manager import PinManager

APP = QApplication.instance() or QApplication([])


class HistoryTests(unittest.TestCase):
    def test_restart_retention_ui_copy_pin_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manager = HistoryManager(directory, 2)
            for source, color in (("screenshot", "red"), ("clipboard", "green"), ("imported", "blue")):
                image = QImage(100, 70, QImage.Format.Format_RGB32)
                image.fill(QColor(color))
                manager.add(image, source)
            manager.shutdown()
            self.assertEqual(len(manager.records), 2)
            self.assertEqual(len(list(manager.directory.glob("*.png"))), 4)
            restored = HistoryManager(directory, 2)
            self.assertEqual(restored.records, manager.records)
            self.assertEqual(restored.records[0]["source"], "imported")
            pins = PinManager()
            window = HistoryWindow(restored, pins)
            window.show()
            QTest.qWait(20)
            window.grid.setCurrentRow(0)
            window.act("copy")
            self.assertEqual(APP.clipboard().image().pixelColor(0, 0), QColor("blue"))
            window.act("pin")
            self.assertEqual(len(pins.windows), 1)
            window.act("preview")
            QTest.qWait(10)
            self.assertTrue(window.preview.isVisible())
            window.act("delete")
            self.assertEqual(window.grid.count(), 1)
            self.assertEqual(len(list(restored.directory.glob("*.png"))), 2)
            pins.close_all()
            window.close()
            restored.shutdown()
            QTest.qWait(20)


if __name__ == "__main__":
    unittest.main()
