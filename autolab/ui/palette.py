"""左侧节点库：分组列出所有可用操作，支持拖拽到画布。"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..core.models import CAT_ACTION, CAT_FLOW, NODE_SPECS, NodeType
from .canvas import MIME_NODE
from .theme import COLORS, FONT_FAMILY

_ROLE_TYPE = Qt.UserRole


def _chip_icon(accent: str, glyph: str) -> QIcon:
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    color = QColor(accent)
    background = QColor(color)
    background.setAlpha(60)
    painter.setPen(Qt.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(0, 0, 20, 20), 6, 6)
    font = QFont(FONT_FAMILY)
    font.setPointSizeF(8.0)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(color)
    painter.drawText(QRectF(0, 0, 20, 20), Qt.AlignCenter, glyph)
    painter.end()
    return QIcon(pixmap)


class _PaletteTree(QTreeWidget):
    """拖拽源：把节点类型写入自定义 MIME，并画一张半透明卡片作为拖动影像。"""

    def startDrag(self, supported_actions) -> None:  # noqa: N802
        item = self.currentItem()
        if item is None:
            return
        raw = item.data(0, _ROLE_TYPE)
        if not raw:
            return
        node_type = NodeType.from_value(str(raw))
        if node_type is None:
            return

        mime = QMimeData()
        mime.setData(MIME_NODE, str(raw).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self._drag_pixmap(node_type))
        drag.setHotSpot(QPoint(30, 22))
        drag.exec(Qt.CopyAction)

    @staticmethod
    def _drag_pixmap(node_type: NodeType) -> QPixmap:
        spec = NODE_SPECS[node_type]
        pixmap = QPixmap(220, 46)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setOpacity(0.92)

        path = QPainterPath()
        path.addRoundedRect(QRectF(1, 1, 218, 44), 10, 10)
        painter.setPen(QPen(QColor(spec.accent), 1.4))
        painter.setBrush(QColor("#1E222B"))
        painter.drawPath(path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(spec.accent))
        painter.drawRoundedRect(QRectF(1, 1, 4, 44), 2, 2)

        font = QFont(FONT_FAMILY)
        font.setPointSizeF(9.6)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text"]))
        painter.drawText(QRectF(18, 6, 190, 18), Qt.AlignLeft | Qt.AlignVCenter, spec.title)

        font.setPointSizeF(8.2)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(QRectF(18, 24, 190, 16), Qt.AlignLeft | Qt.AlignVCenter, spec.description)
        painter.end()
        return pixmap


class NodePalette(QWidget):
    """节点面板。"""

    node_activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)

        header = QLabel("节点库")
        header.setObjectName("PanelTitle")
        layout.addWidget(header)

        self.tree = _PaletteTree()
        self.tree.setObjectName("Palette")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(12)
        self.tree.setAnimated(True)
        self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QTreeWidget.DragOnly)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setFocusPolicy(Qt.NoFocus)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self.tree, 1)

        hint = QLabel("拖拽到画布添加节点\n双击可添加到画布中心")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._populate()

    def _populate(self) -> None:
        groups = {CAT_ACTION: None, CAT_FLOW: None}
        for category in (CAT_ACTION, CAT_FLOW):
            group = QTreeWidgetItem(self.tree)
            group.setText(0, category)
            group.setFlags(Qt.ItemIsEnabled)
            font = group.font(0)
            font.setBold(True)
            font.setPointSizeF(8.6)
            group.setFont(0, font)
            group.setForeground(0, QColor(COLORS["text_dim"]))
            group.setExpanded(True)
            groups[category] = group

        for spec in NODE_SPECS.values():
            parent = groups.get(spec.category)
            if parent is None:
                continue
            item = QTreeWidgetItem(parent)
            item.setText(0, spec.title)
            item.setIcon(0, _chip_icon(spec.accent, spec.glyph))
            item.setToolTip(0, spec.description)
            item.setData(0, _ROLE_TYPE, spec.type.value)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

    def _on_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        raw = item.data(0, _ROLE_TYPE)
        if raw:
            self.node_activated.emit(str(raw))
