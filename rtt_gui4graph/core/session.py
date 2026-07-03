from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .command_sets import CommandItem


@dataclass
class SessionPreset:
    transport: str = ""
    link_configs: dict[str, dict] = field(default_factory=dict)
    channel_configs: dict[str, dict] = field(default_factory=dict)
    command_sections: list[CommandItem] = field(default_factory=list)


class SessionStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, preset: SessionPreset) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "transport": preset.transport,
            "link_configs": preset.link_configs,
            "channel_configs": preset.channel_configs,
            "commands": [
                {
                    "name": command.name,
                    "command": command.command,
                    "encoding": command.encoding,
                }
                for command in preset.command_sections
            ],
        }
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

    def load(self) -> SessionPreset:
        data = json.loads(self.path.read_text("utf-8"))
        return SessionPreset(
            transport=str(data.get("transport", "")),
            link_configs=dict(data.get("link_configs", {})),
            channel_configs=dict(data.get("channel_configs", {})),
            command_sections=[
                CommandItem(
                    str(raw.get("name", "")),
                    str(raw.get("command", "")),
                    str(raw.get("encoding", "text") or "text"),
                )
                for raw in data.get("commands", [])
                if isinstance(raw, dict)
            ],
        )
