"""主窗口：三栏布局 + 顶部工具栏 + 底部日志 + 运行调度。"""

from __future__ import annotations

import html
import importlib.util
import os
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.compiler import compile_flow
from ..core.models import NodeType
from ..io.flow_io import load_document, save_document
from ..runner import FlowWorker
from .canvas import FlowScene, FlowView
from .node_item import NodeItem
from .palette import NodePalette
from .property_panel import PropertyPanel
from .theme import COLORS

LOG_COLORS = {
    "normal": COLORS["text_muted"],
    "info": COLORS["primary"],
    "ok": COLORS["success"],
    "warn": COLORS["warning"],
    "error": COLORS["danger"],
}


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AutoClick · 可视化流程编排器")
        self.setWindowIcon(QIcon("Bilibili.ico"))
        self.resize(1440, 920)
        self.setMinimumSize(1100, 700)

        self.flow_path: str | None = None
        self.worker: FlowWorker | None = None

        self.scene = FlowScene(self)
        self.view = FlowView(self.scene)
        self.palette = NodePalette()
        self.props = PropertyPanel()

        self._build_ui()
        self._build_shortcuts()
        self._wire_signals()
        self._update_status()

    # ------------------------------------------------------------------ 构建
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_top_bar())

        vertical = QSplitter(Qt.Vertical)
        vertical.setChildrenCollapsible(False)

        horizontal = QSplitter(Qt.Horizontal)
        horizontal.setChildrenCollapsible(False)
        horizontal.addWidget(self.palette)
        horizontal.addWidget(self.view)
        horizontal.addWidget(self.props)
        horizontal.setStretchFactor(0, 0)
        horizontal.setStretchFactor(1, 1)
        horizontal.setStretchFactor(2, 0)
        horizontal.setSizes([220, 880, 300])

        vertical.addWidget(horizontal)
        vertical.addWidget(self._build_log_panel())
        vertical.setSizes([740, 160])
        vertical.setStretchFactor(0, 1)
        vertical.setStretchFactor(1, 0)

        layout.addWidget(vertical, 1)
        self._build_status_bar()

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(58)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(10)

        brand_box = QWidget()
        brand_layout = QVBoxLayout(brand_box)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(0)
        brand = QLabel("AutoClick")
        brand.setObjectName("Brand")
        subtitle = QLabel("可视化流程编排")
        subtitle.setObjectName("BrandSub")
        brand_layout.addWidget(brand)
        brand_layout.addWidget(subtitle)
        layout.addWidget(brand_box)

        layout.addWidget(self._separator())

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("未命名流程")
        self.name_edit.setFixedWidth(190)
        self.name_edit.setToolTip("流程名称，会写入配置 JSON")
        layout.addWidget(self.name_edit)

        layout.addStretch(1)

        self.load_btn = QPushButton("加载")
        self.load_btn.setObjectName("GhostButton")
        self.load_btn.clicked.connect(self.load_flow)
        layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("GhostButton")
        self.save_btn.clicked.connect(self.save_flow)
        layout.addWidget(self.save_btn)

        layout.addWidget(self._separator())

        loop_label = QLabel("循环")
        loop_label.setObjectName("TopLabel")
        layout.addWidget(loop_label)

        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(0, 9999)
        self.loop_spin.setValue(1)
        self.loop_spin.setSuffix(" 次")
        self.loop_spin.setSpecialValueText("无限")
        self.loop_spin.setFixedWidth(96)
        self.loop_spin.setToolTip("0 表示无限循环，直到点击停止")
        layout.addWidget(self.loop_spin)

        self.run_btn = QPushButton("▶  运行")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(34)
        self.run_btn.clicked.connect(self.start_run)
        layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("DangerButton")
        self.stop_btn.setMinimumHeight(34)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_run)
        layout.addWidget(self.stop_btn)

        return bar

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFixedWidth(1)
        line.setFixedHeight(26)
        line.setStyleSheet(f"background: {COLORS['border']};")
        return line

    def _build_log_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("LogPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 8, 14, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("运行日志")
        title.setObjectName("PanelTitle")
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("GhostButton")
        clear_btn.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(2000)
        layout.addWidget(self.log_view, 1)
        return panel

    def _build_status_bar(self) -> None:
        status = self.statusBar()
        self.status_nodes = QLabel("节点 0 · 连线 0")
        self.status_zoom = QLabel("缩放 100%")
        status.addWidget(self.status_nodes)
        status.addPermanentWidget(self.status_zoom)

        zoom_out = QPushButton("－")
        zoom_out.setObjectName("GhostButton")
        zoom_out.setFixedWidth(28)
        zoom_out.clicked.connect(self._zoom_out)
        zoom_in = QPushButton("＋")
        zoom_in.setObjectName("GhostButton")
        zoom_in.setFixedWidth(28)
        zoom_in.clicked.connect(self._zoom_in)
        fit = QPushButton("适应")
        fit.setObjectName("GhostButton")
        fit.setFixedWidth(52)
        fit.clicked.connect(self.view.fit_content)
        for widget in (zoom_out, zoom_in, fit):
            status.addPermanentWidget(widget)

    def _build_shortcuts(self) -> None:
        bindings = (
            (QKeySequence.Save, self.save_flow),
            (QKeySequence.Open, self.load_flow),
            (QKeySequence("F5"), self.start_run),
            (QKeySequence("Shift+F5"), self.stop_run),
            (QKeySequence("Ctrl+0"), self.view.reset_zoom),
        )
        for sequence, handler in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)

    def _wire_signals(self) -> None:
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.scene.graph_changed.connect(self._update_status)
        self.scene.message.connect(lambda text: self.log(text, "warn"))
        self.scene.node_double_clicked.connect(self._on_node_double_clicked)

        self.props.params_changed.connect(self._on_params_changed)
        self.props.delete_requested.connect(self._on_delete_node)

        self.palette.node_activated.connect(self._on_palette_activated)
        self.view.zoom_changed.connect(self._on_zoom_changed)

    # ------------------------------------------------------------------ 状态
    def _update_status(self) -> None:
        self.status_nodes.setText(
            f"节点 {self.scene.node_count()} · 连线 {len(self.scene.edge_items)}"
        )
        overview = (
            f"当前流程共 {self.scene.node_count()} 个节点、{len(self.scene.edge_items)} 条连线。\n"
            "选中画布上的节点即可在此编辑参数。"
        )
        self.props.set_overview(overview)

    def _on_zoom_changed(self, zoom: float) -> None:
        self.status_zoom.setText(f"缩放 {zoom * 100:.0f}%")

    def _zoom_in(self) -> None:
        self.view.zoom_by(1.15)

    def _zoom_out(self) -> None:
        self.view.zoom_by(1 / 1.15)

    # ------------------------------------------------------------------ 选择
    def _on_selection_changed(self) -> None:
        items = [i for i in self.scene.selectedItems() if isinstance(i, NodeItem)]
        self.props.show_node(items[0].data if items else None)

    def _on_node_double_clicked(self, node_id: str) -> None:
        item = self.scene.node_item(node_id)
        if item is not None:
            self.props.show_node(item.data)

    def _on_params_changed(self, node_id: str) -> None:
        item = self.scene.node_item(node_id)
        if item is not None:
            item.refresh()

    def _on_delete_node(self, node_id: str) -> None:
        item = self.scene.node_item(node_id)
        if item is not None:
            self.scene.remove_node(item)
            self.props.show_node(None)

    def _on_palette_activated(self, raw: str) -> None:
        node_type = NodeType.from_value(raw)
        if node_type is None:
            return
        center = self.view.mapToScene(self.view.viewport().rect().center())
        item = self.scene.add_node(node_type, center, auto_connect=True)
        self.scene.clearSelection()
        item.setSelected(True)

    # ------------------------------------------------------------------ 运行
    def start_run(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if importlib.util.find_spec("pyautogui") is None:
            QMessageBox.critical(
                self,
                "缺少依赖",
                "未检测到 pyautogui。\n请先执行：\n\npip install pyautogui opencv-python pillow",
            )
            return

        doc = self.scene.to_document()
        doc.loop_count = self.loop_spin.value()
        doc.name = self.name_edit.text().strip() or "未命名流程"

        self.scene.clear_marks()
        try:
            tasks, errors = compile_flow(doc)
        except Exception as exc:  # noqa: BLE001 - 编译器意外异常不应中断界面
            QMessageBox.critical(self, "编译失败", f"流程编译出现异常：\n{exc}")
            self.log(f"✗ 编译异常：{exc}", "error")
            return
        if errors:
            bad_ids: list[str] = []
            for error in errors:
                self.log("✗ " + error.message, "error")
                bad_ids.extend(error.node_ids)
            unique = list(dict.fromkeys(bad_ids))
            self.scene.mark_errors(unique)
            if unique:
                self.scene.focus_node(unique[0])
            self.view.fit_content()
            QMessageBox.warning(self, "无法运行", "\n".join(e.message for e in errors))
            return

        rounds = doc.loop_count
        plan = "无限循环" if rounds <= 0 else f"{rounds} 轮"
        self.log(f"编译成功：{len(tasks)} 个执行步骤 · {plan}", "ok")

        self._set_running(True)
        self.worker = FlowWorker(tasks, rounds, self)
        self.worker.log_signal.connect(self._on_worker_log)
        self.worker.node_signal.connect(self.scene.highlight_node)
        self.worker.done_signal.connect(self._on_worker_done)
        self.worker.start()

        self.showMinimized()

    def stop_run(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.log("正在停止…", "warn")
            self.worker.request_stop()

    def _set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.save_btn.setEnabled(not running)
        self.load_btn.setEnabled(not running)
        self.palette.setEnabled(not running)
        self.props.setEnabled(not running)
        self.loop_spin.setEnabled(not running)

    def _on_worker_log(self, message: str) -> None:
        if message.startswith("✗"):
            level = "error"
        elif message.startswith("✓"):
            level = "ok"
        elif message.startswith("■"):
            level = "warn"
        elif message.startswith("▶"):
            level = "info"
        else:
            level = "normal"
        self.log(message, level)

    def _on_worker_done(self) -> None:
        self._set_running(False)
        self.scene.clear_running()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------ 日志
    def log(self, message: str, level: str = "normal") -> None:
        color = LOG_COLORS.get(level, LOG_COLORS["normal"])
        stamp = time.strftime("%H:%M:%S")
        self.log_view.append(
            f'<span style="color:{COLORS["text_dim"]}">{stamp}</span> '
            f'<span style="color:{color}">{html.escape(str(message))}</span>'
        )
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    # ------------------------------------------------------------------ 文件
    def save_flow(self) -> None:
        doc = self.scene.to_document()
        if doc.is_empty():
            QMessageBox.warning(self, "无法保存", "画布上还没有任何节点")
            return
        doc.name = self.name_edit.text().strip() or "未命名流程"
        doc.loop_count = self.loop_spin.value()

        default_path = self.flow_path or os.path.join(os.getcwd(), f"{doc.name}.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "保存流程", default_path, "流程文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            save_document(doc, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "保存失败", str(exc))
            return

        self.flow_path = path
        self.name_edit.setText(doc.name)
        self.log(f"已保存：{path}", "ok")

    def load_flow(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "加载流程", self.flow_path or os.getcwd(), "流程文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            doc, warnings = load_document(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "加载失败", f"{exc}")
            return

        self.scene.load_document(doc)
        self.loop_spin.setValue(max(0, int(doc.loop_count)))
        self.name_edit.setText(doc.name)
        self.flow_path = path
        self.props.show_node(None)
        self.view.fit_content()

        for warning in warnings:
            self.log("！ " + warning, "warn")
        self.log(f"已加载：{path}（{len(doc.nodes)} 个节点）", "ok")

    # ------------------------------------------------------------------ 关闭
    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)
        super().closeEvent(event)
