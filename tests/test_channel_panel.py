import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.records import Sample
from rtt_gui4graph.ui.channel_panel import ChannelPanel


class ChannelPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_refresh_removes_channels_missing_from_new_registry(self):
        first = ChannelRegistry()
        first.ingest(Sample("TAP.old", 1.0, 1.0, ""))
        second = ChannelRegistry()
        second.ingest(Sample("TAP.new", 1.0, 2.0, ""))
        panel = ChannelPanel()

        panel.refresh(first)
        panel.refresh(second)

        self.assertEqual(panel._list.count(), 1)
        self.assertIn("TAP.new", panel._list.item(0).text())


if __name__ == "__main__":
    unittest.main()
