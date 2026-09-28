"""头像资源：标识约定、路径解析与 QPixmap 加载。

约定：头像图片放在项目根目录 picture/ 下，文件名为
avatar_01.png ~ avatar_10.png。协议中的头像字段使用标识
字符串（如 "avatar_03"），客户端据此加载对应图片。

路径兼容两种运行方式：
- 源码运行：资源根目录为项目根目录（本文件的上级目录）。
- PyInstaller 打包：资源根目录为解包目录 sys._MEIPASS，
  打包时需用 --add-data 把 picture/ 目录带入。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap

AVATAR_COUNT = 10
AVATAR_IDS = [f"avatar_{index:02d}" for index in range(1, AVATAR_COUNT + 1)]
DEFAULT_AVATAR_ID = AVATAR_IDS[0]

_pixmap_cache: dict[tuple[str, int], QPixmap] = {}
_placeholder_cache: dict[int, QPixmap] = {}


def resource_root() -> Path:
    """资源根目录：打包后取 sys._MEIPASS，源码运行取项目根目录。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


def picture_dir() -> Path:
    """picture/ 目录位置。"""
    return resource_root() / "picture"


def is_avatar_id(value: str) -> bool:
    """判断字符串是否为约定的头像标识。"""
    return value in AVATAR_IDS


def avatar_file(avatar_id: str) -> Path | None:
    """返回头像文件路径；标识非法或文件不存在时返回 None。"""
    if not is_avatar_id(avatar_id):
        return None
    path = picture_dir() / f"{avatar_id}.png"
    return path if path.is_file() else None


def avatar_pixmap(avatar_id: str, size: int) -> QPixmap | None:
    """加载圆角头像；文件缺失或读取失败时返回 None。

    返回 None 时由调用方决定降级方案（例如使用 placeholder_pixmap）。
    """
    key = (avatar_id, size)
    cached = _pixmap_cache.get(key)
    if cached is not None:
        return cached
    path = avatar_file(avatar_id)
    if path is None:
        return None
    source = QPixmap(str(path))
    if source.isNull():
        return None
    pixmap = rounded_pixmap(source, size)
    _pixmap_cache[key] = pixmap
    return pixmap


def placeholder_pixmap(size: int) -> QPixmap:
    """默认占位头像：浅灰蓝底 + 白色人形剪影（带缓存，永不失败）。"""
    cached = _placeholder_cache.get(size)
    if cached is not None:
        return cached
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    radius = size * 0.24
    path.addRoundedRect(0.0, 0.0, float(size), float(size), radius, radius)
    painter.setClipPath(path)
    painter.fillPath(path, QColor("#C7D5E3"))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#FFFFFF"))
    center_x = size / 2.0
    # 头部
    painter.drawEllipse(QPointF(center_x, size * 0.40), size * 0.16, size * 0.16)
    # 肩部（超出圆角范围的部分被裁剪掉）
    painter.drawEllipse(QPointF(center_x, size * 1.04), size * 0.30, size * 0.30)
    painter.end()
    _placeholder_cache[size] = pixmap
    return pixmap


def rounded_pixmap(source: QPixmap, size: int) -> QPixmap:
    """把任意图片缩放为正方形、居中裁剪并裁成圆角。"""
    scaled = source.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    offset_x = (scaled.width() - size) // 2
    offset_y = (scaled.height() - size) // 2
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    radius = size * 0.24
    path.addRoundedRect(0.0, 0.0, float(size), float(size), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(-offset_x, -offset_y, scaled)
    painter.end()
    return pixmap
