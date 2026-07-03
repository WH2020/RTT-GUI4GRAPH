# RTT GUI4GRAPH M1+M2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable RTT GUI4GRAPH MVP with J-Link RTT, raw send, line assembly, key-value parsing, channel discovery, and real-time plotting.

**Architecture:** Pure core modules handle parsing, records, bounded buffers, and tests. Qt-aware link and UI modules provide a threaded reader, channel/log/send panels, and pyqtgraph rendering. J-Link imports `pylink` only when opened, while core tests run without hardware.

**Tech Stack:** Python 3.10+, PySide6, pyqtgraph, numpy, pytest, optional pylink-square.

---

## File Structure

- `rtt_gui4graph/__init__.py`: package marker and version.
- `rtt_gui4graph/app.py`: QApplication entry point.
- `rtt_gui4graph/core/records.py`: dataclasses and parser enums.
- `rtt_gui4graph/core/line_assembler.py`: byte stream to timestamped lines.
- `rtt_gui4graph/core/parser_base.py`: parser registry and abstract interface.
- `rtt_gui4graph/core/parsers/kv_line.py`: key-value parser.
- `rtt_gui4graph/core/channels.py`: bounded channel buffers and registry.
- `rtt_gui4graph/core/link_base.py`: Qt link base, field schema, link registry.
- `rtt_gui4graph/core/links/jlink_rtt.py`: optional pylink transport.
- `rtt_gui4graph/core/reader.py`: QThread worker, parse batches, send queue.
- `rtt_gui4graph/ui/main_window.py`: application shell and timer drain.
- `rtt_gui4graph/ui/plot_widget.py`: pyqtgraph curve management.
- `rtt_gui4graph/ui/channel_panel.py`: discovered channel list.
- `rtt_gui4graph/ui/log_view.py`: raw log and issue display.
- `rtt_gui4graph/ui/send_panel.py`: raw text/hex send controls.
- `tests/test_line_assembler.py`: framing tests.
- `tests/test_kv_parser.py`: value grammar and parse issue tests.
- `tests/test_channels.py`: ring buffer and enable tests.
- `tests/test_reader_queue.py`: bounded batch queue behavior.
- `requirements.txt`: runtime and test dependencies.

## Task 1: Core Records And Line Assembler

**Files:**
- Create: `rtt_gui4graph/core/records.py`
- Create: `rtt_gui4graph/core/line_assembler.py`
- Test: `tests/test_line_assembler.py`

- [ ] **Step 1: Write line assembler tests**

```python
from rtt_gui4graph.core.line_assembler import LineAssembler

def test_splits_complete_and_partial_lines():
    assembler = LineAssembler(clock=lambda: 1.25)
    assert assembler.feed(b"TAP a=1") == []
    lines = assembler.feed(b" b=2\r\nnext=3\n")
    assert [line.text for line in lines] == ["TAP a=1 b=2", "next=3"]
    assert [line.t for line in lines] == [1.25, 1.25]

def test_strips_rtt_terminal_escape():
    assembler = LineAssembler(clock=lambda: 2.0)
    lines = assembler.feed(bytes([0xFF, 1]) + b"TAP x=1\n")
    assert len(lines) == 1
    assert lines[0].terminal == 1
    assert lines[0].text == "TAP x=1"

def test_decode_error_replaces_bytes_and_marks_line():
    assembler = LineAssembler(clock=lambda: 3.0)
    lines = assembler.feed(b"bad=\xff\n")
    assert lines[0].text == "bad=\ufffd"
    assert lines[0].decode_error is True
```

- [ ] **Step 2: Run tests and verify import failure**

Run: `pytest tests/test_line_assembler.py -q`
Expected: FAIL because `rtt_gui4graph.core.line_assembler` does not exist.

- [ ] **Step 3: Implement records and assembler**

Create dataclasses `RawLine`, `Sample`, `Event`, `LogLine`, `ParseIssue`; implement `LineAssembler.feed(data: bytes) -> list[RawLine]`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_line_assembler.py -q`
Expected: PASS.

## Task 2: Key-Value Parser

**Files:**
- Create: `rtt_gui4graph/core/parser_base.py`
- Create: `rtt_gui4graph/core/parsers/kv_line.py`
- Test: `tests/test_kv_parser.py`

- [ ] **Step 1: Write parser tests**

```python
import math
from rtt_gui4graph.core.records import Event, LogLine, ParseIssue, RawLine, Sample
from rtt_gui4graph.core.parsers.kv_line import KvLineParser

def parse(text):
    return KvLineParser().parse_line(RawLine(t=10.0, terminal=0, text=text))

def test_numeric_and_enum_values():
    records = parse("TAP wr_dps=-173 gain=1e-3 flags=0x1A state=RUN")
    samples = {r.channel: r.value for r in records if isinstance(r, Sample)}
    events = {r.channel: r.label for r in records if isinstance(r, Event)}
    assert samples["TAP.wr_dps"] == -173.0
    assert samples["TAP.gain"] == 0.001
    assert samples["TAP.flags"] == 26.0
    assert events["TAP.state"] == "RUN"

def test_nan_kept_and_inf_rejected():
    records = parse("TAP a=nan b=inf")
    assert any(isinstance(r, Sample) and math.isnan(r.value) for r in records)
    assert any(isinstance(r, ParseIssue) and r.reason == "INF_DROPPED" for r in records)

def test_duplicate_key_uses_last_value_and_reports_issue():
    records = parse("TAP x=1 x=2")
    assert [r.value for r in records if isinstance(r, Sample) and r.channel == "TAP.x"] == [2.0]
    assert any(isinstance(r, ParseIssue) and r.reason == "DUP_KEY" for r in records)

def test_plain_line_is_log_only():
    records = parse("hello world")
    assert len([r for r in records if isinstance(r, LogLine)]) == 1
    assert not any(isinstance(r, (Sample, Event)) for r in records)

def test_type_conflict_reports_issue():
    parser = KvLineParser()
    parser.parse_line(RawLine(t=1, terminal=0, text="TAP x=1"))
    records = parser.parse_line(RawLine(t=2, terminal=0, text="TAP x=RUN"))
    assert any(isinstance(r, ParseIssue) and r.reason == "TYPE_CONFLICT" for r in records)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_kv_parser.py -q`
Expected: FAIL because parser modules do not exist.

- [ ] **Step 3: Implement parser registry and `KvLineParser`**

Implement numeric grammar, enum mapping, duplicate key handling, decode error issue propagation, and log line output.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_kv_parser.py -q`
Expected: PASS.

## Task 3: Channel Registry

**Files:**
- Create: `rtt_gui4graph/core/channels.py`
- Test: `tests/test_channels.py`

- [ ] **Step 1: Write channel tests**

```python
from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.records import Event, Sample

def test_numeric_ring_buffer_keeps_latest_values():
    registry = ChannelRegistry(capacity=3)
    for i in range(5):
        registry.ingest(Sample(channel="TAP.x", t=float(i), value=float(i), raw_text=""))
    channel = registry.channel("TAP.x")
    assert channel.latest_value == 4.0
    assert channel.series() == ([2.0, 3.0, 4.0], [2.0, 3.0, 4.0])

def test_channel_starts_disabled_and_can_be_enabled():
    registry = ChannelRegistry(capacity=3)
    registry.ingest(Sample(channel="TAP.x", t=0.0, value=1.0, raw_text=""))
    assert registry.channel("TAP.x").enabled is False
    registry.set_enabled("TAP.x", True)
    assert registry.enabled_channels()[0].key == "TAP.x"

def test_event_series_uses_ordinals_and_latest_label():
    registry = ChannelRegistry(capacity=4)
    registry.ingest(Event(channel="TAP.state", t=1.0, label="RUN", ordinal=0, raw_text=""))
    registry.ingest(Event(channel="TAP.state", t=2.0, label="STOP", ordinal=1, raw_text=""))
    channel = registry.channel("TAP.state")
    assert channel.latest_value == "STOP"
    assert channel.series() == ([1.0, 2.0], [0.0, 1.0])
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_channels.py -q`
Expected: FAIL because `ChannelRegistry` does not exist.

- [ ] **Step 3: Implement ring buffer channels**

Create `ChannelKind`, `Channel`, and `ChannelRegistry`; use numpy arrays for fixed-size buffers and expose `series()`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_channels.py -q`
Expected: PASS.

## Task 4: Links And Reader Queue

**Files:**
- Create: `rtt_gui4graph/core/link_base.py`
- Create: `rtt_gui4graph/core/links/jlink_rtt.py`
- Create: `rtt_gui4graph/core/reader.py`
- Test: `tests/test_reader_queue.py`

- [ ] **Step 1: Write bounded queue test**

```python
from rtt_gui4graph.core.reader import BatchQueue

def test_batch_queue_drops_oldest_and_counts_drops():
    queue = BatchQueue(capacity=2)
    queue.push([1])
    queue.push([2])
    queue.push([3])
    assert queue.dropped_batches == 1
    assert queue.drain(max_records=10) == [2, 3]

def test_batch_queue_respects_max_records():
    queue = BatchQueue(capacity=3)
    queue.push([1, 2])
    queue.push([3, 4])
    assert queue.drain(max_records=3) == [1, 2, 3]
    assert queue.drain(max_records=10) == [4]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_reader_queue.py -q`
Expected: FAIL because `BatchQueue` does not exist.

- [ ] **Step 3: Implement link base and reader queue**

Create Qt link interfaces, J-Link transport, `BatchQueue`, and `ReaderWorker`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_reader_queue.py -q`
Expected: PASS.

## Task 5: GUI MVP

**Files:**
- Create: `rtt_gui4graph/app.py`
- Create: `rtt_gui4graph/ui/main_window.py`
- Create: `rtt_gui4graph/ui/plot_widget.py`
- Create: `rtt_gui4graph/ui/channel_panel.py`
- Create: `rtt_gui4graph/ui/log_view.py`
- Create: `rtt_gui4graph/ui/send_panel.py`
- Create: `requirements.txt`

- [ ] **Step 1: Implement UI modules**

Build a `QMainWindow` with toolbar controls, pyqtgraph plot, channel dock, log dock, and send panel. Wire connect/disconnect to `ReaderWorker` and drain parsed records at 30 Hz.

- [ ] **Step 2: Run no-hardware startup**

Run: `python -m rtt_gui4graph.app`
Expected: GUI opens and shows the J-Link RTT connection workflow.

## Task 6: Final Verification

**Files:**
- Verify all created files.

- [ ] **Step 1: Run all tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 2: Run import smoke test**

Run: `python -c "from rtt_gui4graph.core.parsers.kv_line import KvLineParser; from rtt_gui4graph.core.channels import ChannelRegistry; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Note manual GUI verification limits**

If GUI dependencies or display are unavailable, report the exact failure and the successful core verification commands.
