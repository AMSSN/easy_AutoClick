"""后台执行线程：把编译好的任务列表交给 RPAEngine，并把日志与节点高亮回传主线程。"""

from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from .core.engine import RPAEngine


class FlowWorker(QThread):
    """在独立线程中跑流程，绝不触碰任何 widget。"""

    log_signal = Signal(str)
    node_signal = Signal(str)
    done_signal = Signal()

    def __init__(self, tasks: list[dict], loop_count: int = 1, parent=None):
        super().__init__(parent)
        self.tasks = tasks
        self.loop_count = int(loop_count)
        self.engine = RPAEngine()
        self._abort = False

    def request_stop(self) -> None:
        self._abort = True
        self.engine.stop()

    def run(self) -> None:  # noqa: D401 - QThread 接口
        try:
            if self.loop_count <= 0:
                self.log_signal.emit("▶ 开始运行（无限循环，点击「停止」结束）")
                self.engine.run_tasks(self.tasks, True, self._log, self._node)
            else:
                for index in range(1, self.loop_count + 1):
                    if self._abort:
                        break
                    if self.loop_count > 1:
                        self.log_signal.emit(f"▶ 第 {index}/{self.loop_count} 轮开始")
                    elif index == 1:
                        self.log_signal.emit("▶ 开始运行")
                    self.engine.stop_requested = False
                    self.engine.run_tasks(self.tasks, False, self._log, self._node)
                    if self._abort or self.engine.stop_requested:
                        break
            if self._abort:
                self.log_signal.emit("■ 已停止")
            else:
                self.log_signal.emit("✓ 流程执行完毕")
        except Exception as exc:  # noqa: BLE001
            self.log_signal.emit(f"✗ 执行异常：{exc}")
            traceback.print_exc()
        finally:
            self.done_signal.emit()

    # ------------------------------------------------------------------ 回调
    def _log(self, message: str) -> None:
        self.log_signal.emit(message)

    def _node(self, node_id: str) -> None:
        self.node_signal.emit(str(node_id))
