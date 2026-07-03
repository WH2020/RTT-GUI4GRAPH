from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SendPanel(QWidget):
    send_requested = Signal(bytes)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._input = QLineEdit()
        self._input.setPlaceholderText("raw command")
        self._hex = QCheckBox("hex")
        self._ending = QComboBox()
        self._ending.addItem("\\n", b"\n")
        self._ending.addItem("\\r\\n", b"\r\n")
        self._ending.addItem("none", b"")
        self._send = QPushButton("Send")
        self._status = QLabel("")
        self._send.clicked.connect(self._on_send)
        self._input.returnPressed.connect(self._on_send)

        row = QHBoxLayout()
        row.addWidget(self._input, 1)
        row.addWidget(self._hex)
        row.addWidget(self._ending)
        row.addWidget(self._send)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(row)
        layout.addWidget(self._status)

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def _on_send(self) -> None:
        text = self._input.text()
        try:
            if self._hex.isChecked():
                compact = "".join(text.split())
                data = bytes.fromhex(compact)
            else:
                data = text.encode("utf-8") + self._ending.currentData()
        except ValueError as exc:
            self.set_status(f"invalid hex: {exc}")
            return
        self.send_requested.emit(data)
        self.set_status(f"queued {len(data)} bytes")
