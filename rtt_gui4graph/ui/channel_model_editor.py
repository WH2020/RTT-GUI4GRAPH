from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rtt_gui4graph.core.channels import ChannelRegistry


class ChannelModelEditor(QWidget):
    HEADERS = ["Key", "Name", "Unit", "Scale", "Offset", "Target", "Plot"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._registry: ChannelRegistry | None = None
        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._table)

    def refresh(self, registry: ChannelRegistry) -> None:
        self._registry = registry
        channels = registry.channels()
        self._table.setRowCount(len(channels))
        for row, channel in enumerate(channels):
            values = [
                channel.key,
                channel.display_name,
                channel.unit,
                f"{channel.scale:g}",
                f"{channel.offset:g}",
                channel.target,
                "yes" if channel.enabled else "no",
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))

    def update_channel(self, key: str, **config) -> bool:
        if self._registry is None:
            return False
        try:
            self._registry.set_channel_config(key, **config)
        except KeyError:
            return False
        self.refresh(self._registry)
        return True
