import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.records import LogLine, Sample
from rtt_gui4graph.ui.main_window import MainWindow


class MainWindowRecordingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_toolbar_uses_recording_buttons_instead_of_snapshot_save_buttons(self):
        window = MainWindow()
        try:
            self.assertTrue(hasattr(window, "_start_record"))
            self.assertTrue(hasattr(window, "_stop_record"))
            self.assertTrue(hasattr(window, "_save_record"))
            self.assertFalse(hasattr(window, "_save_capture"))
            self.assertFalse(hasattr(window, "_export_csv"))
        finally:
            window.close()

    def test_recording_collects_only_after_start_and_can_save_csv(self):
        window = MainWindow()
        try:
            window._recording.ingest([Sample("TAP.x", 1.0, 1.0, "")])
            window.start_recording()
            window._batches.push(
                [
                    LogLine(terminal=0, t=2.0, text="TAP x=2"),
                    Sample("TAP.x", 2.0, 2.0, ""),
                ]
            )
            window._drain_records()
            window.stop_recording()
            window._recording.ingest([Sample("TAP.x", 3.0, 3.0, "")])

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "record.csv"
                with patch.object(
                    window._file_dialog,
                    "getSaveFileName",
                    return_value=(str(path), "CSV (*.csv)"),
                ):
                    window.save_recording()

                text = path.read_text(encoding="utf-8")

            self.assertIn("TAP.x", text)
            self.assertIn("2.000000,2.000000", text)
            self.assertNotIn("3.000000", text)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
