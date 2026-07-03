from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from rtt_gui4graph.core.channels import ChannelKind, ChannelRegistry
from rtt_gui4graph.core.markers import MarkerStore


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
        self._paused = False
        self._markers = MarkerStore()
        self._marker_lines: list[pg.InfiniteLine] = []

        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.addLegend(offset=(8, 8))
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.setLabel("left", "Value")
        self._status_plot = pg.PlotWidget()
        self._status_plot.showGrid(x=True, y=True, alpha=0.25)
        self._status_plot.addLegend(offset=(8, 8))
        self._status_plot.setLabel("bottom", "Time", units="s")
        self._status_plot.setLabel("left", "State")
        self._pause_button = QPushButton("Pause")
        self._pause_button.setCheckable(True)
        self._pause_button.toggled.connect(self.set_paused)
        self._window_combo = QComboBox()
        for label, seconds in (("10s", 10.0), ("30s", 30.0), ("60s", 60.0), ("All", 1e12)):
            self._window_combo.addItem(label, seconds)
        self._window_combo.setCurrentText("30s")
        self._window_combo.currentIndexChanged.connect(self._window_changed)
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._status_curves: dict[str, pg.PlotDataItem] = {}

        controls = QHBoxLayout()
        controls.setContentsMargins(6, 4, 6, 4)
        controls.addWidget(self._pause_button)
        controls.addWidget(self._window_combo)
        controls.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self._plot)
        layout.addWidget(self._status_plot)

    def set_paused(self, paused: bool) -> None:
        self._paused = bool(paused)
        self._pause_button.setChecked(self._paused)

    def is_paused(self) -> bool:
        return self._paused

    def set_window_seconds(self, seconds: float) -> None:
        if seconds <= 0:
            raise ValueError("window seconds must be positive")
        self._window_seconds = float(seconds)

    def set_markers(self, markers: MarkerStore) -> None:
        self._markers = markers

    def refresh(self, registry: ChannelRegistry) -> None:
        if self._paused:
            return
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
            times, values = channel.display_series_arrays(
                start_time=window_start,
                max_points=self._max_points_per_curve,
            )
            series_by_key[channel.key] = (times, values)

        main_enabled = {
            channel.key
            for channel in enabled_channels
            if channel.target == "main" and channel.kind == ChannelKind.NUMERIC
        }
        status_enabled = {
            channel.key
            for channel in enabled_channels
            if channel.key not in main_enabled
        }
        for key in list(self._curves):
            if key not in main_enabled:
                self._plot.removeItem(self._curves.pop(key))
        for key in list(self._status_curves):
            if key not in status_enabled:
                self._status_plot.removeItem(self._status_curves.pop(key))

        for index, channel in enumerate(enabled_channels):
            times, values = series_by_key[channel.key]
            plot = self._plot if channel.key in main_enabled else self._status_plot
            curves = self._curves if channel.key in main_enabled else self._status_curves
            curve = curves.get(channel.key)
            if curve is None:
                pen = pg.mkPen(pg.intColor(index, hues=12), width=1.5)
                curve = plot.plot(name=channel.display_name, pen=pen)
                curve.setClipToView(True)
                curve.setDownsampling(auto=True, method="peak")
                curves[channel.key] = curve
            if base_time is not None:
                times = times - base_time
            curve.setData(times, values)

        if latest_time is not None and base_time is not None:
            span = max(latest_time - base_time, 1e-6)
            self._plot.setXRange(0.0, span, padding=0)
            self._status_plot.setXRange(0.0, span, padding=0)
            self._refresh_marker_lines(base_time)

    def _window_changed(self) -> None:
        self._window_seconds = float(self._window_combo.currentData())

    def _refresh_marker_lines(self, base_time: float) -> None:
        for line in self._marker_lines:
            self._plot.removeItem(line)
            self._status_plot.removeItem(line)
        self._marker_lines = []
        for marker in self._markers.markers():
            x = marker.t - base_time
            for plot in (self._plot, self._status_plot):
                line = pg.InfiniteLine(pos=x, angle=90, pen=pg.mkPen("#f5c542", width=1))
                line.setToolTip(marker.name)
                plot.addItem(line)
                self._marker_lines.append(line)
