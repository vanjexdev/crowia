import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from giselo.app.window import MainWindow

_ICON = os.path.join(os.path.dirname(__file__), "assets", "icon.png")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Giselo")
    app.setOrganizationName("vanjexdev")
    if os.path.exists(_ICON):
        app.setWindowIcon(QIcon(_ICON))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
