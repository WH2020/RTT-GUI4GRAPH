from __future__ import annotations

from typing import Any

from ..link_base import Field, LinkBase, LinkState, register_link


class UartLink(LinkBase):
    def __init__(self) -> None:
        super().__init__()
        self._serial: Any = None

    @classmethod
    def config_fields(cls) -> list[Field]:
        return [
            Field("port", "Port", "str", "COM1", True),
            Field("baudrate", "Baudrate", "int", 115200, True),
            Field("bytesize", "Data Bits", "choice", 8, True, (5, 6, 7, 8)),
            Field("parity", "Parity", "choice", "N", True, ("N", "E", "O", "M", "S")),
            Field("stopbits", "Stop Bits", "choice", 1, True, (1, 1.5, 2)),
            Field("timeout_ms", "Read Timeout (ms)", "int", 10, True),
            Field("write_timeout_ms", "Write Timeout (ms)", "int", 100, True),
        ]

    def open(self, config: dict[str, Any]) -> None:
        try:
            import serial
        except ModuleNotFoundError as exc:
            self.state_changed.emit(LinkState.ERROR, "pyserial is not installed")
            raise RuntimeError("pyserial is not installed") from exc

        port = str(config.get("port", "COM1") or "").strip()
        if not port:
            raise RuntimeError("UART port is required")

        self.state_changed.emit(LinkState.CONNECTING, f"opening UART {port}")
        self._serial = serial.Serial(
            port=port,
            baudrate=int(config.get("baudrate", 115200) or 115200),
            bytesize=self._bytesize(serial, config.get("bytesize", 8)),
            parity=self._parity(serial, config.get("parity", "N")),
            stopbits=self._stopbits(serial, config.get("stopbits", 1)),
            timeout=self._milliseconds(config.get("timeout_ms", 10)),
            write_timeout=self._milliseconds(config.get("write_timeout_ms", 100)),
        )
        self.state_changed.emit(LinkState.CONNECTED, f"UART connected: {port}")

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None
        self.state_changed.emit(LinkState.CLOSED, "UART closed")

    def read(self, max_bytes: int) -> bytes:
        if self._serial is None:
            return b""
        data = self._serial.read(max_bytes)
        if isinstance(data, bytes):
            return data
        return bytes(data)

    def send(self, data: bytes) -> int:
        if self._serial is None:
            return 0
        return int(self._serial.write(data))

    @staticmethod
    def _milliseconds(value: Any) -> float:
        return max(0, int(value or 0)) / 1000.0

    @staticmethod
    def _bytesize(serial: Any, value: Any) -> Any:
        mapping = {
            5: serial.FIVEBITS,
            6: serial.SIXBITS,
            7: serial.SEVENBITS,
            8: serial.EIGHTBITS,
        }
        try:
            return mapping[int(value)]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"unsupported UART data bits: {value}") from exc

    @staticmethod
    def _parity(serial: Any, value: Any) -> Any:
        mapping = {
            "N": serial.PARITY_NONE,
            "E": serial.PARITY_EVEN,
            "O": serial.PARITY_ODD,
            "M": serial.PARITY_MARK,
            "S": serial.PARITY_SPACE,
        }
        key = str(value or "N").upper()
        try:
            return mapping[key]
        except KeyError as exc:
            raise RuntimeError(f"unsupported UART parity: {value}") from exc

    @staticmethod
    def _stopbits(serial: Any, value: Any) -> Any:
        mapping = {
            1.0: serial.STOPBITS_ONE,
            1.5: serial.STOPBITS_ONE_POINT_FIVE,
            2.0: serial.STOPBITS_TWO,
        }
        try:
            return mapping[float(value)]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"unsupported UART stop bits: {value}") from exc


register_link("uart", UartLink)
