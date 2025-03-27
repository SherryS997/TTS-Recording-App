# main.py
import sys
import os
from PyQt5.QtCore import QSettings # ADD
from PyQt5.QtWidgets import QApplication

def main():
    # --- ASIO Setting Handling ---
    # Must be done BEFORE importing sounddevice (which happens in AudioRecorder -> MainWindow)
    settings = QSettings("AudioRecorder", "RecordingApp")
    enable_asio = settings.value("audio/enable_asio", False, bool)

    if sys.platform == 'win32' and enable_asio:
        print("Attempting to enable ASIO...")
        os.environ["SD_ENABLE_ASIO"] = "1"
    else:
        # Ensure it's not set if disabled or not on Windows
        if "SD_ENABLE_ASIO" in os.environ:
            del os.environ["SD_ENABLE_ASIO"]
    # --- End ASIO ---

    # Now import MainWindow, which will trigger downstream sounddevice imports
    from ui.main_window import MainWindow

    # Set up application
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()