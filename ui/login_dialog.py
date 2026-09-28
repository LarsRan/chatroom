"""QQ 风格的登录/注册对话框：昵称、头像选择与服务器地址。

样式表选择写在代码里（LOGIN_QSS 常量）而不是独立的 .qss 文件，理由：
1. 与项目现有 ui/theme.py「QSS 集中在 Python 常量」的做法保持一致；
2. 登录窗口与聊天窗口样式互不影响，便于单独调整和整体替换；
3. 省去运行时读取 qss 文件的路径兼容问题（打包后同样无需处理）。
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.avatars import (
    AVATAR_IDS,
    DEFAULT_AVATAR_ID,
    avatar_pixmap,
    picture_dir,
    placeholder_pixmap,
    rounded_pixmap,
)

LOGIN_QSS = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif;
}

#loginRoot {
    background: #F7FAFD;
    border: 1px solid #DCE4EE;
    border-radius: 12px;
}

#loginTitle {
    color: #5F7188;
    font-size: 10pt;
    font-weight: bold;
}

#closeButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    color: #93A1B3;
    font-size: 12pt;
    padding: 2px 10px;
}

#closeButton:hover {
    background: #F25555;
    color: #FFFFFF;
}

#logoTitle {
    color: #22384F;
    font-size: 15pt;
    font-weight: bold;
}

#logoSubtitle {
    color: #8496AA;
    font-size: 9pt;
}

QLineEdit {
    background: #FFFFFF;
    border: 1px solid #D3DDE8;
    border-radius: 6px;
    color: #26384C;
    min-height: 34px;
    padding: 0 12px;
}

QLineEdit:focus {
    border: 1px solid #12B7F5;
}

#sectionLabel {
    color: #6D7F93;
    font-size: 9pt;
}

#errorMessage {
    color: #E34D4D;
    font-size: 8pt;
    min-height: 16px;
}

AvatarButton {
    background: #FFFFFF;
    border: 2px solid #E2E9F1;
    border-radius: 10px;
}

AvatarButton:hover {
    border-color: #86D3FF;
}

AvatarButton:checked {
    background: #E9F7FF;
    border-color: #12B7F5;
}

#joinButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #33B9FF, stop:1 #0F8CEF);
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 11pt;
    font-weight: bold;
    min-height: 40px;
}

#joinButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4CC4FF, stop:1 #1B99F5);
}

#joinButton:pressed {
    background: #0C7CD9;
    padding-top: 2px;
}

#footerHint {
    color: #9AAABB;
    font-size: 8pt;
}
"""


class AvatarButton(QPushButton):
    """头像选择按钮：可选中，选中态由 QSS :checked 高亮显示。"""

    def __init__(self, avatar_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.avatar_id = avatar_id
        self.setCheckable(True)
        self.setFixedSize(54, 54)
        self.setIconSize(QSize(44, 44))
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(avatar_id)
        pixmap = avatar_pixmap(avatar_id, 44)
        if pixmap is None:
            # picture/avatar_XX.png 缺失时显示占位头像，保证界面不崩溃
            pixmap = placeholder_pixmap(44)
        self.setIcon(QIcon(pixmap))


class LoginDialog(QDialog):
    """首次进入聊天室的注册/登录对话框（无边框、可拖动、圆角卡片）。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("进入聊天室")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 560)

        self.selected_avatar = DEFAULT_AVATAR_ID
        self._drag_offset = None
        self._centered = False

        self.setStyleSheet(LOGIN_QSS)
        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        root = QWidget(self)
        root.setObjectName("loginRoot")
        outer.addWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(28, 0, 28, 20)
        page.setSpacing(10)

        # 自定义标题栏：空白处可拖动窗口，右侧关闭按钮
        title_bar = QWidget(root)
        title_bar.setFixedHeight(34)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 6, 0, 0)
        title_label = QLabel("聊天室", title_bar)
        title_label.setObjectName("loginTitle")
        close_button = QPushButton("✕", title_bar)
        close_button.setObjectName("closeButton")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setFixedSize(28, 24)
        close_button.clicked.connect(self.reject)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(close_button)
        page.addWidget(title_bar)

        # 顶部 logo / 标题区域（后续可直接放入 picture/logo.png）
        logo_label = QLabel(root)
        logo_label.setFixedSize(68, 68)
        logo_label.setPixmap(self._logo_pixmap(68))
        logo_row = QHBoxLayout()
        logo_row.addStretch(1)
        logo_row.addWidget(logo_label)
        logo_row.addStretch(1)
        page.addLayout(logo_row)

        title = QLabel("局域网聊天室", root)
        title.setObjectName("logoTitle")
        title.setAlignment(Qt.AlignCenter)
        page.addWidget(title)

        subtitle = QLabel("选一张头像，取个昵称，马上开始", root)
        subtitle.setObjectName("logoSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        page.addWidget(subtitle)

        # 输入区
        self.name_input = QLineEdit(root)
        self.name_input.setPlaceholderText("昵称（1-32 个字符）")
        self.name_input.setMaxLength(32)
        page.addWidget(self.name_input)

        server_row = QHBoxLayout()
        server_row.setSpacing(8)
        self.host_input = QLineEdit(root)
        self.host_input.setPlaceholderText("服务器 IP，如 192.168.1.20")
        self.host_input.setText("127.0.0.1")
        self.port_input = QLineEdit(root)
        self.port_input.setPlaceholderText("端口")
        self.port_input.setText("8765")
        self.port_input.setFixedWidth(96)
        server_row.addWidget(self.host_input, 1)
        server_row.addWidget(self.port_input)
        page.addLayout(server_row)

        # 头像选择区：5 列 x 2 行，单选，选中项蓝色描边高亮
        section = QLabel("选择一个喜欢的头像", root)
        section.setObjectName("sectionLabel")
        page.addWidget(section)

        self._avatar_group = QButtonGroup(self)
        self._avatar_group.setExclusive(True)
        grid_holder = QWidget(root)
        grid = QGridLayout(grid_holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        columns = 5
        for index, avatar_id in enumerate(AVATAR_IDS):
            button = AvatarButton(avatar_id, grid_holder)
            button.clicked.connect(lambda checked=False, value=avatar_id: self._select_avatar(value))
            self._avatar_group.addButton(button)
            grid.addWidget(button, index // columns, index % columns)
            if avatar_id == DEFAULT_AVATAR_ID:
                button.setChecked(True)
        page.addWidget(grid_holder, 0, Qt.AlignHCenter)

        # 错误提示与提交按钮
        self.error_label = QLabel(root)
        self.error_label.setObjectName("errorMessage")
        self.error_label.setAlignment(Qt.AlignCenter)
        page.addWidget(self.error_label)

        self.join_button = QPushButton("进入聊天室", root)
        self.join_button.setObjectName("joinButton")
        self.join_button.setCursor(Qt.PointingHandCursor)
        self.join_button.setDefault(True)
        self.join_button.clicked.connect(self._submit)
        page.addWidget(self.join_button)

        hint = QLabel("同一局域网的小伙伴填同一个服务器 IP 就能一起聊", root)
        hint.setObjectName("footerHint")
        hint.setAlignment(Qt.AlignCenter)
        page.addWidget(hint)

        page.addStretch(1)
        self.name_input.setFocus()

    # ------------------------------------------------------------------ 事件

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._centered:
            return
        self._centered = True
        screen = self.screen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(
                area.center().x() - self.width() // 2,
                area.center().y() - self.height() // 2,
            )

    # ------------------------------------------------------------------ 逻辑

    def _select_avatar(self, avatar_id: str) -> None:
        self.selected_avatar = avatar_id

    def _submit(self) -> None:
        name = self.name_input.text().strip()
        if not 1 <= len(name) <= 32:
            self._show_error("昵称长度必须在 1-32 个字符之间")
            return
        if not self.host_input.text().strip():
            self._show_error("服务器 IP 不能为空")
            return
        port_text = self.port_input.text().strip()
        if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            self._show_error("端口必须是 1-65535 的数字")
            return
        self.error_label.clear()
        self.accept()

    def _show_error(self, text: str) -> None:
        self.error_label.setText(text)

    def user_info(self) -> tuple[str, str, str, int]:
        """返回 (昵称, 头像标识, 服务器 IP, 端口)。"""
        return (
            self.name_input.text().strip(),
            self.selected_avatar,
            self.host_input.text().strip(),
            int(self.port_input.text().strip()),
        )

    @staticmethod
    def _logo_pixmap(size: int) -> QPixmap:
        """优先加载 picture/logo.png；不存在时绘制内置占位 logo。"""
        path = picture_dir() / "logo.png"
        if path.is_file():
            source = QPixmap(str(path))
            if not source.isNull():
                return rounded_pixmap(source, size)
        # 占位 logo：蓝色渐变圆形 + 「聊」字
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0.0, 0.0, 0.0, float(size))
        gradient.setColorAt(0.0, QColor("#3FBCFF"))
        gradient.setColorAt(1.0, QColor("#0E8CEF"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(0, 0, size, size)
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(int(size * 0.42))
        painter.setFont(font)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, "聊")
        painter.end()
        return pixmap
