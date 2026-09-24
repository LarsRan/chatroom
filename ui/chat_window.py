"""PySide6 聊天窗口，网络线程消息通过 Qt Signal 转发到主线程。"""
from __future__ import annotations

import base64
import binascii
import hashlib
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from db.chat_db import ChatDatabase
from network.client import ChatClient
from ui.theme import apply_chat_theme, bubble_style
from utils.emoji import EmojiPicker

ALLOWED_AVATARS = ["😀", "😂", "😍", "😭", "😡", "👍", "🎉", "😎", "🤔", "😱"]
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_WIDTH = 240


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


class SystemMessageWidget(QWidget):
    """系统消息控件。"""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addStretch(1)
        label = QLabel(text, self)
        label.setObjectName("systemMessage")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)


class MessageBubbleWidget(QWidget):
    """单条聊天消息控件：头像 + 气泡 + 时间戳。"""

    def __init__(
        self,
        *,
        sender: str,
        avatar: str,
        timestamp: str,
        content_type: str,
        content: str,
        is_self: bool,
        image_path: Path | None = None,
        invalid_image: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.is_self = is_self
        self.content_type = content_type
        self.original_pixmap: QPixmap | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 4, 10, 4)
        root.setSpacing(6)

        avatar_label = QLabel(avatar or "🙂", self)
        avatar_label.setFixedWidth(26)
        avatar_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        bubble_column = QWidget(self)
        bubble_layout = QVBoxLayout(bubble_column)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.setSpacing(2)

        sender_label = QLabel(sender, bubble_column)
        sender_label.setObjectName("senderName")
        sender_label.setAlignment(Qt.AlignRight if is_self else Qt.AlignLeft)
        bubble_layout.addWidget(sender_label)

        self.bubble = QLabel(bubble_column)
        self.bubble.setWordWrap(True)
        self.bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.bubble.setStyleSheet(bubble_style(is_self))

        if content_type == "image":
            self._set_image_content(image_path, invalid_image)
        else:
            self._set_text_content(content)

        bubble_layout.addWidget(self.bubble, 0, Qt.AlignRight if is_self else Qt.AlignLeft)

        time_label = QLabel(timestamp, bubble_column)
        time_label.setObjectName("timestampLabel")
        time_label.setAlignment(Qt.AlignRight if is_self else Qt.AlignLeft)
        bubble_layout.addWidget(time_label)

        if is_self:
            root.addStretch(1)
            root.addWidget(bubble_column, 0)
            root.addWidget(avatar_label, 0, Qt.AlignTop)
        else:
            root.addWidget(avatar_label, 0, Qt.AlignTop)
            root.addWidget(bubble_column, 0)
            root.addStretch(1)

    def _set_text_content(self, content: str) -> None:
        self.bubble.setText(content)
        font = QFont(self.bubble.font())
        if self.content_type == "emoji":
            font.setPointSize(16)
        else:
            font.setPointSize(9)
        self.bubble.setFont(font)

    def _set_image_content(self, image_path: Path | None, invalid_image: bool) -> None:
        self.bubble.setAlignment(Qt.AlignCenter)
        if invalid_image or image_path is None:
            self.bubble.setText("[图片无效]")
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.bubble.setText("[图片无效]")
            return
        self.original_pixmap = pixmap
        self._apply_scaled_pixmap(MAX_IMAGE_WIDTH)

    def _apply_scaled_pixmap(self, max_width: int) -> None:
        if not self.original_pixmap:
            return
        target_width = max(120, min(MAX_IMAGE_WIDTH, max_width))
        scaled = self.original_pixmap.scaledToWidth(target_width, Qt.SmoothTransformation)
        self.bubble.setPixmap(scaled)

    def set_bubble_max_width(self, max_width: int) -> None:
        width = max(140, max_width)
        self.bubble.setMaximumWidth(width)
        if self.content_type == "image":
            self._apply_scaled_pixmap(width)


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
        self._bubble_widgets: list[MessageBubbleWidget] = []

        self.bridge = Bridge()
        self.bridge.message.connect(self.handle)
        self.bridge.disconnected.connect(self._on_disconnect)

        self.build()
        self.login()

    def build(self) -> None:
        root = QWidget(self)
        root.setObjectName("rootPanel")
        self.setCentralWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(8, 8, 8, 8)
        page.setSpacing(6)

        title = QFrame(root)
        title.setObjectName("titleBar")
        title_layout = QHBoxLayout(title)
        title_layout.setContentsMargins(8, 4, 8, 4)
        title_text = QLabel("局域网聊天室", title)
        title_text.setObjectName("titleLabel")
        title_layout.addWidget(title_text)
        title_layout.addStretch(1)
        page.addWidget(title)

        divider = QFrame(root)
        divider.setObjectName("dividerLine")
        divider.setFixedHeight(2)
        page.addWidget(divider)

        body = QHBoxLayout()
        body.setSpacing(8)

        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(6)
        right.setSpacing(6)

        self.scroll = QScrollArea(root)
        self.scroll.setObjectName("chatScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.message_container = QWidget(self.scroll)
        self.message_container.setObjectName("messageContainer")
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(8, 8, 8, 8)
        self.message_layout.setSpacing(4)
        self.message_layout.addStretch(1)
        self.scroll.setWidget(self.message_container)

        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("输入消息，回车发送")
        self.users = QListWidget()
        self.users.setObjectName("userList")

        left.addWidget(self.scroll)
        left.addWidget(self.input)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
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

        user_title = QLabel("在线用户")
        user_title.setObjectName("userTitle")
        right.addWidget(user_title)
        right.addWidget(self.users)

        split = QFrame(root)
        split.setObjectName("splitLine")
        split.setFixedWidth(2)

        body.addLayout(left, 4)
        body.addWidget(split)
        body.addLayout(right, 1)
        page.addLayout(body)

        apply_chat_theme(self)

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
        self._clear_message_widgets()
        if not self.db:
            return
        for message in self.db.history():
            self.render_chat(message)

    def _clear_message_widgets(self) -> None:
        self._bubble_widgets.clear()
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

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
        try:
            raw = Path(filename).read_bytes()
        except OSError as exc:
            QMessageBox.warning(self, "读取失败", str(exc))
            return
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
        self._append_message_widget(SystemMessageWidget(text, self.message_container))

    def render_chat(self, message: dict[str, Any]) -> None:
        sender = str(message.get("sender", "未知用户"))
        avatar = str(message.get("avatar", ""))
        content_type = str(message.get("content_type", "text"))
        timestamp = str(message.get("timestamp", ""))
        content = str(message.get("content", ""))
        is_self = sender == self.name

        image_path: Path | None = None
        invalid_image = False
        if content_type == "image":
            image_path = self._materialize_image_file(content, str(message.get("filename", "image.bin")))
            invalid_image = image_path is None

        bubble = MessageBubbleWidget(
            sender=sender,
            avatar=avatar,
            timestamp=timestamp,
            content_type=content_type,
            content=content,
            is_self=is_self,
            image_path=image_path,
            invalid_image=invalid_image,
            parent=self.message_container,
        )
        self._bubble_widgets.append(bubble)
        self._append_message_widget(bubble)
        self._update_bubble_widths()

    def _append_message_widget(self, widget: QWidget) -> None:
        self.message_layout.insertWidget(self.message_layout.count() - 1, widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def _update_bubble_widths(self) -> None:
        max_width = int(self.scroll.viewport().width() * 0.6)
        for widget in self._bubble_widgets:
            widget.set_bubble_max_width(max_width)

    def _materialize_image_file(self, content: str, filename: str) -> Path | None:
        safe_name = self._safe_filename(filename)
        try:
            data = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError):
            return None
        if len(data) > MAX_IMAGE_BYTES:
            return None
        digest = hashlib.sha1(data).hexdigest()[:16]
        path = self.images / f"{digest}_{safe_name}"
        if not path.exists():
            try:
                if not QImage.fromData(data).isNull():
                    path.write_bytes(data)
                else:
                    return None
            except OSError:
                return None
        return path

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

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_bubble_widths()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.client:
            self.client.close()
        if self.db:
            self.db.close()
        event.accept()
