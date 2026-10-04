import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox

from app.core.config import Config
from app.main import ApplicationController
from app.notes.note_manager import NoteManager

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class NotesSettingsTests(unittest.TestCase):
    def test_command_note_restart_completion_delete_and_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = Config(screenshot_hotkey="Ctrl+Alt+F20")
            config.save(directory)
            controller = ApplicationController(APP, directory)
            controller.toggle_panel()
            controller.execute_command("6GHz 1nH")
            self.assertEqual(controller.panel.result.text(), "C = 703.62 fF")
            controller.execute_command("/note 明天检查 VCO")
            self.assertEqual(controller.panel.notes.text(), "便签：1")
            self.assertEqual(controller.panel.result.text(), "已创建便签")
            restored = NoteManager(directory)
            self.assertEqual(restored.records[0]["text"], "明天检查 VCO")
            controller.show_notes()
            QTest.qWait(20)
            checkbox = controller.note_window.list.findChild(QCheckBox)
            QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
            self.assertTrue(NoteManager(directory).records[0]["done"])
            controller.apply_settings("Ctrl+Alt+F21", 12, False)
            self.assertEqual(controller.hotkey.text, "Ctrl+Alt+F21")
            self.assertFalse(Config.load(directory).auto_copy)
            self.assertEqual(Config.load(directory).history_limit, 12)
            controller.apply_settings("bad", 5, True)
            self.assertEqual(controller.hotkey.text, "Ctrl+Alt+F21")
            self.assertFalse(controller.config.auto_copy)
            controller.notes.delete(controller.notes.records[0]["id"])
            self.assertEqual(NoteManager(directory).records, [])
            controller.shutdown()
            controller.shutdown()
            controller.pet.close()
            QTest.qWait(20)


if __name__ == "__main__":
    unittest.main()
