"""流程数据模型。

画布上的一切都是「节点 + 连线」：
    * `NodeData`   节点的纯数据（类型、坐标、参数），与 Qt 图元解耦，便于序列化。
    * `Edge`       连线，`(source, port)` 唯一确定一条出边。
    * `FlowDocument` 一整张流程图。

条件与循环在图中表现为「块」：
    IF_IMAGE 节点有 ``true`` / ``false`` 两个输出口，两条分支最终汇合到同一个 END_IF 节点；
    LOOP_START 的 ``out`` 进入循环体，循环体最终终止于 LOOP_END。
这样图本身不含环，编译器可以安全地做一次深度优先展开。
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """节点类型。值即 JSON 中的 ``type`` 字段。"""

    LEFT_CLICK = "left_click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    TEXT_INPUT = "text_input"
    WAIT = "wait"
    SCROLL = "scroll"
    HOTKEY = "hotkey"
    LOOP_START = "loop_start"
    LOOP_END = "loop_end"
    IF_IMAGE = "if_image"
    ELSE = "else"
    END_IF = "end_if"

    @property
    def spec(self) -> "NodeSpec":
        return NODE_SPECS[self]

    @classmethod
    def from_value(cls, value: str) -> "NodeType | None":
        try:
            return cls(value)
        except ValueError:
            return None


CAT_ACTION = "动作"
CAT_FLOW = "流程控制"

# 输出口标识 -> 显示名（空字符串表示不显示）
PORT_LABELS = {"out": "", "true": "是", "false": "否"}

# 支持「图像匹配 / 固定位置」双模式的节点
POINT_TYPES = frozenset(
    {NodeType.LEFT_CLICK, NodeType.DOUBLE_CLICK, NodeType.RIGHT_CLICK, NodeType.HOVER}
)


@dataclass(frozen=True)
class NodeSpec:
    """节点元数据：标题、分类、端口、是否需要图片等静态信息。"""

    type: NodeType
    title: str
    category: str
    description: str
    accent: str
    glyph: str
    outputs: tuple[str, ...] = ("out",)
    image: bool = False
    point: bool = False
    marker: bool = False


NODE_SPECS: dict[NodeType, NodeSpec] = {
    NodeType.LEFT_CLICK: NodeSpec(
        NodeType.LEFT_CLICK, "左键单击", CAT_ACTION, "图像匹配或固定坐标左键单击一次",
        "#4F8CFF", "左", image=True, point=True,
    ),
    NodeType.DOUBLE_CLICK: NodeSpec(
        NodeType.DOUBLE_CLICK, "左键双击", CAT_ACTION, "图像匹配或固定坐标左键双击",
        "#4F8CFF", "双", image=True, point=True,
    ),
    NodeType.RIGHT_CLICK: NodeSpec(
        NodeType.RIGHT_CLICK, "右键单击", CAT_ACTION, "图像匹配或固定坐标右键单击",
        "#4F8CFF", "右", image=True, point=True,
    ),
    NodeType.HOVER: NodeSpec(
        NodeType.HOVER, "鼠标悬停", CAT_ACTION, "移动到图像或坐标处但不点击",
        "#4F8CFF", "悬", image=True, point=True,
    ),
    NodeType.TEXT_INPUT: NodeSpec(
        NodeType.TEXT_INPUT, "文本输入", CAT_ACTION, "把一段文本粘贴到当前焦点控件",
        "#22C55E", "文",
    ),
    NodeType.WAIT: NodeSpec(
        NodeType.WAIT, "等待", CAT_ACTION, "暂停指定的秒数",
        "#F59E0B", "等",
    ),
    NodeType.SCROLL: NodeSpec(
        NodeType.SCROLL, "滚轮", CAT_ACTION, "向上或向下滚动指定刻度",
        "#8B5CF6", "滚",
    ),
    NodeType.HOTKEY: NodeSpec(
        NodeType.HOTKEY, "快捷键", CAT_ACTION, "发送组合键，例如 ctrl+s",
        "#06B6D4", "键",
    ),
    NodeType.LOOP_START: NodeSpec(
        NodeType.LOOP_START, "循环开始", CAT_FLOW, "重复执行内部节点 N 次",
        "#F59E0B", "循",
    ),
    NodeType.LOOP_END: NodeSpec(
        NodeType.LOOP_END, "循环结束", CAT_FLOW, "标记循环范围终点",
        "#B45309", "终", marker=True,
    ),
    NodeType.IF_IMAGE: NodeSpec(
        NodeType.IF_IMAGE, "如果存在图像", CAT_FLOW, "条件成立走「是」分支，否则走「否」分支",
        "#EF4444", "如", outputs=("true", "false"), image=True,
    ),
    NodeType.ELSE: NodeSpec(
        NodeType.ELSE, "否则", CAT_FLOW, "「否」分支的起始标记（可选）",
        "#F97316", "否", marker=True,
    ),
    NodeType.END_IF: NodeSpec(
        NodeType.END_IF, "结束条件", CAT_FLOW, "两条分支在此汇合，之后继续执行",
        "#64748B", "合", marker=True,
    ),
}

POINT_DEFAULT: dict[str, Any] = {
    "mode": "image",
    "image": "",
    "x": 0,
    "y": 0,
    "retry": 1,
    "timeout": 60.0,
}


def default_params(node_type: NodeType) -> dict[str, Any]:
    """各类型的默认参数。"""
    if node_type in POINT_TYPES:
        return dict(POINT_DEFAULT)
    if node_type == NodeType.IF_IMAGE:
        return {"mode": "image", "image": "", "timeout": 30.0}
    if node_type == NodeType.TEXT_INPUT:
        return {"text": "", "delay": 0.3}
    if node_type == NodeType.WAIT:
        return {"seconds": 1.0}
    if node_type == NodeType.SCROLL:
        return {"amount": 3}
    if node_type == NodeType.HOTKEY:
        return {"keys": "ctrl+s", "delay": 0.2}
    if node_type == NodeType.LOOP_START:
        return {"count": 3}
    return {}


@dataclass
class NodeData:
    """画布节点的纯数据。"""

    id: str
    type: NodeType
    x: float = 0.0
    y: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        node_type: NodeType,
        x: float = 0.0,
        y: float = 0.0,
        params: dict[str, Any] | None = None,
    ) -> "NodeData":
        return cls(
            id=uuid.uuid4().hex[:12],
            type=node_type,
            x=float(x),
            y=float(y),
            params=dict(params) if params else default_params(node_type),
        )

    # ------------------------------------------------------------------ 展示
    @property
    def title(self) -> str:
        return self.type.spec.title

    def summary(self) -> str:
        """节点卡片上那行灰色摘要。"""
        p = self.params
        t = self.type
        if t in POINT_TYPES:
            if p.get("mode", "image") == "coord":
                return f"坐标 ({int(p.get('x', 0))}, {int(p.get('y', 0))})"
            img = str(p.get("image") or "")
            return f"图 · {os.path.basename(img)}" if img else "未选择图片"
        if t == NodeType.TEXT_INPUT:
            text = str(p.get("text") or "").replace("\n", " ")
            return f"“{text[:18]}”" if text else "（空文本）"
        if t == NodeType.WAIT:
            try:
                return f"{float(p.get('seconds', 0)):g} 秒"
            except (TypeError, ValueError):
                return "1 秒"
        if t == NodeType.SCROLL:
            v = int(p.get("amount", 0) or 0)
            if v > 0:
                return f"向上 {v} 格"
            if v < 0:
                return f"向下 {-v} 格"
            return "0 格"
        if t == NodeType.HOTKEY:
            return str(p.get("keys") or "").upper() or "未设置"
        if t == NodeType.LOOP_START:
            return f"重复 {int(p.get('count', 1) or 1)} 次"
        if t == NodeType.IF_IMAGE:
            img = str(p.get("image") or "")
            return f"如果存在 · {os.path.basename(img)}" if img else "未选择图片"
        return ""

    def image_path(self) -> str:
        return str(self.params.get("image") or "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "x": round(float(self.x), 1),
            "y": round(float(self.y), 1),
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "NodeData | None":
        node_type = NodeType.from_value(str(raw.get("type", "")))
        if node_type is None:
            return None
        params = default_params(node_type)
        params.update(raw.get("params") or {})
        return cls(
            id=str(raw.get("id") or uuid.uuid4().hex[:12]),
            type=node_type,
            x=float(raw.get("x", 0.0)),
            y=float(raw.get("y", 0.0)),
            params=params,
        )


@dataclass
class Edge:
    """一条连线：从 ``source`` 的某个输出口指向 ``target`` 的输入口。"""

    source: str
    port: str
    target: str

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "port": self.port, "target": self.target}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Edge | None":
        source = str(raw.get("source") or "")
        target = str(raw.get("target") or "")
        if not source or not target:
            return None
        return cls(source=source, port=str(raw.get("port") or "out"), target=target)


@dataclass
class FlowDocument:
    """一整张流程图。"""

    nodes: dict[str, NodeData] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    loop_count: int = 1
    name: str = "未命名流程"

    # ------------------------------------------------------------------ 查询
    def add_node(self, node: NodeData) -> NodeData:
        self.nodes[node.id] = node
        return node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]

    def incoming(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.target == node_id]

    def outgoing(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]

    def edge_from(self, node_id: str, port: str) -> Edge | None:
        for edge in self.edges:
            if edge.source == node_id and edge.port == port:
                return edge
        return None

    def targets(self) -> set[str]:
        return {e.target for e in self.edges}

    def entry_nodes(self) -> list[str]:
        """没有任何入边的节点，正常流程应当恰好一个。"""
        targets = self.targets()
        return [nid for nid in self.nodes if nid not in targets]

    # ------------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "loop_count": int(self.loop_count),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    def is_empty(self) -> bool:
        return not self.nodes
