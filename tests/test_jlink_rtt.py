import sys
import types
import unittest
from unittest.mock import patch

from rtt_gui4graph.core.links.jlink_rtt import JLinkRttLink


class FakeJLink:
    instances = []

    def __init__(self):
        self.calls = []
        FakeJLink.instances.append(self)

    def open(self, **kwargs):
        self.calls.append(("open", kwargs))

    def set_script_file(self, path):
        self.calls.append(("set_script_file", path))

    def set_tif(self, interface):
        self.calls.append(("set_tif", interface))

    def connect(self, device, speed):
        self.calls.append(("connect", device, speed))

    def restart(self):
        self.calls.append(("restart",))

    def rtt_start(self, block_address=None):
        self.calls.append(("rtt_start", block_address))

    def rtt_stop(self):
        self.calls.append(("rtt_stop",))

    def close(self):
        self.calls.append(("close",))


class FakeRttStopFailJLink(FakeJLink):
    def rtt_stop(self):
        self.calls.append(("rtt_stop",))
        raise RuntimeError("rtt stop failed")


def fake_pylink_module():
    FakeJLink.instances.clear()
    return types.SimpleNamespace(
        JLink=FakeJLink,
        JLinkInterfaces=types.SimpleNamespace(SWD="SWD_IF", JTAG="JTAG_IF"),
    )


class JLinkRttLinkTest(unittest.TestCase):
    def test_config_fields_cover_rtt_viewer_connection_options(self):
        fields = {field.name: field for field in JLinkRttLink.config_fields()}

        self.assertEqual(fields["connection_mode"].choices, ("USB", "TCP/IP", "Existing Session"))
        self.assertEqual(fields["connection_mode"].default, "USB")
        self.assertEqual(fields["device"].default, "NRF54L15_M33")
        self.assertIn("use_serial_no", fields)
        self.assertIn("force_go", fields)
        self.assertIn("script_file", fields)
        self.assertEqual(fields["interface"].choices, ("SWD", "JTAG"))
        self.assertEqual(fields["speed_khz"].default, 4000)
        self.assertEqual(
            fields["rtt_control_block"].choices,
            ("Auto Detection", "Address", "Search Range"),
        )

    def test_usb_serial_script_force_go_and_fixed_rtt_address(self):
        with patch.dict(sys.modules, {"pylink": fake_pylink_module()}):
            link = JLinkRttLink()
            link.open(
                {
                    "connection_mode": "USB",
                    "use_serial_no": True,
                    "serial_no": "123456",
                    "device": "NRF54L15_M33",
                    "interface": "SWD",
                    "speed_khz": 4000,
                    "script_file": "C:/probe/init.jlink",
                    "force_go": True,
                    "rtt_control_block": "Address",
                    "rtt_block_address": "0x20000000",
                }
            )

        fake = FakeJLink.instances[0]
        self.assertEqual(fake.calls[0], ("open", {"serial_no": 123456}))
        self.assertIn(("set_script_file", "C:/probe/init.jlink"), fake.calls)
        self.assertIn(("set_tif", "SWD_IF"), fake.calls)
        self.assertIn(("connect", "NRF54L15_M33", 4000), fake.calls)
        self.assertIn(("restart",), fake.calls)
        self.assertIn(("rtt_start", 0x20000000), fake.calls)

    def test_tcp_ip_connection_uses_host_and_port(self):
        with patch.dict(sys.modules, {"pylink": fake_pylink_module()}):
            link = JLinkRttLink()
            link.open(
                {
                    "connection_mode": "TCP/IP",
                    "ip_address": "192.168.1.50",
                    "ip_port": 19020,
                    "device": "NRF54L15_M33",
                    "interface": "SWD",
                    "speed_khz": 4000,
                    "rtt_control_block": "Auto Detection",
                }
            )

        fake = FakeJLink.instances[0]
        self.assertEqual(fake.calls[0], ("open", {"ip_addr": "192.168.1.50:19020"}))
        self.assertIn(("rtt_start", None), fake.calls)

    def test_existing_session_reports_clear_error(self):
        with patch.dict(sys.modules, {"pylink": fake_pylink_module()}):
            with self.assertRaisesRegex(RuntimeError, "Existing Session"):
                JLinkRttLink().open({"connection_mode": "Existing Session"})

    def test_search_range_reports_clear_error(self):
        with patch.dict(sys.modules, {"pylink": fake_pylink_module()}):
            with self.assertRaisesRegex(RuntimeError, "Search Range"):
                JLinkRttLink().open(
                    {
                        "connection_mode": "USB",
                        "device": "NRF54L15_M33",
                        "interface": "SWD",
                        "speed_khz": 4000,
                        "rtt_control_block": "Search Range",
                    }
                )

    def test_close_continues_when_rtt_stop_fails(self):
        fake = FakeRttStopFailJLink()
        link = JLinkRttLink()
        link._jlink = fake

        link.close()

        self.assertIn(("rtt_stop",), fake.calls)
        self.assertIn(("close",), fake.calls)
        self.assertIsNone(link._jlink)


if __name__ == "__main__":
    unittest.main()
