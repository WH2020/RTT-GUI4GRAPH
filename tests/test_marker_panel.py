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

    def test_added_marker_is_selected_and_selected_delete_emits_change(self):
        store = MarkerStore()
        panel = MarkerPanel()
        panel.refresh(store)
        changes = []
        panel.markers_changed.connect(lambda: changes.append(True))

        marker = panel.add_marker(2.5, "custom", "offline")

        self.assertEqual(panel._list.currentRow(), 0)
        self.assertTrue(panel.remove_selected_marker())
        self.assertEqual(store.markers(), [])
        self.assertTrue(changes)

    def test_marker_can_be_renamed_with_custom_note(self):
        store = MarkerStore()
        panel = MarkerPanel()
        panel.refresh(store)
        marker = panel.add_marker(1.0, "old", "old note")

        self.assertTrue(panel.edit_marker(marker.id, "new label", "new note"))

        self.assertEqual(store.markers()[0].name, "new label")
        self.assertEqual(store.markers()[0].note, "new note")


if __name__ == "__main__":
    unittest.main()
