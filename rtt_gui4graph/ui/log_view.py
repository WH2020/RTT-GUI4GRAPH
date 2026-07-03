from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

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
        self._clear_button = QPushButton("Clear")
        self._clear_button.setToolTip("Clear the current log tab")
        self._clear_button.clicked.connect(self._clear_current_tab)
        self._auto_scroll = QCheckBox("Auto-scroll")
        self._auto_scroll.setToolTip("Scroll to the newest entry as logs arrive")
        self._auto_scroll.setChecked(True)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 6, 6, 0)
        toolbar.addWidget(self._clear_button)
        toolbar.addWidget(self._auto_scroll)
        toolbar.addStretch(1)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._logs, "Log")
        self._tabs.addTab(self._issues, "Parse Issues")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar)
        layout.addWidget(self._tabs)

    def append_log(self, record: LogLine) -> None:
        self.append_logs([record])

    def append_logs(self, records: list[LogLine]) -> None:
        self._append_lines(
            self._logs,
            [
                f"{record.t:10.3f} T{record.terminal}: {record.text}"
                for record in records
            ],
        )

    def append_issue(self, issue: ParseIssue) -> None:
        self.append_issues([issue])

    def append_issues(self, issues: list[ParseIssue]) -> None:
        self._append_lines(
            self._issues,
            [
                f"{issue.t:10.3f} {issue.severity} {issue.reason} {issue.key or '-'}: {issue.sample_text}"
                for issue in issues
            ],
        )

    def _append_text(self, editor: QPlainTextEdit, text: str) -> None:
        self._append_lines(editor, [text])

    def _append_lines(self, editor: QPlainTextEdit, lines: list[str]) -> None:
        if not lines:
            return
        scrollbar = editor.verticalScrollBar()
        previous_value = scrollbar.value()
        editor.appendPlainText("\n".join(lines))
        if self._auto_scroll.isChecked():
            editor.moveCursor(QTextCursor.End)
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(previous_value)

    def _clear_current_tab(self) -> None:
        current = self._tabs.currentWidget()
        if isinstance(current, QPlainTextEdit):
            current.clear()
