from __future__ import annotations

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QPushButton,
    QToolBar,
)

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.link_base import LINKS, LinkState, create_link
from rtt_gui4graph.core.links import JLinkRttLink  # noqa: F401
from rtt_gui4graph.core.parsers.kv_line import KvLineParser
from rtt_gui4graph.core.reader import BatchQueue, ReaderWorker
from rtt_gui4graph.core.records import Event, LogLine, ParseIssue, Sample
from rtt_gui4graph.ui.channel_panel import ChannelPanel
from rtt_gui4graph.ui.connect_dialog import ConnectDialog, default_config_from_fields
from rtt_gui4graph.ui.log_view import LogView
from rtt_gui4graph.ui.plot_widget import PlotWidget
from rtt_gui4graph.ui.send_panel import SendPanel


class MainWindow(QMainWindow):
    MAX_RECORDS_PER_TICK = 20_000

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RTT GUI4GRAPH")
        self.resize(1280, 820)

        self._registry = ChannelRegistry()
        self._batches = BatchQueue()
        self._thread: QThread | None = None
        self._worker: ReaderWorker | None = None
        self._last_configs: dict[str, dict] = {}

        self._plot = PlotWidget()
        self._channels = ChannelPanel()
        self._logs = LogView()
        self._send_panel = SendPanel()
        self._status = QLabel("disconnected")
        self._metrics = QLabel("")

        self.setCentralWidget(self._plot)
        self._build_toolbar()
        self._build_docks()

        self._channels.channel_enabled_changed.connect(self._set_channel_enabled)
        self._send_panel.send_requested.connect(self._send_bytes)

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._drain_records)
        self._timer.start()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Connection")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._transport = QComboBox()
        for name in sorted(LINKS):
            self._transport.addItem(name)
        self._connect = QPushButton("Connect")
        self._disconnect = QPushButton("Disconnect")
        self._disconnect.setEnabled(False)
        self._connect.clicked.connect(lambda: self.connect_link(prompt=True))
        self._disconnect.clicked.connect(self.disconnect_link)

        toolbar.addWidget(self._transport)
        toolbar.addWidget(self._connect)
        toolbar.addWidget(self._disconnect)
        toolbar.addSeparator()
        toolbar.addWidget(self._status)
        toolbar.addSeparator()
        toolbar.addWidget(self._metrics)

    def _build_docks(self) -> None:
        channel_dock = QDockWidget("Channels", self)
        channel_dock.setWidget(self._channels)
        self.addDockWidget(QtDock.Right, channel_dock)

        log_dock = QDockWidget("Logs", self)
        log_dock.setWidget(self._logs)
        self.addDockWidget(QtDock.Bottom, log_dock)

        send_dock = QDockWidget("Send", self)
        send_dock.setWidget(self._send_panel)
        self.addDockWidget(QtDock.Bottom, send_dock)

    def connect_link(self, prompt: bool = True) -> None:
        if self._worker is not None:
            return
        name = self._transport.currentText()
        link_cls = LINKS[name]
        fields = link_cls.config_fields()
        config = self._last_configs.get(name) or default_config_from_fields(fields)
        if prompt:
            dialog = ConnectDialog(name, fields, config, self)
            if dialog.exec() != ConnectDialog.Accepted:
                return
            config = dialog.config()
            self._last_configs[name] = config
        link = create_link(name)
        self._registry = ChannelRegistry()
        self._batches = BatchQueue()
        self._thread = QThread(self)
        self._worker = ReaderWorker(link, KvLineParser(), self._batches, config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.state_changed.connect(self._on_state_changed)
        self._worker.metrics_changed.connect(self._on_metrics_changed)
        self._worker.send_failed.connect(self._send_panel.set_status)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_reader_thread_finished)
        self._thread.start()
        self._connect.setEnabled(False)
        self._disconnect.setEnabled(True)

    def disconnect_link(self) -> None:
        worker = self._worker
        thread = self._thread
        if worker is not None:
            worker.stop()
        if thread is not None:
            thread.quit()
            thread.wait(1500)
        if self._thread is thread:
            self._clear_reader_state()

    def _on_reader_thread_finished(self) -> None:
        self._clear_reader_state()

    def _clear_reader_state(self) -> None:
        self._worker = None
        self._thread = None
        self._connect.setEnabled(True)
        self._disconnect.setEnabled(False)

    def closeEvent(self, event) -> None:
        self.disconnect_link()
        super().closeEvent(event)

    def _drain_records(self) -> None:
        records = self._batches.drain(self.MAX_RECORDS_PER_TICK)
        if not records:
            return
        for record in records:
            if isinstance(record, LogLine):
                self._logs.append_log(record)
            elif isinstance(record, ParseIssue):
                self._logs.append_issue(record)
            elif isinstance(record, (Sample, Event)):
                self._registry.ingest(record)
        self._channels.refresh(self._registry)
        self._plot.refresh(self._registry)

    def _set_channel_enabled(self, key: str, enabled: bool) -> None:
        self._registry.set_enabled(key, enabled)
        self._plot.refresh(self._registry)

    def _send_bytes(self, data: bytes) -> None:
        if self._worker is None:
            self._send_panel.set_status("not connected")
            return
        if self._worker.enqueue_send(data):
            self._send_panel.set_status(f"queued {len(data)} bytes")

    def _on_state_changed(self, state: LinkState, text: str) -> None:
        self._status.setText(f"{state.value}: {text}")
        if state in (LinkState.CLOSED, LinkState.ERROR):
            self._connect.setEnabled(True)
            self._disconnect.setEnabled(False)

    def _on_metrics_changed(self, metrics: dict) -> None:
        self._metrics.setText(
            "bytes={bytes} lines={lines} q={queue_depth} dropped={dropped_batches}".format(
                **metrics
            )
        )


class QtDock:
    from PySide6.QtCore import Qt

    Right = Qt.RightDockWidgetArea
    Bottom = Qt.BottomDockWidgetArea
