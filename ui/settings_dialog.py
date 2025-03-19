# ui/settings_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                            QPushButton, QLabel, QComboBox, QSpinBox, 
                            QLineEdit, QFileDialog, QGroupBox, QCheckBox)
from PyQt5.QtCore import Qt, QSettings

class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 300)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Audio settings group
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout(audio_group)
        
        self.bit_depth_combo = QComboBox()
        self.bit_depth_combo.addItems(["16-bit", "24-bit", "32-bit float"])
        audio_layout.addRow("Bit Depth:", self.bit_depth_combo)
        
        self.buffer_size_combo = QComboBox()
        self.buffer_size_combo.addItems(["256", "512", "1024", "2048", "4096"])
        audio_layout.addRow("Buffer Size:", self.buffer_size_combo)
        
        self.trim_threshold_spin = QSpinBox()
        self.trim_threshold_spin.setRange(1, 50)
        self.trim_threshold_spin.setSuffix(" %")
        audio_layout.addRow("Trim Threshold:", self.trim_threshold_spin)
        
        self.auto_trim_check = QCheckBox("Auto-trim recordings")
        audio_layout.addRow("", self.auto_trim_check)
        
        main_layout.addWidget(audio_group)
        
        # Storage settings group
        storage_group = QGroupBox("Storage Settings")
        storage_layout = QFormLayout(storage_group)
        
        storage_dir_layout = QHBoxLayout()
        self.storage_dir_edit = QLineEdit()
        storage_dir_layout.addWidget(self.storage_dir_edit)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_directory)
        storage_dir_layout.addWidget(self.browse_btn)
        
        storage_layout.addRow("Storage Directory:", storage_dir_layout)
        
        self.file_format_combo = QComboBox()
        self.file_format_combo.addItems(["WAV", "FLAC", "MP3"])
        storage_layout.addRow("File Format:", self.file_format_combo)
        
        main_layout.addWidget(storage_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load settings from QSettings."""
        settings = QSettings()
        
        # Audio settings
        bit_depth = settings.value("audio/bit_depth", "16-bit")
        buffer_size = settings.value("audio/buffer_size", "1024")
        trim_threshold = settings.value("audio/trim_threshold", 2, int)
        auto_trim = settings.value("audio/auto_trim", True, bool)
        
        # Find and select the right combo box index
        bit_depth_index = self.bit_depth_combo.findText(bit_depth)
        if bit_depth_index >= 0:
            self.bit_depth_combo.setCurrentIndex(bit_depth_index)
            
        buffer_size_index = self.buffer_size_combo.findText(buffer_size)
        if buffer_size_index >= 0:
            self.buffer_size_combo.setCurrentIndex(buffer_size_index)
        
        self.trim_threshold_spin.setValue(trim_threshold)
        self.auto_trim_check.setChecked(auto_trim)
        
        # Storage settings
        storage_dir = settings.value("storage/directory", "data")
        file_format = settings.value("storage/file_format", "WAV")
        
        self.storage_dir_edit.setText(storage_dir)
        
        format_index = self.file_format_combo.findText(file_format)
        if format_index >= 0:
            self.file_format_combo.setCurrentIndex(format_index)
    
    def save_settings(self):
        """Save settings to QSettings."""
        settings = QSettings()
        
        # Audio settings
        settings.setValue("audio/bit_depth", self.bit_depth_combo.currentText())
        settings.setValue("audio/buffer_size", self.buffer_size_combo.currentText())
        settings.setValue("audio/trim_threshold", self.trim_threshold_spin.value())
        settings.setValue("audio/auto_trim", self.auto_trim_check.isChecked())
        
        # Storage settings
        settings.setValue("storage/directory", self.storage_dir_edit.text())
        settings.setValue("storage/file_format", self.file_format_combo.currentText())
    
    def browse_directory(self):
        """Open file dialog to select storage directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Storage Directory",
            self.storage_dir_edit.text()
        )
        
        if directory:
            self.storage_dir_edit.setText(directory)
    
    def accept(self):
        """Save settings when OK button is clicked."""
        self.save_settings()
        super().accept()

    def get_settings(self):
        """Return the current settings as a QSettings object."""
        settings = QSettings()
        
        # Audio settings
        settings.setValue("audio/bit_depth", self.bit_depth_combo.currentText())
        settings.setValue("audio/buffer_size", self.buffer_size_combo.currentText())
        settings.setValue("audio/trim_threshold", self.trim_threshold_spin.value())
        settings.setValue("audio/auto_trim", self.auto_trim_check.isChecked())
        
        # Storage settings
        settings.setValue("storage/directory", self.storage_dir_edit.text())
        settings.setValue("storage/file_format", self.file_format_combo.currentText())
        
        return settings

