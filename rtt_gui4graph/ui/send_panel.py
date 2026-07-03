from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from rtt_gui4graph.core.command_sets import (
    CommandItem,
    CommandSection,
    CommandSetStore,
)


class CommandDialog(QDialog):
    def __init__(
        self,
        parent=None,
        name: str = "",
        command: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command")
        self._name = QLineEdit(name)
        self._name.setPlaceholderText("function")
        self._command = QLineEdit(command)
        self._command.setPlaceholderText("command")

        form = QFormLayout()
        form.addRow("Function", self._name)
        form.addRow("Command", self._command)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def command_item(self) -> CommandItem:
        return CommandItem(self._name.text().strip(), self._command.text())


class SendPanel(QWidget):
    send_requested = Signal(bytes)

    def __init__(
        self,
        parent=None,
        command_store: CommandSetStore | None = None,
    ) -> None:
        super().__init__(parent)
        self._command_store = command_store or CommandSetStore()
        self._command_sections = self._command_store.load()

        self._input = QLineEdit()
        self._input.setPlaceholderText("raw command")
        self._hex = QCheckBox("hex")
        self._ending = QComboBox()
        self._ending.addItem("\\n", b"\n")
        self._ending.addItem("\\r\\n", b"\r\n")
        self._ending.addItem("none", b"")
        self._send = QPushButton("Send")
        self._status = QLabel("")
        self._section_tabs = QTabWidget()
        self._add_section = QPushButton("Add Group")
        self._rename_section = QPushButton("Rename")
        self._delete_section = QPushButton("Delete Group")
        self._add_command = QPushButton("Add Command")
        self._edit_command = QPushButton("Edit")
        self._delete_command = QPushButton("Delete")
        self._fill_command = QPushButton("Fill")
        self._send_command = QPushButton("Send Command")

        self._send.clicked.connect(self._on_send)
        self._input.returnPressed.connect(self._on_send)
        self._add_section.clicked.connect(self._add_section_clicked)
        self._rename_section.clicked.connect(self._rename_section_clicked)
        self._delete_section.clicked.connect(self.delete_current_command_section)
        self._add_command.clicked.connect(self._add_command_clicked)
        self._edit_command.clicked.connect(self._edit_command_clicked)
        self._delete_command.clicked.connect(self.delete_selected_command)
        self._fill_command.clicked.connect(self.fill_selected_command)
        self._send_command.clicked.connect(self.send_selected_command)

        section_row = QHBoxLayout()
        section_row.addWidget(self._add_section)
        section_row.addWidget(self._rename_section)
        section_row.addWidget(self._delete_section)
        section_row.addStretch(1)

        command_row = QHBoxLayout()
        command_row.addWidget(self._add_command)
        command_row.addWidget(self._edit_command)
        command_row.addWidget(self._delete_command)
        command_row.addStretch(1)
        command_row.addWidget(self._fill_command)
        command_row.addWidget(self._send_command)

        row = QHBoxLayout()
        row.addWidget(self._input, 1)
        row.addWidget(self._hex)
        row.addWidget(self._ending)
        row.addWidget(self._send)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(section_row)
        layout.addWidget(self._section_tabs, 1)
        layout.addLayout(command_row)
        layout.addLayout(row)
        layout.addWidget(self._status)
        self._rebuild_command_tabs()

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def command_sections(self) -> list[CommandSection]:
        return [
            CommandSection(
                section.name,
                [
                    CommandItem(command.name, command.command)
                    for command in section.commands
                ],
            )
            for section in self._command_sections
        ]

    def add_command_section(self, name: str) -> bool:
        name = self._clean_name(name)
        if not name:
            self.set_status("group name is required")
            return False
        name = self._unique_section_name(name)
        self._command_sections.append(CommandSection(name, []))
        self._save_command_sections()
        self._rebuild_command_tabs(len(self._command_sections) - 1)
        return True

    def rename_current_command_section(self, name: str) -> bool:
        index = self._current_section_index()
        if index is None:
            return False
        name = self._clean_name(name)
        if not name:
            self.set_status("group name is required")
            return False
        self._command_sections[index].name = self._unique_section_name(name, index)
        self._save_command_sections()
        self._rebuild_command_tabs(index)
        return True

    def delete_current_command_section(self) -> bool:
        index = self._current_section_index()
        if index is None:
            return False
        if len(self._command_sections) <= 1:
            self.set_status("at least one group is required")
            return False
        del self._command_sections[index]
        self._save_command_sections()
        self._rebuild_command_tabs(max(0, index - 1))
        return True

    def add_command_to_current_section(self, name: str, command: str) -> bool:
        index = self._current_section_index()
        if index is None:
            return False
        item = CommandItem(name.strip(), command)
        if not item.name or not item.command:
            self.set_status("function and command are required")
            return False
        self._command_sections[index].commands.append(item)
        self._save_command_sections()
        self._rebuild_command_tabs(index)
        self._current_command_table().selectRow(
            len(self._command_sections[index].commands) - 1
        )
        return True

    def edit_selected_command(self, name: str, command: str) -> bool:
        index = self._current_section_index()
        row = self._selected_command_row()
        if index is None or row is None:
            return False
        item = CommandItem(name.strip(), command)
        if not item.name or not item.command:
            self.set_status("function and command are required")
            return False
        self._command_sections[index].commands[row] = item
        self._save_command_sections()
        self._rebuild_command_tabs(index)
        self._current_command_table().selectRow(row)
        return True

    def delete_selected_command(self) -> bool:
        index = self._current_section_index()
        row = self._selected_command_row()
        if index is None or row is None:
            return False
        del self._command_sections[index].commands[row]
        self._save_command_sections()
        self._rebuild_command_tabs(index)
        return True

    def fill_selected_command(self) -> bool:
        command = self._selected_command()
        if command is None:
            return False
        self._input.setText(command.command)
        return True

    def send_selected_command(self) -> bool:
        if not self.fill_selected_command():
            return False
        self._on_send()
        return True

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

    def _rebuild_command_tabs(self, current_index: int = 0) -> None:
        self._section_tabs.clear()
        for section in self._command_sections:
            table = self._create_command_table()
            table.setRowCount(len(section.commands))
            for row, command in enumerate(section.commands):
                table.setItem(row, 0, QTableWidgetItem(command.name))
                table.setItem(row, 1, QTableWidgetItem(command.command))
            self._section_tabs.addTab(table, section.name)
        if self._command_sections:
            self._section_tabs.setCurrentIndex(
                max(0, min(current_index, len(self._command_sections) - 1))
            )

    def _create_command_table(self) -> QTableWidget:
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Function", "Command"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.doubleClicked.connect(lambda _index: self.send_selected_command())
        return table

    def _save_command_sections(self) -> None:
        self._command_store.save(self._command_sections)

    def _current_section_index(self) -> int | None:
        index = self._section_tabs.currentIndex()
        if index < 0 or index >= len(self._command_sections):
            return None
        return index

    def _current_command_table(self) -> QTableWidget:
        table = self._section_tabs.currentWidget()
        if not isinstance(table, QTableWidget):
            raise RuntimeError("current command tab is not a command table")
        return table

    def _selected_command_row(self) -> int | None:
        table = self._current_command_table()
        row = table.currentRow()
        if row < 0 or row >= table.rowCount():
            self.set_status("select a command")
            return None
        return row

    def _selected_command(self) -> CommandItem | None:
        section_index = self._current_section_index()
        row = self._selected_command_row()
        if section_index is None or row is None:
            return None
        return self._command_sections[section_index].commands[row]

    def _add_section_clicked(self) -> None:
        name, accepted = QInputDialog.getText(self, "Add Group", "Group name")
        if accepted:
            self.add_command_section(name)

    def _rename_section_clicked(self) -> None:
        index = self._current_section_index()
        if index is None:
            return
        name, accepted = QInputDialog.getText(
            self,
            "Rename Group",
            "Group name",
            text=self._command_sections[index].name,
        )
        if accepted:
            self.rename_current_command_section(name)

    def _add_command_clicked(self) -> None:
        dialog = CommandDialog(self)
        if dialog.exec() == QDialog.Accepted:
            item = dialog.command_item()
            self.add_command_to_current_section(item.name, item.command)

    def _edit_command_clicked(self) -> None:
        command = self._selected_command()
        if command is None:
            return
        dialog = CommandDialog(self, command.name, command.command)
        if dialog.exec() == QDialog.Accepted:
            item = dialog.command_item()
            self.edit_selected_command(item.name, item.command)

    def _unique_section_name(self, name: str, current_index: int | None = None) -> str:
        used = {
            section.name
            for index, section in enumerate(self._command_sections)
            if index != current_index
        }
        if name not in used:
            return name
        suffix = 2
        while f"{name} {suffix}" in used:
            suffix += 1
        return f"{name} {suffix}"

    @staticmethod
    def _clean_name(name: str) -> str:
        return " ".join(name.split())
