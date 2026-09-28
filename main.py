"""Application entry point for the PySide6 chat client."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ui.chat_window import ChatWindow

if __name__ == "__main__":
    # 高 DPI 缩放策略必须在 QApplication 创建之前设置（Qt 6 默认已启用高 DPI）。
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    raise SystemExit(app.exec())
