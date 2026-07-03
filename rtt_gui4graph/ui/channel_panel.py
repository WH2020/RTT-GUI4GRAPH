from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from rtt_gui4graph.core.channels import ChannelRegistry


class ChannelPanel(QWidget):
    channel_enabled_changed = Signal(str, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: dict[str, QListWidgetItem] = {}
        self._updating = False
        self._list = QListWidget()
        self._list.itemChanged.connect(self._on_item_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._list)

    def refresh(self, registry: ChannelRegistry) -> None:
        self._updating = True
        try:
            for channel in registry.channels():
                item = self._items.get(channel.key)
                if item is None:
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, channel.key)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self._items[channel.key] = item
                    self._list.addItem(item)
                latest = "" if channel.latest_value is None else str(channel.latest_value)
                item.setText(f"{channel.key} [{channel.kind.value}]  {latest}")
                item.setCheckState(Qt.Checked if channel.enabled else Qt.Unchecked)
        finally:
            self._updating = False

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating:
            return
        key = item.data(Qt.UserRole)
        self.channel_enabled_changed.emit(key, item.checkState() == Qt.Checked)
