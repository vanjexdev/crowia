import sys
from PyQt6.QtWidgets import QApplication
from giselo.app.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Giselo")
    app.setOrganizationName("vanjexdev")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
