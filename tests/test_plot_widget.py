import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.records import Sample
from rtt_gui4graph.ui.plot_widget import PlotWidget


class PlotWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_enabled_channel_times_are_plotted_relative_to_first_sample(self):
        registry = ChannelRegistry()
        registry.ingest(Sample("TAP.wr_dps", 105_917.4, 3.0, ""))
        registry.ingest(Sample("TAP.wr_dps", 105_918.9, -2.0, ""))
        registry.set_enabled("TAP.wr_dps", True)

        widget = PlotWidget()
        widget.refresh(registry)

        curve = widget._curves["TAP.wr_dps"]
        x_data, y_data = curve.getData()
        self.assertEqual(x_data.tolist(), [0.0, 1.5])
        self.assertEqual(y_data.tolist(), [3.0, -2.0])


if __name__ == "__main__":
    unittest.main()
