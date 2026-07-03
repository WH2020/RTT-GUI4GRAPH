from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .records import Event, LogLine, ParseIssue, RawLine, Sample

ParserRecord = Sample | Event | LogLine | ParseIssue

PARSERS: dict[str, type["ParserBase"]] = {}


class ParserBase(ABC):
    @abstractmethod
    def parse_line(self, line: RawLine) -> list[ParserRecord]:
        raise NotImplementedError

    def feed(self, lines: Iterable[RawLine]) -> list[ParserRecord]:
        records: list[ParserRecord] = []
        for line in lines:
            records.extend(self.parse_line(line))
        return records


def register_parser(name: str, parser_cls: type[ParserBase]) -> None:
    PARSERS[name] = parser_cls


def create_parser(name: str) -> ParserBase:
    try:
        parser_cls = PARSERS[name]
    except KeyError as exc:
        raise KeyError(f"unknown parser: {name}") from exc
    return parser_cls()
