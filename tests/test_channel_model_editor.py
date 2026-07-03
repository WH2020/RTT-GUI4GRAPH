import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.records import Sample
from rtt_gui4graph.ui.channel_model_editor import ChannelModelEditor


class ChannelModelEditorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_editor_updates_channel_config(self):
        registry = ChannelRegistry()
        registry.ingest(Sample("TAP.x", 1.0, 2.0, ""))
        editor = ChannelModelEditor()
        editor.refresh(registry)

        self.assertTrue(
            editor.update_channel(
                "TAP.x",
                display_name="Wrist",
                unit="dps",
                scale=2.0,
                offset=1.0,
                target="status",
                enabled=True,
            )
        )

        channel = registry.channel("TAP.x")
        self.assertEqual(channel.display_name, "Wrist")
        self.assertEqual(channel.unit, "dps")
        self.assertEqual(channel.scale, 2.0)
        self.assertEqual(channel.offset, 1.0)
        self.assertEqual(channel.target, "status")
        self.assertTrue(channel.enabled)


if __name__ == "__main__":
    unittest.main()
