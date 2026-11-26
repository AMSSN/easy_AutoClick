"""深色主题：调色板、字体与全局 QSS。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg": "#0F1115",
    "bg_panel": "#171A21",
    "bg_panel_alt": "#141820",
    "bg_card": "#1E222B",
    "bg_input": "#12151A",
    "bg_canvas": "#12151B",
    "grid_minor": "#191E27",
    "grid_major": "#212833",
    "border": "#262C38",
    "border_soft": "#1F242E",
    "text": "#E6EAF2",
    "text_muted": "#9AA4B2",
    "text_dim": "#5C6675",
    "primary": "#4F8CFF",
    "primary_dark": "#3A6FD8",
    "success": "#22C55E",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "purple": "#8B5CF6",
    "cyan": "#06B6D4",
    "edge": "#39404F",
}

FONT_FAMILY = "Microsoft YaHei UI"
MONO_FAMILY = "Consolas"

QSS = """
* { outline: none; }

QWidget {
    color: #E6EAF2;
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow, QWidget#Root { background: #0F1115; }

/* ---------------------------------------------------------------- 顶栏 */
QWidget#TopBar {
    background: #171A21;
    border-bottom: 1px solid #262C38;
}
QLabel#Brand {
    font-size: 16px;
    font-weight: 600;
    color: #E6EAF2;
}
QLabel#BrandSub {
    font-size: 11px;
    color: #5C6675;
    padding-left: 2px;
}
QLabel#TopLabel { color: #9AA4B2; font-size: 12px; }

/* ---------------------------------------------------------------- 面板 */
QWidget#Panel { background: #171A21; }
QWidget#PanelHeader {
    background: #171A21;
    border-bottom: 1px solid #20252F;
}
QLabel#PanelTitle {
    color: #9AA4B2;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}
QLabel#PageTitle { font-size: 15px; font-weight: 600; color: #E6EAF2; }
QLabel#FieldLabel { color: #9AA4B2; font-size: 12px; }
QLabel#Hint { color: #5C6675; font-size: 11px; }
QLabel#Thumb {
    background: #12151A;
    border: 1px dashed #2A3140;
    border-radius: 8px;
    color: #5C6675;
    font-size: 11px;
}

/* ---------------------------------------------------------------- 按钮 */
QPushButton {
    background: #232935;
    border: 1px solid #2C333F;
    border-radius: 8px;
    padding: 6px 14px;
    color: #E6EAF2;
    min-height: 18px;
}
QPushButton:hover { background: #2A3140; border-color: #3A4353; }
QPushButton:pressed { background: #1C2230; padding-top: 7px; padding-bottom: 5px; }
QPushButton:disabled { color: #5C6675; background: #1A1F28; border-color: #232935; }

QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #5C97FF, stop:1 #3A6FD8);
    border: 1px solid #3A6FD8;
    color: #FFFFFF;
    font-weight: 600;
    padding: 7px 20px;
}
QPushButton#PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6EA4FF, stop:1 #4A7FE8);
}
QPushButton#PrimaryButton:disabled { background: #243044; color: #6C7C93; border-color: #2A3547; }

QPushButton#DangerButton {
    background: #2B1B1F;
    border: 1px solid #4A2730;
    color: #FF8A8A;
    font-weight: 600;
    padding: 7px 18px;
}
QPushButton#DangerButton:hover { background: #3A2127; border-color: #6B303B; color: #FFA3A3; }
QPushButton#DangerButton:disabled { background: #1D1A1E; color: #63525A; border-color: #2A2328; }

QPushButton#GhostButton {
    background: transparent;
    border: 1px solid transparent;
    color: #9AA4B2;
    padding: 6px 12px;
}
QPushButton#GhostButton:hover { background: #232935; color: #E6EAF2; border-color: #2C333F; }

QPushButton#LinkButton {
    background: transparent;
    border: none;
    color: #4F8CFF;
    padding: 2px 4px;
}
QPushButton#LinkButton:hover { color: #7FAEFF; }

/* ---------------------------------------------------------------- 输入 */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background: #12151A;
    border: 1px solid #262C38;
    border-radius: 8px;
    padding: 6px 10px;
    color: #E6EAF2;
    selection-background-color: #3A6FD8;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #4F8CFF;
    background: #141821;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: #5C6675;
    background: #161A21;
}
QLineEdit[readOnly="true"] { color: #9AA4B2; }

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    width: 16px;
    border: none;
    background: transparent;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #232935;
    border-radius: 4px;
}

QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #1E222B;
    border: 1px solid #2C333F;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #2A3550;
    outline: none;
}

QCheckBox { spacing: 8px; color: #9AA4B2; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border-radius: 4px;
    border: 1px solid #333B4A;
    background: #12151A;
}
QCheckBox::indicator:checked { background: #4F8CFF; border-color: #4F8CFF; }

/* ---------------------------------------------------------------- 树 */
QTreeWidget#Palette {
    background: transparent;
    border: none;
    outline: none;
}
QTreeWidget#Palette::item {
    height: 34px;
    border-radius: 8px;
    color: #C6CDD9;
    padding-left: 4px;
}
QTreeWidget#Palette::item:hover { background: #1F2531; color: #FFFFFF; }
QTreeWidget#Palette::item:selected { background: #22304A; color: #FFFFFF; }
QTreeWidget#Palette::branch { background: transparent; }

/* ---------------------------------------------------------------- 滚动条 */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #313949;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #414B60; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #313949;
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background: #414B60; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

/* ---------------------------------------------------------------- 画布容器 */
QGraphicsView#Canvas {
    background: #12151B;
    border: 1px solid #20252F;
    border-radius: 10px;
}

/* ---------------------------------------------------------------- 日志 */
QWidget#LogPanel { background: #171A21; border-top: 1px solid #262C38; }
QTextEdit#LogView {
    background: #12151A;
    border: 1px solid #20252F;
    border-radius: 8px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 12px;
    padding: 8px;
}

/* ---------------------------------------------------------------- 其他 */
QSplitter::handle { background: #0F1115; }
QSplitter::handle:horizontal { width: 6px; }
QSplitter::handle:vertical { height: 6px; }
QSplitter::handle:hover { background: #1E222B; }

QMenu {
    background: #1E222B;
    border: 1px solid #2C333F;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 22px 7px 14px;
    border-radius: 6px;
    color: #D6DCE8;
}
QMenu::item:selected { background: #22304A; color: #FFFFFF; }
QMenu::separator { height: 1px; background: #262C38; margin: 5px 8px; }

QToolTip {
    background: #1E222B;
    color: #E6EAF2;
    border: 1px solid #2C333F;
    border-radius: 6px;
    padding: 5px 8px;
}

QStatusBar { background: #171A21; border-top: 1px solid #20252F; color: #5C6675; }
QStatusBar::item { border: none; }

QMessageBox { background: #171A21; }
QMessageBox QLabel { color: #E6EAF2; }
"""


def apply_theme(app: QApplication) -> None:
    """套用深色主题与字体。"""
    # Fusion 风格对 QSS 与深色调色板的支持最稳定
    app.setStyle("Fusion")

    font = QFont(FONT_FAMILY, 10)
    font.setFamilies([FONT_FAMILY, "PingFang SC", "Segoe UI", "sans-serif"])
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["bg_input"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["bg_card"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["bg_card"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["primary_dark"]))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["bg_card"]))
    palette.setColor(QPalette.ToolTipText, QColor(COLORS["text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(COLORS["text_dim"]))
    app.setPalette(palette)

    app.setStyleSheet(QSS)
