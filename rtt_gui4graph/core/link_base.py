from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    from PySide6.QtCore import QObject, Signal
except ModuleNotFoundError:  # Core tests can run without Qt installed.
    class _DummySignal:
        def connect(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def emit(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    def Signal(*_args: Any, **_kwargs: Any) -> _DummySignal:
        return _DummySignal()

    class QObject:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            super().__init__()


class LinkState(str, Enum):
    CLOSED = "closed"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    field_type: str
    default: Any = None
    required: bool = False
    choices: tuple[Any, ...] = ()


LINKS: dict[str, type["LinkBase"]] = {}


class LinkBase(QObject):
    state_changed = Signal(object, str)

    def open(self, config: dict[str, Any]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def read(self, max_bytes: int) -> bytes:
        raise NotImplementedError

    def send(self, data: bytes) -> int:
        raise NotImplementedError

    @classmethod
    def config_fields(cls) -> list[Field]:
        return []


def register_link(name: str, link_cls: type[LinkBase]) -> None:
    LINKS[name] = link_cls


def create_link(name: str) -> LinkBase:
    try:
        link_cls = LINKS[name]
    except KeyError as exc:
        raise KeyError(f"unknown link: {name}") from exc
    return link_cls()
