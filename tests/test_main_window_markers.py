import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.records import Sample
from rtt_gui4graph.ui.main_window import MainWindow


class MainWindowMarkerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_marker_can_be_added_without_device_connection(self):
        window = MainWindow()
        try:
            self.assertIsNone(window._worker)

            marker = window.add_marker("offline label", "offline note")

            self.assertEqual(marker.name, "offline label")
            self.assertEqual(marker.note, "offline note")
            self.assertEqual(window._marker_panel._list.count(), 1)
        finally:
            window.close()

    def test_marker_delete_refreshes_plot_without_device_connection(self):
        window = MainWindow()
        try:
            window._registry.ingest(Sample("TAP.x", 1.0, 2.0, ""))
            window._registry.set_enabled("TAP.x", True)
            marker = window.add_marker("offline label", "offline note")
            self.assertGreater(len(window._plot._marker_lines), 0)

            self.assertTrue(window._marker_panel.remove_marker(marker.id))

            self.assertEqual(window._markers.markers(), [])
            self.assertEqual(len(window._plot._marker_lines), 0)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
