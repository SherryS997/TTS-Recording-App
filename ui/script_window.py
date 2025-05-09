# ui/script_window.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QSizePolicy, QLabel, QSpinBox, QFontComboBox) # Added QLabel, QSpinBox, QFontComboBox
from PyQt5.QtCore import Qt, pyqtSignal, QSettings # Added QSettings
from PyQt5.QtGui import QFont

from .traffic_light_indicator import TrafficLightIndicator

class ScriptWindow(QWidget):
    window_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Script View")
        self.setMinimumSize(400, 350) # Increased min height for font controls

        self._setup_ui()
        self._load_settings() # Load font settings on init

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top row for Indicator and Font Controls
        top_controls_layout = QHBoxLayout()

        self.indicator = TrafficLightIndicator(self)
        top_controls_layout.addWidget(self.indicator, 0, Qt.AlignLeft) # Align left

        top_controls_layout.addStretch(1) # Push font controls to the right

        # Font controls for ScriptWindow
        font_label = QLabel("Font:")
        top_controls_layout.addWidget(font_label)

        self.font_family_combo = QFontComboBox(self)
        self.font_family_combo.setToolTip("Select font family for this script window")
        self.font_family_combo.currentFontChanged.connect(self._apply_font_settings)
        top_controls_layout.addWidget(self.font_family_combo)

        self.font_size_spinbox = QSpinBox(self)
        self.font_size_spinbox.setRange(8, 72)
        self.font_size_spinbox.setToolTip("Select font size for this script window")
        self.font_size_spinbox.setSuffix(" pt")
        self.font_size_spinbox.valueChanged.connect(self._apply_font_settings)
        top_controls_layout.addWidget(self.font_size_spinbox)
        
        main_layout.addLayout(top_controls_layout)

        self.script_text_edit = QTextEdit(self)
        self.script_text_edit.setReadOnly(True)
        self.script_text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Default alignment (can be changed by MainWindow if needed)
        self.script_text_edit.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(self.script_text_edit)
        self.setLayout(main_layout)

    def _load_settings(self):
        settings = QSettings()
        default_font_family = QFont().family() # System default
        
        # Use distinct keys for ScriptWindow settings
        font_family = settings.value("script_window/font_family", default_font_family)
        font_size = settings.value("script_window/font_size", 16, type=int)

        self.font_family_combo.blockSignals(True)
        self.font_size_spinbox.blockSignals(True)

        # Find font in combo box or set directly
        current_font_obj = QFont(font_family, font_size)
        self.font_family_combo.setCurrentFont(current_font_obj) # This sets both family and tries to match size
        self.font_size_spinbox.setValue(font_size) # Ensure spinbox reflects loaded size

        self.font_family_combo.blockSignals(False)
        self.font_size_spinbox.blockSignals(False)
        
        self._apply_font_settings() # Apply loaded settings

    def _save_settings(self):
        settings = QSettings()
        settings.setValue("script_window/font_family", self.font_family_combo.currentFont().family())
        settings.setValue("script_window/font_size", self.font_size_spinbox.value())

    def _apply_font_settings(self):
        """Applies the font family and size from the local controls."""
        font = self.font_family_combo.currentFont()
        font.setPointSize(self.font_size_spinbox.value())
        self.script_text_edit.setFont(font)
        # Alignment is not directly controlled by these local controls in this setup,
        # but could be added if desired. For now, MainWindow can set it.

    def update_script(self, text):
        self.script_text_edit.setPlainText(text)

    def update_indicator_state(self, state):
        self.indicator.setState(state)

    def set_script_alignment(self, alignment):
        """
        Allows MainWindow to set the text alignment if it's a shared property.
        Font family and size are now locally controlled.
        """
        self.script_text_edit.setAlignment(alignment)

    # This method is effectively replaced by local controls + _apply_font_settings
    # def set_script_font_properties(self, font=None, point_size=None, alignment=None):
    #     pass # Kept for reference, but local controls are primary now

    def closeEvent(self, event):
        self._save_settings() # Save settings when window is closed
        self.window_closed.emit()
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QPushButton
    
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background-color: #2E2E2E; color: #E0E0E0; } /* Basic dark theme */ ")
    
    main_test_window = QWidget()
    controller_layout = QVBoxLayout(main_test_window)
    
    script_view_window = ScriptWindow()

    def toggle_script_window_visibility():
        if script_view_window.isVisible():
            script_view_window.hide()
        else:
            script_view_window.show()
            script_view_window.update_script("Test script in the side window.\nChange font using local controls.")
            script_view_window.update_indicator_state("green")
            # Example: MainWindow might still set alignment
            script_view_window.set_script_alignment(Qt.AlignLeft)


    btn_toggle = QPushButton("Toggle Script Window")
    btn_toggle.clicked.connect(toggle_script_window_visibility)
    
    controller_layout.addWidget(btn_toggle)
    
    main_test_window.setWindowTitle("Script Window Controller Test")
    main_test_window.show()
    
    sys.exit(app.exec_())