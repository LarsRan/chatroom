"""Emoji catalog and picker dialog for the chat UI."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

EMOJIS = {
    "常用": ["😀", "😂", "😍", "😭", "😡", "👍", "🎉", "😎", "🤔", "😱"],
    "动物": ["🐶", "🐱", "🐼", "🐯", "🦊"],
    "食物": ["🍎", "🍕", "🍔", "🍜", "🍰", "☕"],
}


def all_emojis() -> list[str]:
    """Return a flattened emoji list used by compatibility checks."""
    return [item for group in EMOJIS.values() for item in group]


class EmojiPicker(QDialog):
    """Emoji picker dialog with grouped grid buttons."""

    emoji_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择表情")
        self.setModal(True)
        self.resize(360, 280)

        root = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        content = QWidget(scroll)
        content_layout = QVBoxLayout(content)

        for title, emojis in EMOJIS.items():
            box = QGroupBox(title, content)
            grid = QGridLayout(box)
            for index, emoji in enumerate(emojis):
                button = QPushButton(emoji, box)
                button.setFixedSize(44, 36)
                button.clicked.connect(lambda _, value=emoji: self._select(value))
                grid.addWidget(button, index // 6, index % 6)
            content_layout.addWidget(box)

        content_layout.addStretch(1)
        scroll.setWidget(content)

    def _select(self, emoji: str) -> None:
        self.emoji_selected.emit(emoji)
        self.accept()
