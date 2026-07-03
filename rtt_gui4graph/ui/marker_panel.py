from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from rtt_gui4graph.core.markers import Marker, MarkerStore


class MarkerDialog(QDialog):
    def __init__(
        self,
        parent=None,
        name: str = "",
        note: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Marker")
        self._name = QLineEdit(name)
        self._name.setPlaceholderText("label")
        self._note = QLineEdit(note)
        self._note.setPlaceholderText("note")

        form = QFormLayout()
        form.addRow("Label", self._name)
        form.addRow("Note", self._note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def marker_text(self) -> tuple[str, str]:
        return self._name.text().strip(), self._note.text()


class MarkerPanel(QWidget):
    markers_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._store = MarkerStore()
        self._list = QListWidget()
        self._add = QPushButton("Add")
        self._edit = QPushButton("Edit")
        self._remove = QPushButton("Delete")
        self._add.clicked.connect(self._add_clicked)
        self._edit.clicked.connect(self._edit_selected)
        self._remove.clicked.connect(self.remove_selected_marker)

        row = QHBoxLayout()
        row.addWidget(self._add)
        row.addWidget(self._edit)
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
        self._select_marker(marker.id)
        self.markers_changed.emit()
        return marker

    def remove_marker(self, marker_id: int) -> bool:
        removed = self._store.remove(marker_id)
        if removed:
            self.refresh(self._store)
            self.markers_changed.emit()
        return removed

    def edit_marker(self, marker_id: int, name: str, note: str) -> bool:
        renamed = self._store.rename(marker_id, name)
        noted = self._store.update_note(marker_id, note)
        if renamed or noted:
            self.refresh(self._store)
            self._select_marker(marker_id)
            self.markers_changed.emit()
            return True
        return False

    def remove_selected_marker(self) -> bool:
        item = self._list.currentItem()
        if item is None:
            return False
        return self.remove_marker(int(item.data(Qt.UserRole)))

    def _add_clicked(self) -> None:
        dialog = MarkerDialog(self, f"marker {len(self._store.markers()) + 1}", "")
        if dialog.exec() == QDialog.Accepted:
            name, note = dialog.marker_text()
            self.add_marker(0.0, name, note)

    def _edit_selected(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        marker_id = int(item.data(Qt.UserRole))
        marker = next(
            (
                candidate
                for candidate in self._store.markers()
                if candidate.id == marker_id
            ),
            None,
        )
        if marker is None:
            return
        dialog = MarkerDialog(self, marker.name, marker.note)
        if dialog.exec() == QDialog.Accepted:
            name, note = dialog.marker_text()
            self.edit_marker(marker.id, name, note)

    def _select_marker(self, marker_id: int) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if int(item.data(Qt.UserRole)) == marker_id:
                self._list.setCurrentRow(row)
                return
