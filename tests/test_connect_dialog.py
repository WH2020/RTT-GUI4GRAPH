import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.link_base import Field
from rtt_gui4graph.ui.connect_dialog import ConnectDialog, default_config_from_fields


class ConnectDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_defaults_are_returned_with_declared_types(self):
        dialog = ConnectDialog(
            "jlink-rtt",
            [
                Field("serial_no", "Serial No.", "str", ""),
                Field("device", "Device", "str", "STM32F407VG", True),
                Field("interface", "Interface", "choice", "SWD", True, ("SWD", "JTAG")),
                Field("speed_khz", "Speed (kHz)", "int", 4000, True),
                Field("auto_start", "Auto Start RTT", "bool", True),
            ],
        )

        self.assertEqual(
            dialog.config(),
            {
                "serial_no": "",
                "device": "STM32F407VG",
                "interface": "SWD",
                "speed_khz": 4000,
                "auto_start": True,
            },
        )

    def test_initial_config_overrides_defaults(self):
        dialog = ConnectDialog(
            "jlink-rtt",
            [
                Field("device", "Device", "str", "Cortex-M", True),
                Field("speed_khz", "Speed (kHz)", "int", 4000, True),
            ],
            initial_config={"device": "STM32H743ZI", "speed_khz": 8000},
        )

        self.assertEqual(dialog.config()["device"], "STM32H743ZI")
        self.assertEqual(dialog.config()["speed_khz"], 8000)

    def test_default_config_from_fields(self):
        config = default_config_from_fields(
            [
                Field("device", "Device", "str", "Cortex-M", True),
                Field("speed_khz", "Speed (kHz)", "int", 4000, True),
            ]
        )

        self.assertEqual(config, {"device": "Cortex-M", "speed_khz": 4000})


if __name__ == "__main__":
    unittest.main()
