from __future__ import annotations

import csv
from pathlib import Path

from .channels import ChannelRegistry


def export_channels_csv(path: str | Path, registry: ChannelRegistry) -> None:
    channels = registry.channels()
    time_values: dict[float, dict[str, float]] = {}
    for channel in channels:
        times, values = channel.display_series_arrays()
        for t, value in zip(times.tolist(), values.tolist(), strict=False):
            time_values.setdefault(float(t), {})[channel.key] = float(value)

    with Path(path).open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["time", *[channel.key for channel in channels]])
        for t in sorted(time_values):
            row = [f"{t:.6f}"]
            for channel in channels:
                value = time_values[t].get(channel.key)
                row.append("" if value is None else f"{value:.6f}")
            writer.writerow(row)
