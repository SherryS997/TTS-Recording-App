# ui/main_window.py
import os
import datetime
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QComboBox, QFileDialog, 
                            QTextEdit, QLineEdit, QMessageBox, QAction, 
                            QMenuBar, QMenu, QTabWidget, QSplitter, QProgressBar,
                            QDateEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSettings
from pydub import AudioSegment

from ui.waveform_widget import WaveformWidget
from ui.recording_panel import RecordingPanel
from ui.settings_dialog import SettingsDialog
from core.audio_recorder import AudioRecorder
from core.audio_player import AudioPlayer
from core.data_manager import DataManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.audio_recorder = AudioRecorder()
        self.audio_player = AudioPlayer()
        self.data_manager = DataManager()
        
        # Set up window properties
        self.setWindowTitle("Audio Recorder")
        self.setMinimumSize(1000, 600)
        
        # Create UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Load settings
        self.load_settings()
    
    def setup_ui(self):
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top controls
        top_layout = QHBoxLayout()
        
        # Create date and language selection
        date_layout = QVBoxLayout()
        date_layout.addWidget(QLabel("Recording Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.date.today())
        date_layout.addWidget(self.date_edit)
        
        # Create language, style, and speaker selection
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Select Language", "HIN", "ENG", "TEL"])
        date_layout.addWidget(QLabel("Language:"))
        date_layout.addWidget(self.language_combo)
        
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Select Style", "HAPPY", "SAD", "NEUTRAL"])
        date_layout.addWidget(QLabel("Style:"))
        date_layout.addWidget(self.style_combo)
        
        self.speaker_combo = QComboBox()
        self.speaker_combo.addItems(["Select Speaker", "Male", "Female"])
        date_layout.addWidget(QLabel("Speaker:"))
        date_layout.addWidget(self.speaker_combo)
        
        top_layout.addLayout(date_layout)
        
        # Create device selection
        device_layout = QVBoxLayout()
        device_layout.addWidget(QLabel("48kHz Device:"))
        self.device_48k_combo = QComboBox()
        device_layout.addWidget(self.device_48k_combo)
        
        device_layout.addWidget(QLabel("8kHz Device:"))
        self.device_8k_combo = QComboBox()
        device_layout.addWidget(self.device_8k_combo)
        
        self.update_device_list_btn = QPushButton("Refresh Devices")
        device_layout.addWidget(self.update_device_list_btn)
        
        top_layout.addLayout(device_layout)
        
        # Create submit button
        self.submit_btn = QPushButton("Initialize Recording")
        self.submit_btn.setFixedWidth(150)
        top_layout.addWidget(self.submit_btn)
        
        main_layout.addLayout(top_layout)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Vertical)
        
        # Create text content area
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("ID:"))
        self.text_id = QLineEdit()
        id_layout.addWidget(self.text_id)
        
        counter_layout = QHBoxLayout()
        self.audio_counter_label = QLabel("Audio Count: 0")
        counter_layout.addWidget(self.audio_counter_label)
        self.duration_label = QLabel("Total Duration: 0:00")
        counter_layout.addWidget(self.duration_label)
        
        text_layout.addLayout(counter_layout)
        text_layout.addLayout(id_layout)
        
        self.text_sentence = QTextEdit()
        self.text_sentence.setMinimumHeight(100)
        text_layout.addWidget(self.text_sentence)
        
        splitter.addWidget(text_widget)
        
        # Create waveform widget
        self.waveform_widget = WaveformWidget()
        splitter.addWidget(self.waveform_widget)
        
        main_layout.addWidget(splitter, 1)
        
        # Create recording panel
        self.recording_panel = RecordingPanel()
        main_layout.addWidget(self.recording_panel)
        
        # Create status bar for db meter
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setTextVisible(False)
        self.statusBar().addPermanentWidget(self.level_meter, 1)
        
        # Populate device combo boxes
        self.update_device_list()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        load_csv_action = QAction("Load CSV", self)
        load_csv_action.triggered.connect(self.load_csv)
        file_menu.addAction(load_csv_action)
        
        select_output_dir_action = QAction("Set Output Directory", self)
        select_output_dir_action.triggered.connect(self.select_output_directory)
        file_menu.addAction(select_output_dir_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        audio_settings_action = QAction("Audio Settings", self)
        audio_settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(audio_settings_action)
    
    def connect_signals(self):
        # Connect UI signals
        self.update_device_list_btn.clicked.connect(self.update_device_list)
        self.submit_btn.clicked.connect(self.initialize_recording)
        
        # Connect recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped)
        self.audio_recorder.level_meter.connect(self.update_level_meter)
        self.audio_recorder.error_occurred.connect(self.show_error)
        
        # Connect player signals
        self.audio_player.playback_started.connect(self.on_playback_started)
        self.audio_player.playback_stopped.connect(self.on_playback_stopped)
        self.audio_player.position_changed.connect(self.waveform_widget.update_position)
        self.audio_player.error_occurred.connect(self.show_error)
        
        # Connect data manager signals
        self.data_manager.data_loaded.connect(self.on_data_loaded)
        self.data_manager.current_item_changed.connect(self.update_ui_with_item)
        
        # Connect recording panel signals
        self.recording_panel.record_button_clicked.connect(self.start_recording)
        self.recording_panel.stop_button_clicked.connect(self.stop_recording)
        self.recording_panel.play_button_clicked.connect(self.play_audio)
        self.recording_panel.pause_button_clicked.connect(self.pause_audio)
        self.recording_panel.next_button_clicked.connect(self.next_sentence)
        self.recording_panel.prev_button_clicked.connect(self.prev_sentence)
        self.recording_panel.trim_button_clicked.connect(self.trim_audio)
        
        # Connect text input signals
        self.text_id.returnPressed.connect(self.load_by_id)

    def update_device_list(self):
        """Update the device combo boxes with available audio devices."""
        devices = self.audio_recorder.get_available_devices()
        
        self.device_48k_combo.clear()
        self.device_8k_combo.clear()
        
        for device in devices:
            device_text = f"{device['name']}"
            if device['is_asio']:
                device_text += " (ASIO)"
            
            self.device_48k_combo.addItem(device_text, device['index'])
            self.device_8k_combo.addItem(device_text, device['index'])
    
    def initialize_recording(self):
        """Set up the recording session with current settings."""
        # Validate settings
        if (self.language_combo.currentText() == "Select Language" or
            self.style_combo.currentText() == "Select Style" or
            self.speaker_combo.currentText() == "Select Speaker"):
            QMessageBox.warning(self, "Incomplete Settings", 
                               "Please select language, style, and speaker before proceeding.")
            return
        
        # Create output directory structure
        now = datetime.datetime.now()
        date_str = self.date_edit.date().toString("yyyyMMdd")
        unique_id = now.strftime("%H%M%S")
        
        language = self.language_combo.currentText()
        style = self.style_combo.currentText()
        speaker = self.speaker_combo.currentText()
        
        # Create directory path
        self.output_dir = os.path.join(
            self.data_manager.base_dir,
            f"{date_str}_{language}_{style}_{speaker}_{unique_id}"
        )
        
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, '48khz'), exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, '8khz'), exist_ok=True)
            
            QMessageBox.information(self, "Success", f"Recording session initialized.\nOutput directory: {self.output_dir}")
            
            # Enable recording controls
            self.recording_panel.enable_controls(True)
        except Exception as e:
            self.show_error(f"Failed to create output directory: {str(e)}")

    # Further methods for UI interaction, recording, etc. would be added here
    def load_csv(self):
        """Load a CSV file containing recording text data."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                self.data_manager.load_csv(file_path)
                QMessageBox.information(self, "Success", f"CSV loaded: {file_path}")
            except Exception as e:
                self.show_error(f"Error loading CSV: {str(e)}")
    
    def select_output_directory(self):
        """Select base output directory for recordings."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.data_manager.base_dir
        )
        
        if directory:
            self.data_manager.set_base_directory(directory)
            QMessageBox.information(self, "Success", f"Output directory set to: {directory}")
    
    def open_settings(self):
        """Open the settings dialog."""
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec_():
            # Apply settings if dialog was accepted
            settings = settings_dialog.get_settings()
            self.audio_recorder.apply_settings(settings)
    
    def start_recording(self):
        """Start recording audio."""
        # Get device indices
        device_48k = self.device_48k_combo.currentData()
        device_8k = self.device_8k_combo.currentData()
        
        # Get current ID and text
        text_id = self.text_id.text()
        text = self.text_sentence.toPlainText()
        
        if not text:
            self.show_error("Please enter text before recording.")
            return
        
        # Create output file paths
        filename_48k = os.path.join(self.output_dir, '48khz', f"{text_id}.wav")
        filename_8k = os.path.join(self.output_dir, '8khz', f"{text_id}.wav")
        
        # Start recording
        self.audio_recorder.start_recording(device_48k, device_8k, filename_48k, filename_8k)
        self.recording_panel.set_recording_state(True)

    def stop_recording(self):
        """Stop current recording."""
        self.audio_recorder.stop_recording()
        self.recording_panel.set_recording_state(False)

    def play_audio(self):
        """Play the current audio file."""
        current_id = self.text_id.text()
        if not current_id:
            return
        
        # Use 48kHz file for playback
        audio_file = os.path.join(self.output_dir, '48khz', f"{current_id}.wav")
        
        if os.path.exists(audio_file):
            self.audio_player.play(audio_file)
            self.recording_panel.set_playing_state(True)
        else:
            self.show_error(f"Audio file not found: {audio_file}")

    def pause_audio(self):
        """Pause/resume audio playback."""
        if self.audio_player.is_playing():
            if self.recording_panel.is_paused:
                self.audio_player.resume()
                self.recording_panel.set_paused_state(False)
            else:
                self.audio_player.pause()
                self.recording_panel.set_paused_state(True)
    
    def next_sentence(self):
        """Move to the next item in the dataset."""
        self.data_manager.next_item()
    
    def prev_sentence(self):
        """Move to the previous item in the dataset."""
        self.data_manager.prev_item()
    
    # Implement trim_audio method properly
    def trim_audio(self):
        """Trim silence from the current audio file."""
        current_id = self.text_id.text()
        if not current_id:
            return
            
        audio_file_48k = os.path.join(self.output_dir, '48khz', f"{current_id}.wav")
        audio_file_8k = os.path.join(self.output_dir, '8khz', f"{current_id}.wav")
        
        if not os.path.exists(audio_file_48k):
            self.show_error(f"Audio file not found: {audio_file_48k}")
            return
            
        try:
            # Apply trimming to both files
            # For 48kHz file
            audio_segment = AudioSegment.from_wav(audio_file_48k)
            trimmed_segment = self.trim_silence_from_audio(audio_segment)
            trimmed_segment.export(audio_file_48k, format="wav")
            
            # For 8kHz file if exists
            if os.path.exists(audio_file_8k):
                audio_segment = AudioSegment.from_wav(audio_file_8k)
                trimmed_segment = self.trim_silence_from_audio(audio_segment)
                trimmed_segment.export(audio_file_8k, format="wav")
                
            self.statusBar().showMessage(f"Audio file trimmed: {current_id}.wav")
            # Update waveform display
            self.waveform_widget.load_audio_file(audio_file_48k)
        except Exception as e:
            self.show_error(f"Error trimming audio: {str(e)}")

    def trim_silence_from_audio(self, audio_segment, silence_threshold=-50, min_silence_len=100):
        """Trim silence from beginning and end of an audio segment."""
        # Import here to avoid circular imports
        from pydub.silence import detect_leading_silence
        
        # Trim silence from beginning
        start_trim = detect_leading_silence(audio_segment, silence_threshold=silence_threshold)
        
        # Trim silence from end (reverse audio, trim, then reverse back)
        end_trim = detect_leading_silence(
            audio_segment.reverse(), 
            silence_threshold=silence_threshold
        )
        
        # Keep only audio between silences
        duration = len(audio_segment)
        trimmed = audio_segment[start_trim:duration-end_trim]
        
        return trimmed
    
    def load_by_id(self):
        """Load item by ID when Enter is pressed in the ID field."""
        id_text = self.text_id.text()
        if id_text:
            self.data_manager.set_current_item_by_id(id_text)
    
    def on_recording_started(self):
        """Handle recording started signal."""
        self.statusBar().showMessage("Recording...")
    
    def on_recording_stopped(self, duration):
        """Handle recording stopped signal."""
        self.statusBar().showMessage(f"Recording completed. Duration: {duration:.1f} seconds")
        # Update the audio counter
        self.update_audio_counter()
        # Update total duration
        self.update_total_duration(duration)

    def update_total_duration(self, new_duration):
        """Update the total duration display."""
        # Extract current duration value
        current_text = self.duration_label.text()
        try:
            current_mins, current_secs = current_text.split(": ")[1].split(":")
            current_total_secs = int(current_mins) * 60 + float(current_secs)
        except:
            current_total_secs = 0
            
        # Add new duration
        new_total_secs = current_total_secs + new_duration
        mins = int(new_total_secs // 60)
        secs = int(new_total_secs % 60)

        # Update label
        self.duration_label.setText(f"Total Duration: {mins}:{secs:02d}")
    
    def on_playback_started(self, duration):
        """Handle playback started signal."""
        self.statusBar().showMessage(f"Playing... Duration: {duration:.1f} seconds")
        self.waveform_widget.set_duration(duration)
    
    def on_playback_stopped(self):
        """Handle playback stopped signal."""
        self.statusBar().showMessage("Playback stopped")
        self.recording_panel.set_playing_state(False)
        self.recording_panel.set_paused_state(False)
        
    def update_level_meter(self, level):
        """Update the level meter in the status bar."""
        self.level_meter.setValue(int(level * 100))
    
    def on_data_loaded(self, count):
        """Handle data loaded signal."""
        self.statusBar().showMessage(f"Loaded {count} items")
    
    def update_ui_with_item(self, item):
        """Update UI with the current data item."""
        if item:
            self.text_id.setText(item.get('id', ''))
            self.text_sentence.setPlainText(item.get('text', ''))
    
    def update_audio_counter(self):
        """Update the counter for recorded audio files."""
        if hasattr(self, 'output_dir'):
            dir_48k = os.path.join(self.output_dir, '48khz')
            if os.path.exists(dir_48k):
                count = len([f for f in os.listdir(dir_48k) if f.endswith('.wav')])
                self.audio_counter_label.setText(f"Audio Count: {count}")
    
    def show_error(self, message):
        """Display error message."""
        QMessageBox.critical(self, "Error", message)
    
    def load_settings(self):
        """Load application settings."""
        settings = QSettings("AudioRecorder", "RecordingApp")
        
        # Load last used directory
        last_dir = settings.value("last_directory", "")
        if last_dir and os.path.exists(last_dir):
            self.data_manager.set_base_directory(last_dir)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save settings before closing
        settings = QSettings("AudioRecorder", "RecordingApp")
        settings.setValue("last_directory", self.data_manager.base_dir)
        
        # Accept the close event
        event.accept()