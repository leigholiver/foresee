import sys

from PyQt5.QtWidgets import QApplication

from Worker import Worker
from MainWindow import MainWindow

if __name__ == "__main__":

    # Initialize the QApplication
    app = QApplication(sys.argv)

    # Start polling the SC2 API
    w = Worker()
    w.start()

    # Start the application
    mw = MainWindow(w)
    sys.exit(app.exec_())
