import sys
import types
import unittest
from unittest.mock import patch

from rtt_gui4graph.core.link_base import LINKS
from rtt_gui4graph.core.links import UartLink


class FakeSerialPort:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        self.read_calls = []
        self.write_calls = []
        self.read_buffer = b"abc"
        FakeSerialPort.instances.append(self)

    def read(self, size):
        self.read_calls.append(size)
        data = self.read_buffer[:size]
        self.read_buffer = self.read_buffer[size:]
        return data

    def write(self, data):
        self.write_calls.append(bytes(data))
        return len(data)

    def close(self):
        self.closed = True


def fake_serial_module():
    FakeSerialPort.instances.clear()
    return types.SimpleNamespace(
        Serial=FakeSerialPort,
        FIVEBITS=5,
        SIXBITS=6,
        SEVENBITS=7,
        EIGHTBITS=8,
        PARITY_NONE="N",
        PARITY_EVEN="E",
        PARITY_ODD="O",
        PARITY_MARK="M",
        PARITY_SPACE="S",
        STOPBITS_ONE=1,
        STOPBITS_ONE_POINT_FIVE=1.5,
        STOPBITS_TWO=2,
    )


class UartLinkTest(unittest.TestCase):
    def test_link_is_registered(self):
        self.assertIs(LINKS["uart"], UartLink)

    def test_config_fields_cover_common_uart_settings(self):
        fields = {field.name: field for field in UartLink.config_fields()}

        self.assertEqual(fields["port"].default, "COM1")
        self.assertEqual(fields["baudrate"].default, 115200)
        self.assertEqual(fields["bytesize"].choices, (5, 6, 7, 8))
        self.assertEqual(fields["parity"].choices, ("N", "E", "O", "M", "S"))
        self.assertEqual(fields["stopbits"].choices, (1, 1.5, 2))
        self.assertEqual(fields["timeout_ms"].default, 10)
        self.assertEqual(fields["write_timeout_ms"].default, 100)

    def test_open_maps_config_to_pyserial(self):
        with patch.dict(sys.modules, {"serial": fake_serial_module()}):
            link = UartLink()
            link.open(
                {
                    "port": "COM7",
                    "baudrate": 921600,
                    "bytesize": 8,
                    "parity": "E",
                    "stopbits": 2,
                    "timeout_ms": 25,
                    "write_timeout_ms": 250,
                }
            )

        fake = FakeSerialPort.instances[0]
        self.assertEqual(
            fake.kwargs,
            {
                "port": "COM7",
                "baudrate": 921600,
                "bytesize": 8,
                "parity": "E",
                "stopbits": 2,
                "timeout": 0.025,
                "write_timeout": 0.25,
            },
        )

    def test_read_send_and_close_use_serial_port(self):
        with patch.dict(sys.modules, {"serial": fake_serial_module()}):
            link = UartLink()
            link.open({"port": "COM3"})
            self.assertEqual(link.read(2), b"ab")
            self.assertEqual(link.send(b"cmd\n"), 4)
            link.close()

        fake = FakeSerialPort.instances[0]
        self.assertEqual(fake.read_calls, [2])
        self.assertEqual(fake.write_calls, [b"cmd\n"])
        self.assertTrue(fake.closed)

    def test_missing_pyserial_reports_clear_error(self):
        with patch.dict(sys.modules, {"serial": None}):
            with self.assertRaisesRegex(RuntimeError, "pyserial"):
                UartLink().open({"port": "COM1"})


if __name__ == "__main__":
    unittest.main()
