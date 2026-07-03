import unittest

import rtt_gui4graph.core.links  # noqa: F401
from rtt_gui4graph.core.link_base import LINKS


class LinkRegistryTest(unittest.TestCase):
    def test_only_real_jlink_transport_is_registered(self):
        self.assertIn("jlink-rtt", LINKS)
        self.assertNotIn("mock", LINKS)


if __name__ == "__main__":
    unittest.main()
