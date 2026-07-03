from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from rtt_gui4graph.core.channels import ChannelRegistry


class PlotWidget(QWidget):
    DEFAULT_WINDOW_SECONDS = 30.0
    DEFAULT_MAX_POINTS_PER_CURVE = 5000

    def __init__(
        self,
        parent=None,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        max_points_per_curve: int = DEFAULT_MAX_POINTS_PER_CURVE,
    ) -> None:
        super().__init__(parent)
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_points_per_curve <= 0:
            raise ValueError("max_points_per_curve must be positive")
        self._window_seconds = float(window_seconds)
        self._max_points_per_curve = int(max_points_per_curve)

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
        enabled_channels = registry.enabled_channels()
        latest_time = max(
            (channel.latest_time for channel in enabled_channels if channel.latest_time is not None),
            default=None,
        )
        earliest_time = min(
            (
                channel.earliest_time
                for channel in enabled_channels
                if channel.earliest_time is not None
            ),
            default=None,
        )
        window_start = (
            latest_time - self._window_seconds if latest_time is not None else None
        )
        if latest_time is None or earliest_time is None or window_start is None:
            base_time = None
        elif earliest_time > window_start:
            base_time = earliest_time
        else:
            base_time = window_start

        series_by_key = {}
        for channel in enabled_channels:
            times, values = channel.series_arrays(
                start_time=window_start,
                max_points=self._max_points_per_curve,
            )
            series_by_key[channel.key] = (times, values)

        enabled = {channel.key for channel in enabled_channels}
        for key in list(self._curves):
            if key not in enabled:
                self._plot.removeItem(self._curves.pop(key))

        for index, channel in enumerate(enabled_channels):
            times, values = series_by_key[channel.key]
            curve = self._curves.get(channel.key)
            if curve is None:
                pen = pg.mkPen(pg.intColor(index, hues=12), width=1.5)
                curve = self._plot.plot(name=channel.key, pen=pen)
                curve.setClipToView(True)
                curve.setDownsampling(auto=True, method="peak")
                self._curves[channel.key] = curve
            if base_time is not None:
                times = times - base_time
            curve.setData(times, values)

        if latest_time is not None and base_time is not None:
            span = max(latest_time - base_time, 1e-6)
            self._plot.setXRange(0.0, span, padding=0)
