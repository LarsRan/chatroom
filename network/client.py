"""Background-thread TCP client for the PySide6 UI."""
from __future__ import annotations

import json
import socket
import threading
from typing import Any, Callable

MAX_LINE = 8 * 1024 * 1024


class ChatClient:
    def __init__(
        self,
        on_message: Callable[[dict[str, Any]], None],
        on_disconnect: Callable[[str], None] | None = None,
    ):
        self.on_message = on_message
        self.on_disconnect = on_disconnect or (lambda _: None)
        self.sock: socket.socket | None = None
        self.running = threading.Event()
        self.send_lock = threading.Lock()

    def connect(self, host: str, port: int, name: str, avatar: str = "😀") -> None:
        self.close()
        self.sock = socket.create_connection((host, port), timeout=8)
        self.sock.settimeout(None)
        self.running.set()
        threading.Thread(target=self._receive, daemon=True).start()
        self.send({"type": "register", "name": name, "avatar": avatar})

    def send(self, payload: dict[str, Any]) -> None:
        data = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self.send_lock:
            if not self.sock or not self.running.is_set():
                raise ConnectionError("未连接服务器")
            self.sock.sendall(data)

    def send_chat(self, content: str, content_type: str = "text", filename: str = "") -> None:
        self.send(
            {
                "type": "chat",
                "content": content,
                "content_type": content_type,
                "filename": filename,
            }
        )

    def send_emoji(self, emoji: str) -> None:
        self.send_chat(emoji, "emoji")

    def send_image(self, image_b64: str, filename: str) -> None:
        self.send_chat(image_b64, "image", filename)

    def send_delete(self) -> None:
        self.send({"type": "delete"})

    def _receive(self) -> None:
        buffer = b""
        reason = "连接已断开"
        try:
            while self.running.is_set() and self.sock:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > MAX_LINE:
                    self.on_message({"type": "error", "message": "收到超长消息"})
                    break
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    if not raw.strip():
                        continue
                    try:
                        value = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        self.on_message({"type": "error", "message": "收到无效消息"})
                        continue
                    if isinstance(value, dict):
                        self.on_message(value)
        except (OSError, ConnectionError) as exc:
            reason = str(exc) or reason
        finally:
            self.running.clear()
            self.on_disconnect(reason)

    def close(self) -> None:
        self.running.clear()
        with self.send_lock:
            sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
