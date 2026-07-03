import math
import unittest

from rtt_gui4graph.core.records import Event, LogLine, ParseIssue, RawLine, Sample
from rtt_gui4graph.core.parsers.kv_line import KvLineParser


def parse(text: str):
    return KvLineParser().parse_line(RawLine(t=10.0, terminal=0, text=text))


class KvLineParserTest(unittest.TestCase):
    def test_numeric_and_enum_values(self):
        records = parse("TAP wr_dps=-173 gain=1e-3 flags=0x1A state=RUN")
        samples = {r.channel: r.value for r in records if isinstance(r, Sample)}
        events = {r.channel: r.label for r in records if isinstance(r, Event)}
        self.assertEqual(samples["TAP.wr_dps"], -173.0)
        self.assertEqual(samples["TAP.gain"], 0.001)
        self.assertEqual(samples["TAP.flags"], 26.0)
        self.assertEqual(events["TAP.state"], "RUN")

    def test_nan_kept_and_inf_rejected(self):
        records = parse("TAP a=nan b=inf")
        self.assertTrue(
            any(isinstance(r, Sample) and math.isnan(r.value) for r in records)
        )
        self.assertTrue(
            any(
                isinstance(r, ParseIssue) and r.reason == "INF_DROPPED"
                for r in records
            )
        )

    def test_duplicate_key_uses_last_value_and_reports_issue(self):
        records = parse("TAP x=1 x=2")
        self.assertEqual(
            [r.value for r in records if isinstance(r, Sample) and r.channel == "TAP.x"],
            [2.0],
        )
        self.assertTrue(
            any(isinstance(r, ParseIssue) and r.reason == "DUP_KEY" for r in records)
        )

    def test_plain_line_is_log_only(self):
        records = parse("hello world")
        self.assertEqual(len([r for r in records if isinstance(r, LogLine)]), 1)
        self.assertFalse(any(isinstance(r, (Sample, Event)) for r in records))

    def test_type_conflict_reports_issue(self):
        parser = KvLineParser()
        parser.parse_line(RawLine(t=1, terminal=0, text="TAP x=1"))
        records = parser.parse_line(RawLine(t=2, terminal=0, text="TAP x=RUN"))
        self.assertTrue(
            any(
                isinstance(r, ParseIssue) and r.reason == "TYPE_CONFLICT"
                for r in records
            )
        )

    def test_empty_value_reports_issue(self):
        records = parse("TAP state=")
        self.assertTrue(
            any(isinstance(r, ParseIssue) and r.reason == "EMPTY_VALUE" for r in records)
        )

    def test_decode_error_is_reported(self):
        parser = KvLineParser()
        records = parser.parse_line(
            RawLine(t=1.0, terminal=0, text="TAP x=1\ufffd", decode_error=True)
        )
        self.assertTrue(
            any(isinstance(r, ParseIssue) and r.reason == "DECODE_ERROR" for r in records)
        )

    def test_enum_overflow_reports_issue_and_stops_events(self):
        parser = KvLineParser(enum_limit=2)
        parser.parse_line(RawLine(t=1.0, terminal=0, text="TAP state=A"))
        parser.parse_line(RawLine(t=2.0, terminal=0, text="TAP state=B"))
        records = parser.parse_line(RawLine(t=3.0, terminal=0, text="TAP state=C"))
        self.assertTrue(
            any(isinstance(r, ParseIssue) and r.reason == "ENUM_OVERFLOW" for r in records)
        )
        self.assertFalse(any(isinstance(r, Event) for r in records))


if __name__ == "__main__":
    unittest.main()
