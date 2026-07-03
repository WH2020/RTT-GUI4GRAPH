import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.link_base import LinkBase, register_link
from rtt_gui4graph.ui.main_window import MainWindow


class FailingLink(LinkBase):
    def open(self, config):
        raise RuntimeError("open failed for test")

    def close(self):
        return None

    def read(self, max_bytes):
        return b""

    def send(self, data):
        return 0


class FailingOpenAndCloseLink(FailingLink):
    def close(self):
        raise RuntimeError("close failed for test")


class MainWindowConnectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])
        register_link("failing-test", FailingLink)
        register_link("failing-close-test", FailingOpenAndCloseLink)

    def test_failed_connection_clears_worker_so_user_can_retry(self):
        window = MainWindow()
        try:
            window._transport.setCurrentText("failing-test")
            window.connect_link(prompt=False)

            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and window._worker is not None:
                self._app.processEvents()
                time.sleep(0.01)

            self.assertIsNone(window._worker)
            self.assertIsNone(window._thread)
            self.assertTrue(window._connect.isEnabled())
            self.assertFalse(window._disconnect.isEnabled())
        finally:
            window.disconnect_link()
            window.close()

    def test_failed_connection_clears_worker_even_when_close_fails(self):
        window = MainWindow()
        try:
            window._transport.setCurrentText("failing-close-test")
            window.connect_link(prompt=False)

            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and window._worker is not None:
                self._app.processEvents()
                time.sleep(0.01)

            self.assertIsNone(window._worker)
            self.assertIsNone(window._thread)
            self.assertTrue(window._connect.isEnabled())
        finally:
            window.disconnect_link()
            window.close()


if __name__ == "__main__":
    unittest.main()
