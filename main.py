# main.py
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
from ui.main_window import MainWindow

def main():
    # Set up application
    app = QApplication(sys.argv)
    app.setOrganizationName("AudioRecorder")
    app.setApplicationName("PyQt Audio Recorder")
    
    # Create and show the main window
    main_window = MainWindow()
    main_window.show()
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()