"""画布节点图元。

一张圆角卡片：左侧类别色条 + 字形徽标 + 标题 + 参数摘要，图像类节点底部内嵌缩略图。
右侧输出口可拖出连线，条件节点有「是 / 否」两个输出口。
"""

from __future__ import annotations

import os

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from ..core.models import NODE_SPECS, PORT_LABELS, NodeData, NodeSpec
from .theme import COLORS, FONT_FAMILY

CARD_W = 208.0
CARD_RADIUS = 12.0
PORT_R = 5.5
SNAP = 4.0


class NodeItem(QGraphicsObject):
    """画布上的一个节点。"""

    double_clicked = Signal(str)

    def __init__(self, data: NodeData, scene_ref=None, parent=None):
        super().__init__(parent)
        self.data = data
        self.scene_ref = scene_ref
        self.spec: NodeSpec = NODE_SPECS[data.type]
        self._hover = False
        self._hover_port: str | None = None
        self._drag_port: str | None = None
        self._dragging_edge = False
        self._running = False
        self._error = False
        self._thumb: QPixmap | None = None
        self._thumb_missing = False

        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self.setPos(data.x, data.y)
        self.refresh_thumb()

    # ------------------------------------------------------------------ 尺寸
    def card_height(self) -> float:
        if self._has_thumb():
            return 106.0
        if len(self.spec.outputs) > 1:
            return 78.0
        return 64.0

    def _has_thumb(self) -> bool:
        """只有「图像匹配」模式的动作节点才展示缩略图条。"""
        if not self.spec.image or len(self.spec.outputs) != 1:
            return False
        return str(self.data.params.get("mode") or "image") != "coord"

    def boundingRect(self) -> QRectF:  # noqa: N802 - Qt 接口
        return QRectF(-14, -14, CARD_W + 30, self.card_height() + 30)

    def shape(self) -> QPainterPath:  # noqa: N802 - Qt 接口
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, CARD_W, self.card_height()), CARD_RADIUS, CARD_RADIUS)
        for port in self.spec.outputs:
            center = self.output_port_pos(port)
            path.addEllipse(center, PORT_R + 7, PORT_R + 7)
        return path

    # ------------------------------------------------------------------ 端口
    def input_port_pos(self) -> QPointF:
        return QPointF(0.0, self.card_height() / 2.0)

    def output_port_pos(self, port: str) -> QPointF:
        height = self.card_height()
        if len(self.spec.outputs) == 1:
            return QPointF(CARD_W, height / 2.0)
        if port == "true":
            return QPointF(CARD_W, height * 0.30)
        return QPointF(CARD_W, height * 0.70)

    def scene_port_pos(self, port: str) -> QPointF:
        return self.mapToScene(self.output_port_pos(port))

    def scene_input_pos(self) -> QPointF:
        return self.mapToScene(self.input_port_pos())

    def output_port_at(self, item_pos: QPointF) -> str | None:
        for port in self.spec.outputs:
            if QLineF(self.output_port_pos(port), item_pos).length() <= PORT_R + 9:
                return port
        return None

    # ------------------------------------------------------------------ 状态
    def set_running(self, running: bool) -> None:
        if self._running != running:
            self._running = running
            self.update()

    def set_error(self, error: bool) -> None:
        if self._error != error:
            self._error = error
            self.update()

    def refresh_thumb(self) -> None:
        self._thumb = None
        self._thumb_missing = False
        if not self.spec.image:
            return
        path = self.data.image_path()
        if not path:
            return
        if not os.path.exists(path):
            self._thumb_missing = True
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._thumb_missing = True
            return
        self._thumb = pixmap

    def refresh(self) -> None:
        """参数变化后刷新摘要、缩略图与卡片高度（可能从图像模式切到坐标模式）。"""
        self.prepareGeometryChange()
        self.refresh_thumb()
        if self.scene_ref is not None:
            self.scene_ref.refresh_edges(self.data.id)
        self.update()

    # ------------------------------------------------------------------ 绘制
    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        height = self.card_height()
        rect = QRectF(0, 0, CARD_W, height)
        card = QPainterPath()
        card.addRoundedRect(rect, CARD_RADIUS, CARD_RADIUS)
        accent = QColor(self.spec.accent)

        # ---- 外发光：错误 > 运行 > 选中
        glow = None
        if self._error:
            glow = QColor(COLORS["danger"])
        elif self._running:
            glow = QColor(COLORS["success"])
        elif self.isSelected():
            glow = QColor(COLORS["primary"])
        if glow is not None:
            painter.setBrush(Qt.NoBrush)
            for i, alpha in enumerate((72, 42, 20)):
                pen = QPen(QColor(glow.red(), glow.green(), glow.blue(), alpha), 4.0 + i * 3.0)
                shape = QPainterPath()
                shape.addRoundedRect(rect.adjusted(-i * 1.6, -i * 1.6, i * 1.6, i * 1.6),
                                     CARD_RADIUS + i, CARD_RADIUS + i)
                painter.setPen(pen)
                painter.drawPath(shape)

        # ---- 底色
        gradient = QLinearGradient(0, 0, 0, height)
        if self.isSelected():
            gradient.setColorAt(0.0, QColor("#28313F"))
            gradient.setColorAt(1.0, QColor("#1D2330"))
        else:
            gradient.setColorAt(0.0, QColor("#232935"))
            gradient.setColorAt(1.0, QColor("#1A1E26"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(card)

        # ---- 类别色条
        painter.save()
        painter.setClipPath(card)
        painter.fillRect(QRectF(0, 0, 4.0, height), accent)
        painter.restore()

        # ---- 边框
        if self._error:
            border = QColor(COLORS["danger"])
        elif self._running:
            border = QColor(COLORS["success"])
        elif self.isSelected():
            border = QColor(COLORS["primary"])
        elif self._hover:
            border = QColor("#3B4456")
        else:
            border = QColor("#2A3140")
        painter.setPen(QPen(border, 2.0 if (self._error or self._running or self.isSelected()) else 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(card)

        # ---- 字形徽标
        chip = QRectF(14, 13, 24, 24)
        chip_path = QPainterPath()
        chip_path.addRoundedRect(chip, 7, 7)
        chip_color = QColor(accent)
        chip_color.setAlpha(46)
        painter.setPen(Qt.NoPen)
        painter.setBrush(chip_color)
        painter.drawPath(chip_path)

        glyph_font = QFont(FONT_FAMILY)
        glyph_font.setPointSizeF(9.5)
        glyph_font.setBold(True)
        painter.setFont(glyph_font)
        painter.setPen(accent)
        painter.drawText(chip, Qt.AlignCenter, self.spec.glyph)

        # ---- 标题
        title_font = QFont(FONT_FAMILY)
        title_font.setPointSizeF(9.8)
        title_font.setWeight(QFont.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(COLORS["text"]))
        painter.drawText(QRectF(46, 13, CARD_W - 60, 24), Qt.AlignLeft | Qt.AlignVCenter, self.spec.title)

        # ---- 摘要
        summary_font = QFont(FONT_FAMILY)
        summary_font.setPointSizeF(8.4)
        painter.setFont(summary_font)
        painter.setPen(QColor(COLORS["text_muted"]))
        summary_rect = QRectF(14, 38, CARD_W - 28, 16)
        painter.drawText(
            summary_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            self._elided(self.data.summary(), summary_font, summary_rect.width()),
        )

        # ---- 缩略图
        if self._has_thumb():
            self._paint_thumb(painter, QRectF(14, 56, CARD_W - 28, 40), summary_font)

        # ---- 端口
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#4A5265"), 2.0))
        painter.setBrush(QColor(COLORS["bg_card"]))
        painter.drawEllipse(self.input_port_pos(), PORT_R, PORT_R)

        for port in self.spec.outputs:
            center = self.output_port_pos(port)
            hovered = self._hover_port == port
            color = QColor(COLORS["primary"]) if hovered else QColor(self.spec.accent)
            painter.setPen(QPen(QColor("#0F1115"), 2.0))
            painter.setBrush(color)
            painter.drawEllipse(center, PORT_R + (1.8 if hovered else 0.0), PORT_R + (1.8 if hovered else 0.0))

            label = PORT_LABELS.get(port, "")
            if label:
                label_font = QFont(FONT_FAMILY)
                label_font.setPointSizeF(8.2)
                painter.setFont(label_font)
                painter.setPen(QColor(COLORS["text_muted"] if not hovered else COLORS["primary"]))
                painter.drawText(
                    QRectF(CARD_W - 26, center.y() - 9, 18, 18),
                    Qt.AlignRight | Qt.AlignVCenter,
                    label,
                )

    def _paint_thumb(self, painter: QPainter, rect: QRectF, font: QFont) -> None:
        path = QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        painter.save()
        painter.setClipPath(path)
        painter.fillPath(path, QColor("#12151A"))
        if self._thumb is not None:
            scaled = self._thumb.scaled(
                int(rect.width()), int(rect.height()),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation,
            )
            source_x = max(0, (scaled.width() - int(rect.width())) // 2)
            source_y = max(0, (scaled.height() - int(rect.height())) // 2)
            painter.drawPixmap(
                rect.toRect(),
                scaled,
                scaled.rect().adjusted(source_x, source_y, -source_x, -source_y),
            )
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#151920"))
            painter.drawPath(path)
        painter.restore()

        if self._thumb is None:
            painter.setFont(font)
            painter.setPen(QColor(COLORS["danger"] if self._thumb_missing else COLORS["text_dim"]))
            text = "图片缺失" if self._thumb_missing else "未选择图片"
            painter.drawText(rect, Qt.AlignCenter, text)

        painter.setPen(QPen(QColor("#2A3140"), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    @staticmethod
    def _elided(text: str, font: QFont, width: float) -> str:
        metrics = painter_metrics(font)
        return metrics.elidedText(text, Qt.ElideRight, int(width))

    # ------------------------------------------------------------------ 交互
    def hoverEnterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self._hover_port = None
        self.update()
        super().hoverLeaveEvent(event)

    def hoverMoveEvent(self, event) -> None:  # noqa: N802
        port = self.output_port_at(event.pos())
        if port != self._hover_port:
            self._hover_port = port
            self.setCursor(Qt.CrossCursor if port else Qt.ArrowCursor)
            self.update()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            port = self.output_port_at(event.pos())
            if port is not None and self.scene_ref is not None:
                self._drag_port = port
                self._dragging_edge = True
                self.scene_ref.begin_edge_drag(self, port)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging_edge and self.scene_ref is not None:
            self.scene_ref.update_edge_drag(event.scenePos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._dragging_edge and self.scene_ref is not None:
            self._dragging_edge = False
            port, self._drag_port = self._drag_port, None
            self.scene_ref.end_edge_drag(self, port, event.scenePos())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.double_clicked.emit(self.data.id)
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None:
            pos = value
            return QPointF(round(pos.x() / SNAP) * SNAP, round(pos.y() / SNAP) * SNAP)
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.data.x = float(self.pos().x())
            self.data.y = float(self.pos().y())
            if self.scene_ref is not None:
                self.scene_ref.refresh_edges(self.data.id)
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)


def painter_metrics(font: QFont):
    """延迟导入 QFontMetrics，避免模块顶部引入多余依赖。"""
    from PySide6.QtGui import QFontMetrics

    return QFontMetrics(font)
