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
            Field("connection_mode", "Connection", "choice", "USB", True, ("USB", "TCP/IP", "Existing Session")),
            Field("use_serial_no", "Use Serial No.", "bool", False),
            Field("serial_no", "Serial No.", "str", ""),
            Field("ip_address", "TCP/IP Address", "str", "127.0.0.1"),
            Field("ip_port", "TCP/IP Port", "int", 19020),
            Field("device", "Target Device", "str", "NRF54L15_M33", True),
            Field("force_go", "Force Go On Connect", "bool", False),
            Field("script_file", "Script File", "str", ""),
            Field("interface", "Interface", "choice", "SWD", True, ("SWD", "JTAG")),
            Field("speed_khz", "Speed (kHz)", "int", 4000, True),
            Field("rtt_control_block", "RTT Control Block", "choice", "Auto Detection", True, ("Auto Detection", "Address", "Search Range")),
            Field("rtt_block_address", "RTT Block Address", "str", ""),
            Field("rtt_search_start", "RTT Search Start", "str", ""),
            Field("rtt_search_end", "RTT Search End", "str", ""),
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
        connection_mode = str(config.get("connection_mode", "USB") or "USB")
        interface_name = str(config.get("interface", "SWD") or "SWD").upper()
        serial_no = str(config.get("serial_no", "") or "").strip()
        device = str(config.get("device", "NRF54L15_M33") or "NRF54L15_M33")
        speed_khz = int(config.get("speed_khz", 4000) or 4000)
        script_file = str(config.get("script_file", "") or "").strip()

        self._jlink = pylink.JLink()
        open_kwargs = self._open_kwargs(connection_mode, serial_no, config)
        self._jlink.open(**open_kwargs)
        if script_file:
            self._jlink.set_script_file(script_file)
        if hasattr(pylink, "JLinkInterfaces"):
            interface = getattr(pylink.JLinkInterfaces, interface_name)
            self._jlink.set_tif(interface)
        self._jlink.connect(device, speed=speed_khz)
        if bool(config.get("force_go", False)):
            self._jlink.restart()
        rtt_address = self._rtt_block_address(config)
        self._jlink.rtt_start(block_address=rtt_address)
        self.state_changed.emit(LinkState.CONNECTED, "J-Link RTT connected")

    def _open_kwargs(
        self, connection_mode: str, serial_no: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        if connection_mode == "Existing Session":
            raise RuntimeError("Existing Session is not supported by pylink-square")
        use_serial_no = bool(config.get("use_serial_no", False))
        if connection_mode == "TCP/IP":
            host = str(config.get("ip_address", "") or "").strip()
            port = int(config.get("ip_port", 19020) or 19020)
            if not host:
                raise RuntimeError("TCP/IP address is required")
            kwargs: dict[str, Any] = {"ip_addr": f"{host}:{port}"}
            if use_serial_no and serial_no:
                kwargs["serial_no"] = int(serial_no)
            return kwargs
        if use_serial_no and serial_no:
            return {"serial_no": int(serial_no)}
        return {}

    def _rtt_block_address(self, config: dict[str, Any]) -> int | None:
        mode = str(config.get("rtt_control_block", "Auto Detection") or "Auto Detection")
        if mode == "Auto Detection":
            return None
        if mode == "Search Range":
            raise RuntimeError("RTT Control Block Search Range is not supported by pylink-square")
        if mode == "Address":
            value = str(config.get("rtt_block_address", "") or "").strip()
            if not value:
                raise RuntimeError("RTT block address is required when Address mode is selected")
            return int(value, 0)
        raise RuntimeError(f"unknown RTT control block mode: {mode}")

    def close(self) -> None:
        if self._jlink is not None:
            try:
                try:
                    self._jlink.rtt_stop()
                except Exception:
                    pass
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
