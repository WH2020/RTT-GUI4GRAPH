from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawLine:
    t: float
    terminal: int
    text: str
    decode_error: bool = False


@dataclass(frozen=True)
class Sample:
    channel: str
    t: float
    value: float
    raw_text: str


@dataclass(frozen=True)
class Event:
    channel: str
    t: float
    label: str
    ordinal: int
    raw_text: str


@dataclass(frozen=True)
class LogLine:
    terminal: int
    t: float
    text: str


@dataclass(frozen=True)
class ParseIssue:
    t: float
    severity: str
    key: str
    reason: str
    sample_text: str
    count: int = 1
