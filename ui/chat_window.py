"""PySide6 聊天窗口，网络线程消息通过 Qt Signal 转发到主线程。"""
from __future__ import annotations

import base64
import binascii
import html
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from db.chat_db import ChatDatabase
from network.client import ChatClient
from utils.emoji import EmojiPicker

ALLOWED_AVATARS = ["😀", "😂", "😍", "😭", "😡", "👍", "🎉", "😎", "🤔", "😱"]
MAX_IMAGE_BYTES = 4 * 1024 * 1024


class Bridge(QObject):
    message = Signal(dict)
    disconnected = Signal(str)


class UserInfoDialog(QDialog):
    """用户信息输入框：昵称 + 头像。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户信息")
        self.setModal(True)

        form = QFormLayout(self)
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("请输入 1-32 字符昵称")
        self.avatar_combo = QComboBox(self)
        self.avatar_combo.addItems(ALLOWED_AVATARS)
        self.host_input = QLineEdit(self)
        self.host_input.setText("127.0.0.1")
        self.port_input = QLineEdit(self)
        self.port_input.setText("8765")

        form.addRow("昵称", self.name_input)
        form.addRow("头像", self.avatar_combo)
        form.addRow("服务器 IP", self.host_input)
        form.addRow("端口", self.port_input)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("连接", self)
        cancel_btn = QPushButton("取消", self)
        ok_btn.clicked.connect(self._submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        form.addRow(buttons)

    def _submit(self) -> None:
        name = self.name_input.text().strip()
        if not 1 <= len(name) <= 32:
            QMessageBox.warning(self, "输入错误", "昵称长度必须在 1-32 字符之间")
            return
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "输入错误", "服务器 IP 不能为空")
            return
        port_text = self.port_input.text().strip()
        if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            QMessageBox.warning(self, "输入错误", "端口必须是 1-65535 的数字")
            return
        self.accept()

    def user_info(self) -> tuple[str, str, str, int]:
        return (
            self.name_input.text().strip(),
            self.avatar_combo.currentText(),
            self.host_input.text().strip(),
            int(self.port_input.text().strip()),
        )


class ChatWindow(QMainWindow):
    """聊天室主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("局域网聊天室")
        self.resize(900, 600)

        self.name = ""
        self.avatar = "😀"
        self.db: ChatDatabase | None = None
        self.client: ChatClient | None = None
        self.images = Path.home() / ".chatroom" / "images"
        self.images.mkdir(parents=True, exist_ok=True)

        self.bridge = Bridge()
        self.bridge.message.connect(self.handle)
        self.bridge.disconnected.connect(self._on_disconnect)

        self.build()
        self.login()

    def build(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        left = QVBoxLayout()
        right = QVBoxLayout()

        self.view = QTextBrowser()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入消息，回车发送")
        self.users = QListWidget()

        left.addWidget(self.view)
        left.addWidget(self.input)

        buttons = QHBoxLayout()
        for text, callback in (
            ("表情", self.emoji),
            ("图片", self.image),
            ("发送", self.send),
            ("清空记录", self.clear),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            buttons.addWidget(button)

        self.input.returnPressed.connect(self.send)
        left.addLayout(buttons)

        right.addWidget(QLabel("在线用户"))
        right.addWidget(self.users)

        layout.addLayout(left, 4)
        layout.addLayout(right, 1)

    def login(self) -> None:
        dialog = UserInfoDialog(self)
        if dialog.exec() != QDialog.Accepted:
            self.close()
            return
        name, avatar, host, port = dialog.user_info()

        self.name = name
        self.avatar = avatar
        self.db = ChatDatabase(self.name)
        self.reload_history()

        self.client = ChatClient(
            lambda message: self.bridge.message.emit(message),
            lambda reason: self.bridge.disconnected.emit(reason),
        )
        try:
            self.client.connect(host, port, self.name, self.avatar)
        except OSError as exc:
            QMessageBox.critical(self, "连接失败", str(exc))
            self.close()

    def reload_history(self) -> None:
        self.view.clear()
        if not self.db:
            return
        for message in self.db.history():
            self.render_chat(message)

    @Slot()
    def send(self) -> None:
        text = self.input.text().strip()
        if not text or not self.client:
            return
        try:
            self.client.send_chat(text)
            self.input.clear()
        except (OSError, ConnectionError) as exc:
            QMessageBox.warning(self, "发送失败", str(exc))

    @Slot()
    def emoji(self) -> None:
        if not self.client:
            return
        picker = EmojiPicker(self)
        picker.emoji_selected.connect(self._send_emoji)
        picker.exec()

    @Slot(str)
    def _send_emoji(self, value: str) -> None:
        if not self.client:
            return
        try:
            self.client.send_emoji(value)
        except (OSError, ConnectionError) as exc:
            QMessageBox.warning(self, "发送失败", str(exc))

    @Slot()
    def image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)",
        )
        if not filename or not self.client:
            return
        raw = Path(filename).read_bytes()
        if len(raw) > MAX_IMAGE_BYTES:
            QMessageBox.warning(self, "图片过大", "图片不能超过 4 MB")
            return
        payload = base64.b64encode(raw).decode("utf-8")
        try:
            self.client.send_image(payload, Path(filename).name)
        except (OSError, ConnectionError) as exc:
            QMessageBox.warning(self, "发送失败", str(exc))

    @Slot(dict)
    def handle(self, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "registered":
            self.statusBar().showMessage(f"已连接：{message.get('name', '')}")
        elif kind == "chat":
            if self.db:
                self.db.add(message)
            self.render_chat(message)
        elif kind == "user_list":
            self.users.clear()
            self.users.addItems(
                [f"{user.get('avatar', '')} {user.get('name', '')}" for user in message.get("users", [])]
            )
        elif kind in {"user_join", "user_leave"}:
            self.render_system(message.get("message", "用户状态变更"))
        elif kind == "system":
            self.render_system(message.get("message", ""))
        elif kind == "delete":
            if self.db:
                self.db.clear()
            self.reload_history()
            self.render_system(f"{message.get('avatar', '')} {message.get('sender', '')} 清空了聊天记录")
        elif kind == "error":
            QMessageBox.warning(self, "服务器提示", message.get("message", "未知错误"))

    def render_system(self, text: str) -> None:
        self.view.append(f"<i>{html.escape(text)}</i>")
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())

    def render_chat(self, message: dict[str, Any]) -> None:
        sender = html.escape(message.get("sender", "未知用户"))
        avatar = html.escape(message.get("avatar", ""))
        content_type = message.get("content_type", "text")
        timestamp = html.escape(message.get("timestamp", ""))

        if content_type == "image":
            self._render_image_message(sender, avatar, timestamp, message)
            return

        content = html.escape(message.get("content", ""))
        self.view.append(f"<b>{avatar} {sender}</b>：{content} <span style='color:#888'>[{timestamp}]</span>")
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())

    def _render_image_message(self, sender: str, avatar: str, timestamp: str, message: dict[str, Any]) -> None:
        content = message.get("content", "")
        filename = self._safe_filename(message.get("filename", "image.bin"))
        try:
            data = base64.b64decode(content, validate=True)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("图片超限")
            stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            path = self.images / f"{stamp}_{filename}"
            path.write_bytes(data)
            self.view.append(
                f"<b>{avatar} {sender}</b>：<img src='{path.as_uri()}' width='240'>"
                f" <span style='color:#888'>[{timestamp}]</span>"
            )
        except (OSError, ValueError, binascii.Error):
            self.view.append(f"<b>{avatar} {sender}</b>：[图片无效] <span style='color:#888'>[{timestamp}]</span>")
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())

    @staticmethod
    def _safe_filename(filename: str) -> str:
        raw = Path(str(filename)).name
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in raw)
        return safe[:128] or "image.bin"

    @Slot()
    def clear(self) -> None:
        if not self.client:
            return
        if QMessageBox.question(self, "确认", "清空所有客户端聊天记录？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.client.send_delete()
        except (OSError, ConnectionError) as exc:
            QMessageBox.warning(self, "发送失败", str(exc))

    @Slot(str)
    def _on_disconnect(self, reason: str) -> None:
        self.statusBar().showMessage(reason)
        self.render_system(f"连接断开：{reason}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.client:
            self.client.close()
        if self.db:
            self.db.close()
        event.accept()
