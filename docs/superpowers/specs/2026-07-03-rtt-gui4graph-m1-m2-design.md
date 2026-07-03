# RTT GUI4GRAPH M1+M2 Design

## Goal

Build the first runnable RTT GUI4GRAPH MVP: a PySide6 desktop app that can read an RTT-like byte stream from a mock source or J-Link, assemble text lines, parse `key=value` records into channels, show logs, allow raw command sending, and plot user-selected channels in real time.

## Scope

Included:

- M1: link registry, `MockLink`, `JLinkRttLink`, log view, raw send panel.
- M2: `LineAssembler`, `KvLineParser`, `ChannelRegistry`, channel discovery, manual plot enable, real-time pyqtgraph plot.
- Parser tests for framing, value grammar, duplicate keys, non-UTF-8, type conflicts, enum overflow, and queue overflow counters.
- `python -m rtt_gui4graph.app --mock` as the no-hardware acceptance path.

Deferred:

- Plugin directory loading.
- `.rttcap` recording and replay.
- channel model editor beyond enable/disable and latest value display.
- marker panel, command library editor, parameter tuning panel.
- session presets and persistent window layout.

## Architecture

The app is split into pure core modules and Qt UI modules. Core parser and channel code must be testable without a running Qt application. Link implementations are Qt-aware because the GUI uses signals for connection state and byte delivery.

Data flow:

```text
LinkBase bytes
  -> ReaderWorker
  -> LineAssembler
  -> KvLineParser
  -> deque batches
  -> MainWindow QTimer drain
  -> ChannelRegistry + LogView + ChannelPanel + PlotWidget
```

`MockLink` is the default development and demo transport. `JLinkRttLink` is implemented as an optional transport that imports `pylink` only when used, so the mock path remains runnable on machines without SEGGER/J-Link installed.

## Core Contracts

`LineAssembler` accepts byte chunks and emits decoded `RawLine` objects with monotonic timestamps and terminal index. It strips SEGGER RTT virtual terminal escapes (`0xFF` plus terminal byte), handles `\n`, `\r\n`, half lines, and replacement decoding for invalid UTF-8.

`KvLineParser` accepts `RawLine` and emits:

- `Sample(channel, t, value, raw_text)` for numeric values.
- `Event(channel, t, label, ordinal, raw_text)` for enum values.
- `LogLine(terminal, t, text)` for every line.
- `ParseIssue(t, severity, key, reason, sample_text, count)` for parser issues.

Numeric grammar is explicit: signed decimal integer, signed float, scientific notation, `0x` hex, and `nan`. `inf` is rejected and reported. Empty values are rejected. Duplicate keys use the last value and report an issue. Numeric channels reject later enum values as type conflicts. Enum channels accept later numeric tokens as labels. Enum channels with more than 64 labels are demoted to log-only for new values.

`ChannelRegistry` owns bounded numpy ring buffers per channel. New channels are discovered automatically but are not plotted until the user enables them in `ChannelPanel`.

## Queue And Threading

The reader runs in a `QThread`. All link reads and writes happen in that thread. The reader parses data and appends batches to `collections.deque(maxlen=2000)`. Overflow drops oldest batches and increments `dropped_batches`.

The GUI drains the queue on a 30 Hz `QTimer`. It processes at most `MAX_RECORDS_PER_TICK` records per tick to prevent UI freezes. Command sending uses `queue.Queue(maxsize=64)` and `put_nowait`; full queues report a visible send error instead of blocking.

## UI

The main window contains:

- top toolbar: connect/disconnect, transport selector, status metrics.
- center plot: pyqtgraph time plot for selected numeric channels; enum channels appear as stepped ordinal traces in the same MVP plot.
- right dock: discovered channels with enable checkboxes and latest values.
- bottom dock: raw log lines and parser issue summaries.
- bottom/right send panel: text or hex raw command input, line ending selector, send status.

No landing page is created. The first screen is the actual tool.

## J-Link Behavior

The J-Link transport exposes explicit config fields:

- serial number, optional.
- target device, default `Cortex-M`.
- interface, default `SWD`.
- speed kHz, default `4000`.
- RTT up buffer index, default `0`.
- RTT down buffer index, default `0`.

Open sequence: create `pylink.JLink`, open by serial if supplied, set interface, connect device, start RTT, then poll `rtt_read(up_buffer, 4096)`. Send writes to `rtt_write(down_buffer, data)`.

Failures are reported through link state and do not crash the app.

## Verification

Core acceptance:

- `pytest` passes parser and channel tests.
- `python -m rtt_gui4graph.app --mock` starts without hardware.
- mock stream discovers channels including `TAP.wr_dps`, `TAP.wy_dps`, `TAP.state`, and `TAP.align`.
- enabling a numeric channel draws a live curve.
- raw text send and hex send both reach the active link path; mock mode logs outgoing bytes.

## Constraints

The implementation stays intentionally narrow. It must not introduce plugin scanning, recording, replay, markers, or command library features in this milestone. Those features depend on this core data path and should be added after M1+M2 is verified.
