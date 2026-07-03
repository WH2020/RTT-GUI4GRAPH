import csv
import tempfile
import unittest
from pathlib import Path

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.command_sets import CommandItem, CommandParam, render_command
from rtt_gui4graph.core.csv_export import export_channels_csv
from rtt_gui4graph.core.markers import MarkerStore
from rtt_gui4graph.core.recorder import load_rttcap, save_rttcap
from rtt_gui4graph.core.records import Event, Sample
from rtt_gui4graph.core.session import SessionPreset, SessionStore


class MilestoneModelTest(unittest.TestCase):
    def test_channel_config_controls_display_series_and_target(self):
        registry = ChannelRegistry(capacity=8)
        registry.ingest(Sample("TAP.x", 1.0, 2.0, ""))
        registry.ingest(Sample("TAP.x", 2.0, 3.0, ""))

        registry.set_channel_config(
            "TAP.x",
            display_name="Wrist",
            unit="dps",
            scale=10.0,
            offset=-1.0,
            target="status",
            enabled=True,
        )

        channel = registry.channel("TAP.x")
        self.assertEqual(channel.display_name, "Wrist")
        self.assertEqual(channel.unit, "dps")
        self.assertEqual(channel.target, "status")
        self.assertTrue(channel.enabled)
        times, values = channel.display_series_arrays()
        self.assertEqual(times.tolist(), [1.0, 2.0])
        self.assertEqual(values.tolist(), [19.0, 29.0])

    def test_marker_store_adds_updates_and_serializes_markers(self):
        store = MarkerStore()
        marker = store.add(12.5, "toe strike", "left foot")
        store.rename(marker.id, "strike")
        store.update_note(marker.id, "confirmed")

        reloaded = MarkerStore.from_json(store.to_json())

        self.assertEqual(reloaded.markers()[0].t, 12.5)
        self.assertEqual(reloaded.markers()[0].name, "strike")
        self.assertEqual(reloaded.markers()[0].note, "confirmed")

    def test_rttcap_roundtrip_preserves_channels_and_markers(self):
        registry = ChannelRegistry(capacity=8)
        registry.ingest(Sample("TAP.x", 1.0, 2.0, ""))
        registry.ingest(Event("TAP.state", 1.0, "RUN", 0, ""))
        registry.set_enabled("TAP.x", True)
        markers = MarkerStore()
        markers.add(1.0, "start", "")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.rttcap"
            save_rttcap(path, registry, markers, {"transport": "uart"}, raw_log="raw")
            loaded = load_rttcap(path)

        self.assertEqual(loaded.meta["transport"], "uart")
        self.assertEqual(loaded.raw_log, "raw")
        self.assertIn("TAP.x", [channel.key for channel in loaded.registry.channels()])
        self.assertEqual(loaded.registry.channel("TAP.x").series(), ([1.0], [2.0]))
        self.assertEqual(loaded.markers.markers()[0].name, "start")

    def test_csv_export_writes_aligned_channel_rows(self):
        registry = ChannelRegistry(capacity=8)
        registry.ingest(Sample("TAP.x", 1.0, 2.0, ""))
        registry.ingest(Sample("TAP.y", 2.0, 3.0, ""))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.csv"
            export_channels_csv(path, registry)
            rows = list(csv.reader(path.open(newline="", encoding="utf-8")))

        self.assertEqual(rows[0], ["time", "TAP.x", "TAP.y"])
        self.assertEqual(rows[1], ["1.000000", "2.000000", ""])
        self.assertEqual(rows[2], ["2.000000", "", "3.000000"])

    def test_session_preset_roundtrip(self):
        preset = SessionPreset(
            transport="uart",
            link_configs={"uart": {"port": "COM7"}},
            channel_configs={"TAP.x": {"display_name": "Wrist", "enabled": True}},
            command_sections=[CommandItem("Start", "tap start")],
        )

        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(preset)
            loaded = store.load()

        self.assertEqual(loaded.transport, "uart")
        self.assertEqual(loaded.link_configs["uart"]["port"], "COM7")
        self.assertEqual(loaded.channel_configs["TAP.x"]["display_name"], "Wrist")
        self.assertEqual(loaded.command_sections[0].name, "Start")

    def test_parameterized_command_renders_text_and_hex(self):
        text_item = CommandItem(
            "Set KP",
            "tap kp={kp}",
            params=[CommandParam("kp", "float", default=1.5)],
        )
        hex_item = CommandItem("Ping", "AA 55 01", encoding="hex")

        self.assertEqual(render_command(text_item, {"kp": 2.25}), b"tap kp=2.25\n")
        self.assertEqual(render_command(text_item, {}), b"tap kp=1.5\n")
        self.assertEqual(render_command(hex_item, {}), bytes.fromhex("AA5501"))


if __name__ == "__main__":
    unittest.main()
