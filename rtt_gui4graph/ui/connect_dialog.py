from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rtt_gui4graph.core.link_base import Field


def default_config_from_fields(fields: list[Field]) -> dict[str, Any]:
    return {field.name: field.default for field in fields}


class ConnectDialog(QDialog):
    def __init__(
        self,
        link_name: str,
        fields: list[Field],
        initial_config: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Connect: {link_name}")
        self._fields = fields
        self._widgets: dict[str, QWidget] = {}
        initial_config = initial_config or {}

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        for field in fields:
            value = initial_config.get(field.name, field.default)
            widget = self._make_widget(field, value)
            self._widgets[field.name] = widget
            label = f"{field.label} *" if field.required else field.label
            form.addRow(label, widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def config(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field in self._fields:
            widget = self._widgets[field.name]
            if isinstance(widget, QLineEdit):
                result[field.name] = widget.text()
            elif isinstance(widget, QSpinBox):
                result[field.name] = widget.value()
            elif isinstance(widget, QComboBox):
                result[field.name] = widget.currentData()
            elif isinstance(widget, QCheckBox):
                result[field.name] = widget.isChecked()
            else:
                raise TypeError(f"unsupported widget for field {field.name}")
        return result

    def _make_widget(self, field: Field, value: Any) -> QWidget:
        if field.field_type == "int":
            widget = QSpinBox()
            widget.setRange(0, 1_000_000_000)
            widget.setValue(int(value or 0))
            return widget
        if field.field_type == "choice":
            widget = QComboBox()
            choices = field.choices or ((value,) if value is not None else ())
            for choice in choices:
                widget.addItem(str(choice), choice)
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
            return widget
        if field.field_type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.setLayoutDirection(Qt.RightToLeft)
            return widget
        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        return widget
