"""Entry point for Neuro Localization app."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from src.frontend.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Inter", 13))
    app.setApplicationName("Neuro Localization")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
