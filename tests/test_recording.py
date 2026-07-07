import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from rtt_gui4graph.core.markers import MarkerStore
from rtt_gui4graph.core.recorder import (
    RecordingSession,
    infer_recording_format,
    save_recording,
)
from rtt_gui4graph.core.records import LogLine, Sample


class RecordingSessionTest(unittest.TestCase):
    def test_records_only_between_start_and_stop(self):
        session = RecordingSession()
        session.ingest([Sample("TAP.x", 1.0, 1.0, "")])

        session.start({"transport": "uart"})
        session.ingest(
            [
                LogLine(terminal=0, t=2.0, text="TAP x=2"),
                Sample("TAP.x", 2.0, 2.0, ""),
            ]
        )
        session.stop()
        session.ingest([Sample("TAP.x", 3.0, 3.0, "")])

        self.assertFalse(session.is_recording)
        self.assertEqual(session.registry.channel("TAP.x").series(), ([2.0], [2.0]))
        self.assertEqual(session.raw_log, "     2.000 T0: TAP x=2")
        self.assertEqual(session.meta["transport"], "uart")

    def test_save_recording_supports_rttcap_csv_and_json(self):
        session = RecordingSession()
        session.start({"transport": "uart"})
        session.ingest([Sample("TAP.x", 1.0, 2.0, "")])
        session.stop()
        markers = MarkerStore()
        markers.add(1.0, "start", "")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rttcap = root / "record.rttcap"
            csv_path = root / "record.csv"
            json_path = root / "record.json"

            save_recording(rttcap, session, markers, "rttcap")
            save_recording(csv_path, session, markers, "csv")
            save_recording(json_path, session, markers, "json")

            self.assertIn("meta.json", zipfile.ZipFile(rttcap).namelist())
            rows = list(csv.reader(csv_path.open(newline="", encoding="utf-8")))
            data = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(rows[0], ["time", "TAP.x"])
        self.assertEqual(rows[1], ["1.000000", "2.000000"])
        self.assertEqual(data["meta"]["transport"], "uart")
        self.assertEqual(data["channels"][0]["key"], "TAP.x")
        self.assertEqual(data["markers"]["markers"][0]["name"], "start")

    def test_recording_format_can_be_inferred_from_filter_or_extension(self):
        self.assertEqual(infer_recording_format("a.rttcap", ""), "rttcap")
        self.assertEqual(infer_recording_format("a.csv", ""), "csv")
        self.assertEqual(infer_recording_format("a.json", ""), "json")
        self.assertEqual(infer_recording_format("a", "CSV (*.csv)"), "csv")
        self.assertEqual(infer_recording_format("a", ""), "rttcap")


if __name__ == "__main__":
    unittest.main()
