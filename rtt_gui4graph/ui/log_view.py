from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget

from rtt_gui4graph.core.records import LogLine, ParseIssue


class LogView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logs = QPlainTextEdit()
        self._logs.setReadOnly(True)
        self._logs.document().setMaximumBlockCount(5000)
        self._issues = QPlainTextEdit()
        self._issues.setReadOnly(True)
        self._issues.document().setMaximumBlockCount(2000)

        tabs = QTabWidget()
        tabs.addTab(self._logs, "Log")
        tabs.addTab(self._issues, "Parse Issues")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tabs)

    def append_log(self, record: LogLine) -> None:
        self._logs.appendPlainText(f"{record.t:10.3f} T{record.terminal}: {record.text}")

    def append_issue(self, issue: ParseIssue) -> None:
        key = issue.key or "-"
        self._issues.appendPlainText(
            f"{issue.t:10.3f} {issue.severity} {issue.reason} {key}: {issue.sample_text}"
        )
