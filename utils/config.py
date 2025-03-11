import os
import json
from PyQt5.QtCore import QSettings

class AppConfig:
    """
    Handles application configuration and settings management.
    Provides defaults and persistent storage of user preferences.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Audio recording settings
        "audio": {
            "channels": 1,
            "sample_rate_high": 48000,
            "sample_rate_low": 8000,
            "frames_per_buffer": 1024,
            "format": "int16",
            "default_device_index": 0,
            "use_asio": True,  # Windows-specific setting
        },
        
        # File paths and directories
        "paths": {
            "base_dir": "data",
            "auto_create_dirs": True,
        },
        
        # UI preferences
        "ui": {
            "dark_mode": False,
            "waveform_color": "#2980b9",
            "show_grid": True,
            "auto_trim": True,
            "trim_threshold": 0.03,  # Silence detection threshold
            "trim_padding_ms": 100,  # Padding around detected audio
        },
        
        # CSV data settings
        "data": {
            "id_column": "ID",
            "text_column": "Text",
            "auto_save": True,
            "auto_save_interval": 300,  # seconds
        }
    }
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.settings = QSettings("AudioRecorder", "PyQt Audio Recorder")
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """Load configuration from QSettings."""
        # Load from QSettings if available
        if self.settings.contains("config"):
            stored_config = json.loads(self.settings.value("config"))
            
            # Update our config with stored values, preserving the structure
            self._update_dict_recursive(self.config, stored_config)
        
        # Create base directory if it doesn't exist
        if self.config["paths"]["auto_create_dirs"]:
            os.makedirs(self.get_path("base_dir"), exist_ok=True)
    
    def save_config(self):
        """Save current configuration to QSettings."""
        self.settings.setValue("config", json.dumps(self.config))
        self.settings.sync()
    
    def get(self, section, key):
        """Get a configuration value."""
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return None
    
    def set(self, section, key, value):
        """Set a configuration value and save."""
        if section in self.config:
            self.config[section][key] = value
            self.save_config()
            return True
        return False
    
    def get_path(self, key):
        """Get a path from the paths section."""
        if key in self.config["paths"]:
            path = self.config["paths"][key]
            # Convert relative paths to absolute
            if not os.path.isabs(path):
                return os.path.abspath(path)
            return path
        return None
    
    def set_path(self, key, path):
        """Set a path in the paths section."""
        return self.set("paths", key, path)
    
    def get_audio_setting(self, key):
        """Get an audio setting."""
        return self.get("audio", key)
    
    def set_audio_setting(self, key, value):
        """Set an audio setting."""
        return self.set("audio", key, value)
    
    def get_ui_setting(self, key):
        """Get a UI setting."""
        return self.get("ui", key)
    
    def set_ui_setting(self, key, value):
        """Set a UI setting."""
        return self.set("ui", key, value)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    def _update_dict_recursive(self, target_dict, source_dict):
        """Update target_dict with values from source_dict recursively."""
        for key, value in source_dict.items():
            if key in target_dict:
                if isinstance(value, dict) and isinstance(target_dict[key], dict):
                    # Recursively update nested dictionaries
                    self._update_dict_recursive(target_dict[key], value)
                else:
                    # Direct update for non-dictionary values
                    target_dict[key] = value