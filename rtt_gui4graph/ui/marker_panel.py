from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

from rtt_gui4graph.core.markers import Marker, MarkerStore


class MarkerPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._store = MarkerStore()
        self._list = QListWidget()
        self._remove = QPushButton("Delete")
        self._remove.clicked.connect(self._remove_selected)

        row = QHBoxLayout()
        row.addWidget(self._remove)
        row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(row)
        layout.addWidget(self._list)

    def refresh(self, store: MarkerStore) -> None:
        self._store = store
        self._list.clear()
        for marker in store.markers():
            item = QListWidgetItem(f"{marker.t:.3f}  {marker.name}  {marker.note}")
            item.setData(Qt.UserRole, marker.id)
            self._list.addItem(item)

    def add_marker(self, t: float, name: str = "marker", note: str = "") -> Marker:
        marker = self._store.add(t, name, note)
        self.refresh(self._store)
        return marker

    def remove_marker(self, marker_id: int) -> bool:
        removed = self._store.remove(marker_id)
        self.refresh(self._store)
        return removed

    def _remove_selected(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            self.remove_marker(int(item.data(Qt.UserRole)))
