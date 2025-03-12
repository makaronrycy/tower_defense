from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtCore import Slot


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tower Defense")
        self.setGeometry(100, 100, 800, 600)

        self.start_button = QPushButton("Start Game", self)
        self.start_button.setGeometry(350, 250, 100, 50)
        self.start_button.clicked.connect(self.start_game)

    @Slot()
    def start_game(self):
        print("Game Started")

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
