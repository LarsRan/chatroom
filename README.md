# 局域网聊天室

Python 3.10+ / TCP socket / newline-delimited JSON / threading / PySide6 / SQLite。

## 功能列表

- 客户端启动先显示用户信息对话框，必须输入 1-32 字符昵称并选择头像。
- 服务端支持昵称注册与去重，并广播 `user_join` / `user_leave` / `user_list`。
- 协议使用“一行一个 UTF-8 JSON，结尾 `\n`”，支持粘包拆包与异常兜底。
- 支持文本、emoji、图片三类消息，图片以 base64 传输并限制解码后 4MB。
- 客户端接收图片后统一保存到 `~/.chatroom/images` 并在聊天区内嵌显示。
- 每个昵称独立 SQLite 历史记录，重启客户端可重载文本/emoji/图片消息。
- 点击“清空记录”会发送 `{"type":"delete"}`，服务端广播给所有客户端同步清空。

## 安装与运行

```bash
python -m pip install -r requirements.txt
```

### 启动服务端

```bash
python network/server.py --host 0.0.0.0 --port 8765
```

默认监听 `0.0.0.0:8765`，可通过参数修改。

### 启动客户端

```bash
python main.py
```

客户端启动后填写昵称、头像、服务器 IP 与端口。

## 防火墙与端口说明

- 局域网互联时，服务端所在机器需放行 TCP `8765`（或你自定义的端口）。
- 如无法连接，请确认两端在同一网段、端口未被占用且防火墙规则已生效。

## 目录说明

- `main.py`：客户端入口。
- `network/server.py`：多线程服务器，负责注册、广播、在线用户和 delete 转发。
- `network/client.py`：换行分隔 JSON 客户端，后台线程接收并提供发送便捷方法。
- `ui/chat_window.py`：PySide6 界面、用户注册对话框、消息渲染与本地图片落盘。
- `db/chat_db.py`：按昵称独立 SQLite 历史记录。
- `utils/emoji.py`：emoji 分组、扁平列表与 EmojiPicker。

## 快速检查

```bash
python -m compileall main.py network db ui utils
```
