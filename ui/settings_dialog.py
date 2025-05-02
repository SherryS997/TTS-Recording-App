from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox,
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
        self.buffer_size_combo.addItems(["4", "8", "16", "32", "64", "128", "256", "512", "1024", "2048", "4096"])
        audio_layout.addRow("Buffer Size:", self.buffer_size_combo)
        
        self.trim_threshold_db_spin = QDoubleSpinBox()
        self.trim_threshold_db_spin.setRange(-70.0, -10.0) # Example dB range
        self.trim_threshold_db_spin.setSuffix(" dB")
        self.trim_threshold_db_spin.setDecimals(1)
        self.trim_threshold_db_spin.setSingleStep(1.0)
        audio_layout.addRow("Trim Threshold (dB):", self.trim_threshold_db_spin) # Update label

        self.padding_ms_spin = QSpinBox() # Add padding setting if not already there
        self.padding_ms_spin.setRange(0, 1000)
        self.padding_ms_spin.setSuffix(" ms")
        self.padding_ms_spin.setSingleStep(50)
        audio_layout.addRow("Trim Padding:", self.padding_ms_spin)

        self.auto_trim_check = QCheckBox("Auto-trim recordings")
        audio_layout.addRow("", self.auto_trim_check)

        self.enable_asio_check = QCheckBox("Enable ASIO (Requires Restart)")
        self.enable_asio_check.setToolTip(
            "Check this to enable ASIO audio devices on Windows.\n"
            "The application must be restarted for this change to take effect."
        )
        audio_layout.addRow("", self.enable_asio_check)
        
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
        self.file_format_combo.addItems(["WAV", "FLAC"])
        storage_layout.addRow("File Format:", self.file_format_combo)
        
        # Add auto-upload checkbox
        self.auto_upload_check = QCheckBox("Automatically upload recordings after saving")
        self.auto_upload_check.setToolTip("When enabled, recordings will be automatically uploaded to the server after being saved")
        storage_layout.addRow("", self.auto_upload_check)

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
        trim_threshold_db = settings.value("audio/trim_threshold_db", -40.0, float)
        padding_ms = settings.value("audio/padding_ms", 100, int)
        auto_trim = settings.value("audio/auto_trim", True, bool)
        
        # Find and select the right combo box index
        bit_depth_index = self.bit_depth_combo.findText(bit_depth)
        if bit_depth_index >= 0:
            self.bit_depth_combo.setCurrentIndex(bit_depth_index)
            
        buffer_size_index = self.buffer_size_combo.findText(buffer_size)
        if buffer_size_index >= 0:
            self.buffer_size_combo.setCurrentIndex(buffer_size_index)
        
        self.trim_threshold_db_spin.setValue(trim_threshold_db)
        self.padding_ms_spin.setValue(padding_ms)
        self.auto_trim_check.setChecked(auto_trim)

        # Load ASIO setting
        enable_asio = settings.value("audio/enable_asio", False, bool)
        self.enable_asio_check.setChecked(enable_asio)

        # Storage settings
        storage_dir = settings.value("storage/directory", "data")
        file_format = settings.value("storage/file_format", "WAV")
        auto_upload = settings.value("storage/auto_upload", False, bool)
        
        self.storage_dir_edit.setText(storage_dir)
        self.auto_upload_check.setChecked(auto_upload)

        format_index = self.file_format_combo.findText(file_format)
        if format_index >= 0:
            self.file_format_combo.setCurrentIndex(format_index)
    
    def save_settings(self):
        """Save settings to QSettings."""
        settings = QSettings()

        # Check if ASIO setting changed
        old_asio_setting = settings.value("audio/enable_asio", False, bool)
        new_asio_setting = self.enable_asio_check.isChecked()
        if old_asio_setting != new_asio_setting:
            self._asio_changed = True # Flag that restart is needed
        else:
            self._asio_changed = False
        
        # Audio settings
        settings.setValue("audio/bit_depth", self.bit_depth_combo.currentText())
        settings.setValue("audio/buffer_size", self.buffer_size_combo.currentText())
        settings.setValue("audio/trim_threshold_db", self.trim_threshold_db_spin.value())
        settings.setValue("audio/padding_ms", self.padding_ms_spin.value())
        settings.setValue("audio/auto_trim", self.auto_trim_check.isChecked())
        settings.setValue("audio/enable_asio", new_asio_setting)
        
        # Storage settings
        settings.setValue("storage/directory", self.storage_dir_edit.text())
        settings.setValue("storage/file_format", self.file_format_combo.currentText())
        settings.setValue("storage/auto_upload", self.auto_upload_check.isChecked())
            
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
        """Save settings and inform user if restart is needed."""
        self.save_settings()
        if self._asio_changed:
            QMessageBox.information(
                self,
                "Restart Required",
                "Changing the ASIO setting requires restarting the application for it to take effect."
            )
        super().accept()
    
    def get_settings(self):
        """Return the current settings as a QSettings object for immediate use."""
        # Ensure QSettings is up-to-date and use the same QSettings constructor
        self.save_settings() 
        return QSettings()  # Use default constructor to match what's used elsewhere