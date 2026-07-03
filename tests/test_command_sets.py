import tempfile
import unittest
from pathlib import Path

from rtt_gui4graph.core.command_sets import (
    CommandItem,
    CommandSection,
    CommandSetStore,
)


class CommandSetStoreTest(unittest.TestCase):
    def test_missing_file_loads_default_section(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CommandSetStore(Path(directory) / "command_sets.json")

            sections = store.load()

            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].name, "Default")
            self.assertEqual(sections[0].commands, [])

    def test_save_and_load_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CommandSetStore(Path(directory) / "command_sets.json")
            store.save(
                [
                    CommandSection(
                        "TAP",
                        [
                            CommandItem("Enable", "tap enable=1"),
                            CommandItem("Disable", "tap enable=0"),
                        ],
                    )
                ]
            )

            sections = store.load()

            self.assertEqual(sections[0].name, "TAP")
            self.assertEqual(sections[0].commands[0].name, "Enable")
            self.assertEqual(sections[0].commands[0].command, "tap enable=1")
            self.assertEqual(sections[0].commands[1].name, "Disable")

    def test_invalid_file_loads_default_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "command_sets.json"
            path.write_text("{invalid", encoding="utf-8")
            store = CommandSetStore(path)

            sections = store.load()

            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].name, "Default")


if __name__ == "__main__":
    unittest.main()
