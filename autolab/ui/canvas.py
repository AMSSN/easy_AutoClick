"""流程画布：场景（图模型 + 拖放 + 连线）与视图（缩放 / 平移 / 右键菜单）。"""

from __future__ import annotations

from PySide6.QtCore import QLineF, QMimeData, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
)

from ..core.models import Edge, FlowDocument, NodeData, NodeType
from .edge_item import EdgeItem
from .node_item import CARD_W, NodeItem
from .theme import COLORS

MIME_NODE = "application/x-autolab-node"


class FlowScene(QGraphicsScene):
    """持有节点与连线的场景。"""

    graph_changed = Signal()
    node_double_clicked = Signal(str)
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-3000, -3000, 6000, 6000)
        self.node_items: dict[str, NodeItem] = {}
        self.edge_items: list[EdgeItem] = []
        self._preview: QGraphicsPathItem | None = None
        self._edge_source: NodeItem | None = None
        self._edge_port: str | None = None
        self._running_item: NodeItem | None = None

    # ------------------------------------------------------------------ 背景
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        painter.fillRect(rect, QColor(COLORS["bg_canvas"]))
        painter.setRenderHint(QPainter.Antialiasing, False)

        minor, major = 24, 120
        left = int(rect.left()) - (int(rect.left()) % minor)
        top = int(rect.top()) - (int(rect.top()) % minor)

        minor_lines = []
        major_lines = []
        x = left
        while x < rect.right():
            target = major_lines if x % major == 0 else minor_lines
            target.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += minor
        y = top
        while y < rect.bottom():
            target = major_lines if y % major == 0 else minor_lines
            target.append(QLineF(rect.left(), y, rect.right(), y))
            y += minor

        painter.setPen(QPen(QColor(COLORS["grid_minor"]), 1))
        painter.drawLines(minor_lines)
        painter.setPen(QPen(QColor(COLORS["grid_major"]), 1))
        painter.drawLines(major_lines)

    # ------------------------------------------------------------------ 拖放
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_NODE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_NODE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(MIME_NODE):
            super().dropEvent(event)
            return
        raw = bytes(event.mimeData().data(MIME_NODE)).decode("utf-8")
        node_type = NodeType.from_value(raw)
        if node_type is None:
            event.ignore()
            return
        self.add_node(node_type, event.scenePos(), auto_connect=True)
        event.acceptProposedAction()

    # ------------------------------------------------------------------ 节点
    def add_node(
        self,
        node_type: NodeType,
        scene_pos: QPointF,
        auto_connect: bool = True,
        data: NodeData | None = None,
    ) -> NodeItem:
        created = data is None
        node = data or NodeData.create(
            node_type,
            scene_pos.x() - CARD_W / 2.0,
            scene_pos.y() - 32.0,
        )
        item = NodeItem(node, self)
        self.addItem(item)
        item.setPos(node.x, node.y)
        item.double_clicked.connect(self.node_double_clicked)
        self.node_items[node.id] = item

        if created and auto_connect:
            self.auto_connect(item)
        self.graph_changed.emit()
        return item

    def node_item(self, node_id: str) -> NodeItem | None:
        return self.node_items.get(node_id)

    def node_at(self, scene_pos: QPointF) -> NodeItem | None:
        for item in self.items(scene_pos):
            if isinstance(item, NodeItem):
                return item
        return None

    def remove_node(self, item: NodeItem) -> None:
        node_id = item.data.id
        for edge in list(self.edge_items):
            if edge.source is item or edge.target is item:
                self._drop_edge(edge)
        self.node_items.pop(node_id, None)
        if self._running_item is item:
            self._running_item = None
        self.removeItem(item)
        self.graph_changed.emit()

    def remove_selected(self) -> int:
        removed = 0
        for item in list(self.selectedItems()):
            if isinstance(item, NodeItem):
                self.remove_node(item)
                removed += 1
        return removed

    # ------------------------------------------------------------------ 连线
    def create_edge(self, source: NodeItem, port: str, target: NodeItem) -> EdgeItem | None:
        if source is target:
            self.message.emit("不能连接到自身")
            return None
        if port not in source.spec.outputs:
            return None
        if self._would_cycle(source, target):
            self.message.emit("无法连接：会形成环路")
            return None

        for edge in list(self.edge_items):
            if edge.source is source and edge.port == port:
                self._drop_edge(edge)
        # 「结束条件」是两条分支的汇合点，必须能接收多条入边；
        # 其余节点作为顺序流的一环，输入口只保留一条入边。
        if target.data.type != NodeType.END_IF:
            for edge in list(self.edge_items):
                if edge.target is target:
                    self._drop_edge(edge)

        edge = EdgeItem(source, port, target)
        self.addItem(edge)
        self.edge_items.append(edge)
        self.graph_changed.emit()
        return edge

    def edge_from(self, node_id: str, port: str) -> EdgeItem | None:
        for edge in self.edge_items:
            if edge.source.data.id == node_id and edge.port == port:
                return edge
        return None

    def out_edges(self, node_id: str) -> list[EdgeItem]:
        return [e for e in self.edge_items if e.source.data.id == node_id]

    def _drop_edge(self, edge: EdgeItem) -> None:
        if edge in self.edge_items:
            self.edge_items.remove(edge)
        self.removeItem(edge)

    def remove_edge(self, edge: EdgeItem) -> None:
        self._drop_edge(edge)
        self.graph_changed.emit()

    def disconnect_all(self) -> None:
        for edge in list(self.edge_items):
            self._drop_edge(edge)
        self.graph_changed.emit()

    def free_port(self, item: NodeItem) -> str | None:
        for port in item.spec.outputs:
            if self.edge_from(item.data.id, port) is None:
                return port
        return None

    def _would_cycle(self, source: NodeItem, target: NodeItem) -> bool:
        stack = [target.data.id]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == source.data.id:
                return True
            if current in seen:
                continue
            seen.add(current)
            for edge in self.edge_items:
                if edge.source.data.id == current:
                    stack.append(edge.target.data.id)
        return False

    def refresh_edges(self, node_id: str | None = None) -> None:
        for edge in self.edge_items:
            if (
                node_id is None
                or edge.source.data.id == node_id
                or edge.target.data.id == node_id
            ):
                edge.update_path()

    # ------------------------------------------------------------------ 自动串联
    def auto_connect(self, item: NodeItem) -> None:
        """把新节点接到链尾：优先接当前选中节点，否则接唯一的叶子节点。"""
        others = [n for n in self.node_items.values() if n is not item]
        if not others:
            return

        source: NodeItem | None = None
        port: str | None = None

        for candidate in self.selectedItems():
            if isinstance(candidate, NodeItem) and candidate is not item:
                free = self.free_port(candidate)
                if free:
                    source, port = candidate, free
                    break

        if source is None:
            leaves = [
                n
                for n in others
                if not self.out_edges(n.data.id)
                and n.data.type not in (NodeType.END_IF, NodeType.LOOP_END, NodeType.ELSE)
            ]
            if len(leaves) == 1:
                free = self.free_port(leaves[0])
                if free:
                    source, port = leaves[0], free

        if source is not None and port is not None:
            edge = self.create_edge(source, port, item)
            if edge is not None:
                # 落在来源节点下方，避免叠在一起
                target_y = source.y() + source.card_height() + 46
                if abs(item.y() - target_y) < 30:
                    item.setPos(source.x(), target_y)

    # ------------------------------------------------------------------ 连线拖拽
    def begin_edge_drag(self, item: NodeItem, port: str) -> None:
        self._edge_source = item
        self._edge_port = port
        if self._preview is None:
            preview = QGraphicsPathItem()
            pen = QPen(QColor(COLORS["primary"]), 1.8, Qt.DashLine)
            pen.setDashPattern([4, 4])
            preview.setPen(pen)
            preview.setBrush(Qt.NoBrush)
            preview.setZValue(30)
            self.addItem(preview)
            self._preview = preview

    def update_edge_drag(self, scene_pos: QPointF) -> None:
        if self._edge_source is None or self._edge_port is None or self._preview is None:
            return
        start = self._edge_source.scene_port_pos(self._edge_port)
        span = max(50.0, abs(scene_pos.x() - start.x()) * 0.5)
        path = QPainterPath(start)
        path.cubicTo(
            QPointF(start.x() + span, start.y()),
            QPointF(scene_pos.x() - span, scene_pos.y()),
            scene_pos,
        )
        self._preview.setPath(path)

    def end_edge_drag(self, item: NodeItem, port: str | None, scene_pos: QPointF) -> None:
        if self._preview is not None:
            self.removeItem(self._preview)
            self._preview = None
        self._edge_source = None
        self._edge_port = None
        if port is None:
            return

        target = self.node_at(scene_pos)
        if target is None or target is item:
            return
        self.create_edge(item, port, target)

    # ------------------------------------------------------------------ 运行态
    def highlight_node(self, node_id: str) -> None:
        if self._running_item is not None:
            self._running_item.set_running(False)
        item = self.node_items.get(node_id)
        if item is not None:
            item.set_running(True)
            self._running_item = item
        else:
            self._running_item = None

    def clear_running(self) -> None:
        if self._running_item is not None:
            self._running_item.set_running(False)
            self._running_item = None

    def mark_errors(self, node_ids) -> None:
        for node_id in node_ids:
            item = self.node_items.get(node_id)
            if item is not None:
                item.set_error(True)

    def clear_marks(self) -> None:
        for item in self.node_items.values():
            item.set_error(False)

    def focus_node(self, node_id: str) -> None:
        item = self.node_items.get(node_id)
        if item is not None:
            self.clearSelection()
            item.setSelected(True)
            self.views() and self.views()[0].centerOn(item)

    # ------------------------------------------------------------------ 文档
    def to_document(self) -> FlowDocument:
        doc = FlowDocument()
        for item in self.node_items.values():
            doc.add_node(item.data)
        for edge in self.edge_items:
            doc.edges.append(Edge(edge.source.data.id, edge.port, edge.target.data.id))
        return doc

    def load_document(self, doc: FlowDocument) -> None:
        self.clear_all()
        for node in doc.nodes.values():
            item = NodeItem(node, self)
            self.addItem(item)
            item.setPos(node.x, node.y)
            item.double_clicked.connect(self.node_double_clicked)
            self.node_items[node.id] = item
        for edge in doc.edges:
            source = self.node_items.get(edge.source)
            target = self.node_items.get(edge.target)
            if source is None or target is None:
                continue
            edge_item = EdgeItem(source, edge.port, target)
            self.addItem(edge_item)
            self.edge_items.append(edge_item)
        self.graph_changed.emit()

    def clear_all(self) -> None:
        for edge in list(self.edge_items):
            self._drop_edge(edge)
        for item in list(self.node_items.values()):
            self.removeItem(item)
        self.node_items.clear()
        self._running_item = None
        self.graph_changed.emit()

    def node_count(self) -> int:
        return len(self.node_items)

    # ------------------------------------------------------------------ 布局
    def auto_layout(self) -> None:
        if not self.node_items:
            return
        depth = {nid: 0 for nid in self.node_items}
        for _ in range(len(self.node_items) + 2):
            changed = False
            for edge in self.edge_items:
                want = depth[edge.source.data.id] + 1
                if depth[edge.target.data.id] < want:
                    depth[edge.target.data.id] = want
                    changed = True
            if not changed:
                break

        layers: dict[int, list[str]] = {}
        for node_id, level in depth.items():
            layers.setdefault(level, []).append(node_id)

        center_x = 420.0
        for level in sorted(layers):
            row = sorted(layers[level], key=lambda nid: self.node_items[nid].x())
            count = len(row)
            for index, node_id in enumerate(row):
                item = self.node_items[node_id]
                item.setPos(center_x + (index - (count - 1) / 2.0) * 268.0, 70.0 + level * 152.0)
        self.refresh_edges()


class FlowView(QGraphicsView):
    """带缩放、平移与右键菜单的画布视图。"""

    zoom_changed = Signal(float)

    MIN_ZOOM = 0.3
    MAX_ZOOM = 2.5

    def __init__(self, scene: FlowScene, parent=None):
        super().__init__(scene, parent)
        self.setObjectName("Canvas")
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        self._zoom = 1.0
        self._panning = False
        self._pan_origin = QPoint()

    # ------------------------------------------------------------------ 缩放
    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        factor = 1.12 if delta > 0 else 1 / 1.12
        target = self._zoom * factor
        if target < self.MIN_ZOOM or target > self.MAX_ZOOM:
            event.accept()
            return
        self._zoom = target
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom)
        event.accept()

    def zoom_by(self, factor: float) -> None:
        target = self._zoom * factor
        if target < self.MIN_ZOOM or target > self.MAX_ZOOM:
            return
        self._zoom = target
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom)

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)

    def fit_content(self) -> None:
        scene = self.scene()
        if scene is None:
            return
        rect = scene.itemsBoundingRect()
        if rect.isEmpty():
            self.reset_zoom()
            return
        self.fitInView(rect.adjusted(-60, -60, 60, 60), Qt.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self._zoom)

    # ------------------------------------------------------------------ 平移
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_origin = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            current = event.position().toPoint()
            delta = current - self._pan_origin
            self._pan_origin = current
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------ 键盘
    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            scene = self.scene()
            if isinstance(scene, FlowScene):
                scene.remove_selected()
                event.accept()
                return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------ 菜单
    def contextMenuEvent(self, event) -> None:  # noqa: N802
        scene = self.scene()
        if not isinstance(scene, FlowScene):
            return
        menu = QMenu(self)
        hovered = self.itemAt(event.pos())
        edge_action = None
        if isinstance(hovered, EdgeItem):
            edge_action = menu.addAction("删除该连线")
            menu.addSeparator()

        layout_action = menu.addAction("自动整理布局")
        fit_action = menu.addAction("适应窗口")
        menu.addSeparator()
        disconnect_action = menu.addAction("全部断开连线")
        delete_action = menu.addAction("删除选中节点")
        delete_action.setEnabled(bool(scene.selectedItems()))

        chosen = menu.exec(event.globalPos())
        if edge_action is not None and chosen is edge_action:
            scene.remove_edge(hovered)
        elif chosen is layout_action:
            scene.auto_layout()
            self.fit_content()
        elif chosen is fit_action:
            self.fit_content()
        elif chosen is disconnect_action:
            scene.disconnect_all()
        elif chosen is delete_action:
            scene.remove_selected()
