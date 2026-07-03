import unittest

from rtt_gui4graph.core.line_assembler import LineAssembler


class LineAssemblerTest(unittest.TestCase):
    def test_splits_complete_and_partial_lines(self):
        assembler = LineAssembler(clock=lambda: 1.25)
        self.assertEqual(assembler.feed(b"TAP a=1"), [])
        lines = assembler.feed(b" b=2\r\nnext=3\n")
        self.assertEqual([line.text for line in lines], ["TAP a=1 b=2", "next=3"])
        self.assertEqual([line.t for line in lines], [1.25, 1.25])

    def test_strips_rtt_terminal_escape(self):
        assembler = LineAssembler(clock=lambda: 2.0)
        lines = assembler.feed(bytes([0xFF, 1]) + b"TAP x=1\n")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].terminal, 1)
        self.assertEqual(lines[0].text, "TAP x=1")

    def test_strips_ascii_rtt_terminal_escape(self):
        assembler = LineAssembler(clock=lambda: 2.0)
        lines = assembler.feed(b"\xff0\xff1TAP x=1\n")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].terminal, 1)
        self.assertEqual(lines[0].text, "TAP x=1")
        self.assertFalse(lines[0].decode_error)

    def test_decode_error_replaces_bytes_and_marks_line(self):
        assembler = LineAssembler(clock=lambda: 3.0)
        lines = assembler.feed(b"bad=\xff\n")
        self.assertEqual(lines[0].text, "bad=\ufffd")
        self.assertTrue(lines[0].decode_error)


if __name__ == "__main__":
    unittest.main()
