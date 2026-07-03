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

    def test_plot_uses_recent_window_and_point_limit(self):
        registry = ChannelRegistry()
        for i in range(100):
            registry.ingest(Sample("TAP.wr_dps", 1_000.0 + i, float(i), ""))
        registry.set_enabled("TAP.wr_dps", True)

        widget = PlotWidget(window_seconds=10.0, max_points_per_curve=5)
        widget.refresh(registry)

        x_data, y_data = widget._curves["TAP.wr_dps"].getData()
        self.assertEqual(x_data.tolist(), [6.0, 7.0, 8.0, 9.0, 10.0])
        self.assertEqual(y_data.tolist(), [95.0, 96.0, 97.0, 98.0, 99.0])


if __name__ == "__main__":
    unittest.main()
