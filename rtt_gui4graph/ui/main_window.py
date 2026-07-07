from __future__ import annotations

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QToolBar,
)

from rtt_gui4graph.core.channels import ChannelRegistry
from rtt_gui4graph.core.link_base import LINKS, LinkState, create_link
from rtt_gui4graph.core.links import JLinkRttLink  # noqa: F401
from rtt_gui4graph.core.markers import MarkerStore
from rtt_gui4graph.core.parsers.kv_line import KvLineParser
from rtt_gui4graph.core.reader import BatchQueue, ReaderWorker
from rtt_gui4graph.core.recorder import (
    RecordingSession,
    infer_recording_format,
    load_rttcap,
    save_recording,
)
from rtt_gui4graph.core.records import Event, LogLine, ParseIssue, Sample
from rtt_gui4graph.core.session import SessionPreset, SessionStore
from rtt_gui4graph.ui.channel_model_editor import ChannelModelEditor
from rtt_gui4graph.ui.channel_panel import ChannelPanel
from rtt_gui4graph.ui.connect_dialog import ConnectDialog, default_config_from_fields
from rtt_gui4graph.ui.log_view import LogView
from rtt_gui4graph.ui.marker_panel import MarkerDialog, MarkerPanel
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
        self._markers = MarkerStore()
        self._recording = RecordingSession()
        self._file_dialog = QFileDialog

        self._plot = PlotWidget()
        self._plot.set_markers(self._markers)
        self._channels = ChannelPanel()
        self._channel_editor = ChannelModelEditor()
        self._marker_panel = MarkerPanel()
        self._marker_panel.refresh(self._markers)
        self._logs = LogView()
        self._send_panel = SendPanel()
        self._status = QLabel("disconnected")
        self._metrics = QLabel("")

        self.setCentralWidget(self._plot)
        self._build_toolbar()
        self._build_docks()

        self._channels.channel_enabled_changed.connect(self._set_channel_enabled)
        self._marker_panel.markers_changed.connect(self._on_markers_changed)
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
        self._mark = QPushButton("Mark")
        self._start_record = QPushButton("Start Record")
        self._stop_record = QPushButton("Stop Record")
        self._save_record = QPushButton("Save Record")
        self._open_capture = QPushButton("Open Cap")
        self._save_session = QPushButton("Save Session")
        self._load_session = QPushButton("Load Session")
        self._disconnect.setEnabled(False)
        self._stop_record.setEnabled(False)
        self._save_record.setEnabled(False)
        self._connect.clicked.connect(lambda: self.connect_link(prompt=True))
        self._disconnect.clicked.connect(self.disconnect_link)
        self._mark.clicked.connect(lambda: self.add_marker(prompt=True))
        self._start_record.clicked.connect(self.start_recording)
        self._stop_record.clicked.connect(self.stop_recording)
        self._save_record.clicked.connect(self.save_recording)
        self._open_capture.clicked.connect(self.open_capture)
        self._save_session.clicked.connect(self.save_session)
        self._load_session.clicked.connect(self.load_session)

        toolbar.addWidget(self._transport)
        toolbar.addWidget(self._connect)
        toolbar.addWidget(self._disconnect)
        toolbar.addSeparator()
        toolbar.addWidget(self._mark)
        toolbar.addWidget(self._start_record)
        toolbar.addWidget(self._stop_record)
        toolbar.addWidget(self._save_record)
        toolbar.addWidget(self._open_capture)
        toolbar.addWidget(self._save_session)
        toolbar.addWidget(self._load_session)
        toolbar.addSeparator()
        toolbar.addWidget(self._status)
        toolbar.addSeparator()
        toolbar.addWidget(self._metrics)

    def _build_docks(self) -> None:
        channel_dock = QDockWidget("Channels", self)
        channel_dock.setWidget(self._channels)
        self.addDockWidget(QtDock.Right, channel_dock)

        channel_model_dock = QDockWidget("Channel Model", self)
        channel_model_dock.setWidget(self._channel_editor)
        self.addDockWidget(QtDock.Right, channel_model_dock)

        marker_dock = QDockWidget("Markers", self)
        marker_dock.setWidget(self._marker_panel)
        self.addDockWidget(QtDock.Right, marker_dock)

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
        self._markers = MarkerStore()
        self._plot.set_markers(self._markers)
        self._marker_panel.refresh(self._markers)
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
        logs: list[LogLine] = []
        issues: list[ParseIssue] = []
        for record in records:
            if isinstance(record, LogLine):
                logs.append(record)
            elif isinstance(record, ParseIssue):
                issues.append(record)
            elif isinstance(record, (Sample, Event)):
                self._registry.ingest(record)
        self._logs.append_logs(logs)
        self._logs.append_issues(issues)
        self._recording.ingest(records)
        self._channels.refresh(self._registry)
        self._channel_editor.refresh(self._registry)
        self._plot.refresh(self._registry)

    def _set_channel_enabled(self, key: str, enabled: bool) -> None:
        self._registry.set_enabled(key, enabled)
        self._channel_editor.refresh(self._registry)
        self._plot.refresh(self._registry)

    def add_marker(
        self,
        name: str | None = None,
        note: str = "",
        prompt: bool = False,
    ):
        t = max(
            (
                channel.latest_time
                for channel in self._registry.channels()
                if channel.latest_time is not None
            ),
            default=0.0,
        )
        default_name = name or f"marker {len(self._markers.markers()) + 1}"
        if prompt:
            dialog = MarkerDialog(self, default_name, note)
            if dialog.exec() != MarkerDialog.Accepted:
                return None
            default_name, note = dialog.marker_text()
        return self._marker_panel.add_marker(t, default_name, note)

    def _on_markers_changed(self) -> None:
        self._plot.refresh(self._registry)

    def start_recording(self) -> None:
        self._recording.start(
            {
                "transport": self._transport.currentText(),
                "link_configs": self._last_configs,
            }
        )
        self._start_record.setEnabled(False)
        self._stop_record.setEnabled(True)
        self._save_record.setEnabled(False)
        self._status.setText("recording: started")

    def stop_recording(self) -> None:
        self._recording.stop()
        self._start_record.setEnabled(True)
        self._stop_record.setEnabled(False)
        self._save_record.setEnabled(self._recording.has_data())
        self._status.setText("recording: stopped")

    def save_recording(self) -> None:
        if self._recording.is_recording:
            self.stop_recording()
        if not self._recording.has_data():
            self._status.setText("recording: no data")
            return
        path, selected_filter = self._file_dialog.getSaveFileName(
            self,
            "Save Recording",
            "record.rttcap",
            "RTT Capture (*.rttcap);;CSV (*.csv);;JSON (*.json)",
        )
        if not path:
            return
        file_format = infer_recording_format(path, selected_filter)
        path = self._path_with_recording_suffix(path, file_format)
        save_recording(
            path,
            self._recording,
            self._markers,
            file_format,
        )
        self._status.setText(f"recording saved: {path}")

    def open_capture(self) -> None:
        path, _ = self._file_dialog.getOpenFileName(
            self,
            "Open Capture",
            "",
            "RTT Capture (*.rttcap)",
        )
        if not path:
            return
        replay = load_rttcap(path)
        self._registry = replay.registry
        self._markers = replay.markers
        self._plot.set_markers(self._markers)
        self._marker_panel.refresh(self._markers)
        self._channels.refresh(self._registry)
        self._channel_editor.refresh(self._registry)
        self._plot.refresh(self._registry)
        self._status.setText(f"opened: {path}")

    def save_session(self) -> None:
        path, _ = self._file_dialog.getSaveFileName(
            self,
            "Save Session",
            "session.json",
            "Session (*.json)",
        )
        if not path:
            return
        SessionStore(path).save(
            SessionPreset(
                transport=self._transport.currentText(),
                link_configs=self._last_configs,
                channel_configs=self._registry.channel_configs(),
            )
        )
        self._status.setText(f"session saved: {path}")

    def load_session(self) -> None:
        path, _ = self._file_dialog.getOpenFileName(
            self,
            "Load Session",
            "",
            "Session (*.json)",
        )
        if not path:
            return
        preset = SessionStore(path).load()
        self._last_configs = preset.link_configs
        index = self._transport.findText(preset.transport)
        if index >= 0:
            self._transport.setCurrentIndex(index)
        self._registry.apply_channel_configs(preset.channel_configs)
        self._channels.refresh(self._registry)
        self._channel_editor.refresh(self._registry)
        self._plot.refresh(self._registry)
        self._status.setText(f"session loaded: {path}")

    @staticmethod
    def _path_with_recording_suffix(path: str, file_format: str) -> str:
        suffix = {"rttcap": ".rttcap", "csv": ".csv", "json": ".json"}[file_format]
        if path.lower().endswith(suffix):
            return path
        return path + suffix

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
