"""右侧属性面板：按节点类型切换表单，负责参数录入与即时回写。"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.models import NODE_SPECS, POINT_TYPES, NodeData, NodeType
from .theme import COLORS

PAGE_EMPTY = 0
PAGE_POINT = 1
PAGE_TEXT = 2
PAGE_WAIT = 3
PAGE_SCROLL = 4
PAGE_HOTKEY = 5
PAGE_LOOP = 6
PAGE_IF = 7
PAGE_MARKER = 8

HOTKEY_PRESETS = [
    ("（自定义）", ""),
    ("保存 Ctrl+S", "ctrl+s"),
    ("复制 Ctrl+C", "ctrl+c"),
    ("粘贴 Ctrl+V", "ctrl+v"),
    ("撤销 Ctrl+Z", "ctrl+z"),
    ("全选 Ctrl+A", "ctrl+a"),
    ("查找 Ctrl+F", "ctrl+f"),
    ("切换窗口 Alt+Tab", "alt+tab"),
    ("关闭窗口 Alt+F4", "alt+f4"),
    ("确认 Enter", "enter"),
    ("取消 Esc", "esc"),
    ("刷新 F5", "f5"),
]


class PropertyPanel(QWidget):
    """节点参数编辑面板。"""

    params_changed = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(250)

        self.node: NodeData | None = None
        self._loading = False
        self._last_dir = os.getcwd()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("PanelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("属性")
        title.setObjectName("PanelTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(14, 14, 14, 14)
        self._container_layout.setSpacing(12)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_point_page())
        self.stack.addWidget(self._build_text_page())
        self.stack.addWidget(self._build_wait_page())
        self.stack.addWidget(self._build_scroll_page())
        self.stack.addWidget(self._build_hotkey_page())
        self.stack.addWidget(self._build_loop_page())
        self.stack.addWidget(self._build_if_page())
        self.stack.addWidget(self._build_marker_page())
        self._container_layout.addWidget(self.stack)

        self.delete_btn = QPushButton("删除此节点")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setVisible(False)
        self._container_layout.addWidget(self.delete_btn)
        self._container_layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self._connect_signals()

    # ------------------------------------------------------------------ 构造
    def _page(self, title_text: str) -> tuple[QWidget, QVBoxLayout, QLabel]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        title = QLabel(title_text)
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        return page, layout, title

    def _hint(self, layout: QVBoxLayout, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Hint")
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    def _field(self, layout: QVBoxLayout, text: str, widget: QWidget) -> QWidget:
        caption = QLabel(text)
        caption.setObjectName("FieldLabel")
        layout.addWidget(caption)
        layout.addWidget(widget)
        return caption

    # ---- 空页
    def _build_empty_page(self) -> QWidget:
        page, layout, _title = self._page("流程概览")
        self.overview_label = QLabel("未选择节点")
        self.overview_label.setWordWrap(True)
        self.overview_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self.overview_label)

        box = QFrame()
        box.setStyleSheet(
            f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_soft']};"
            "border-radius: 10px;"
        )
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(12, 12, 12, 12)
        box_layout.setSpacing(6)
        for line in (
            "· 从左侧拖拽节点到画布",
            "· 节点右侧的圆点拖出即可连线",
            "· 双击节点或选中后在此编辑参数",
            "· Delete 删除选中节点，滚轮缩放画布",
        ):
            tip = QLabel(line)
            tip.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; border: none;")
            box_layout.addWidget(tip)
        layout.addWidget(box)
        layout.addStretch()
        return page

    # ---- 图像 / 坐标
    def _build_point_page(self) -> QWidget:
        page, layout, title = self._page("动作")
        self.point_title = title

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["图像匹配", "固定位置 (x, y)"])
        self._field(layout, "定位方式", self.mode_combo)

        self.point_image_box = QWidget()
        image_layout = QVBoxLayout(self.point_image_box)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(8)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        self.image_edit = QLineEdit()
        self.image_edit.setReadOnly(True)
        self.image_edit.setPlaceholderText("尚未选择模板图片")
        self.pick_btn = QPushButton("选择…")
        self.pick_btn.setFixedWidth(64)
        row_layout.addWidget(self.image_edit, 1)
        row_layout.addWidget(self.pick_btn)
        image_layout.addWidget(row)
        image_layout.addWidget(self._make_caption("模板图片"))

        self.thumb = QLabel("未选择图片")
        self.thumb.setObjectName("Thumb")
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setMinimumHeight(132)
        image_layout.addWidget(self.thumb)
        layout.addWidget(self.point_image_box)

        self.point_coord_box = QWidget()
        coord_layout = QVBoxLayout(self.point_coord_box)
        coord_layout.setContentsMargins(0, 0, 0, 0)
        coord_layout.setSpacing(8)
        coord_row = QWidget()
        coord_row_layout = QHBoxLayout(coord_row)
        coord_row_layout.setContentsMargins(0, 0, 0, 0)
        coord_row_layout.setSpacing(8)

        self.coord_x = QSpinBox()
        self.coord_x.setRange(0, 20000)
        self.coord_y = QSpinBox()
        self.coord_y.setRange(0, 20000)
        for caption, widget in (("X", self.coord_x), ("Y", self.coord_y)):
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(4)
            label = QLabel(caption)
            label.setObjectName("FieldLabel")
            box_layout.addWidget(label)
            box_layout.addWidget(widget)
            coord_row_layout.addWidget(box)
        coord_layout.addWidget(coord_row)
        self._hint(coord_layout, "坐标为屏幕绝对像素，原点在左上角。")
        layout.addWidget(self.point_coord_box)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(-1, 9999)
        self.retry_spin.setSpecialValueText("无限重试（直到超时）")
        self._field(layout, "重试次数", self.retry_spin)

        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0, 3600)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setSingleStep(1)
        self.timeout_spin.setSuffix(" 秒")
        self._field(layout, "超时时间（0 表示不限）", self.timeout_spin)

        self._hint(layout, "图像匹配需要模板图，建议截图时只保留控件主体，避免动态内容。")
        layout.addStretch()
        return page

    def _make_caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    # ---- 文本
    def _build_text_page(self) -> QWidget:
        page, layout, _title = self._page("文本输入")
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("要输入的文本内容，支持多行")
        self.text_edit.setFixedHeight(120)
        self._field(layout, "文本内容", self.text_edit)

        self.text_delay = QDoubleSpinBox()
        self.text_delay.setRange(0, 10)
        self.text_delay.setDecimals(2)
        self.text_delay.setSingleStep(0.1)
        self.text_delay.setSuffix(" 秒")
        self._field(layout, "输入后等待", self.text_delay)
        self._hint(layout, "通过剪贴板粘贴实现，可输入中文；请确保目标输入框已获得焦点。")
        layout.addStretch()
        return page

    # ---- 等待
    def _build_wait_page(self) -> QWidget:
        page, layout, _title = self._page("等待")
        self.wait_seconds = QDoubleSpinBox()
        self.wait_seconds.setRange(0, 3600)
        self.wait_seconds.setDecimals(2)
        self.wait_seconds.setSingleStep(0.5)
        self.wait_seconds.setSuffix(" 秒")
        self._field(layout, "等待时长", self.wait_seconds)
        self._hint(layout, "等待期间点击「停止」可立即中断。")
        layout.addStretch()
        return page

    # ---- 滚轮
    def _build_scroll_page(self) -> QWidget:
        page, layout, _title = self._page("滚轮")
        self.scroll_amount = QSpinBox()
        self.scroll_amount.setRange(-100, 100)
        self._field(layout, "滚动刻度（正数向上，负数向下）", self.scroll_amount)
        self.scroll_hint = QLabel("")
        self.scroll_hint.setStyleSheet(f"color: {COLORS['primary']};")
        layout.addWidget(self.scroll_hint)
        self._hint(layout, "1 格约等于鼠标滚轮滚动一格。")
        layout.addStretch()
        return page

    # ---- 快捷键
    def _build_hotkey_page(self) -> QWidget:
        page, layout, _title = self._page("快捷键")
        self.hotkey_combo = QComboBox()
        for label, value in HOTKEY_PRESETS:
            self.hotkey_combo.addItem(label, value)
        self._field(layout, "常用组合", self.hotkey_combo)

        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setPlaceholderText("例如 ctrl+shift+s 或 enter")
        self._field(layout, "按键组合", self.hotkey_edit)

        self.hotkey_delay = QDoubleSpinBox()
        self.hotkey_delay.setRange(0, 10)
        self.hotkey_delay.setDecimals(2)
        self.hotkey_delay.setSingleStep(0.1)
        self.hotkey_delay.setSuffix(" 秒")
        self._field(layout, "按键后等待", self.hotkey_delay)
        self._hint(layout, "多个键用 + 连接；单键（如 enter / esc / f5）直接填写即可。")
        layout.addStretch()
        return page

    # ---- 循环
    def _build_loop_page(self) -> QWidget:
        page, layout, _title = self._page("循环开始")
        self.loop_count_spin = QSpinBox()
        self.loop_count_spin.setRange(1, 9999)
        self.loop_count_spin.setSuffix(" 次")
        self._field(layout, "循环次数", self.loop_count_spin)
        self._hint(layout, "循环体为「循环开始」到「循环结束」之间的所有节点。")
        layout.addStretch()
        return page

    # ---- 条件
    def _build_if_page(self) -> QWidget:
        page, layout, _title = self._page("如果存在图像")
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        self.if_image_edit = QLineEdit()
        self.if_image_edit.setReadOnly(True)
        self.if_image_edit.setPlaceholderText("尚未选择条件图片")
        self.if_pick_btn = QPushButton("选择…")
        self.if_pick_btn.setFixedWidth(64)
        row_layout.addWidget(self.if_image_edit, 1)
        row_layout.addWidget(self.if_pick_btn)
        # 必须挂到页面上，否则 row 无父对象会被 Python 回收，其子控件随之销毁
        layout.addWidget(self._make_caption("条件图片"))
        layout.addWidget(row)

        self.if_thumb = QLabel("未选择图片")
        self.if_thumb.setObjectName("Thumb")
        self.if_thumb.setAlignment(Qt.AlignCenter)
        self.if_thumb.setMinimumHeight(132)
        layout.addWidget(self.if_thumb)

        self._hint(
            layout,
            "把「是」「否」两个输出口分别接到两条分支，两条分支最终汇合到同一个「结束条件」节点。",
        )
        layout.addStretch()
        return page

    # ---- 结构标记
    def _build_marker_page(self) -> QWidget:
        page, layout, title = self._page("流程控制")
        self.marker_title = title
        self.marker_desc = QLabel("")
        self.marker_desc.setWordWrap(True)
        self.marker_desc.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self.marker_desc)
        self._hint(layout, "此节点用于标记结构范围，不需要额外参数。")
        layout.addStretch()
        return page

    # ------------------------------------------------------------------ 信号
    def _connect_signals(self) -> None:
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.pick_btn.clicked.connect(lambda: self._pick_image(self.image_edit, self.thumb))
        self.if_pick_btn.clicked.connect(lambda: self._pick_image(self.if_image_edit, self.if_thumb))
        self.text_edit.textChanged.connect(self._commit)
        self.hotkey_edit.textEdited.connect(self._commit)
        self.hotkey_combo.currentIndexChanged.connect(self._on_preset_changed)

        for widget in (
            self.coord_x,
            self.coord_y,
            self.retry_spin,
            self.scroll_amount,
            self.loop_count_spin,
        ):
            widget.valueChanged.connect(self._commit)
        for widget in (self.timeout_spin, self.text_delay, self.wait_seconds, self.hotkey_delay):
            widget.valueChanged.connect(self._commit)

    def _on_mode_changed(self, _index: int) -> None:
        self._refresh_mode_visibility()
        self._commit()

    def _on_preset_changed(self, _index: int) -> None:
        value = self.hotkey_combo.currentData()
        if self._loading or not value:
            return
        self._loading = True
        self.hotkey_edit.setText(str(value))
        self._loading = False
        self._commit()

    def _refresh_mode_visibility(self) -> None:
        coord = self.mode_combo.currentIndex() == 1
        self.point_image_box.setVisible(not coord)
        self.point_coord_box.setVisible(coord)

    # ------------------------------------------------------------------ 外部接口
    def set_overview(self, text: str) -> None:
        self.overview_label.setText(text)

    def show_node(self, data: NodeData | None) -> None:
        self.node = data
        if data is None:
            self.stack.setCurrentIndex(PAGE_EMPTY)
            self.delete_btn.setVisible(False)
            return

        self._loading = True
        try:
            page = self._page_for(data.type)
            self.stack.setCurrentIndex(page)
            self.delete_btn.setVisible(True)
            self._fill(data, page)
        finally:
            self._loading = False

    def refresh_from_node(self) -> None:
        if self.node is not None:
            self.show_node(self.node)

    @staticmethod
    def _page_for(node_type: NodeType) -> int:
        if node_type in POINT_TYPES:
            return PAGE_POINT
        return {
            NodeType.TEXT_INPUT: PAGE_TEXT,
            NodeType.WAIT: PAGE_WAIT,
            NodeType.SCROLL: PAGE_SCROLL,
            NodeType.HOTKEY: PAGE_HOTKEY,
            NodeType.LOOP_START: PAGE_LOOP,
            NodeType.IF_IMAGE: PAGE_IF,
        }.get(node_type, PAGE_MARKER)

    def _fill(self, data: NodeData, page: int) -> None:
        params = data.params
        if page == PAGE_POINT:
            self.point_title.setText(data.type.spec.title)
            mode = str(params.get("mode") or "image")
            self.mode_combo.setCurrentIndex(1 if mode == "coord" else 0)
            self.image_edit.setText(str(params.get("image") or ""))
            self._update_thumb(self.thumb, str(params.get("image") or ""))
            self.coord_x.setValue(int(params.get("x", 0) or 0))
            self.coord_y.setValue(int(params.get("y", 0) or 0))
            retry = int(params.get("retry", 1) if params.get("retry") not in (None, "") else 1)
            self.retry_spin.setValue(max(-1, retry))
            self.timeout_spin.setValue(float(params.get("timeout", 60) or 0))
            self._refresh_mode_visibility()
        elif page == PAGE_TEXT:
            self.text_edit.setPlainText(str(params.get("text") or ""))
            self.text_delay.setValue(float(params.get("delay", 0.3) or 0))
        elif page == PAGE_WAIT:
            self.wait_seconds.setValue(float(params.get("seconds", 1) or 0))
        elif page == PAGE_SCROLL:
            self.scroll_amount.setValue(int(params.get("amount", 0) or 0))
            self._update_scroll_hint()
        elif page == PAGE_HOTKEY:
            keys = str(params.get("keys") or "")
            self.hotkey_edit.setText(keys)
            index = self.hotkey_combo.findData(keys)
            self.hotkey_combo.setCurrentIndex(index if index >= 0 else 0)
            self.hotkey_delay.setValue(float(params.get("delay", 0.2) or 0))
        elif page == PAGE_LOOP:
            self.loop_count_spin.setValue(max(1, int(params.get("count", 1) or 1)))
        elif page == PAGE_IF:
            self.if_image_edit.setText(str(params.get("image") or ""))
            self._update_thumb(self.if_thumb, str(params.get("image") or ""))
        elif page == PAGE_MARKER:
            spec = data.type.spec
            self.marker_title.setText(spec.title)
            self.marker_desc.setText(spec.description)

    # ------------------------------------------------------------------ 回写
    def _commit(self, *_args) -> None:
        if self._loading or self.node is None:
            return
        params = self.node.params
        page = self._page_for(self.node.type)
        if page == PAGE_POINT:
            params["mode"] = "coord" if self.mode_combo.currentIndex() == 1 else "image"
            params["image"] = self.image_edit.text()
            params["x"] = self.coord_x.value()
            params["y"] = self.coord_y.value()
            params["retry"] = self.retry_spin.value()
            params["timeout"] = self.timeout_spin.value()
        elif page == PAGE_TEXT:
            params["text"] = self.text_edit.toPlainText()
            params["delay"] = self.text_delay.value()
        elif page == PAGE_WAIT:
            params["seconds"] = self.wait_seconds.value()
        elif page == PAGE_SCROLL:
            params["amount"] = self.scroll_amount.value()
            self._update_scroll_hint()
        elif page == PAGE_HOTKEY:
            params["keys"] = self.hotkey_edit.text().strip()
            params["delay"] = self.hotkey_delay.value()
        elif page == PAGE_LOOP:
            params["count"] = self.loop_count_spin.value()
        elif page == PAGE_IF:
            params["image"] = self.if_image_edit.text()
        self.params_changed.emit(self.node.id)

    def _update_scroll_hint(self) -> None:
        value = self.scroll_amount.value()
        if value > 0:
            text = f"向上滚动 {value} 格"
        elif value < 0:
            text = f"向下滚动 {-value} 格"
        else:
            text = "不滚动（0 格）"
        self.scroll_hint.setText(text)

    # ------------------------------------------------------------------ 图片
    def _pick_image(self, line_edit: QLineEdit, thumb: QLabel) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择模板图片",
            self._last_dir,
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*.*)",
        )
        if not filename:
            return
        self._last_dir = os.path.dirname(filename)
        self._loading = True
        line_edit.setText(filename)
        self._update_thumb(thumb, filename)
        self._loading = False
        self._commit()

    @staticmethod
    def _update_thumb(label: QLabel, path: str) -> None:
        def show_text(text: str) -> None:
            # QLabel 一旦进入 pixmap 模式就不再显示文本，必须先 clear()
            label.clear()
            label.setText(text)

        if not path:
            show_text("未选择图片")
            return
        if not os.path.exists(path):
            show_text("图片文件不存在")
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            show_text("无法读取图片")
            return
        label.setText("")
        label.setPixmap(
            pixmap.scaled(246, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    # ------------------------------------------------------------------ 删除
    def _on_delete(self) -> None:
        if self.node is not None:
            self.delete_requested.emit(self.node.id)

    # ------------------------------------------------------------------ 兼容
    def describe(self) -> str:
        if self.node is None:
            return ""
        return f"{NODE_SPECS[self.node.type].title} · {self.node.summary()}"
