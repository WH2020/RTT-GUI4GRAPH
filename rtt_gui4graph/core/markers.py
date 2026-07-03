from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Marker:
    id: int
    t: float
    name: str
    note: str = ""


class MarkerStore:
    def __init__(self) -> None:
        self._markers: list[Marker] = []
        self._next_id = 1

    def add(self, t: float, name: str = "marker", note: str = "") -> Marker:
        marker = Marker(self._next_id, float(t), name.strip() or "marker", note)
        self._next_id += 1
        self._markers.append(marker)
        self._markers.sort(key=lambda item: item.t)
        return marker

    def remove(self, marker_id: int) -> bool:
        before = len(self._markers)
        self._markers = [marker for marker in self._markers if marker.id != marker_id]
        return len(self._markers) != before

    def rename(self, marker_id: int, name: str) -> bool:
        return self._replace(marker_id, name=name.strip() or "marker")

    def update_note(self, marker_id: int, note: str) -> bool:
        return self._replace(marker_id, note=note)

    def markers(self) -> list[Marker]:
        return list(self._markers)

    def to_json(self) -> dict:
        return {
            "next_id": self._next_id,
            "markers": [
                {"id": marker.id, "t": marker.t, "name": marker.name, "note": marker.note}
                for marker in self._markers
            ],
        }

    @classmethod
    def from_json(cls, data: dict) -> "MarkerStore":
        store = cls()
        for raw in data.get("markers", []):
            marker = Marker(
                int(raw["id"]),
                float(raw["t"]),
                str(raw.get("name", "marker")),
                str(raw.get("note", "")),
            )
            store._markers.append(marker)
            store._next_id = max(store._next_id, marker.id + 1)
        store._next_id = max(store._next_id, int(data.get("next_id", store._next_id)))
        store._markers.sort(key=lambda item: item.t)
        return store

    def _replace(self, marker_id: int, **changes) -> bool:
        for index, marker in enumerate(self._markers):
            if marker.id != marker_id:
                continue
            self._markers[index] = Marker(
                changes.get("id", marker.id),
                changes.get("t", marker.t),
                changes.get("name", marker.name),
                changes.get("note", marker.note),
            )
            return True
        return False
