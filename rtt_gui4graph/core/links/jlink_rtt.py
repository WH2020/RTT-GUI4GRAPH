from __future__ import annotations

from typing import Any

from ..link_base import Field, LinkBase, LinkState, register_link


class JLinkRttLink(LinkBase):
    def __init__(self) -> None:
        super().__init__()
        self._jlink: Any = None
        self._up_buffer = 0
        self._down_buffer = 0

    @classmethod
    def config_fields(cls) -> list[Field]:
        return [
            Field("serial_no", "Serial No.", "str", ""),
            Field("device", "Device", "str", "Cortex-M", True),
            Field("interface", "Interface", "choice", "SWD", True, ("SWD", "JTAG")),
            Field("speed_khz", "Speed (kHz)", "int", 4000, True),
            Field("up_buffer", "RTT Up Buffer", "int", 0, True),
            Field("down_buffer", "RTT Down Buffer", "int", 0, True),
        ]

    def open(self, config: dict[str, Any]) -> None:
        try:
            import pylink
        except ModuleNotFoundError as exc:
            self.state_changed.emit(LinkState.ERROR, "pylink-square is not installed")
            raise RuntimeError("pylink-square is not installed") from exc

        self.state_changed.emit(LinkState.CONNECTING, "opening J-Link")
        self._up_buffer = int(config.get("up_buffer", 0) or 0)
        self._down_buffer = int(config.get("down_buffer", 0) or 0)
        interface_name = str(config.get("interface", "SWD") or "SWD").upper()
        serial_no = str(config.get("serial_no", "") or "").strip()
        device = str(config.get("device", "Cortex-M") or "Cortex-M")
        speed_khz = int(config.get("speed_khz", 4000) or 4000)

        self._jlink = pylink.JLink()
        if serial_no:
            self._jlink.open(serial_no=int(serial_no))
        else:
            self._jlink.open()
        if hasattr(pylink, "JLinkInterfaces"):
            interface = getattr(pylink.JLinkInterfaces, interface_name)
            self._jlink.set_tif(interface)
        self._jlink.connect(device, speed=speed_khz)
        self._jlink.rtt_start()
        self.state_changed.emit(LinkState.CONNECTED, "J-Link RTT connected")

    def close(self) -> None:
        if self._jlink is not None:
            try:
                self._jlink.rtt_stop()
                self._jlink.close()
            finally:
                self._jlink = None
        self.state_changed.emit(LinkState.CLOSED, "J-Link closed")

    def read(self, max_bytes: int) -> bytes:
        if self._jlink is None:
            return b""
        data = self._jlink.rtt_read(self._up_buffer, max_bytes)
        if isinstance(data, bytes):
            return data
        return bytes(data)

    def send(self, data: bytes) -> int:
        if self._jlink is None:
            return 0
        return int(self._jlink.rtt_write(self._down_buffer, list(data)))


register_link("jlink-rtt", JLinkRttLink)
