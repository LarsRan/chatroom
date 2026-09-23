# 局域网聊天室

Python 3.10+ / TCP socket / newline-delimited JSON / threading / PySide6 / SQLite。

## 安装与运行

```bash
python -m pip install -r requirements.txt
python network/server.py --host 0.0.0.0 --port 8765
python main.py
```

客户端输入服务器所在电脑的局域网 IP。防火墙需放行 TCP 8765；可同时启动多个客户端。服务器负责注册、昵称去重、广播聊天消息和在线用户列表。客户端网络接收运行在后台线程，并通过 Qt signal 更新界面。图片使用 base64 传输，限制 4 MB，接收后保存到 `~/.chatroom/images`。聊天历史按昵称保存到 `~/.chatroom/*.sqlite3`。

## 目录

`main.py`：客户端入口；`network/server.py`：多线程服务器；`network/client.py`：JSON TCP 客户端；`ui/chat_window.py`：PySide6 UI；`db/chat_db.py`：SQLite 历史；`utils/emoji.py`：emoji 数据。

## 检查

```bash
python -m compileall main.py network db ui utils
```
