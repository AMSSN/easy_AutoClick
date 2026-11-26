"""连线图元：三次贝塞尔曲线 + 实心三角箭头，随节点移动实时重算。"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem

from .theme import COLORS


class EdgeItem(QGraphicsPathItem):
    """从 ``source`` 的某个输出口到 ``target`` 输入口的连线。"""

    HIT_WIDTH = 14.0
    ARROW_SIZE = 9.0

    def __init__(self, source, port: str, target):
        super().__init__()
        self.source = source
        self.port = port
        self.target = target
        self._hover = False
        self.setZValue(2)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.update_path()

    # ------------------------------------------------------------------ 几何
    def update_path(self) -> None:
        start = self.source.scene_port_pos(self.port)
        end = self.target.scene_input_pos()
        span = max(60.0, abs(end.x() - start.x()) * 0.5)
        c1 = QPointF(start.x() + span, start.y())
        c2 = QPointF(end.x() - span, end.y())
        path = QPainterPath(start)
        path.cubicTo(c1, c2, end)
        self.setPath(path)

    def boundingRect(self) -> QRectF:  # noqa: N802
        return self.path().boundingRect().adjusted(-8, -8, 8, 8)

    def shape(self) -> QPainterPath:  # noqa: N802
        stroker = QPainterPathStroker()
        stroker.setWidth(self.HIT_WIDTH)
        return stroker.createStroke(self.path())

    # ------------------------------------------------------------------ 绘制
    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        path = self.path()
        if path.isEmpty():
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor(COLORS["primary"] if self._hover else COLORS["edge"])
        pen = QPen(color, 2.6 if self._hover else 2.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # 箭头：用 99% 处的切线方向推算，避免 angleAtPercent 的坐标系歧义
        end = path.pointAtPercent(1.0)
        prev = path.pointAtPercent(0.97)
        dx, dy = end.x() - prev.x(), end.y() - prev.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            return
        ux, uy = dx / length, dy / length
        size = self.ARROW_SIZE
        base = QPointF(end.x() - ux * size, end.y() - uy * size)
        nx, ny = -uy, ux
        half = size * 0.45
        poly = QPolygonF(
            [
                end,
                QPointF(base.x() + nx * half, base.y() + ny * half),
                QPointF(base.x() - nx * half, base.y() - ny * half),
            ]
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(poly)

    # ------------------------------------------------------------------ 交互
    def hoverEnterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)
