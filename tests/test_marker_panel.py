import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.markers import MarkerStore
from rtt_gui4graph.ui.marker_panel import MarkerPanel


class MarkerPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_marker_panel_adds_and_removes_markers(self):
        store = MarkerStore()
        panel = MarkerPanel()
        panel.refresh(store)

        marker = panel.add_marker(1.25, "start", "note")
        self.assertEqual(marker.name, "start")
        self.assertEqual(panel._list.count(), 1)

        self.assertTrue(panel.remove_marker(marker.id))
        self.assertEqual(panel._list.count(), 0)


if __name__ == "__main__":
    unittest.main()
