# ui/main_window.py
import os
import datetime
import sys
import requests # For upload
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QFileDialog,
                             QTextEdit, QLineEdit, QMessageBox, QAction,
                             QMenuBar, QMenu, QSplitter, QProgressBar,
                             QDateEdit, QCheckBox, QSizePolicy, QSpinBox,
                             QFontComboBox, QProgressDialog, QApplication) # Added QSizePolicy, QSpinBox, QFontComboBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSettings, QSize # Added QSize
from PyQt5.QtGui import QFont # Added QFont

from ui.waveform_widget import WaveformWidget
from ui.recording_panel import RecordingPanel
from ui.settings_dialog import SettingsDialog
from ui.traffic_light_indicator import TrafficLightIndicator # ADDED
from ui.script_window import ScriptWindow # ADDED
from core.audio_recorder import AudioRecorder
from core.audio_player import AudioPlayer
from core.data_manager import DataManager
# from utils.audio_utils import trim_silence_numpy # No longer directly used in MainWindow for trim_audio

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.audio_recorder = AudioRecorder()
        self.audio_player = AudioPlayer()
        self.data_manager = DataManager()
        
        # Set up window properties
        self.setWindowTitle("Audio Recorder")
        self.setMinimumSize(1000, 700) # Increased min height slightly
        
        # Initialize output_dir to None
        self.output_dir = None
        
        # Initialize ScriptWindow reference
        self.script_window = None
        
        # Create UI
        self.setup_ui()
        self.waveform_widget.audio_player = self.audio_player
        
        # Connect signals
        self.connect_signals()
        
        # Load settings (including font settings)
        self.load_settings()
        self.apply_text_sentence_font_settings() # Apply loaded font settings

    def setup_ui(self):
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top controls
        top_controls_layout = QHBoxLayout() # Renamed for clarity
        
        # Date, Language, Style, Speaker selection (left column of top controls)
        metadata_layout = QVBoxLayout()
        
        date_speaker_row = QHBoxLayout()
        date_group_layout = QVBoxLayout()
        date_group_layout.addWidget(QLabel("Recording Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.date.today())
        date_group_layout.addWidget(self.date_edit)
        date_speaker_row.addLayout(date_group_layout)

        speaker_group_layout = QVBoxLayout()
        speaker_group_layout.addWidget(QLabel("Speaker:"))
        self.speaker_combo = QComboBox()
        self.speaker_combo.addItems(["Select Speaker", "Male", "Female"]) # Default items
        speaker_group_layout.addWidget(self.speaker_combo)
        date_speaker_row.addLayout(speaker_group_layout)
        metadata_layout.addLayout(date_speaker_row)

        lang_style_row = QHBoxLayout()
        language_group_layout = QVBoxLayout()
        language_group_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Select Language", "HIN", "ENG", "TEL"]) # Default items
        language_group_layout.addWidget(self.language_combo)
        lang_style_row.addLayout(language_group_layout)

        style_group_layout = QVBoxLayout()
        style_group_layout.addWidget(QLabel("Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Select Style", "HAPPY", "SAD", "NEUTRAL"]) # Default items
        style_group_layout.addWidget(self.style_combo)
        lang_style_row.addLayout(style_group_layout)
        metadata_layout.addLayout(lang_style_row)

        top_controls_layout.addLayout(metadata_layout)
        top_controls_layout.addSpacing(20) # Add some space

        # Device selection (middle column of top controls)
        device_layout = QVBoxLayout()
        device_layout.addWidget(QLabel("48kHz Device:"))
        self.device_48k_combo = QComboBox()
        device_layout.addWidget(self.device_48k_combo)
        
        device_layout.addWidget(QLabel("8kHz Device:"))
        self.device_8k_combo = QComboBox()
        device_layout.addWidget(self.device_8k_combo)

        self.enable_8k_checkbox = QCheckBox("Enable 8k Recording")
        self.enable_8k_checkbox.setChecked(False)
        self.audio_recorder.enable_8k = False
        device_layout.addWidget(self.enable_8k_checkbox)
        
        self.update_device_list_btn = QPushButton("Refresh Devices")
        device_layout.addWidget(self.update_device_list_btn)
        top_controls_layout.addLayout(device_layout)
        top_controls_layout.addStretch(1) # Add stretch to push initialize button to the right

        # Initialize button and Traffic Light Indicator (right part of top controls)
        init_indicator_layout = QVBoxLayout()
        init_indicator_layout.setAlignment(Qt.AlignTop) # Align this group to the top

        self.submit_btn = QPushButton("Initialize Recording")
        self.submit_btn.setMinimumHeight(40) # Make button taller
        init_indicator_layout.addWidget(self.submit_btn)

        # Add Traffic Light Indicator
        self.traffic_indicator = TrafficLightIndicator(self)
        init_indicator_layout.addWidget(self.traffic_indicator, 0, Qt.AlignCenter) # Center horizontally
        init_indicator_layout.addStretch(1)

        top_controls_layout.addLayout(init_indicator_layout)
        main_layout.addLayout(top_controls_layout)
        
        # Create splitter for main content (Text Area and Waveform)
        splitter = QSplitter(Qt.Vertical)
        
        # Create text content area (top part of splitter)
        text_widget_container = QWidget()
        text_layout = QVBoxLayout(text_widget_container)
        text_layout.setContentsMargins(0, 5, 0, 0) # Adjust margins
        
        # Row for ID, Counters, and Font Controls
        id_font_counter_layout = QHBoxLayout()

        id_group_layout = QVBoxLayout()
        id_label_layout = QHBoxLayout()
        id_label_layout.addWidget(QLabel("ID:"))
        id_label_layout.addStretch()
        id_group_layout.addLayout(id_label_layout)
        self.text_id = QLineEdit()
        self.text_id.setToolTip("Enter ID and press Enter to jump")
        id_group_layout.addWidget(self.text_id)
        id_font_counter_layout.addLayout(id_group_layout, 1) # Give ID field some stretch

        # Font controls
        font_controls_layout = QHBoxLayout()
        font_controls_layout.addWidget(QLabel("Font:"))
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setToolTip("Select font family for the script text")
        font_controls_layout.addWidget(self.font_family_combo)

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 72)
        self.font_size_spinbox.setToolTip("Select font size for the script text")
        self.font_size_spinbox.setSuffix(" pt")
        font_controls_layout.addWidget(self.font_size_spinbox)
        id_font_counter_layout.addLayout(font_controls_layout, 2) # Give font controls more space

        # Counters
        counter_layout = QVBoxLayout()
        counter_layout.setAlignment(Qt.AlignRight) # Align counters to the right
        self.audio_counter_label = QLabel("Audio Count: 0")
        counter_layout.addWidget(self.audio_counter_label)
        self.duration_label = QLabel("Total Duration: 0:00") # This seems session specific, might remove if not used
        counter_layout.addWidget(self.duration_label)
        id_font_counter_layout.addLayout(counter_layout)

        text_layout.addLayout(id_font_counter_layout)
        
        self.text_sentence = QTextEdit()
        self.text_sentence.setMinimumHeight(100) # Initial reasonable height
        self.text_sentence.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Ensure it expands
        self.text_sentence.setAlignment(Qt.AlignCenter) # Default center alignment
        default_font = QFont()
        default_font.setPointSize(16) # Default size
        self.text_sentence.setFont(default_font)
        text_layout.addWidget(self.text_sentence)

        splitter.addWidget(text_widget_container)
        
        # Create waveform widget (bottom part of splitter)
        self.waveform_widget = WaveformWidget()
        splitter.addWidget(self.waveform_widget)
        
        # Set initial sizes for splitter sections (optional, Qt tries to distribute evenly)
        splitter.setSizes([int(self.height() * 0.3), int(self.height() * 0.7)]) # Example: 30% text, 70% waveform
        
        main_layout.addWidget(splitter, 1) # Give splitter expanding space
        
        # Create recording panel (bottom controls)
        self.recording_panel = RecordingPanel()
        self.recording_panel.set_audio_player(self.audio_player) # Pass audio_player
        main_layout.addWidget(self.recording_panel)
        
        # Status Bar for DB meter and progress bar
        status_bar = self.statusBar()
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setMaximumWidth(200) # Limit width of level meter
        self.level_meter.setTextVisible(False)
        status_bar.addPermanentWidget(self.level_meter, 1) # Stretch factor 1
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setMaximumWidth(250) # Limit width of progress bar
        status_bar.addPermanentWidget(self.progress_bar, 2) # Stretch factor 2

        # Populate device combo boxes
        self.update_device_list()
        self.recording_panel.enable_controls(False) # Initially disable playback/record controls

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        load_csv_action = QAction("Load CSV", self)
        load_csv_action.triggered.connect(self.load_csv)
        file_menu.addAction(load_csv_action)
        
        file_menu.addSeparator()
        select_output_dir_action = QAction("Set Output Directory", self)
        select_output_dir_action.triggered.connect(self.select_output_directory)
        file_menu.addAction(select_output_dir_action)
        
        file_menu.addSeparator()
        upload_action = QAction("Upload Current Recording (Ctrl+S)", self)
        upload_action.setShortcut("Ctrl+S")
        upload_action.triggered.connect(self.upload_recording)
        file_menu.addAction(upload_action)
        
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Navigation Menu
        nav_menu = menubar.addMenu("Navigation")
        next_action = QAction("Next Item (→)", self)
        next_action.setShortcut(Qt.Key_Right)
        next_action.triggered.connect(self.next_sentence)
        nav_menu.addAction(next_action)

        prev_action = QAction("Previous Item (←)", self)
        prev_action.setShortcut(Qt.Key_Left)
        prev_action.triggered.connect(self.prev_sentence)
        nav_menu.addAction(prev_action)

        nav_menu.addSeparator()
        goto_next_unrecorded_action = QAction("Go to Next Unrecorded", self)
        goto_next_unrecorded_action.setToolTip("Find the next item in the list that hasn't been recorded yet.")
        goto_next_unrecorded_action.triggered.connect(self.go_to_next_unrecorded)
        nav_menu.addAction(goto_next_unrecorded_action)

        # View Menu (for ScriptWindow)
        view_menu = menubar.addMenu("View")
        toggle_script_window_action = QAction("Toggle Script Window", self)
        toggle_script_window_action.setCheckable(True)
        toggle_script_window_action.triggered.connect(self.toggle_script_window)
        view_menu.addAction(toggle_script_window_action)
        self.toggle_script_window_action = toggle_script_window_action # Keep reference for sync

        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        audio_settings_action = QAction("Application Settings", self)
        audio_settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(audio_settings_action)

        test_devices_action = QAction("Test Recording Devices", self)
        test_devices_action.triggered.connect(self.test_recording_devices)
        settings_menu.addAction(test_devices_action)

    def connect_signals(self):
        # Top controls
        self.update_device_list_btn.clicked.connect(self.update_device_list)
        self.submit_btn.clicked.connect(self.initialize_recording)
        self.enable_8k_checkbox.stateChanged.connect(self.update_ui_for_8k_toggle)
        
        # Font controls
        self.font_family_combo.currentFontChanged.connect(self.on_font_family_changed)
        self.font_size_spinbox.valueChanged.connect(self.on_font_size_changed)

        # Recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped) # This gets duration
        self.audio_recorder.level_meter.connect(self.update_level_meter)
        self.audio_recorder.error_occurred.connect(self.show_error)
        
        # Player signals
        self.audio_player.playback_started.connect(self.on_playback_started)
        self.audio_player.playback_stopped.connect(self.on_playback_stopped)
        self.audio_player.position_changed.connect(self.on_player_position_changed)
        self.audio_player.position_changed.connect(self.waveform_widget.update_waveform_position_line)
        self.audio_player.error_occurred.connect(self.show_error)
        
        # Waveform widget and its interaction with recording panel's slider
        self.waveform_widget.set_time_slider(self.recording_panel.time_slider)
        # self.recording_panel.time_slider.sliderMoved.connect(self.on_slider_moved) # Replaced by sliderReleased in RecordingPanel
        
        # Data manager signals
        self.data_manager.data_loaded.connect(self.on_data_loaded)
        self.data_manager.current_item_changed.connect(self.update_ui_with_item)
        self.data_manager.error_occurred.connect(self.show_error) # Connect error signal
        
        # Recording panel signals
        self.recording_panel.record_button_clicked.connect(self.handle_record_button_press) # Centralized handler
        self.recording_panel.stop_button_clicked.connect(self.stop_recording)
        self.recording_panel.play_button_clicked.connect(self.play_audio)
        self.recording_panel.pause_button_clicked.connect(self.pause_audio)
        self.recording_panel.next_button_clicked.connect(self.next_sentence)
        self.recording_panel.prev_button_clicked.connect(self.prev_sentence)
        self.recording_panel.trim_button_clicked.connect(self.trim_audio)
        self.recording_panel.upload_button_clicked.connect(self.upload_recording)
        
        # Text input signals
        self.text_id.returnPressed.connect(self.load_by_id)

    # --- Font Control Handlers ---
    def on_font_family_changed(self, font):
        self.apply_text_sentence_font_settings()

    def on_font_size_changed(self, size):
        self.apply_text_sentence_font_settings()

    def apply_text_sentence_font_settings(self):
        font = self.font_family_combo.currentFont()
        size = self.font_size_spinbox.value()
        font.setPointSize(size)
        
        self.text_sentence.setFont(font)
        self.text_sentence.setAlignment(Qt.AlignCenter) # This is set once, but could be made dynamic

        # MainWindow now only sets alignment for ScriptWindow, if desired.
        # Font family and size are managed by ScriptWindow itself.
        if self.script_window and self.script_window.isVisible():
            self.script_window.set_script_alignment(
                self.text_sentence.alignment() # Example: Sync alignment from main window
            )
            
    def load_font_settings(self):
        settings = QSettings()
        font_family = settings.value("ui/font_family", QFont().family())
        font_size = settings.value("ui/font_size", 16, type=int)

        # Block signals to prevent immediate application during loading
        self.font_family_combo.blockSignals(True)
        self.font_size_spinbox.blockSignals(True)

        # Find font in combo box
        for i in range(self.font_family_combo.count()):
            if self.font_family_combo.itemText(i) == font_family:
                self.font_family_combo.setCurrentIndex(i)
                break
        else: # If not found, set to default (first item or system default)
            self.font_family_combo.setCurrentFont(QFont(font_family))


        self.font_size_spinbox.setValue(font_size)

        self.font_family_combo.blockSignals(False)
        self.font_size_spinbox.blockSignals(False)

        # Apply settings after loading
        self.apply_text_sentence_font_settings()

    def save_font_settings(self):
        settings = QSettings()
        settings.setValue("ui/font_family", self.font_family_combo.currentFont().family())
        settings.setValue("ui/font_size", self.font_size_spinbox.value())

    # --- Other Methods ---
    def update_ui_for_8k_toggle(self):
        is_enabled = self.enable_8k_checkbox.isChecked()
        self.device_8k_combo.setEnabled(is_enabled)
        self.audio_recorder.enable_8k = is_enabled

    def initialize_recording(self):
        if (self.language_combo.currentIndex() == 0 or
            self.style_combo.currentIndex() == 0 or
            self.speaker_combo.currentIndex() == 0):
            QMessageBox.warning(self, "Incomplete Settings", 
                               "Please select language, style, and speaker before proceeding.")
            return
        
        date_str = self.date_edit.date().toString("yyyyMMdd")
        language = self.language_combo.currentText()
        style = self.style_combo.currentText()
        speaker = self.speaker_combo.currentText()
        
        base_dir_name = f"{date_str}_{language}_{style}_{speaker}"
        base_output_path = os.path.join(self.data_manager.base_dir, base_dir_name)
        
        self.output_dir = base_output_path
        counter = 1
        while os.path.exists(self.output_dir):
            self.output_dir = f"{base_output_path}_{counter}"
            counter += 1
            
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, '48khz'), exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, '8khz'), exist_ok=True)
            
            self.statusBar().showMessage(f"Recording session initialized. Output: {self.output_dir}")
            QMessageBox.information(self, "Success", f"Recording session initialized.\nOutput directory: {self.output_dir}")
            self.recording_panel.enable_controls(True)
            # Update submit button to indicate it's initialized, maybe disable it or change text
            self.submit_btn.setText("Session Initialized")
            self.submit_btn.setEnabled(False)
            self.traffic_indicator.setState("off") # Ready for first recording
        except Exception as e:
            self.show_error(f"Failed to create output directory: {str(e)}")
            self.traffic_indicator.setState("off")

    def handle_record_button_press(self):
        """Handles the record button press from the recording panel."""
        if not self.audio_recorder.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if not self.output_dir:
            QMessageBox.warning(self, "Not Initialized", 
                            "Please click 'Initialize Recording' first.")
            return

        file_extension = getattr(self.audio_recorder, 'file_format', 'wav')

        device_48k = self.device_48k_combo.currentData() if self.device_48k_combo.currentData() != -1 else self.audio_recorder.get_system_default_device("input")
        device_8k = self.device_8k_combo.currentData() if self.device_8k_combo.currentData() != -1 else self.audio_recorder.get_system_default_device("input")
        
        current_item = self.data_manager.get_current_item()
        if current_item is None:
            self.show_error("No data item selected.")
            return
        text_id = str(current_item.get('id', ''))
        
        if not text_id:
            self.show_error("Current item has no ID.")
            return
        
        filename_48k = os.path.join(self.output_dir, '48khz', f"{text_id}.{file_extension}")
        filename_8k = os.path.join(self.output_dir, '8khz', f"{text_id}.{file_extension}")

        os.makedirs(os.path.dirname(filename_48k), exist_ok=True)
        if self.enable_8k_checkbox.isChecked():
            os.makedirs(os.path.dirname(filename_8k), exist_ok=True)
        
        try:
            self.audio_recorder.start_recording(device_48k, device_8k, filename_48k, filename_8k)
            # on_recording_started will handle UI updates like traffic light
        except Exception as e:
            self.show_error(f"Recording error: {str(e)}")
            self.recording_panel.set_recording_state(False)
            self.traffic_indicator.setState("off")
            if self.script_window and self.script_window.isVisible():
                self.script_window.update_indicator_state("off")

    def stop_recording(self):
        if not self.audio_recorder.is_recording:
            return

        self.traffic_indicator.setState("orange") # Saving
        if self.script_window and self.script_window.isVisible():
            self.script_window.update_indicator_state("orange")

        # Store filenames used by the recorder before stopping
        filename_48k = getattr(self.audio_recorder, 'filename_48k', None)
        filename_8k = getattr(self.audio_recorder, 'filename_8k', None)
        enable_8k_was_on = self.audio_recorder.enable_8k

        self.audio_recorder.stop_recording() # This emits recording_stopped with duration
        # UI state like button text is handled in on_recording_stopped or by recording_panel directly

        # Actual file registration and traffic light update to GREEN happens in on_recording_stopped
        # after duration (and implicitly save) is confirmed.

    def on_recording_started(self):
        self.statusBar().showMessage("Recording...")
        self.recording_panel.set_recording_state(True)
        self.traffic_indicator.setState("red")
        if self.script_window and self.script_window.isVisible():
            self.script_window.update_indicator_state("red")
    
    def on_recording_stopped(self, duration): # duration is from the saved file
        self.recording_panel.set_recording_state(False) # Update button in panel
        
        current_id = self.text_id.text()
        if not current_id:
            print("Warning: Cannot register recording, no ID in UI field after stop.")
            self.traffic_indicator.setState("off") # Or red if error state is preferred
            if self.script_window and self.script_window.isVisible(): self.script_window.update_indicator_state(self.traffic_indicator.getState())
            return

        filename_48k = getattr(self.audio_recorder, 'filename_48k', None)
        filename_8k = getattr(self.audio_recorder, 'filename_8k', None)
        enable_8k_was_on = getattr(self.audio_recorder, 'enable_8k', False) # Check the state during recording

        final_audio_path_48k = filename_48k if (filename_48k and os.path.exists(filename_48k)) else ''
        final_audio_path_8k = filename_8k if (enable_8k_was_on and filename_8k and os.path.exists(filename_8k)) else ''
        
        if duration > 0 and final_audio_path_48k:
            self.data_manager.register_recording(
                final_audio_path_48k,
                final_audio_path_8k,
                duration
            )
            self.recording_panel.set_recorded_indicator(True)
            self.recording_panel.set_upload_status(False) # Reset upload status for new recording
            
            stats = self.data_manager.get_total_stats()
            self.progress_bar.setValue(int(stats['progress_percent']))
            self.statusBar().showMessage(f"Saved {current_id}. Duration: {duration:.1f}s")
            self.traffic_indicator.setState("green") # Saved successfully

            if self.waveform_widget.load_audio_file(final_audio_path_48k):
                self.audio_player.load_audio_file(final_audio_path_48k, final_audio_path_8k) # Pre-load for player
            
            # Auto-upload if enabled
            settings = QSettings()
            if settings.value("storage/auto_upload", False, bool):
                QTimer.singleShot(500, self.upload_recording)
        else:
            self.show_error(f"Recording for {current_id} failed to save or duration was zero.")
            self.traffic_indicator.setState("off") # Or Red for error state

        if self.script_window and self.script_window.isVisible():
            self.script_window.update_indicator_state(self.traffic_indicator.getState())
        
        self.update_audio_counter()
        self.update_total_duration(duration if duration > 0 else 0)


    def play_audio(self):
        current_item = self.data_manager.get_current_item()
        if current_item is None:
            self.show_error("No current item selected.")
            return

        audio_file = str(current_item.get('audio_path_48k', '')) # Ensure string

        if audio_file and os.path.exists(audio_file):
            secondary_path_val = current_item.get('audio_path_8k', None)
            secondary_file = None # Initialize to None
            # Ensure secondary_path is a string or None BEFORE os.path.exists
            if isinstance(secondary_path_val, str) and secondary_path_val.strip():
                secondary_file = secondary_path_val
                if not os.path.exists(secondary_file): # Now it's safe to check
                    secondary_file = None
            # If secondary_path_val was not a non-empty string, secondary_file remains None

            if self.waveform_widget.load_audio_file(audio_file): # Ensure waveform is current
                if self.audio_player.load_audio_file(audio_file, secondary_file):
                    self.audio_player.play()
                else:
                    self.show_error("Failed to load audio for playback.")
            else:
                self.show_error("Failed to load audio for waveform display.")
        elif audio_file: # audio_file is a non-empty string but does not exist
            self.show_error(f"Audio file path found, but file does not exist: {audio_file}")
        else: # audio_file is an empty string (or was None initially)
            self.show_error("This item has not been recorded yet or the audio path is missing.")

    def pause_audio(self):
        if self.audio_player.is_currently_playing():
            self.audio_player.pause()
            self.recording_panel.set_paused_state(True)
        elif self.audio_player.is_playing and self.audio_player.is_paused:
            self.audio_player.resume()
            self.recording_panel.set_paused_state(False)
        # If not playing at all, this button (if it's a pause icon) shouldn't be active
        # or should act as play. The RecordingPanel's on_play_clicked handles this.

    def on_playback_started(self, filename, duration):
        self.statusBar().showMessage(f"Playing: {os.path.basename(filename)}. Duration: {duration:.1f}s")
        self.waveform_widget.set_duration(duration)
        
        total_minutes = int(duration // 60)
        total_seconds = int(duration % 60)
        total_time = f"{total_minutes}:{total_seconds:02d}"
        
        self.recording_panel.update_time_display("0:00", total_time)
        self.recording_panel.set_slider_maximum(1000) # Ensure slider max is set
        self.recording_panel.set_playing_state(True)
        self.recording_panel.set_paused_state(False)
    
    def on_playback_stopped(self):
        self.statusBar().showMessage("Playback stopped")
        self.recording_panel.set_playing_state(False)
        self.recording_panel.set_paused_state(False)
        self.recording_panel.update_time_display("0:00", self.recording_panel.duration_label.text()) # Reset current time
        self.recording_panel.update_slider_position(0) # Reset slider
        self.recording_panel.update() # Force UI update
        
    def on_player_position_changed(self, position, duration=None):
        if duration is None:
            duration = self.audio_player.get_duration()
        if duration <= 0: return

        current_time_str = f"{int(position // 60)}:{int(position % 60):02d}"
        total_time_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
        self.recording_panel.update_time_display(current_time_str, total_time_str)

        if not self.recording_panel.time_slider.isSliderDown():
             slider_val = int((position / duration) * self.recording_panel.time_slider.maximum())
             self.recording_panel.update_slider_position(slider_val)

    def next_sentence(self):
        self.data_manager.next_item()
    
    def prev_sentence(self):
        self.data_manager.previous_item()

    def go_to_next_unrecorded(self):
        if self.data_manager.dataframe is None or self.data_manager.dataframe.empty:
            self.statusBar().showMessage("No data loaded to navigate.")
            return
        df = self.data_manager.dataframe
        current_idx = self.data_manager.current_index
        total_items = len(df)
        search_indices = list(range(current_idx + 1, total_items)) + list(range(0, current_idx + 1))
        for idx in search_indices:
            if not df.iloc[idx].get('recorded', False): # Use .get for safety
                self.data_manager.current_index = idx
                self.data_manager.current_item_changed.emit(df.iloc[idx])
                self.statusBar().showMessage(f"Jumped to next unrecorded: {df.iloc[idx]['id']}")
                return
        QMessageBox.information(self, "Navigation", "No unrecorded items found.")

    def trim_audio(self):
        current_item = self.data_manager.get_current_item()
        if current_item is None: self.show_error("No item selected."); return

        audio_file_48k = current_item.get('audio_path_48k', '')
        if not audio_file_48k or not os.path.exists(audio_file_48k):
            self.show_error(f"48kHz audio not found: {audio_file_48k}"); return

        self._set_ui_busy(True, f"Trimming {os.path.basename(audio_file_48k)}...")
        self.traffic_indicator.setState("orange")
        if self.script_window and self.script_window.isVisible(): self.script_window.update_indicator_state("orange")
        
        QApplication.processEvents() # Update UI

        success_48k, new_duration_48k, msg_48k = self._trim_single_file(audio_file_48k, current_item.get('id', '48k'))
        
        trimmed_successfully = False
        if success_48k:
            self.data_manager.update_current_item({'duration': new_duration_48k, 'trimmed': True})
            status_message = msg_48k
            trimmed_successfully = True
            self.traffic_indicator.setState("green") # Trimmed successfully
        else:
            status_message = msg_48k
            self.data_manager.update_current_item({'trimmed': False}) # Revert if failed
            self.traffic_indicator.setState("off") # Or red for error

        # Trim 8k if exists
        audio_file_8k = current_item.get('audio_path_8k', '')
        if self.enable_8k_checkbox.isChecked() and audio_file_8k and os.path.exists(audio_file_8k):
            self._set_ui_busy(True, f"Trimming {os.path.basename(audio_file_8k)}...")
            QApplication.processEvents() # Update UI
            success_8k, _, msg_8k = self._trim_single_file(audio_file_8k, current_item.get('id', '8k'))
            if not success_8k:
                self.show_error(f"Failed to trim 8kHz file: {msg_8k}")
            # No need to update duration in data_manager for 8k, 48k is primary

        self._set_ui_busy(False, status_message)
        if self.script_window and self.script_window.isVisible(): self.script_window.update_indicator_state(self.traffic_indicator.getState())

        if trimmed_successfully:
            self.waveform_widget.load_audio_file(audio_file_48k)
            self.audio_player.load_audio_file(audio_file_48k, current_item.get('audio_path_8k', None)) # Reload player
        self.update_ui_with_item(self.data_manager.get_current_item()) # Refresh UI

    def _trim_single_file(self, file_path, item_id_for_log):
        """Helper to trim a single audio file. Returns (success_bool, new_duration, message_str)."""
        from utils.audio_utils import trim_silence_numpy # Local import for helper
        try:
            # Load audio data using soundfile
            audio_data, samplerate = sf.read(file_path, always_2d=False)
            if audio_data.ndim > 1: # Ensure mono for trimming
                audio_data = audio_data[:, 0]
            
            original_dtype = audio_data.dtype # Preserve original dtype for saving

            # Get trimming parameters from AudioRecorder settings
            threshold_db = getattr(self.audio_recorder, 'silence_threshold_db', -40.0)
            padding_ms = getattr(self.audio_recorder, 'padding_ms', 100)

            trimmed_audio, new_duration = trim_silence_numpy(
                audio_data,
                samplerate,
                threshold_db=threshold_db,
                padding_ms=padding_ms
            )

            if new_duration > 0:
                # Convert back to original dtype if it was changed by trim_silence_numpy (e.g. to float)
                # and if soundfile needs specific subtype
                subtype = getattr(self.audio_recorder, 'subtype', 'PCM_16')
                if subtype == 'PCM_16' and trimmed_audio.dtype != np.int16:
                    # Example: If trim_silence_numpy returns float in [-1, 1]
                    trimmed_audio = (trimmed_audio * 32767).astype(np.int16)
                elif subtype == 'PCM_24' and trimmed_audio.dtype != np.int32: # sf uses int32 for 24bit
                    # Assuming float in [-1, 1]
                    trimmed_audio = (trimmed_audio * 8388607).astype(np.int32)
                elif subtype == 'FLOAT' and trimmed_audio.dtype != np.float32:
                    trimmed_audio = trimmed_audio.astype(np.float32)
                # Add more conversions if necessary based on how trim_silence_numpy handles dtypes

                sf.write(file_path, trimmed_audio, samplerate, subtype=subtype)
                return True, new_duration, f"Trimmed {os.path.basename(file_path)}. New duration: {new_duration:.2f}s"
            else:
                return False, 0.0, f"Trimming resulted in empty audio for {os.path.basename(file_path)}. File not changed."
        except Exception as e:
            return False, 0.0, f"Error trimming {os.path.basename(file_path)}: {str(e)}"

    def upload_recording(self):
        current_item = self.data_manager.get_current_item()
        if current_item is None: self.show_error("No item selected for upload."); return False
        
        audio_path_48k = current_item.get('audio_path_48k', '')
        if not audio_path_48k or not os.path.exists(audio_path_48k):
            self.show_error("48kHz audio not found for upload."); return False
        
        # if current_item.get('uploaded', False):
        #     QMessageBox.information(self, "Already Uploaded", "This item has already been marked as uploaded.")
        #     return True # Consider it success if already uploaded

        self._set_ui_busy(True, f"Uploading {current_item.get('id', '')}...")
        self.traffic_indicator.setState("orange")
        if self.script_window and self.script_window.isVisible(): self.script_window.update_indicator_state("orange")
        QApplication.processEvents()

        data = {
            "easy_id": self.date_edit.date().toString("yyyyMMdd"),
            "Sentence": str(current_item.get('text', '')),
            "speaker": self.speaker_combo.currentText(),
            "language": self.language_combo.currentText(),
            "style": self.style_combo.currentText(),
            "category": "DEFAULT", # Or make this configurable
            "data_id": str(current_item.get('id', ''))
        }
        
        files_to_send = {}
        opened_files = [] # To ensure they are closed
        try:
            file_48k_handle = open(audio_path_48k, 'rb')
            opened_files.append(file_48k_handle)
            files_to_send['audio_file_48khz'] = (os.path.basename(audio_path_48k), file_48k_handle, 'audio/wav')
            
            audio_path_8k = current_item.get('audio_path_8k', '')
            if self.enable_8k_checkbox.isChecked() and audio_path_8k and os.path.exists(audio_path_8k):
                file_8k_handle = open(audio_path_8k, 'rb')
                opened_files.append(file_8k_handle)
                files_to_send['audio_file_8khz'] = (os.path.basename(audio_path_8k), file_8k_handle, 'audio/wav')

            # API endpoint from settings or hardcoded
            settings = QSettings()
            api_url = settings.value("network/upload_url", 'http://tts-dc-prod.centralindia.cloudapp.azure.com:8094/audio_upload')
            
            response = requests.post(api_url, files=files_to_send, data=data, timeout=30) # Added timeout

            if response.ok:
                self.statusBar().showMessage(f"Successfully uploaded: {data['data_id']}")
                self.data_manager.update_current_item({'uploaded': True})
                self.recording_panel.set_upload_status(True)
                QMessageBox.information(self, "Upload Successful", f"Audio {data['data_id']} uploaded.")
                self.traffic_indicator.setState("green") # Uploaded successfully
                QTimer.singleShot(100, self.next_sentence) # Auto-advance
                self._set_ui_busy(False)
                return True
            else:
                self.show_error(f"Upload failed: Status {response.status_code}, {response.text}")
                # If upload fails, it's still saved, so indicator might stay green or a specific "upload failed" state
                # For now, keep it as per last successful operation (likely green from saving)
                self.traffic_indicator.setState(self.traffic_indicator.getState()) # No change or set to a "warning" state
                self._set_ui_busy(False)
                return False
        except requests.exceptions.RequestException as e_req: # Catch network errors
            self.show_error(f"Network error during upload: {str(e_req)}")
            self.traffic_indicator.setState(self.traffic_indicator.getState()) # No change
            self._set_ui_busy(False)
            return False
        except Exception as e:
            self.show_error(f"Upload error: {str(e)}")
            self.traffic_indicator.setState(self.traffic_indicator.getState()) # No change
            self._set_ui_busy(False)
            return False
        finally:
            for f in opened_files:
                f.close()
            if self.script_window and self.script_window.isVisible():
                self.script_window.update_indicator_state(self.traffic_indicator.getState())


    def load_by_id(self):
        id_text = self.text_id.text()
        if id_text:
            if not self.data_manager.set_current_item_by_id(id_text): # Returns False if not found
                self.show_error(f"ID '{id_text}' not found in the loaded CSV.")
    
    def update_level_meter(self, level): # level is 0-1
        self.level_meter.setValue(int(level)) # Assuming level is already 0-100 from recorder
    
    def load_csv(self):
        """Load a CSV file containing recording text data."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                success = self.data_manager.load_csv(file_path)
                if success:
                    # Show instructions
                    QMessageBox.information(self, "CSV Loaded Successfully", 
                                        "To record sentences:\n\n"
                                        "1. Select your recording devices\n"
                                        "2. Click 'Initialize Recording'\n"
                                        "3. Use the red record button (⏺) to record each sentence\n"
                                        "4. Press the right arrow (→) to move to the next sentence\n\n"
                                        "You can also use keyboard shortcuts:\n"
                                        "R: Start/stop recording\n"
                                        "Space: Play/pause\n"
                                        "Arrow keys: Navigate between sentences")
            except Exception as e:
                self.show_error(f"Error loading CSV: {str(e)}")

    def on_data_loaded(self, dataframe):
        count = len(dataframe) if dataframe is not None else 0
        self.statusBar().showMessage(f"Loaded {count} items")
        if dataframe is not None:
            self._populate_combo_from_df_column(self.language_combo, dataframe, 'language', "Select Language")
            self._populate_combo_from_df_column(self.style_combo, dataframe, 'style', "Select Style")
            self._populate_combo_from_df_column(self.speaker_combo, dataframe, 'speaker', "Select Speaker")
        stats = self.data_manager.get_total_stats()
        self.progress_bar.setValue(int(stats['progress_percent']))
        if count > 0 and self.data_manager.current_index == -1 : # If loaded, and no item yet selected
            self.data_manager.current_index = 0 # select first one
            self.data_manager.current_item_changed.emit(dataframe.iloc[0])
        elif count == 0:
            self.update_ui_with_item(None) # Clear UI if no data

    def _populate_combo_from_df_column(self, combo, df, column_name, default_text):
        combo.blockSignals(True)
        current_text = combo.currentText()
        combo.clear()
        combo.addItem(default_text)
        if column_name in df.columns:
            for value in df[column_name].unique():
                if pd.notna(value) and str(value).strip():
                    combo.addItem(str(value))
        
        idx = combo.findText(current_text)
        if idx != -1:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def update_ui_with_item(self, item_series): # item is pd.Series
        if item_series is not None and isinstance(item_series, pd.Series):
            item = item_series.to_dict()
            self.text_id.setText(str(item.get('id', '')))
            self.text_sentence.setPlainText(str(item.get('text', '')))
            
            # Sync script window
            if self.script_window and self.script_window.isVisible():
                self.script_window.update_script(str(item.get('text', '')))

            audio_path = str(item.get('audio_path_48k', '')) # Ensure string
            if audio_path and os.path.exists(audio_path):
                self.waveform_widget.load_audio_file(audio_path)
                
                secondary_path_val = item.get('audio_path_8k', None)
                # Ensure secondary_path is a string or None BEFORE os.path.exists
                if isinstance(secondary_path_val, str) and secondary_path_val.strip():
                    secondary_path = secondary_path_val
                    if not os.path.exists(secondary_path): # Now it's safe to check
                        secondary_path = None
                else: # If it's not a non-empty string (e.g., None, NaN, empty string)
                    secondary_path = None
                
                self.audio_player.load_audio_file(audio_path, secondary_path)
                # Update duration display if player is not currently playing this file
                if not (self.audio_player.is_playing and self.audio_player.current_file == audio_path):
                    # Ensure player has loaded the file to get correct duration
                    # self.audio_player.load_audio_file(audio_path, secondary_path) # Already called above
                    self.on_player_position_changed(0, self.audio_player.get_duration())

            else:
                self.waveform_widget.set_audio_data(None, 48000)
                self.recording_panel.update_time_display("0:00", "0:00")
                self.recording_panel.update_slider_position(0)

            # Update combo boxes to reflect current item's metadata
            for combo, key in [(self.language_combo, 'language'), (self.style_combo, 'style'), (self.speaker_combo, 'speaker')]:
                val = str(item.get(key, ''))
                idx = combo.findText(val, Qt.MatchExactly)
                if idx >=0: combo.setCurrentIndex(idx)
                # else: combo.setCurrentIndex(0) # Or add if not present, or leave as is

            recorded = item.get('recorded', False)
            uploaded = item.get('uploaded', False)
            trimmed = item.get('trimmed', False)

            self.recording_panel.set_recorded_indicator(recorded)
            self.recording_panel.set_upload_status(uploaded)

            status_msg = f"Item {item.get('id', '')}"
            current_indicator_state = "off"
            if uploaded:
                status_msg += " (Uploaded)"
                current_indicator_state = "green"
            elif recorded:
                status_msg += " (Recorded"
                if trimmed: status_msg += ", Trimmed"
                status_msg += ")"
                current_indicator_state = "green" # Saved is also green
            else:
                 status_msg = f"Ready to record item {item.get('id', '')}"
            
            self.statusBar().showMessage(status_msg)
            self.traffic_indicator.setState(current_indicator_state)
            if self.script_window and self.script_window.isVisible():
                self.script_window.update_indicator_state(current_indicator_state)

        else: # Item is None (e.g. empty CSV or end of list)
            self.text_id.clear()
            self.text_sentence.clear()
            self.waveform_widget.set_audio_data(None, 48000)
            self.recording_panel.set_recorded_indicator(False)
            self.recording_panel.set_upload_status(False)
            self.recording_panel.update_time_display("0:00", "0:00")
            self.recording_panel.update_slider_position(0)
            self.statusBar().showMessage("No data loaded or item selected.")
            self.traffic_indicator.setState("off")
            if self.script_window and self.script_window.isVisible():
                self.script_window.update_script("")
                self.script_window.update_indicator_state("off")

    def update_audio_counter(self):
        if self.output_dir and os.path.exists(os.path.join(self.output_dir, '48khz')):
            dir_48k = os.path.join(self.output_dir, '48khz')
            count = len([f for f in os.listdir(dir_48k) if f.endswith( ('.wav', '.flac') )]) # Check for common formats
            self.audio_counter_label.setText(f"Audio Count: {count}")
        else:
            self.audio_counter_label.setText(f"Audio Count: 0")

    def update_total_duration(self, new_duration_for_last_file):
        # This seems to track session duration, sum up from DataManager instead
        stats = self.data_manager.get_total_stats()
        total_secs = stats['total_duration']
        mins = int(total_secs // 60)
        secs = int(total_secs % 60)
        self.duration_label.setText(f"Total Duration: {mins}:{secs:02d}")
    
    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)
        self.statusBar().showMessage(f"Error: {message[:50]}...", 5000) # Show brief error in status bar
    
    def _set_ui_busy(self, busy, message=""):
        self.recording_panel.enable_controls(not busy)
        # Consider disabling other UI elements like menus too
        for menu in [self.menuBar().findChild(QMenu, name) for name in ["File", "Navigation", "View", "Settings"] if name]:
            if menu: menu.setEnabled(not busy)
        
        if message: self.statusBar().showMessage(message)
        if busy: QApplication.setOverrideCursor(Qt.WaitCursor)
        else: QApplication.restoreOverrideCursor()
        QApplication.processEvents()

    def load_settings(self):
        settings = QSettings()
        last_dir = settings.value("data_manager/base_dir", "data") # Use DataManager's setting
        self.audio_recorder.apply_settings(settings)
        if last_dir and os.path.exists(last_dir):
            self.data_manager.set_base_directory(last_dir)
        else: # If last_dir doesn't exist, ensure data_manager's default is created
            if not os.path.exists(self.data_manager.base_dir):
                try: os.makedirs(self.data_manager.base_dir, exist_ok=True)
                except: pass
        
        # Load font settings
        self.load_font_settings()

        # Load 8k checkbox state
        self.enable_8k_checkbox.setChecked(settings.value("audio/enable_8k_recording", False, type=bool))
        self.update_ui_for_8k_toggle() # Apply the loaded state

    def save_settings(self):
        settings = QSettings()
        self.data_manager.save_settings() # DataManager handles its own base_dir
        self.save_font_settings() # Save font settings
        settings.setValue("audio/enable_8k_recording", self.enable_8k_checkbox.isChecked())

    def closeEvent(self, event):
        self.save_settings()
        # Clean up script window if it exists
        if self.script_window:
            self.script_window.close() # Ensure it's properly closed
        # Clean up audio player/recorder if they have explicit cleanup methods
        self.audio_player.cleanup()
        event.accept()

    def keyPressEvent(self, event):
        key_text = event.text()
        modifiers = event.modifiers()

        if key_text == '*': # Start/Stop recording
            self.handle_record_button_press()
        elif event.key() == Qt.Key_Space: # Stop recording (as per latest spec)
            if self.audio_recorder.is_recording:
                self.stop_recording()
            elif self.audio_player.is_playing: # If not recording, Space can be Play/Pause
                 self.pause_audio() # Or self.play_audio() if you want it to start if stopped
            else: # If not recording and not playing, try to play
                 self.play_audio()

        elif modifiers == Qt.ControlModifier and event.key() == Qt.Key_S: # Upload
            self.upload_recording()
        elif event.key() == Qt.Key_Right and not modifiers: # Next
            self.next_sentence()
        elif event.key() == Qt.Key_Left and not modifiers: # Previous
            self.prev_sentence()
        else:
            super().keyPressEvent(event)
    
    def select_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Base Output Directory", self.data_manager.base_dir)
        if directory:
            if self.data_manager.set_base_directory(directory):
                QMessageBox.information(self, "Success", f"Base output directory set to: {directory}")
    
    def open_settings(self):
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec_():
            settings = settings_dialog.get_settings() # This re-saves all settings from dialog
            self.audio_recorder.apply_settings(settings)
            self.data_manager._load_settings() # Reload DataManager settings like base_dir if changed
            # Potentially apply other settings immediately (e.g. auto-upload flag)
            self.statusBar().showMessage("Settings applied.")

    def test_recording_devices(self):
        devices = self.audio_recorder.get_available_devices()
        if not devices: QMessageBox.warning(self, "No Devices", "No recording devices detected."); return
            
        progress = QProgressDialog("Testing audio devices...", "Cancel", 0, len(devices), self)
        progress.setWindowTitle("Device Test")
        progress.setWindowModality(Qt.WindowModal)
        progress.show(); QApplication.processEvents()
        
        working_devices = []
        results_text = "Device Test Results:\n\n"
        for i, device_info in enumerate(devices):
            progress.setValue(i)
            progress.setLabelText(f"Testing: {device_info['name']}")
            if progress.wasCanceled(): results_text += "Test Canceled.\n"; break
            QApplication.processEvents()
            
            success, message = self.audio_recorder.test_recording_device(device_info['index'])
            status_char = "✓" if success else "✗"
            results_text += f"{status_char} {device_info['name']}: {message}\n"
            if success: working_devices.append(device_info)
        progress.close()
        
        # Update device lists in UI (could be done by self.update_device_list after filtering)
        self.update_device_list(working_devices_first=working_devices) # Pass tested devices
        
        QMessageBox.information(self, "Device Test Complete", 
                            f"{results_text}\nFound {len(working_devices)} working devices out of {len(devices)} detected.")

    def update_device_list(self, working_devices_first=None):
        all_devices = self.audio_recorder.get_available_devices()
        
        current_48k_data = self.device_48k_combo.currentData()
        current_8k_data = self.device_8k_combo.currentData()

        self.device_48k_combo.clear()
        self.device_8k_combo.clear()
        
        self.device_48k_combo.addItem("System Default Device", -1) # UserData -1 for default
        self.device_8k_combo.addItem("System Default Device", -1)
        
        # Prioritize working devices if list is provided
        sorted_devices = []
        if working_devices_first:
            sorted_devices.extend(working_devices_first)
            # Add remaining devices that were not in working_devices_first
            for dev in all_devices:
                if not any(wd['index'] == dev['index'] for wd in working_devices_first):
                    sorted_devices.append(dev)
        else:
            sorted_devices = all_devices

        asio_found_in_list = False
        for device in sorted_devices:
            prefix = ""
            if working_devices_first and any(wd['index'] == device['index'] for wd in working_devices_first) :
                prefix = "✓ "
            elif working_devices_first : # Tested but not in working list
                prefix = "✗ "

            device_text = f"{prefix}{device['name']} ({device['channels']} ch)"
            if device['is_asio']:
                device_text += " [ASIO]"
                asio_found_in_list = True

            self.device_48k_combo.addItem(device_text, device['index'])
            self.device_8k_combo.addItem(device_text, device['index'])
            
        idx_48k = self.device_48k_combo.findData(current_48k_data)
        self.device_48k_combo.setCurrentIndex(idx_48k if idx_48k >= 0 else 0)
        idx_8k = self.device_8k_combo.findData(current_8k_data)
        self.device_8k_combo.setCurrentIndex(idx_8k if idx_8k >= 0 else 0)

        if asio_found_in_list:
            print("ASIO devices listed.")
        else:
            settings = QSettings()
            if sys.platform == 'win32' and settings.value("audio/enable_asio", False, bool):
                QMessageBox.warning(self, "ASIO Warning", 
                                    "ASIO is enabled, but no ASIO devices were found by sounddevice.\n"
                                    "Ensure ASIO drivers are installed and working, then Refresh Devices.")

    # --- Script Window Management ---
    def toggle_script_window(self):
        if self.script_window is None:
            self.script_window = ScriptWindow() 
            self.script_window.window_closed.connect(self.on_script_window_closed)
        
        if self.script_window.isVisible():
            self.script_window.hide()
            self.toggle_script_window_action.setChecked(False)
        else:
            current_item = self.data_manager.get_current_item()
            if current_item is not None:
                self.script_window.update_script(str(current_item.get('text', '')))
            else:
                self.script_window.update_script("")
            
            # Sync alignment if needed (font family/size are local to ScriptWindow now)
            self.script_window.set_script_alignment(self.text_sentence.alignment())
            
            # Sync indicator state
            self.script_window.update_indicator_state(self.traffic_indicator.getState())
            self.script_window.show()
            self.toggle_script_window_action.setChecked(True)

    def on_script_window_closed(self):
        # self.script_window = None # If you want to recreate it each time
        # Or just update the menu item if it's hidden via 'X'
        if self.toggle_script_window_action:
             self.toggle_script_window_action.setChecked(False)
        # If you set self.script_window to None, ensure toggle_script_window recreates it.
        # For now, let's assume it just gets hidden. If it's truly closed and destroyed,
        # then self.script_window = None is correct. QWidget.close() by default just hides.
        # If you set Qt.WA_DeleteOnClose attribute, then it's destroyed.