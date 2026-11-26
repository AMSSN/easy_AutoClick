"""画布图 -> 线性任务序列的编译器。

输出格式与 `demo.py` 中 `RPAEngine.run_tasks()` 接受的列表完全一致：

    {"type": 1.0, "value": "(100,200)", "retry": 1, "timeout": 60, "id": "节点id"}

条件分支展开为 ``10.0 / 10.1 / 10.9``，局部循环展开为 ``11.0 / 11.9``，
因此执行语义可以直接复用已经验证过的引擎，不需要重写跳过与回跳逻辑。

编译失败时返回结构化的 :class:`CompileError` 列表（带节点 id，用于画布标红），
而不是抛异常，方便 UI 层逐条展示。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .models import FlowDocument, NodeData, NodeType, POINT_TYPES

# 与 demo.py 的 CMD_TYPES 完全一致
T_LEFT_CLICK = 1.0
T_DOUBLE_CLICK = 2.0
T_RIGHT_CLICK = 3.0
T_TEXT = 4.0
T_WAIT = 5.0
T_SCROLL = 6.0
T_HOTKEY = 7.0
T_HOVER = 8.0
T_IF = 10.0
T_ELSE = 10.1
T_END_IF = 10.9
T_LOOP = 11.0
T_LOOP_END = 11.9

_CLICK_CODE = {
    NodeType.LEFT_CLICK: T_LEFT_CLICK,
    NodeType.DOUBLE_CLICK: T_DOUBLE_CLICK,
    NodeType.RIGHT_CLICK: T_RIGHT_CLICK,
    NodeType.HOVER: T_HOVER,
}


@dataclass
class CompileError:
    message: str
    node_ids: list[str] = field(default_factory=list)


class _Abort(Exception):
    def __init__(self, error: CompileError):
        super().__init__(error.message)
        self.error = error


def _coord_text(params: dict) -> str:
    try:
        x = int(float(params.get("x", 0)))
        y = int(float(params.get("y", 0)))
    except (TypeError, ValueError):
        x = y = 0
    return f"({x},{y})"


class _Compiler:
    def __init__(self, doc: FlowDocument):
        self.doc = doc
        self.tasks: list[dict] = []
        self.entered: set[str] = set()

    # ------------------------------------------------------------------ 入口
    def run(self) -> tuple[list[dict], list[CompileError]]:
        doc = self.doc
        if not doc.nodes:
            return [], [CompileError("流程为空，请先从左侧把节点拖到画布上")]

        starts = doc.entry_nodes()
        if not starts:
            return [], [CompileError("找不到入口节点，流程可能存在环", list(doc.nodes))]
        if len(starts) > 1:
            names = "、".join(self._name(nid) for nid in starts[:4])
            more = " 等" if len(starts) > 4 else ""
            return [], [
                CompileError(
                    f"存在 {len(starts)} 个未接入的起点（{names}{more}），请把它们串成一条链",
                    starts,
                )
            ]

        try:
            self._chain(starts[0], frozenset())
        except _Abort as exc:
            return [], [exc.error]

        lost = [nid for nid in doc.nodes if nid not in self.entered]
        if lost:
            names = "、".join(self._name(nid) for nid in lost[:4])
            return [], [CompileError(f"存在未接入主流程的游离节点：{names}", lost)]
        return self.tasks, []

    # ------------------------------------------------------------------ 工具
    def _name(self, node_id: str) -> str:
        node = self.doc.nodes.get(node_id)
        return node.type.spec.title if node else node_id

    def _target(self, node_id: str, port: str) -> str | None:
        edge = self.doc.edge_from(node_id, port)
        return edge.target if edge else None

    def _require_image(self, node: NodeData, label: str) -> str:
        image = str(node.params.get("image") or "").strip()
        if not image:
            raise _Abort(CompileError(f"「{label}」节点还没有选择图片", [node.id]))
        if not os.path.exists(image):
            raise _Abort(CompileError(f"「{label}」节点的图片文件不存在：{image}", [node.id]))
        return image

    # ------------------------------------------------------------------ 展开
    def _chain(self, node_id: str | None, stop_types: frozenset[NodeType]) -> str | None:
        """沿 ``out`` 口线性展开，直到遇到 ``stop_types`` 中的节点（返回其 id）。"""
        cur = node_id
        while cur is not None:
            node = self.doc.nodes.get(cur)
            if node is None:
                raise _Abort(CompileError(f"连线指向了不存在的节点：{cur}"))

            if node.type in stop_types:
                return cur

            if cur in self.entered:
                raise _Abort(
                    CompileError(
                        f"节点「{self._name(cur)}」被重复引用，分支可能形成了环或提前汇合",
                        [cur],
                    )
                )
            self.entered.add(cur)

            node_type = node.type
            if node_type == NodeType.IF_IMAGE:
                cur = self._emit_if(node)
                continue
            if node_type == NodeType.LOOP_START:
                cur = self._emit_loop(node)
                continue
            if node_type == NodeType.ELSE:
                # 结构标记：不产生任务，直接跳过
                cur = self._target(cur, "out")
                continue
            if node_type in (NodeType.END_IF, NodeType.LOOP_END):
                raise _Abort(
                    CompileError(f"「{node.type.spec.title}」缺少对应的块起始节点", [cur])
                )

            self._emit_action(node)
            cur = self._target(cur, "out")
        return None

    def _emit_action(self, node: NodeData) -> None:
        node_type = node.type
        params = node.params

        if node_type in POINT_TYPES:
            mode = str(params.get("mode") or "image")
            if mode == "coord":
                value = _coord_text(params)
            else:
                image = self._require_image(node, node_type.spec.title)
                value = image
            self.tasks.append(
                {
                    "type": _CLICK_CODE[node_type],
                    "value": value,
                    "retry": int(params.get("retry", 1) or 1),
                    "timeout": float(params.get("timeout", 60) or 0),
                    "id": node.id,
                }
            )
            return

        if node_type == NodeType.TEXT_INPUT:
            self.tasks.append(
                {
                    "type": T_TEXT,
                    "value": str(params.get("text") or ""),
                    "retry": 1,
                    "delay": float(params.get("delay", 0.3) or 0),
                    "id": node.id,
                }
            )
            return

        if node_type == NodeType.WAIT:
            try:
                seconds = max(0.0, float(params.get("seconds", 1.0)))
            except (TypeError, ValueError):
                seconds = 1.0
            self.tasks.append(
                {"type": T_WAIT, "value": str(seconds), "retry": 1, "id": node.id}
            )
            return

        if node_type == NodeType.SCROLL:
            try:
                amount = int(params.get("amount", 0))
            except (TypeError, ValueError):
                amount = 0
            self.tasks.append(
                {"type": T_SCROLL, "value": str(amount), "retry": 1, "id": node.id}
            )
            return

        if node_type == NodeType.HOTKEY:
            keys = str(params.get("keys") or "").strip()
            if not keys:
                raise _Abort(CompileError("快捷键节点还没有设置按键", [node.id]))
            self.tasks.append(
                {
                    "type": T_HOTKEY,
                    "value": keys,
                    "retry": 1,
                    "delay": float(params.get("delay", 0.2) or 0),
                    "id": node.id,
                }
            )
            return

        raise _Abort(CompileError(f"未知节点类型：{node_type}", [node.id]))

    def _emit_if(self, node: NodeData) -> str | None:
        if str(node.params.get("mode") or "image") != "image":
            raise _Abort(CompileError("条件节点只能使用图像匹配", [node.id]))
        image = self._require_image(node, node.type.spec.title)

        true_start = self._target(node.id, "true")
        false_start = self._target(node.id, "false")
        if true_start is None and false_start is None:
            raise _Abort(
                CompileError("条件节点的「是」「否」两个输出口都没有接线", [node.id])
            )

        self.tasks.append({"type": T_IF, "value": image, "retry": 1, "id": node.id})

        stop = frozenset({NodeType.END_IF})
        join_true = self._chain(true_start, stop) if true_start else None

        self.tasks.append({"type": T_ELSE, "value": "", "retry": 1, "id": node.id})
        join_false = self._chain(false_start, stop) if false_start else None

        if join_true and join_false and join_true != join_false:
            raise _Abort(
                CompileError(
                    "条件的两条分支没有汇合到同一个「结束条件」节点",
                    [node.id, join_true, join_false],
                )
            )
        join = join_true or join_false
        if join is None:
            raise _Abort(
                CompileError("条件分支缺少「结束条件」节点", [node.id] + [
                    nid for nid in (true_start, false_start) if nid
                ])
            )

        join_node = self.doc.nodes.get(join)
        if join_node is None or join_node.type != NodeType.END_IF:
            raise _Abort(CompileError("分支必须终止于「结束条件」节点", [join]))

        self.entered.add(join)
        self.tasks.append({"type": T_END_IF, "value": "", "retry": 1, "id": join})
        return self._target(join, "out")

    def _emit_loop(self, node: NodeData) -> str | None:
        try:
            count = max(1, int(node.params.get("count", 1) or 1))
        except (TypeError, ValueError):
            count = 1
        self.tasks.append({"type": T_LOOP, "value": str(count), "retry": 1, "id": node.id})

        body = self._target(node.id, "out")
        end: str | None = None
        if body:
            end = self._chain(body, frozenset({NodeType.LOOP_END}))
        if end is None:
            raise _Abort(CompileError("循环缺少对应的「循环结束」节点", [node.id]))

        self.entered.add(end)
        self.tasks.append({"type": T_LOOP_END, "value": "", "retry": 1, "id": end})
        return self._target(end, "out")


def compile_flow(doc: FlowDocument) -> tuple[list[dict], list[CompileError]]:
    """把画布图展开为 demo.py 兼容的任务列表。

    Returns:
        (tasks, errors)。``errors`` 非空时 ``tasks`` 一定为空列表。
    """
    return _Compiler(doc).run()
