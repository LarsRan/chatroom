"""Threaded TCP chat server using newline-delimited JSON messages."""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import logging
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

MAX_LINE = 8 * 1024 * 1024
MAX_TEXT = 4000
MAX_IMAGE_B64 = 6 * 1024 * 1024
MAX_IMAGE_BYTES = 4 * 1024 * 1024


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def send_json(sock: socket.socket, value: dict[str, Any]) -> None:
    data = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    sock.sendall(data)


@dataclass
class Client:
    sock: socket.socket
    address: tuple[str, int]
    name: str
    avatar: str


class ChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host, self.port = host, port
        self.listener: socket.socket | None = None
        self.clients: dict[socket.socket, Client] = {}
        self.lock = threading.RLock()
        self.stopping = threading.Event()

    def start(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            self.listener = listener
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self.host, self.port))
            listener.listen()
            logging.info("Listening on %s:%s", self.host, self.port)
            while not self.stopping.is_set():
                try:
                    sock, address = listener.accept()
                except OSError:
                    break
                threading.Thread(target=self.handle_client, args=(sock, address), daemon=True).start()

    def handle_client(self, sock: socket.socket, address: tuple[str, int]) -> None:
        client: Client | None = None
        buffer = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > MAX_LINE:
                    self.safe_send(sock, {"type": "error", "message": "消息过大"})
                    break
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    if not raw.strip():
                        continue
                    try:
                        message = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        self.safe_send(sock, {"type": "error", "message": "无效 JSON"})
                        continue
                    if not isinstance(message, dict):
                        self.safe_send(sock, {"type": "error", "message": "消息格式错误"})
                        continue
                    if client is None:
                        client = self.register(sock, address, message)
                        if client is None:
                            return
                    else:
                        self.handle_message(client, message)
        except (OSError, ConnectionError):
            logging.info("Disconnected: %s", address)
        finally:
            if client:
                self.remove(sock)
            else:
                try:
                    sock.close()
                except OSError:
                    pass

    def register(self, sock: socket.socket, address: tuple[str, int], message: dict[str, Any]) -> Client | None:
        name = message.get("name")
        if message.get("type") != "register" or not isinstance(name, str) or not 1 <= len(name.strip()) <= 32:
            self.safe_send(sock, {"type": "error", "message": "请先使用 1-32 个字符的昵称注册"})
            return None
        name = name.strip()
        avatar = str(message.get("avatar", "😀"))[:8]
        with self.lock:
            if any(c.name == name for c in self.clients.values()):
                self.safe_send(sock, {"type": "error", "message": "昵称已被占用"})
                return None
            client = Client(sock, address, name, avatar)
            self.clients[sock] = client
        self.safe_send(sock, {"type": "registered", "name": name, "avatar": avatar})
        self.broadcast(
            {
                "type": "user_join",
                "user": {"name": name, "avatar": avatar},
                "message": f"{avatar} {name} 加入了聊天室",
                "timestamp": timestamp(),
            }
        )
        self.broadcast_users()
        return client

    def handle_message(self, sender: Client, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "delete":
            self.broadcast(
                {
                    "type": "delete",
                    "sender": sender.name,
                    "avatar": sender.avatar,
                    "timestamp": timestamp(),
                }
            )
            return
        if message_type != "chat":
            self.safe_send(sender.sock, {"type": "error", "message": "不支持的消息类型"})
            return

        kind = message.get("content_type", "text")
        content = message.get("content", "")
        if kind not in {"text", "emoji", "image"} or not isinstance(content, str):
            self.safe_send(sender.sock, {"type": "error", "message": "消息内容不合法"})
            return
        if kind != "image" and (not content.strip() or len(content) > MAX_TEXT):
            self.safe_send(sender.sock, {"type": "error", "message": "文本消息不合法"})
            return

        payload: dict[str, Any] = {
            "type": "chat",
            "sender": sender.name,
            "avatar": sender.avatar,
            "content": content,
            "content_type": kind,
            "filename": str(message.get("filename", "")),
            "timestamp": timestamp(),
        }

        if kind == "image":
            if len(content) > MAX_IMAGE_B64:
                self.safe_send(sender.sock, {"type": "error", "message": "图片过大"})
                return
            try:
                data = base64.b64decode(content, validate=True)
            except (binascii.Error, ValueError):
                self.safe_send(sender.sock, {"type": "error", "message": "图片编码无效"})
                return
            if len(data) > MAX_IMAGE_BYTES:
                self.safe_send(sender.sock, {"type": "error", "message": "图片解码后超过 4MB"})
                return

        self.broadcast(payload)

    def broadcast_users(self) -> None:
        with self.lock:
            users = [{"name": client.name, "avatar": client.avatar} for client in self.clients.values()]
        self.broadcast({"type": "user_list", "users": users, "timestamp": timestamp()})

    def broadcast(self, payload: dict[str, Any]) -> None:
        with self.lock:
            targets = list(self.clients)
        for sock in targets:
            if not self.safe_send(sock, payload):
                self.remove(sock)

    @staticmethod
    def safe_send(sock: socket.socket, payload: dict[str, Any]) -> bool:
        try:
            send_json(sock, payload)
            return True
        except (OSError, ConnectionError):
            return False

    def remove(self, sock: socket.socket) -> None:
        with self.lock:
            client = self.clients.pop(sock, None)
        try:
            sock.close()
        except OSError:
            pass
        if client:
            self.broadcast(
                {
                    "type": "user_leave",
                    "user": {"name": client.name, "avatar": client.avatar},
                    "message": f"{client.avatar} {client.name} 离开了聊天室",
                    "timestamp": timestamp(),
                }
            )
            self.broadcast_users()

    def stop(self) -> None:
        self.stopping.set()
        if self.listener:
            self.listener.close()
        with self.lock:
            sockets = list(self.clients)
        for sock in sockets:
            self.remove(sock)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    server = ChatServer(args.host, args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
