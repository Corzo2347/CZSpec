"""Sistema visual centralizado de CZSpec."""

from __future__ import annotations


APP_STYLESHEET = r"""
QWidget {
    color: #172033;
    background-color: #F4F7FB;
    font-size: 10pt;
}

QLabel, QCheckBox {
    background-color: transparent;
}

QMainWindow, QDialog {
    background-color: #F4F7FB;
}

QFrame#toastNotification {
    color: #F8FAFC;
    background-color: #13223D;
    border: 1px solid #31517D;
    border-radius: 12px;
}

QLabel#toastTitle {
    color: #FFFFFF;
    background-color: transparent;
    font-size: 10pt;
    font-weight: 700;
}

QLabel#toastMessage {
    color: #D7E3F6;
    background-color: transparent;
}

QPushButton#toastCloseButton {
    color: #D7E3F6;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    min-height: 0;
    padding: 0;
    font-size: 13pt;
}

QPushButton#toastCloseButton:hover {
    color: #FFFFFF;
    background-color: #294468;
}

QWidget#appHeader {
    background-color: #0B1630;
    border-radius: 11px;
}

QLabel#brandMark {
    background-color: transparent;
    border: none;
    padding: 0;
}

QLabel#appTitle {
    color: #FFFFFF;
    background: transparent;
    font-size: 16pt;
    font-weight: 700;
}

QLabel#appSubtitle {
    color: #AFC1DF;
    background: transparent;
    font-size: 8pt;
}

QLabel#versionBadge {
    color: #DCE8FF;
    background-color: #182C52;
    border: 1px solid #284879;
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 8pt;
    font-weight: 600;
}

QPushButton#windowControlButton,
QPushButton#windowCloseButton {
    color: #DCE8FF;
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    min-height: 0;
    padding: 0;
    font-size: 11pt;
    font-weight: 700;
}

QPushButton#windowControlButton:hover {
    color: #FFFFFF;
    background-color: #233B66;
    border-color: #355685;
}

QPushButton#appUpdateButton {
    color: #DCE8FB;
    background-color: #142A50;
    border: 1px solid #31517F;
    border-radius: 7px;
    min-height: 20px;
    padding: 2px 9px;
    font-size: 8pt;
}

QPushButton#appUpdateButton:hover {
    color: #FFFFFF;
    background-color: #1D4178;
    border-color: #4A7FC4;
}

QPushButton#networkModeButton {
    color: #DCE8FB;
    background-color: #374151;
    border: 1px solid #5D6776;
    border-radius: 7px;
    min-height: 20px;
    padding: 2px 9px;
    font-size: 8pt;
    font-weight: 650;
}

QPushButton#networkModeButton[online="true"] {
    color: #ECFDF5;
    background-color: #0F6B57;
    border-color: #2F9C7E;
}

QPushButton#networkModeButton[online="false"] {
    color: #E5E7EB;
    background-color: #374151;
    border-color: #6B7280;
}

QPushButton#networkModeButton:hover {
    color: #FFFFFF;
    border-color: #7FB2F0;
}

QPushButton#windowCloseButton:hover {
    color: #FFFFFF;
    background-color: #C9364B;
    border-color: #E45C70;
}

QTabWidget::pane {
    background-color: #FFFFFF;
    border: 1px solid #D8E1EF;
    border-radius: 12px;
    top: -1px;
}

QTabBar::tab {
    color: #52627A;
    background-color: transparent;
    border: none;
    padding: 11px 18px;
    margin-right: 5px;
    font-weight: 600;
}

QTabBar::tab:selected {
    color: #1C63D5;
    background-color: #EAF2FF;
    border-radius: 9px;
}

QTabBar::tab:hover:!selected {
    color: #1C63D5;
    background-color: #F1F5FB;
    border-radius: 9px;
}

QTabWidget#resultsTabs::pane {
    background-color: #FFFFFF;
    border: 1px solid #D8E1EF;
    border-radius: 10px;
    top: -1px;
}

QTabWidget#resultsTabs QTabBar::tab {
    min-width: 105px;
    padding: 8px 16px;
    margin-right: 4px;
}

QWidget#resultsTabPage {
    background-color: #FFFFFF;
}

QGroupBox[role="comparisonPanel"] {
    margin-top: 10px;
    padding: 8px 5px 5px 5px;
}

QGroupBox[role="comparisonPanel"]::title {
    left: 8px;
    padding: 0 4px;
}

QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #DCE4EF;
    border-radius: 11px;
    margin-top: 13px;
    padding: 14px 10px 10px 10px;
    font-weight: 650;
}

QGroupBox::title {
    color: #26364D;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QGroupBox[role="tablePanel"] {
    margin-top: 10px;
    padding: 8px 5px 5px 5px;
}

QGroupBox[role="tablePanel"]::title {
    left: 8px;
    padding: 0 4px;
}

QPushButton {
    color: #26364D;
    background-color: #FFFFFF;
    border: 1px solid #CBD6E5;
    border-radius: 8px;
    min-height: 24px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    color: #1557BE;
    background-color: #F3F7FE;
    border-color: #75A7EE;
}

QPushButton:pressed {
    background-color: #E5EEFC;
}

QPushButton:disabled {
    color: #9AA7B7;
    background-color: #EFF2F6;
    border-color: #E0E5EC;
}

QCheckBox {
    spacing: 7px;
}

QCheckBox#filterCheckBox::indicator {
    width: 0;
    height: 0;
    border: none;
}

QCheckBox#filterCheckBox:checked {
    color: #1557BE;
    font-weight: 650;
}

QCheckBox::indicator,
QTableWidget::indicator {
    width: 15px;
    height: 15px;
    background-color: #FFFFFF;
    border: 1px solid #8191A8;
    border-radius: 3px;
}

QCheckBox::indicator:checked,
QTableWidget::indicator:checked {
    background-color: #246BDE;
    border: 2px solid #164FAE;
}

QCheckBox::indicator:hover,
QTableWidget::indicator:hover {
    border-color: #246BDE;
}

QPushButton[role="primary"] {
    color: #FFFFFF;
    background-color: #246BDE;
    border-color: #246BDE;
}

QPushButton[role="primary"]:hover {
    background-color: #185BC4;
    border-color: #185BC4;
}

QPushButton[role="accent"] {
    color: #0B594B;
    background-color: #DCF8F1;
    border-color: #98DFCE;
}

QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    color: #172033;
    background-color: #FFFFFF;
    border: 1px solid #C9D4E3;
    border-radius: 8px;
    min-height: 27px;
    padding: 4px 8px;
    selection-background-color: #2E7CF6;
}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border: 2px solid #2E7CF6;
}

QTableWidget, QListWidget, QTextEdit {
    color: #1F2D40;
    background-color: #FFFFFF;
    alternate-background-color: #F6F9FD;
    border: 1px solid #D5DFEC;
    border-radius: 8px;
    gridline-color: #E5EBF3;
    selection-background-color: #DCEAFF;
    selection-color: #163C73;
}

QHeaderView::section {
    color: #344760;
    background-color: #EEF3F9;
    border: none;
    border-right: 1px solid #D8E1EC;
    border-bottom: 1px solid #D8E1EC;
    padding: 7px;
    font-weight: 650;
}

QScrollBar:vertical {
    background: transparent;
    width: 11px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #BCC9D9;
    border-radius: 5px;
    min-height: 28px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollArea#sidePanelScroll {
    background-color: transparent;
    border: none;
}

QSplitter::handle {
    background-color: #E5EAF1;
    width: 2px;
    height: 2px;
}

QStatusBar {
    color: #53647B;
    background-color: #F4F7FB;
    border-top: 1px solid #DEE5EF;
}

QProgressBar#taskProgress {
    background-color: #DFE7F2;
    border: none;
    border-radius: 4px;
    max-height: 8px;
}

QProgressBar#taskProgress::chunk {
    background-color: #2E7CF6;
    border-radius: 4px;
}

/* Semantic action colors.  Roles are assigned in the GUI; disabled buttons
   continue to use Qt's disabled-state styling. */
QPushButton[actionRole="primary"] { background:#2563EB; color:white; border-color:#1D4ED8; font-weight:700; }
QPushButton[actionRole="primary"]:hover { background:#1D4ED8; }
QPushButton[actionRole="success"] { background:#059669; color:white; border-color:#047857; font-weight:700; }
QPushButton[actionRole="success"]:hover { background:#047857; }
QPushButton[actionRole="export"] { background:#0F766E; color:white; border-color:#115E59; font-weight:700; }
QPushButton[actionRole="export"]:hover { background:#115E59; }
QPushButton[actionRole="secondary"] { background:#E8F0FE; color:#174EA6; border-color:#AFC8F6; font-weight:650; }
QPushButton[actionRole="secondary"]:hover { background:#DCE8FD; }
QPushButton[actionRole="folder"] { background:#EEF2F7; color:#334155; border-color:#CBD5E1; font-weight:650; }
QPushButton[actionRole="folder"]:hover { background:#E2E8F0; }
QPushButton[actionRole="danger"] { background:#FEE2E2; color:#B91C1C; border-color:#FCA5A5; font-weight:700; }
QPushButton[actionRole="danger"]:hover { background:#FECACA; }
QPushButton[actionRole="utility"] { background:#F8FAFC; color:#475569; border-color:#CBD5E1; }
QPushButton[actionRole]:disabled { background:#EEF2F7; color:#94A3B8; border-color:#D7DEE8; font-weight:600; }
"""


def build_app_stylesheet(scale_percent: int | float = 100, font_family: str | None = None) -> str:
    """Scale typography while keeping widget geometry stable.

    Font-family changes are applied through the application font rather than by
    rebuilding every widget.  A light stylesheet override keeps Plot/Qt labels
    consistent without forcing expensive relayout loops.
    """
    import re as _re
    try:
        scale = max(80.0, min(150.0, float(scale_percent))) / 100.0
    except Exception:
        scale = 1.0
    def repl(match):
        value = float(match.group(1)) * scale
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"font-size: {text}pt"
    css = _re.sub(r"font-size:\s*([0-9]+(?:\.[0-9]+)?)pt", repl, APP_STYLESHEET)
    family = str(font_family or "").strip().replace('"', '')
    if family:
        css += f'\nQWidget {{ font-family: "{family}"; }}\n'
    return css
