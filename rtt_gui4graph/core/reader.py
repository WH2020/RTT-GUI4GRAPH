from __future__ import annotations

import queue
import time
from collections import deque
from typing import Any

try:
    from PySide6.QtCore import QObject, Signal, Slot
except ModuleNotFoundError:  # Core tests can run without Qt installed.
    class _DummySignal:
        def connect(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def emit(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    def Signal(*_args: Any, **_kwargs: Any) -> _DummySignal:
        return _DummySignal()

    def Slot(*_args: Any, **_kwargs: Any):
        def decorate(func):
            return func

        return decorate

    class QObject:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            super().__init__()

from .line_assembler import LineAssembler
from .link_base import LinkBase, LinkState
from .parser_base import ParserBase, ParserRecord


class BatchQueue:
    def __init__(self, capacity: int = 2000) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._queue: deque[list[Any]] = deque(maxlen=capacity)
        self.dropped_batches = 0

    def push(self, batch: list[Any]) -> None:
        if len(self._queue) == self._queue.maxlen:
            self.dropped_batches += 1
        self._queue.append(list(batch))

    def drain(self, max_records: int) -> list[Any]:
        drained: list[Any] = []
        while self._queue and len(drained) < max_records:
            batch = self._queue.popleft()
            remaining = max_records - len(drained)
            drained.extend(batch[:remaining])
            if len(batch) > remaining:
                self._queue.appendleft(batch[remaining:])
                break
        return drained

    def __len__(self) -> int:
        return len(self._queue)


class ReaderWorker(QObject):
    state_changed = Signal(object, str)
    metrics_changed = Signal(dict)
    send_failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        link: LinkBase,
        parser: ParserBase,
        batches: BatchQueue,
        config: dict[str, Any] | None = None,
        read_size: int = 4096,
    ) -> None:
        super().__init__()
        self._link = link
        self._parser = parser
        self._batches = batches
        self._config = config or {}
        self._read_size = read_size
        self._assembler = LineAssembler()
        self._commands: queue.Queue[bytes] = queue.Queue(maxsize=64)
        self._running = False
        self._bytes = 0
        self._lines = 0

    def enqueue_send(self, data: bytes) -> bool:
        try:
            self._commands.put_nowait(bytes(data))
        except queue.Full:
            self.send_failed.emit("command queue full")
            return False
        return True

    @Slot()
    def run(self) -> None:
        self._running = True
        try:
            self._link.open(self._config)
            self.state_changed.emit(LinkState.CONNECTED, "connected")
            while self._running:
                self._drain_commands()
                data = self._link.read(self._read_size)
                if data:
                    self._bytes += len(data)
                    lines = self._assembler.feed(data)
                    self._lines += len(lines)
                    records = self._parser.feed(lines)
                    if records:
                        self._batches.push(records)
                self.metrics_changed.emit(
                    {
                        "bytes": self._bytes,
                        "lines": self._lines,
                        "queue_depth": len(self._batches),
                        "dropped_batches": self._batches.dropped_batches,
                    }
                )
                time.sleep(0.002)
        except Exception as exc:
            self.state_changed.emit(LinkState.ERROR, str(exc))
        finally:
            try:
                self._link.close()
            except Exception as exc:
                self.state_changed.emit(LinkState.ERROR, f"close failed: {exc}")
            self.state_changed.emit(LinkState.CLOSED, "closed")
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        self._running = False

    def _drain_commands(self) -> None:
        while True:
            try:
                data = self._commands.get_nowait()
            except queue.Empty:
                return
            written = self._link.send(data)
            if written != len(data):
                self.send_failed.emit(f"wrote {written}/{len(data)} bytes")
