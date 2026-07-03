from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from rtt_gui4graph.core.channels import ChannelRegistry


class PlotWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.addLegend(offset=(8, 8))
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.setLabel("left", "Value")
        self._curves: dict[str, pg.PlotDataItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)

    def refresh(self, registry: ChannelRegistry) -> None:
        enabled = {channel.key for channel in registry.enabled_channels()}
        for key in list(self._curves):
            if key not in enabled:
                self._plot.removeItem(self._curves.pop(key))

        for index, channel in enumerate(registry.enabled_channels()):
            times, values = channel.series()
            curve = self._curves.get(channel.key)
            if curve is None:
                pen = pg.mkPen(pg.intColor(index, hues=12), width=1.5)
                curve = self._plot.plot(name=channel.key, pen=pen)
                self._curves[channel.key] = curve
            curve.setData(times, values)
