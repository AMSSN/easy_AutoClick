"""AutoClick 可视化流程编排器 —— 程序入口。

用法：
    python main.py
"""

from __future__ import annotations

import os
import sys
import traceback


def _ensure_path() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)


def _install_excepthook() -> None:
    def hook(exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                QMessageBox.critical(None, "未处理的异常", detail[-2000:])
        except Exception:  # noqa: BLE001 - 异常钩子里不能再抛
            pass

    sys.excepthook = hook


def main() -> int:
    _ensure_path()
    _install_excepthook()

    from PySide6.QtWidgets import QApplication

    from autolab.ui.main_window import MainWindow
    from autolab.ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName("AutoClick")
    app.setApplicationDisplayName("AutoClick 可视化流程编排器")
    apply_theme(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
