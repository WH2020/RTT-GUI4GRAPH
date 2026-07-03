import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.records import LogLine, ParseIssue
from rtt_gui4graph.ui.log_view import LogView


class LogViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_clear_button_clears_only_current_tab(self):
        view = LogView()
        view.append_log(LogLine(terminal=0, t=1.0, text="line one"))
        view.append_issue(
            ParseIssue(
                t=2.0,
                severity="warning",
                key="TAP.x",
                reason="TYPE_CONFLICT",
                sample_text="TAP x=RUN",
            )
        )

        view._tabs.setCurrentWidget(view._logs)
        view._clear_button.click()

        self.assertEqual(view._logs.toPlainText(), "")
        self.assertIn("TYPE_CONFLICT", view._issues.toPlainText())

    def test_auto_scroll_disabled_preserves_scroll_position(self):
        view = LogView()
        view.resize(480, 180)
        view.show()
        self._app.processEvents()
        for index in range(100):
            view.append_log(LogLine(terminal=0, t=float(index), text=f"line {index}"))
        self._app.processEvents()

        scrollbar = view._logs.verticalScrollBar()
        self.assertGreater(scrollbar.maximum(), 0)
        scrollbar.setValue(0)
        view._auto_scroll.setChecked(False)
        view.append_log(LogLine(terminal=0, t=200.0, text="new line"))
        self._app.processEvents()

        self.assertEqual(scrollbar.value(), 0)

    def test_auto_scroll_enabled_scrolls_to_bottom(self):
        view = LogView()
        view.resize(480, 180)
        view.show()
        self._app.processEvents()
        for index in range(100):
            view.append_log(LogLine(terminal=0, t=float(index), text=f"line {index}"))
        self._app.processEvents()

        scrollbar = view._logs.verticalScrollBar()
        scrollbar.setValue(0)
        view._auto_scroll.setChecked(True)
        view.append_log(LogLine(terminal=0, t=200.0, text="new line"))
        self._app.processEvents()

        self.assertEqual(scrollbar.value(), scrollbar.maximum())


if __name__ == "__main__":
    unittest.main()
