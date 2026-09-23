"""Application entry point for the PySide6 chat client."""
import sys
from PySide6.QtWidgets import QApplication
from ui.chat_window import ChatWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    raise SystemExit(app.exec())
