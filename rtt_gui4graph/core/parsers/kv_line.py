from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..parser_base import ParserBase, ParserRecord, register_parser
from ..records import Event, LogLine, ParseIssue, RawLine, Sample

KV_RE = re.compile(r"(?P<key>\w+)=(?P<value>\S*)")
PREFIX_RE = re.compile(r"[A-Za-z_]\w*")
INT_RE = re.compile(r"^[+-]?\d+$")
FLOAT_RE = re.compile(
    r"^[+-]?(?:(?:\d+\.\d*)|(?:\.\d+)|(?:\d+))(?:[eE][+-]?\d+)$|^[+-]?(?:\d+\.\d*|\.\d+)$"
)
HEX_RE = re.compile(r"^[+-]?0[xX][0-9a-fA-F]+$")


@dataclass
class _ChannelType:
    kind: str
    labels: dict[str, int] = field(default_factory=dict)
    enum_overflow: bool = False


class KvLineParser(ParserBase):
    def __init__(self, enum_limit: int = 64) -> None:
        self._types: dict[str, _ChannelType] = {}
        self._enum_limit = enum_limit

    def parse_line(self, line: RawLine) -> list[ParserRecord]:
        records: list[ParserRecord] = [LogLine(line.terminal, line.t, line.text)]
        if line.decode_error:
            records.append(self._issue(line, "", "DECODE_ERROR"))

        matches = list(KV_RE.finditer(line.text))
        if not matches:
            return records

        prefix = self._prefix(line.text, matches[0].start())
        pairs: dict[str, str] = {}
        duplicate_keys: set[str] = set()
        empty_keys: set[str] = set()
        for match in matches:
            key = match.group("key")
            value = match.group("value")
            if key in pairs:
                duplicate_keys.add(key)
            if value == "":
                empty_keys.add(key)
            pairs[key] = value

        for key in duplicate_keys:
            records.append(self._issue(line, self._channel(prefix, key), "DUP_KEY"))
        for key in empty_keys:
            records.append(self._issue(line, self._channel(prefix, key), "EMPTY_VALUE"))

        for key, value in pairs.items():
            if value == "":
                continue
            channel = self._channel(prefix, key)
            value_kind, numeric_value = self._classify_value(value)
            if value_kind == "inf":
                records.append(self._issue(line, channel, "INF_DROPPED"))
                continue
            if value_kind == "numeric":
                self._append_numeric(records, line, channel, value, numeric_value)
            else:
                self._append_enum(records, line, channel, value)
        return records

    def _append_numeric(
        self,
        records: list[ParserRecord],
        line: RawLine,
        channel: str,
        token: str,
        value: float | None,
    ) -> None:
        state = self._types.get(channel)
        if state is None:
            self._types[channel] = _ChannelType("numeric")
            records.append(Sample(channel, line.t, float(value), line.text))
            return
        if state.kind == "numeric":
            records.append(Sample(channel, line.t, float(value), line.text))
            return
        if state.enum_overflow:
            return
        records.append(self._enum_record(line, channel, token, state))

    def _append_enum(
        self, records: list[ParserRecord], line: RawLine, channel: str, label: str
    ) -> None:
        state = self._types.get(channel)
        if state is None:
            state = _ChannelType("enum")
            self._types[channel] = state
        if state.kind == "numeric":
            records.append(self._issue(line, channel, "TYPE_CONFLICT"))
            return
        if state.enum_overflow:
            return
        if label not in state.labels and len(state.labels) >= self._enum_limit:
            state.enum_overflow = True
            records.append(self._issue(line, channel, "ENUM_OVERFLOW"))
            return
        records.append(self._enum_record(line, channel, label, state))

    def _enum_record(
        self, line: RawLine, channel: str, label: str, state: _ChannelType
    ) -> Event:
        if label not in state.labels:
            state.labels[label] = len(state.labels)
        return Event(channel, line.t, label, state.labels[label], line.text)

    @staticmethod
    def _prefix(text: str, first_kv_start: int) -> str:
        match = PREFIX_RE.search(text[:first_kv_start])
        if match is None:
            return "root"
        return match.group(0)

    @staticmethod
    def _channel(prefix: str, key: str) -> str:
        return f"{prefix}.{key}"

    @staticmethod
    def _issue(line: RawLine, key: str, reason: str) -> ParseIssue:
        return ParseIssue(line.t, "warning", key, reason, line.text)

    @staticmethod
    def _classify_value(token: str) -> tuple[str, float | None]:
        lowered = token.lower()
        if lowered in {"inf", "+inf", "-inf"}:
            return "inf", None
        if lowered == "nan" or INT_RE.match(token) or FLOAT_RE.match(token):
            return "numeric", float(token)
        if HEX_RE.match(token):
            sign = -1 if token.startswith("-") else 1
            unsigned = token[1:] if token[0] in "+-" else token
            return "numeric", float(sign * int(unsigned, 16))
        return "enum", None


register_parser("kv-line", KvLineParser)
