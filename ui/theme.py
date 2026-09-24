"""聊天窗口主题样式（QQ 2000 / Windows XP 银蓝风）。"""
from __future__ import annotations

CHAT_QSS = """
QMainWindow {
    background: #E6EEF6;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 9pt;
    color: #1B2F44;
}

#rootPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #F2F5F8,
                                stop:1 #D8E4F0);
}

#titleBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2E7EC5,
                                stop:1 #0A5FA8);
    border: 1px solid #285A8D;
    border-radius: 4px;
    padding: 4px 8px;
}

#titleLabel {
    color: #FFFFFF;
    font-size: 10pt;
    font-weight: bold;
}

#dividerLine,
#splitLine {
    background: transparent;
    border: none;
}

#dividerLine {
    border-top: 1px solid #7C95AC;
    border-bottom: 1px solid #FFFFFF;
}

#splitLine {
    border-left: 1px solid #7C95AC;
    border-right: 1px solid #FFFFFF;
}

#chatScroll,
#userList {
    background: #FFFFFF;
    border: 1px solid #7B95AE;
    border-top-color: #5E7183;
    border-left-color: #5E7183;
    border-right-color: #D7E2EC;
    border-bottom-color: #D7E2EC;
}

#messageContainer {
    background: transparent;
}

#chatInput {
    background: #FFFFFF;
    border: 1px solid #7B95AE;
    border-top-color: #5E7183;
    border-left-color: #5E7183;
    border-right-color: #D7E2EC;
    border-bottom-color: #D7E2EC;
    padding: 4px 6px;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #FDFEFF,
                                stop:0.45 #E7EEF5,
                                stop:1 #C8D8E8);
    border: 1px solid #6E8BA7;
    border-radius: 4px;
    padding: 4px 12px;
    color: #183149;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #FFFFFF,
                                stop:0.5 #EDF4FB,
                                stop:1 #D7E5F3);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #B7CADF,
                                stop:1 #E4EDF7);
    padding-top: 5px;
    padding-left: 13px;
}

#userTitle {
    color: #0A5FA8;
    font-weight: bold;
}

QListWidget#userList::item {
    padding: 2px 6px;
    min-height: 22px;
}

#systemMessage {
    color: #6B6B6B;
    font-size: 8pt;
}

#senderName {
    color: #0A5FA8;
    font-size: 8pt;
    font-weight: bold;
}

#timestampLabel {
    color: #6B6B6B;
    font-size: 8pt;
}

QScrollBar:vertical {
    background: #D8E4F0;
    width: 16px;
    border: 1px solid #7A93AC;
}

QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #F8FBFF,
                                stop:0.5 #D4E2F0,
                                stop:1 #BCCFE2);
    border: 1px solid #6D88A3;
    min-height: 26px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 16px;
    border: 1px solid #6D88A3;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #F6FAFF,
                                stop:1 #C4D6E8);
}

QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical {
    width: 8px;
    height: 8px;
    background: #4A6987;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: #D8E4F0;
}
"""


def bubble_style(is_self: bool) -> str:
    """返回聊天气泡样式。"""
    if is_self:
        return (
            "background-color:#CFE6FF;"
            "border:1px solid #8FAEC8;"
            "border-radius:10px;"
            "padding:6px 10px;"
            "color:#203647;"
        )
    return (
        "background-color:#FFFFFF;"
        "border:1px solid #9DB8D2;"
        "border-radius:10px;"
        "padding:6px 10px;"
        "color:#203647;"
    )


def apply_chat_theme(window) -> None:
    """应用窗口主题样式。"""
    window.setStyleSheet(CHAT_QSS)
