# main.py
import sys
import os
from PyQt5.QtCore import QSettings, QCoreApplication
from PyQt5.QtWidgets import QApplication

# A basic dark theme stylesheet
# You can expand this or load it from a .qss file for more complex themes
DARK_THEME_STYLESHEET = """
    QWidget {
        background-color: #2E2E2E; /* Dark gray background */
        color: #E0E0E0; /* Light gray text */
        font-family: Segoe UI, Arial, sans-serif; /* Common clean font */
    }
    QMainWindow, QDialog {
        background-color: #2E2E2E;
    }
    QMenuBar {
        background-color: #3C3C3C; /* Slightly lighter for menu bar */
        color: #E0E0E0;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 4px 8px;
    }
    QMenuBar::item:selected {
        background-color: #5A5A5A; /* Highlight for selected menu item */
    }
    QMenu {
        background-color: #3C3C3C;
        border: 1px solid #5A5A5A; /* Border for dropdown menus */
    }
    QMenu::item {
        padding: 4px 20px 4px 20px;
    }
    QMenu::item:selected {
        background-color: #5A5A5A;
    }
    QPushButton {
        background-color: #4A4A4A; /* Button background */
        border: 1px solid #6A6A6A; /* Button border */
        padding: 6px 12px;
        min-width: 60px; /* Ensure buttons have some minimum width */
    }
    QPushButton:hover {
        background-color: #5A5A5A; /* Lighter on hover */
    }
    QPushButton:pressed {
        background-color: #6A6A6A; /* Even Lighter/different when pressed */
    }
    QPushButton:disabled {
        background-color: #404040;
        color: #808080;
    }
    QComboBox {
        background-color: #3C3C3C;
        border: 1px solid #5A5A5A;
        padding: 4px;
        min-height: 20px; /* Ensure combo box has some height */
    }
    QComboBox::drop-down {
        border: none; /* Remove default dropdown arrow border */
        background-color: #4A4A4A;
        width: 20px;
    }
    QComboBox QAbstractItemView { /* Dropdown list style */
        background-color: #3C3C3C;
        border: 1px solid #5A5A5A;
        selection-background-color: #5A5A5A;
    }
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
        background-color: #3C3C3C;
        border: 1px solid #5A5A5A;
        padding: 4px;
        selection-background-color: #5A5A5A; /* Background for selected text */
        selection-color: #E0E0E0; /* Color for selected text */
    }
    QTextEdit {
        font-size: 16px; /* Default for the main text area if not overridden */
    }
    QSlider::groove:horizontal {
        border: 1px solid #5A5A5A;
        background: #3C3C3C;
        height: 8px;
        border-radius: 4px;
    }
    QSlider::handle:horizontal {
        background: #8A8A8A; /* Handle color */
        border: 1px solid #5A5A5A;
        width: 16px;
        margin: -4px 0; /* Center the handle vertically */
        border-radius: 8px;
    }
    QProgressBar {
        border: 1px solid #5A5A5A;
        border-radius: 4px;
        text-align: center; /* Center the percentage text */
        background-color: #3C3C3C;
        color: #E0E0E0;
    }
    QProgressBar::chunk {
        background-color: #007ACC; /* A blue for progress, adjust as needed */
        width: 10px; /* Width of the progress segments */
        margin: 0.5px;
        border-radius: 3px;
    }
    QLabel {
        color: #E0E0E0;
    }
    QGroupBox {
        border: 1px solid #4A4A4A;
        margin-top: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left; /* position at the top left */
        padding: 0 5px 0 5px;
        background-color: #3C3C3C; /* Match groupbox border context */
    }
    QStatusBar {
        background-color: #3C3C3C;
    }
    QSplitter::handle {
        background-color: #4A4A4A; /* Color for splitter handles */
        border: 1px solid #5A5A5A;
    }
    QSplitter::handle:horizontal {
        width: 5px;
    }
    QSplitter::handle:vertical {
        height: 5px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }
    QCheckBox::indicator:unchecked {
        background-color: #3C3C3C;
        border: 1px solid #5A5A5A;
    }
    QCheckBox::indicator:checked {
        background-color: #007ACC; /* Blue checkmark */
        border: 1px solid #5A5A5A;
        image: url(none); /* Can use an actual checkmark image if preferred */
    }
    QToolTip {
        background-color: #4A4A4A;
        color: #E0E0E0;
        border: 1px solid #6A6A6A;
        padding: 4px;
    }
"""

def main():
    # Set up consistent QSettings application info first
    QCoreApplication.setOrganizationName("AudioRecorder")
    QCoreApplication.setApplicationName("RecordingApp")
    
    # --- ASIO Setting Handling ---
    # Must be done BEFORE importing sounddevice (which happens in AudioRecorder -> MainWindow)
    settings = QSettings()  # Use default QSettings() now that app info is set
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

    # Apply the dark theme stylesheet
    # You can also add a setting to enable/disable dark theme and apply conditionally
    app.setStyleSheet(DARK_THEME_STYLESHEET)
    
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()