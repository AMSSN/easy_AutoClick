"""流程文件读写。

文件格式（version 1）::

    {
      "version": 1,
      "name": "登录流程",
      "loop_count": 3,
      "nodes": [{"id": "...", "type": "left_click", "x": 120, "y": 80,
                 "params": {"mode": "image", "image": "img/login.png", ...}}],
      "edges": [{"source": "a", "port": "out", "target": "b"}]
    }

图片路径在保存时若位于流程文件目录之下，会转成相对路径；加载时再基于流程文件
所在目录解析回来，方便整个工程目录整体迁移。旧版 `demo.py` 的扁平 tasks JSON
（``[{"type": 1.0, "value": "...", "retry": 1}, ...]``）也做了向上兼容导入。
"""

from __future__ import annotations

import json
import os
from typing import Any

from ..core.models import Edge, FlowDocument, NodeData, NodeType

VERSION = 1

# 旧版 demo.py 的浮点类型码 -> 新节点类型
_LEGACY_ACTIONS = {
    1.0: NodeType.LEFT_CLICK,
    2.0: NodeType.DOUBLE_CLICK,
    3.0: NodeType.RIGHT_CLICK,
    4.0: NodeType.TEXT_INPUT,
    5.0: NodeType.WAIT,
    6.0: NodeType.SCROLL,
    7.0: NodeType.HOTKEY,
    8.0: NodeType.HOVER,
    10.0: NodeType.IF_IMAGE,
    10.1: NodeType.ELSE,
    10.9: NodeType.END_IF,
    11.0: NodeType.LOOP_START,
    11.9: NodeType.LOOP_END,
}


# ---------------------------------------------------------------------- 路径
def _to_relative(path: str, base_dir: str) -> str:
    if not path or not os.path.isabs(path):
        return path
    try:
        rel = os.path.relpath(path, base_dir)
    except ValueError:
        return path
    return path if rel.startswith("..") else rel.replace("\\", "/")


def _to_absolute(path: str, base_dir: str) -> str:
    if not path or os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(base_dir, path))


# ---------------------------------------------------------------------- 写
def to_payload(doc: FlowDocument, base_dir: str | None = None) -> dict[str, Any]:
    payload = doc.to_dict()
    payload["version"] = VERSION
    if base_dir:
        for node in payload["nodes"]:
            image = node.get("params", {}).get("image")
            if image:
                node["params"]["image"] = _to_relative(str(image), base_dir)
    return payload


def save_document(doc: FlowDocument, path: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(path))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(to_payload(doc, base_dir), handle, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------- 读
def load_document(path: str) -> tuple[FlowDocument, list[str]]:
    """读取流程文件，返回 ``(doc, warnings)``。"""
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    base_dir = os.path.dirname(os.path.abspath(path))
    warnings: list[str] = []

    if isinstance(raw, list):
        doc = _from_legacy(raw, warnings)
        doc.name = os.path.splitext(os.path.basename(path))[0]
        return doc, warnings

    if not isinstance(raw, dict):
        raise ValueError("文件格式不正确：既不是流程对象也不是旧版指令列表")

    doc = FlowDocument()
    doc.name = str(raw.get("name") or os.path.splitext(os.path.basename(path))[0])
    try:
        doc.loop_count = max(0, int(raw.get("loop_count", 1)))
    except (TypeError, ValueError):
        doc.loop_count = 1

    for raw_node in raw.get("nodes") or []:
        node = NodeData.from_dict(raw_node)
        if node is None:
            warnings.append(f"跳过未知节点类型：{raw_node.get('type')!r}")
            continue
        image = node.params.get("image")
        if image:
            node.params["image"] = _to_absolute(str(image), base_dir)
        doc.add_node(node)

    for raw_edge in raw.get("edges") or []:
        edge = Edge.from_dict(raw_edge)
        if edge is None:
            continue
        if edge.source not in doc.nodes or edge.target not in doc.nodes:
            warnings.append("跳过指向不存在节点的连线")
            continue
        doc.edges.append(edge)

    try:
        version = int(raw.get("version") or VERSION)
    except (TypeError, ValueError):
        version = VERSION
    if version > VERSION:
        warnings.append(f"文件版本 {version} 高于当前程序支持的 {VERSION}，可能缺少部分特性")

    return doc, warnings


# ---------------------------------------------------------------------- 旧版
def _from_legacy(items: list[dict], warnings: list[str]) -> FlowDocument:
    """把 demo.py 的扁平指令列表还原成带分支的节点图。"""
    doc = FlowDocument()

    def new_node(node_type: NodeType) -> str:
        node = NodeData.create(node_type, 0.0, 0.0)
        doc.add_node(node)
        return node.id

    def build(node_type: NodeType, item: dict) -> str:
        node_id = new_node(node_type)
        node = doc.nodes[node_id]
        value = str(item.get("value") or "")
        retry = item.get("retry", 1)
        try:
            retry = int(retry)
        except (TypeError, ValueError):
            retry = 1

        if node_type in (
            NodeType.LEFT_CLICK,
            NodeType.DOUBLE_CLICK,
            NodeType.RIGHT_CLICK,
            NodeType.HOVER,
        ):
            node.params.update(_guess_point_params(value, retry))
        elif node_type == NodeType.TEXT_INPUT:
            node.params["text"] = value
        elif node_type == NodeType.WAIT:
            try:
                node.params["seconds"] = float(value)
            except (TypeError, ValueError):
                node.params["seconds"] = 1.0
        elif node_type == NodeType.SCROLL:
            try:
                node.params["amount"] = int(float(value))
            except (TypeError, ValueError):
                node.params["amount"] = 0
        elif node_type == NodeType.HOTKEY:
            node.params["keys"] = value
        elif node_type == NodeType.LOOP_START:
            try:
                node.params["count"] = max(1, int(float(value)))
            except (TypeError, ValueError):
                node.params["count"] = 1
        elif node_type == NodeType.IF_IMAGE:
            node.params["image"] = value
        return node_id

    def connect(seq: list[str], tail: str | None) -> None:
        for src, dst in zip(seq, seq[1:]):
            if doc.nodes[src].type in (NodeType.IF_IMAGE,):
                continue
            doc.edges.append(Edge(src, "out", dst))
        if seq and tail:
            last = doc.nodes[seq[-1]]
            if last.type not in (NodeType.IF_IMAGE,):
                doc.edges.append(Edge(seq[-1], "out", tail))

    def parse_block(start: int, stop_codes: set[float]) -> tuple[list[str], int]:
        seq: list[str] = []
        index = start
        while index < len(items):
            item = items[index]
            try:
                code = float(item.get("type"))
            except (TypeError, ValueError):
                index += 1
                continue
            if code in stop_codes:
                return seq, index

            if code == 9.0:  # 截图保存在新版本中没有对应节点
                warnings.append("旧配置中的「截图保存」指令已跳过")
                index += 1
                continue

            if code == 10.0:
                if_id = build(NodeType.IF_IMAGE, item)
                seq.append(if_id)
                true_seq, index = parse_block(index + 1, {10.1, 10.9})
                false_seq: list[str] = []
                if index < len(items) and _code(items[index]) == 10.1:
                    index += 1
                    false_seq, index = parse_block(index, {10.9})
                end_if = new_node(NodeType.END_IF)
                connect(true_seq, end_if)
                connect(false_seq, end_if)
                first_true, first_false = _head(true_seq), _head(false_seq)
                doc.edges.append(Edge(if_id, "true", first_true or end_if))
                doc.edges.append(Edge(if_id, "false", first_false or end_if))
                seq.append(end_if)
                if index < len(items) and _code(items[index]) == 10.9:
                    index += 1
                continue

            if code == 11.0:
                loop_id = build(NodeType.LOOP_START, item)
                seq.append(loop_id)
                body, index = parse_block(index + 1, {11.9})
                end_loop = new_node(NodeType.LOOP_END)
                doc.edges.append(Edge(loop_id, "out", _head(body) or end_loop))
                connect(body, end_loop)
                seq.append(end_loop)
                if index < len(items) and _code(items[index]) == 11.9:
                    index += 1
                continue

            node_type = _LEGACY_ACTIONS.get(code)
            if node_type is None:
                warnings.append(f"跳过未知指令类型：{code}")
                index += 1
                continue
            seq.append(build(node_type, item))
            index += 1
        return seq, index

    def _head(seq: list[str]) -> str | None:
        return seq[0] if seq else None

    seq, _ = parse_block(0, set())
    connect(seq, None)
    _layout(doc)
    return doc


def _code(item: dict) -> float:
    try:
        return float(item.get("type"))
    except (TypeError, ValueError):
        return -1.0


def _guess_point_params(value: str, retry: int) -> dict[str, Any]:
    import re

    match = re.match(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", value.strip())
    if match:
        return {
            "mode": "coord",
            "image": "",
            "x": int(match.group(1)),
            "y": int(match.group(2)),
            "retry": retry,
            "timeout": 30.0,
        }
    return {
        "mode": "image",
        "image": value,
        "x": 0,
        "y": 0,
        "retry": retry,
        "timeout": 60.0,
    }


def _layout(doc: FlowDocument) -> None:
    """给旧配置导入的节点一个能看的初始布局：按入边 BFS 分层。"""
    if not doc.nodes:
        return
    depth: dict[str, int] = {nid: 0 for nid in doc.nodes}
    changed = True
    guard = 0
    while changed and guard < len(doc.nodes) + 5:
        changed = False
        guard += 1
        for edge in doc.edges:
            want = depth.get(edge.source, 0) + 1
            if depth.get(edge.target, 0) < want:
                depth[edge.target] = want
                changed = True

    rows: dict[int, int] = {}
    for nid, level in sorted(depth.items(), key=lambda kv: (kv[1], kv[0])):
        row = rows.get(level, 0)
        rows[level] = row + 1
        node = doc.nodes[nid]
        node.x = 120 + row * 270
        node.y = 60 + level * 120
