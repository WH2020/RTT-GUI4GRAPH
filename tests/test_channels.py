import unittest

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.records import Event, Sample


class ChannelRegistryTest(unittest.TestCase):
    def test_numeric_ring_buffer_keeps_latest_values(self):
        registry = ChannelRegistry(capacity=3)
        for i in range(5):
            registry.ingest(
                Sample(channel="TAP.x", t=float(i), value=float(i), raw_text="")
            )
        channel = registry.channel("TAP.x")
        self.assertEqual(channel.latest_value, 4.0)
        self.assertEqual(channel.series(), ([2.0, 3.0, 4.0], [2.0, 3.0, 4.0]))

    def test_channel_starts_disabled_and_can_be_enabled(self):
        registry = ChannelRegistry(capacity=3)
        registry.ingest(Sample(channel="TAP.x", t=0.0, value=1.0, raw_text=""))
        self.assertFalse(registry.channel("TAP.x").enabled)
        registry.set_enabled("TAP.x", True)
        self.assertEqual(registry.enabled_channels()[0].key, "TAP.x")

    def test_event_series_uses_ordinals_and_latest_label(self):
        registry = ChannelRegistry(capacity=4)
        registry.ingest(
            Event(channel="TAP.state", t=1.0, label="RUN", ordinal=0, raw_text="")
        )
        registry.ingest(
            Event(channel="TAP.state", t=2.0, label="STOP", ordinal=1, raw_text="")
        )
        channel = registry.channel("TAP.state")
        self.assertEqual(channel.latest_value, "STOP")
        self.assertEqual(channel.series(), ([1.0, 2.0], [0.0, 1.0]))

    def test_series_arrays_can_return_recent_window_and_tail_limit(self):
        registry = ChannelRegistry(capacity=10)
        for i in range(8):
            registry.ingest(
                Sample(channel="TAP.x", t=float(i), value=float(i * 10), raw_text="")
            )

        times, values = registry.channel("TAP.x").series_arrays(
            start_time=3.0,
            max_points=3,
        )

        self.assertEqual(times.tolist(), [5.0, 6.0, 7.0])
        self.assertEqual(values.tolist(), [50.0, 60.0, 70.0])


if __name__ == "__main__":
    unittest.main()
