import sys
from PyQt5.QtWidgets import QApplication
from controllers.library_controller import LibraryController

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = LibraryController()
    controller.show()
    sys.exit(app.exec_())