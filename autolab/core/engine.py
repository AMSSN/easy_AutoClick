"""执行引擎。

由 `demo.py` 的 `parse_position` / `mouseClick` / `mouseMove` / `RPAEngine` 提炼而来，
执行语义（条件跳过、循环回跳）保持完全一致，只做了三件事：

1. ``pyautogui`` / ``pyperclip`` **延迟导入**，避免拖慢 GUI 启动；
2. 把重试、超时、置信度做成参数，而不是全局常量；
3. 增加 ``callback_node`` 与「防失控保护」的友好处理。

模块内不依赖任何 Qt 类型，可以在纯命令行环境单独测试。
"""

from __future__ import annotations

import os
import re
import time
import traceback
from typing import Callable, Optional

DEFAULT_CONFIDENCE = 0.6
DEFAULT_TIMEOUT = 60.0

# 任务类型码（与 demo.py 的 CMD_TYPES 一致）
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

_COORD_RE = re.compile(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)")

_pg = None
_clip = None


class FailSafe(Exception):
    """鼠标扫到屏幕左上角触发的防失控保护。"""


def pyautogui():
    """延迟导入 pyautogui（Windows 上导入耗时接近 1 秒）。"""
    global _pg
    if _pg is None:
        try:
            import pyautogui as module
        except Exception as exc:  # pragma: no cover - 依赖缺失时的提示
            raise RuntimeError(
                "无法导入 pyautogui，请先执行：pip install pyautogui opencv-python pillow"
            ) from exc
        module.PAUSE = 0.05
        module.FAILSAFE = True
        _pg = module
    return _pg


def pyperclip():
    global _clip
    if _clip is None:
        try:
            import pyperclip as module
        except Exception:  # pragma: no cover - 剪贴板不可用时走逐字输入
            module = None
        _clip = module
    return _clip


def _log(log: Optional[Callable[[str], None]], message: str) -> None:
    if log is not None:
        log(message)


def _is_failsafe(exc: BaseException) -> bool:
    return exc.__class__.__name__ == "FailSafeException"


def parse_position(value) -> tuple:
    """解析输入值：返回 ``(True, x, y)`` 或 ``(False, image_path)``。

    支持 ``"(100,200)"`` / ``" ( 300 , 400 ) "`` 形式的坐标，其余一律视为图片路径。
    """
    match = _COORD_RE.match(str(value).strip())
    if match:
        return True, int(match.group(1)), int(match.group(2))
    return False, str(value)


def _image_not_found(pg) -> tuple:
    exc = getattr(pg, "ImageNotFoundException", None)
    return (exc,) if isinstance(exc, type) else ()


def mouse_click(
    click_times: int,
    button: str,
    value: str,
    retry: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
    confidence: float = DEFAULT_CONFIDENCE,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """图像匹配 / 坐标点击。``retry=-1`` 表示在超时前不断重试。"""
    pg = pyautogui()
    is_coord, *rest = parse_position(value)
    infinite = retry == -1
    deadline = time.time() + timeout if (infinite and timeout and timeout > 0) else None
    attempts = 0
    label = os.path.basename(rest[0]) if not is_coord else str(value)

    while True:
        try:
            if is_coord:
                x, y = int(rest[0]), int(rest[1])
            else:
                location = pg.locateCenterOnScreen(rest[0], confidence=confidence)
                if location is None:
                    raise LookupError("not found")
                x, y = int(location.x), int(location.y)
            pg.click(x, y, clicks=click_times, interval=0.2, duration=0.2, button=button)
            _log(log, f"点击 {'坐标' if is_coord else '图片'} ({x}, {y}) ← {label}")
            return True
        except Exception as exc:  # noqa: BLE001 - 需要区分三类异常
            if _is_failsafe(exc):
                raise FailSafe() from exc
            if isinstance(exc, LookupError) or isinstance(exc, _image_not_found(pg)):
                pass
            else:
                _log(log, f"点击失败：{exc}")
                return False

        attempts += 1
        if not infinite:
            if attempts >= max(1, int(retry or 1)):
                _log(log, f"未找到目标：{label}")
                return False
            time.sleep(0.3)
        else:
            if deadline is not None and time.time() > deadline:
                _log(log, f"等待目标超时（{timeout:g} 秒）：{label}")
                return False
            time.sleep(0.1)


def mouse_move(
    value: str,
    retry: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
    confidence: float = DEFAULT_CONFIDENCE,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """鼠标悬停：移动但不点击。"""
    pg = pyautogui()
    is_coord, *rest = parse_position(value)
    infinite = retry == -1
    deadline = time.time() + timeout if (infinite and timeout and timeout > 0) else None
    attempts = 0
    label = os.path.basename(rest[0]) if not is_coord else str(value)

    while True:
        try:
            if is_coord:
                x, y = int(rest[0]), int(rest[1])
            else:
                location = pg.locateCenterOnScreen(rest[0], confidence=confidence)
                if location is None:
                    raise LookupError("not found")
                x, y = int(location.x), int(location.y)
            pg.moveTo(x, y, duration=0.2)
            _log(log, f"悬停 ({x}, {y}) ← {label}")
            return True
        except Exception as exc:  # noqa: BLE001
            if _is_failsafe(exc):
                raise FailSafe() from exc
            if isinstance(exc, LookupError) or isinstance(exc, _image_not_found(pg)):
                pass
            else:
                _log(log, f"悬停失败：{exc}")
                return False

        attempts += 1
        if not infinite:
            if attempts >= max(1, int(retry or 1)):
                _log(log, f"未找到目标：{label}")
                return False
            time.sleep(0.3)
        else:
            if deadline is not None and time.time() > deadline:
                _log(log, f"等待目标超时（{timeout:g} 秒）：{label}")
                return False
            time.sleep(0.1)


def text_input(text: str, delay: float = 0.3, log: Optional[Callable[[str], None]] = None) -> None:
    """优先剪贴板粘贴（支持中文），失败则退化为逐字输入。"""
    pg = pyautogui()
    clip = pyperclip()
    try:
        if clip is None:
            raise RuntimeError("no clipboard backend")
        clip.copy(str(text))
        pg.hotkey("ctrl", "v")
    except Exception:  # noqa: BLE001
        pg.write(str(text), interval=0.01)
    if delay:
        time.sleep(float(delay))
    preview = str(text).replace("\n", " ")[:30]
    _log(log, f"输入文本：“{preview}”")


def press_hotkey(keys: str, delay: float = 0.2, log: Optional[Callable[[str], None]] = None) -> None:
    pg = pyautogui()
    parts = [k.strip().lower() for k in str(keys).split("+") if k.strip()]
    if not parts:
        return
    if len(parts) == 1:
        pg.press(parts[0])
    else:
        pg.hotkey(*parts)
    if delay:
        time.sleep(float(delay))
    _log(log, f"按键 {'+'.join(parts)}")


class RPAEngine:
    """顺序执行任务列表，支持条件跳过与局部循环回跳。"""

    def __init__(self) -> None:
        self.is_running = False
        self.stop_requested = False

    def stop(self) -> None:
        self.stop_requested = True

    # ------------------------------------------------------------------ 主循环
    def run_tasks(
        self,
        tasks: list[dict],
        loop_forever: bool = False,
        callback_msg: Optional[Callable[[str], None]] = None,
        callback_node: Optional[Callable[[str], None]] = None,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> None:
        self.is_running = True
        self.stop_requested = False

        def msg(text: str) -> None:
            if callback_msg is not None:
                callback_msg(text)

        def node(nid) -> None:
            if callback_node is not None and nid:
                callback_node(str(nid))

        try:
            while True:
                condition_stack: list[tuple[float, object]] = []
                index = 0
                while index < len(tasks):
                    if self.stop_requested:
                        msg("任务已停止")
                        return

                    task = tasks[index]
                    cmd_type = task.get("type")
                    cmd_value = task.get("value")
                    retry = int(task.get("retry", 1) or 1)
                    timeout = float(task.get("timeout", DEFAULT_TIMEOUT) or 0)

                    node(task.get("id"))

                    # --- 条件：如果存在图片则执行 ---
                    if cmd_type == T_IF:
                        try:
                            found = (
                                pyautogui().locateOnScreen(str(cmd_value), confidence=confidence)
                                is not None
                            )
                        except Exception as exc:  # noqa: BLE001
                            if _is_failsafe(exc):
                                raise FailSafe() from exc
                            found = False
                        condition_stack.append((T_IF, found))
                        msg(f"如果存在图片 → {'成立' if found else '不成立'}：{cmd_value}")

                    elif cmd_type == T_ELSE:
                        if condition_stack and condition_stack[-1][0] == T_IF:
                            _, parent = condition_stack[-1]
                            condition_stack[-1] = (T_IF, not bool(parent))
                        else:
                            msg("结构错误：「否则」前没有「如果」")

                    elif cmd_type == T_END_IF:
                        if condition_stack and condition_stack[-1][0] == T_IF:
                            condition_stack.pop()
                        else:
                            msg("结构错误：「结束条件」缺少对应的「如果」")

                    # --- 循环 ---
                    elif cmd_type == T_LOOP:
                        try:
                            count = int(float(str(cmd_value).strip() or 1))
                        except (TypeError, ValueError):
                            msg("循环次数格式错误，按 1 次执行")
                            count = 1
                        condition_stack.append((T_LOOP, max(1, count)))
                        msg(f"循环开始：共 {max(1, count)} 次")

                    elif cmd_type == T_LOOP_END:
                        if condition_stack and condition_stack[-1][0] == T_LOOP:
                            _, remaining = condition_stack.pop()
                            if int(remaining) > 1:
                                target = self._find_prev_loop_start(tasks, index)
                                if target is not None:
                                    condition_stack.append((T_LOOP, int(remaining) - 1))
                                    # 回到循环体的第一条语句，跳过 T_LOOP 本身，
                                    # 否则会重复压栈导致死循环
                                    index = target + 1
                                    continue
                        else:
                            msg("结构错误：「结束循环」缺少对应的「循环开始」")

                    # --- 动作 ---
                    else:
                        skipped = self._should_skip(condition_stack, cmd_type)
                        if skipped:
                            index += 1
                            continue
                        self._run_action(
                            cmd_type, cmd_value, retry, timeout, confidence, msg, task
                        )

                    index += 1

                if not loop_forever:
                    break
                msg("等待 0.1 秒进入下一轮…")
                time.sleep(0.1)

        except FailSafe:
            msg("已触发防失控保护（鼠标移动到屏幕左上角），任务中止")
        except Exception as exc:  # noqa: BLE001
            msg(f"执行出错：{exc}")
            traceback.print_exc()
        finally:
            self.is_running = False
            msg("任务结束")

    # ------------------------------------------------------------------ 细节
    @staticmethod
    def _should_skip(condition_stack: list[tuple[float, object]], cmd_type) -> bool:
        for block_type, condition in reversed(condition_stack):
            if block_type == T_IF and not condition:
                return True
        return False

    def _run_action(self, cmd_type, cmd_value, retry, timeout, confidence, msg, task) -> None:
        if cmd_type == T_LEFT_CLICK:
            mouse_click(1, "left", cmd_value, retry, timeout, confidence, msg)
        elif cmd_type == T_DOUBLE_CLICK:
            mouse_click(2, "left", cmd_value, retry, timeout, confidence, msg)
        elif cmd_type == T_RIGHT_CLICK:
            mouse_click(1, "right", cmd_value, retry, timeout, confidence, msg)
        elif cmd_type == T_TEXT:
            text_input(cmd_value, float(task.get("delay", 0.3) or 0), msg)
        elif cmd_type == T_WAIT:
            seconds = float(cmd_value)
            msg(f"等待 {seconds:g} 秒")
            self._sleep(seconds)
        elif cmd_type == T_SCROLL:
            pyautogui().scroll(int(cmd_value))
            msg(f"滚轮 {cmd_value} 格")
        elif cmd_type == T_HOTKEY:
            press_hotkey(cmd_value, float(task.get("delay", 0.2) or 0), msg)
        elif cmd_type == T_HOVER:
            mouse_move(cmd_value, retry, timeout, confidence, msg)
        else:
            msg(f"未知任务类型：{cmd_type}")

    def _sleep(self, seconds: float) -> None:
        """可被 stop() 打断的等待。"""
        end = time.time() + max(0.0, seconds)
        while time.time() < end:
            if self.stop_requested:
                return
            time.sleep(min(0.05, max(0.0, end - time.time())))

    @staticmethod
    def _find_prev_loop_start(tasks: list[dict], current_pos: int) -> Optional[int]:
        nesting = 0
        for i in range(current_pos - 1, -1, -1):
            cmd_type = tasks[i].get("type")
            if cmd_type == T_LOOP_END:
                nesting += 1
            elif cmd_type == T_LOOP:
                if nesting == 0:
                    return i
                nesting -= 1
        return None
