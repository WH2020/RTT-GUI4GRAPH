from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CommandItem:
    name: str
    command: str


@dataclass
class CommandSection:
    name: str
    commands: list[CommandItem] = field(default_factory=list)


def default_command_set_path() -> Path:
    override = os.environ.get("RTT_GUI4GRAPH_COMMAND_SETS")
    if override:
        return Path(override)
    return Path.home() / ".rtt_gui4graph" / "command_sets.json"


def default_command_sections() -> list[CommandSection]:
    return [CommandSection("Default", [])]


class CommandSetStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_command_set_path()

    def load(self) -> list[CommandSection]:
        if not self.path.exists():
            return default_command_sections()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return self._decode(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return default_command_sections()

    def save(self, sections: list[CommandSection]) -> None:
        normalized = normalize_command_sections(sections)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "sections": [
                {
                    "name": section.name,
                    "commands": [
                        {"name": command.name, "command": command.command}
                        for command in section.commands
                    ],
                }
                for section in normalized
            ],
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _decode(self, data: Any) -> list[CommandSection]:
        if not isinstance(data, dict):
            raise ValueError("command set file must be a JSON object")
        raw_sections = data.get("sections")
        if not isinstance(raw_sections, list):
            raise ValueError("sections must be a list")
        sections: list[CommandSection] = []
        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                continue
            name = str(raw_section.get("name", "")).strip()
            if not name:
                continue
            commands: list[CommandItem] = []
            raw_commands = raw_section.get("commands", [])
            if isinstance(raw_commands, list):
                for raw_command in raw_commands:
                    if not isinstance(raw_command, dict):
                        continue
                    command_name = str(raw_command.get("name", "")).strip()
                    command_text = str(raw_command.get("command", ""))
                    if command_name and command_text:
                        commands.append(CommandItem(command_name, command_text))
            sections.append(CommandSection(name, commands))
        return normalize_command_sections(sections)


def normalize_command_sections(sections: list[CommandSection]) -> list[CommandSection]:
    normalized: list[CommandSection] = []
    for section in sections:
        name = section.name.strip()
        if not name:
            continue
        commands = [
            CommandItem(command.name.strip(), command.command)
            for command in section.commands
            if command.name.strip() and command.command
        ]
        normalized.append(CommandSection(name, commands))
    return normalized or default_command_sections()
