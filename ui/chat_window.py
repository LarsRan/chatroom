"""PySide6 chat window. Network callbacks are marshalled through Qt signals."""
from __future__ import annotations
import base64
from datetime import datetime
from pathlib import Path
from typing import Any
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout, QWidget
from db.chat_db import ChatDatabase
from network.client import ChatClient
from utils.emoji import all_emojis

class Bridge(QObject):
    message = Signal(dict); disconnected = Signal(str)

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("局域网聊天室"); self.resize(900, 600); self.name = ""; self.avatar = "🙂"; self.db = None; self.client = None; self.images = Path.home() / ".chatroom" / "images"; self.images.mkdir(parents=True, exist_ok=True); self.bridge = Bridge(); self.bridge.message.connect(self.handle); self.bridge.disconnected.connect(lambda reason: self.statusBar().showMessage(reason)); self.build(); self.login()
    def build(self):
        root = QWidget(); self.setCentralWidget(root); layout = QHBoxLayout(root); left = QVBoxLayout(); right = QVBoxLayout(); self.view = QTextBrowser(); self.input = QLineEdit(); self.input.setPlaceholderText("输入消息，回车发送"); self.users = QListWidget(); left.addWidget(self.view); left.addWidget(self.input); buttons = QHBoxLayout()
        for text, callback in (("表情", self.emoji), ("图片", self.image), ("发送", self.send), ("清空记录", self.clear)):
            button = QPushButton(text); button.clicked.connect(callback); buttons.addWidget(button)
        self.input.returnPressed.connect(self.send); left.addLayout(buttons); right.addWidget(QLabel("在线用户")); right.addWidget(self.users); layout.addLayout(left, 4); layout.addLayout(right, 1)
    def login(self):
        name, ok = QInputDialog.getText(self, "注册", "昵称：")
        if not ok or not name.strip(): self.close(); return
        host, ok = QInputDialog.getText(self, "服务器", "IP：", text="127.0.0.1")
        if not ok: self.close(); return
        port, ok = QInputDialog.getInt(self, "服务器", "端口：", 8765, 1, 65535)
        if not ok: self.close(); return
        self.name = name.strip(); self.db = ChatDatabase(self.name); [self.render(m) for m in self.db.history()]; self.client = ChatClient(lambda m: self.bridge.message.emit(m), lambda r: self.bridge.disconnected.emit(r))
        try: self.client.connect(host.strip(), port, self.name, self.avatar)
        except OSError as exc: QMessageBox.critical(self, "连接失败", str(exc)); self.close()
    @Slot()
    def send(self):
        text = self.input.text().strip()
        if text and self.client:
            try: self.client.send_chat(text); self.input.clear()
            except (OSError, ConnectionError) as exc: QMessageBox.warning(self, "发送失败", str(exc))
    @Slot()
    def emoji(self):
        value, ok = QInputDialog.getItem(self, "选择表情", "表情：", all_emojis(), 0, False)
        if ok and self.client: self.client.send_chat(value, "emoji")
    @Slot()
    def image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not filename or not self.client: return
        raw = Path(filename).read_bytes()
        if len(raw) > 4 * 1024 * 1024: QMessageBox.warning(self, "图片过大", "图片不能超过 4 MB"); return
        self.client.send_chat(base64.b64encode(raw).decode(), "image", Path(filename).name)
    @Slot(dict)
    def handle(self, message: dict[str, Any]):
        kind = message.get("type")
        if kind == "chat":
            if self.db: self.db.add(message)
            self.render(message)
        elif kind == "system": self.view.append(f"<i>{message.get('message','')}</i>")
        elif kind == "user_list": self.users.clear(); self.users.addItems([f"{u.get('avatar','')} {u.get('name','')}" for u in message.get('users', [])])
        elif kind == "error": QMessageBox.warning(self, "服务器提示", message.get("message", "未知错误"))
    def render(self, message):
        sender = message.get("sender", "未知用户")
        if message.get("content_type") == "image":
            try:
                data = base64.b64decode(message["content"], validate=True); path = self.images / f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{Path(message.get('filename','image')).name}"; path.write_bytes(data); self.view.append(f"<b>{sender}</b>：<img src='{path.as_uri()}' width='240'>")
            except Exception: self.view.append(f"<b>{sender}</b>：[图片无效]")
        else: self.view.append(f"<b>{sender}</b>：{message.get('content','')}")
    @Slot()
    def clear(self):
        if self.db and QMessageBox.question(self, "确认", "清空本地记录？") == QMessageBox.StandardButton.Yes: self.db.clear(); self.view.clear()
    def closeEvent(self, event):
        if self.client: self.client.close()
        if self.db: self.db.close()
        event.accept()
