import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rtt_gui4graph.core.command_sets import CommandSetStore
from rtt_gui4graph.ui.send_panel import SendPanel


class SendPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_custom_command_sections_are_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CommandSetStore(Path(directory) / "command_sets.json")
            panel = SendPanel(command_store=store)

            panel.add_command_section("TAP")
            panel.add_command_to_current_section("Enable", "tap enable=1")

            reloaded = SendPanel(command_store=store)
            sections = reloaded.command_sections()
            self.assertEqual(sections[1].name, "TAP")
            self.assertEqual(sections[1].commands[0].name, "Enable")
            self.assertEqual(sections[1].commands[0].command, "tap enable=1")

    def test_selected_command_can_fill_raw_input_and_send(self):
        with tempfile.TemporaryDirectory() as directory:
            panel = SendPanel(
                command_store=CommandSetStore(Path(directory) / "command_sets.json")
            )
            sent = []
            panel.send_requested.connect(sent.append)

            panel.add_command_section("TAP")
            panel.add_command_to_current_section("Calibrate", "tap cal")
            panel._current_command_table().selectRow(0)

            self.assertTrue(panel.fill_selected_command())
            self.assertEqual(panel._input.text(), "tap cal")
            self.assertTrue(panel.send_selected_command())
            self.assertEqual(sent, [b"tap cal\n"])

    def test_sections_and_commands_can_be_renamed_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            panel = SendPanel(
                command_store=CommandSetStore(Path(directory) / "command_sets.json")
            )

            panel.add_command_section("TAP")
            panel.rename_current_command_section("Motion")
            panel.add_command_to_current_section("Start", "tap start")
            panel._current_command_table().selectRow(0)
            panel.edit_selected_command("Stop", "tap stop")

            sections = panel.command_sections()
            self.assertEqual(sections[1].name, "Motion")
            self.assertEqual(sections[1].commands[0].name, "Stop")
            self.assertEqual(sections[1].commands[0].command, "tap stop")

            self.assertTrue(panel.delete_selected_command())
            self.assertEqual(panel.command_sections()[1].commands, [])

            self.assertTrue(panel.delete_current_command_section())
            self.assertEqual(
                [section.name for section in panel.command_sections()],
                ["Default"],
            )


if __name__ == "__main__":
    unittest.main()
