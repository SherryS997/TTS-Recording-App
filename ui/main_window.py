# ui/main_window.py
import os
import datetime, sys, requests
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QComboBox, QFileDialog, 
                            QTextEdit, QLineEdit, QMessageBox, QAction, 
                            QMenuBar, QMenu, QTabWidget, QSplitter, QSlider, QProgressBar,
                            QDateEdit, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSettings

from ui.waveform_widget import WaveformWidget
from ui.recording_panel import RecordingPanel
from ui.settings_dialog import SettingsDialog
from core.audio_recorder import AudioRecorder
from core.audio_player import AudioPlayer
from core.data_manager import DataManager
from utils.audio_utils import trim_silence_numpy

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
        
        # Initialize output_dir to None
        self.output_dir = None
        
        # Create UI
        self.setup_ui()
        self.waveform_widget.audio_player = self.audio_player
        
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

        # Add a progress bar for CSV recording progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.statusBar().addPermanentWidget(self.progress_bar, 2)

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

        # Add a checkbox for enabling/disabling 8k recording
        self.enable_8k_checkbox = QCheckBox("Enable 8k Recording")
        self.enable_8k_checkbox.setChecked(False)  # Default is enabled
        self.audio_recorder.enable_8k = False
        device_layout.addWidget(self.enable_8k_checkbox)

        
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
        self.text_sentence.setMinimumHeight(5)
        text_layout.addWidget(self.text_sentence)
        font = self.text_sentence.font()
        font.setPointSize(16)
        self.text_sentence.setFont(font)
        text_layout.addWidget(self.text_sentence)

        splitter.addWidget(text_widget)
        
        # Create waveform widget
        self.waveform_widget = WaveformWidget()
        
        # We'll connect to the recording panel's slider instead of creating a new one
        splitter.addWidget(self.waveform_widget)
        
        main_layout.addWidget(splitter, 1)
        
        # Create recording panel
        self.recording_panel = RecordingPanel()

        # Pass the audio_player to recording_panel so that it can control playback
        self.recording_panel.set_audio_player(self.audio_player)

        main_layout.addWidget(self.recording_panel)
        
        # Create status bar for db meter
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setTextVisible(False)
        self.statusBar().addPermanentWidget(self.level_meter, 1)
        
        # Populate device combo boxes
        self.update_device_list()

        self.recording_panel.enable_controls(False)
    
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

        # Add upload action to the menu
        file_menu.addSeparator()
        upload_action = QAction("Upload Current Recording", self)
        upload_action.triggered.connect(self.upload_recording)
        file_menu.addAction(upload_action)

        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Navigation Menu --- ADDED ---
        nav_menu = menubar.addMenu("Navigation")

        next_action = QAction("Next Item (→)", self)
        next_action.triggered.connect(self.next_sentence)
        nav_menu.addAction(next_action)

        prev_action = QAction("Previous Item (←)", self)
        prev_action.triggered.connect(self.prev_sentence)
        nav_menu.addAction(prev_action)

        nav_menu.addSeparator()

        goto_next_unrecorded_action = QAction("Go to Next Unrecorded", self)
        goto_next_unrecorded_action.setToolTip("Find the next item in the list that hasn't been recorded yet.")
        goto_next_unrecorded_action.triggered.connect(self.go_to_next_unrecorded)
        nav_menu.addAction(goto_next_unrecorded_action)
        # --- End Navigation Menu ---

        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        audio_settings_action = QAction("Audio Settings", self)
        audio_settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(audio_settings_action)

        test_devices_action = QAction("Test Recording Devices", self)
        test_devices_action.triggered.connect(self.test_recording_devices)
        settings_menu.addAction(test_devices_action)

    def go_to_next_unrecorded(self):
        """Finds and jumps to the next item where 'recorded' is False."""
        if self.data_manager.dataframe is None or self.data_manager.dataframe.empty:
            self.statusBar().showMessage("No data loaded to navigate.")
            return

        df = self.data_manager.dataframe
        current_idx = self.data_manager.current_index
        total_items = len(df)

        # Start searching from the item *after* the current one
        search_indices = list(range(current_idx + 1, total_items)) + list(range(0, current_idx + 1))

        found_idx = -1
        for idx in search_indices:
            try:
                # Check the 'recorded' status for the row at index 'idx'
                if not df.iloc[idx]['recorded']:
                    found_idx = idx
                    break # Stop at the first unrecorded item found
            except IndexError:
                 continue # Should not happen with correct range, but safety first
            except KeyError:
                 self.show_error("Error: 'recorded' column not found in DataFrame.")
                 return

        if found_idx != -1:
            # Jump to the found item using its index
            # Directly set index and emit signal for update
            self.data_manager.current_index = found_idx
            self.data_manager.current_item_changed.emit(df.iloc[found_idx])
            self.statusBar().showMessage(f"Jumped to next unrecorded item: {df.iloc[found_idx]['id']}")
        else:
            QMessageBox.information(self, "Navigation", "No unrecorded items found.")
            self.statusBar().showMessage("All items seem to be recorded.")

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
        # Connect position changed to BOTH the main window handler (for slider/labels)
        # AND the waveform widget handler (for the red line)
        self.audio_player.position_changed.connect(self.on_player_position_changed)
        self.audio_player.position_changed.connect(self.waveform_widget.update_waveform_position_line) # ADD THIS LINE
        self.audio_player.error_occurred.connect(self.show_error)
        
        # Set up the waveform widget to use the recording panel's time slider
        self.waveform_widget.set_time_slider(self.recording_panel.time_slider)
        
        # Connect the slider's value change to seek audio
        self.recording_panel.time_slider.sliderMoved.connect(self.on_slider_moved)
        
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
        self.recording_panel.upload_button_clicked.connect(self.upload_recording)  # Add this line
        
        # Connect text input signals
        self.text_id.returnPressed.connect(self.load_by_id)

        self.enable_8k_checkbox.stateChanged.connect(self.update_ui_for_toggle)
        self.audio_recorder.enable_8k = self.enable_8k_checkbox.isChecked()

    def on_slider_moved(self, position):
        """Handle when user moves the slider to seek audio"""
        if self.audio_player.get_duration() > 0:
            # Convert slider position (0-1000) to seconds
            seek_position = (position / 1000.0) * self.audio_player.get_duration()
            
            # Update the audio player's current position
            self.audio_player.seek(seek_position)
            
            # If audio was playing, force a restart from the new position
            was_playing = self.audio_player.is_playing and not self.audio_player.is_paused
            if was_playing:
                # Store current position
                current_file = self.audio_player.current_file
                
                # Stop and restart playback from new position
                self.audio_player.stop()
                self.audio_player.current_position = seek_position
                self.audio_player.play(current_file)

    def update_ui_for_toggle(self):
        """Update UI elements based on the toggle state."""
        is_enabled = self.enable_8k_checkbox.isChecked()
        self.device_8k_combo.setEnabled(is_enabled)
        self.audio_recorder.enable_8k = is_enabled
        print(self.enable_8k_checkbox.isChecked())

    def upload_recording(self):
        """Upload the current recording to the API endpoint."""
        # Get current item
        current_item = self.data_manager.get_current_item()
        if current_item is None:
            self.show_error("No current item selected for upload.")
            return False
        
        # Check if this item has been recorded
        audio_path_48k = current_item.get('audio_path_48k', '')
        audio_path_8k = current_item.get('audio_path_8k', '')
        
        if not audio_path_48k or not os.path.exists(audio_path_48k):
            self.show_error("No 48kHz audio file found for upload.")
            return False
        
        # Get metadata from the current item and UI controls
        text_id = str(current_item.get('id', ''))
        text = str(current_item.get('text', ''))
        
        # Get current date for easy_id
        current_date = self.date_edit.date().toString("yyyyMMdd")
        
        # Get language, style, and speaker from combo boxes
        language = self.language_combo.currentText()
        style = self.style_combo.currentText()
        speaker = self.speaker_combo.currentText()
        
        # Add category (you might want to add this as a UI field later)
        category = "DEFAULT"
        
        # Prepare data for the API request
        data = {
            "easy_id": current_date,
            "Sentence": text,
            "speaker": speaker,
            "language": language,
            "style": style,
            "category": category,
            "data_id": text_id
        }
        
        # Get filenames for upload
        filename_48k = os.path.basename(audio_path_48k)
        
        # Prepare files for the API request
        files = {
            'audio_file_48khz': (filename_48k, open(audio_path_48k, 'rb'), 'audio/wav')
        }
        
        # Add 8kHz file if available
        if audio_path_8k and os.path.exists(audio_path_8k) and self.enable_8k_checkbox.isChecked():
            filename_8k = os.path.basename(audio_path_8k)
            files['audio_file_8khz'] = (filename_8k, open(audio_path_8k, 'rb'), 'audio/wav')
        
        try:
            self._set_ui_busy(True, f"Uploading {text_id}...") # Add busy indicator
            self.statusBar().showMessage(f"Uploading {text_id}...")
            # Send POST request to the API
            response = requests.post(
                'http://tts-dc-prod.centralindia.cloudapp.azure.com:8094/audio_upload', 
                files=files, 
                data=data
            )
            
            # Clean up file handles
            for key in files:
                files[key][1].close()
            
            # Check response
            if response.ok:
                self.statusBar().showMessage(f"Successfully uploaded audio {text_id}")
                self.data_manager.update_current_item({'uploaded': True})
                self.recording_panel.set_upload_status(True) # Update button state immediately
                QMessageBox.information(self, "Upload Successful", f"Audio {text_id} uploaded.")
                # Optional: Auto-advance if configured
                # if self.settings.value(...): self.next_sentence()
                self._set_ui_busy(False) # End busy state
                return True
            else:
                self._set_ui_busy(False, f"Upload failed for {text_id}") # End busy state
                self.show_error(f"Upload failed: Status {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            self.show_error(f"Upload error: {str(e)}")
            self._set_ui_busy(False, f"Upload error for {text_id}") # End busy state
            
            # Clean up file handles in case of exception
            for key in files:
                if not files[key][1].closed:
                    files[key][1].close()
            
            return False

    def update_device_list(self):
        """Update the device combo boxes with available audio devices."""
        devices = self.audio_recorder.get_available_devices()

        # Store current selections
        current_48k_data = self.device_48k_combo.currentData()
        current_8k_data = self.device_8k_combo.currentData()

        self.device_48k_combo.clear()
        self.device_8k_combo.clear()
        
        # Add default device option first
        self.device_48k_combo.addItem("System Default Device", -1)
        self.device_8k_combo.addItem("System Default Device", -1)
        
        asio_found = False
        for device in devices:
            # Create more informative device labels
            device_text = f"{device['name']} ({device['channels']} ch)"
            if device['is_asio']:
                device_text += " [ASIO]"
                asio_found = True

            self.device_48k_combo.addItem(device_text, device['index'])
            self.device_8k_combo.addItem(device_text, device['index'])
            
        # Try to restore previous selection
        idx_48k = self.device_48k_combo.findData(current_48k_data)
        self.device_48k_combo.setCurrentIndex(idx_48k if idx_48k >= 0 else 0) # Default to first item if not found

        idx_8k = self.device_8k_combo.findData(current_8k_data)
        self.device_8k_combo.setCurrentIndex(idx_8k if idx_8k >= 0 else 0)

        if asio_found:
            print("ASIO devices listed.")
        else:
            # Check if ASIO was expected
            settings = QSettings()  # Remove organization/app name
            asio_enabled = settings.value("audio/enable_asio", False, bool)
            if sys.platform == 'win32' and asio_enabled:
                print("Warning: ASIO was enabled in settings, but no ASIO devices were found by sounddevice.")
                QMessageBox.warning(self, "ASIO Warning", "ASIO is enabled in settings, but no ASIO devices were found.\nEnsure ASIO drivers are installed and working.")
    
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
        # !!! IMPORTANT: Update SettingsDialog to handle dB threshold input !!!
        # For now, it only has '%'. This needs harmonization.
        # Let's assume settings dialog is updated to save 'audio/trim_threshold_db'
        if settings_dialog.exec_():
            settings = settings_dialog.get_settings()
            # Apply settings (AudioRecorder.apply_settings needs to read these)
            self.audio_recorder.apply_settings(settings)
            # Maybe apply settings to other components if needed
            print("Settings applied.")
    
    def start_recording(self):
        """Start recording audio."""
        # Check if recording has been initialized
        if not hasattr(self, 'output_dir') or self.output_dir is None:
            QMessageBox.warning(self, "Not Initialized", 
                            "Please click 'Initialize Recording' first to set up the output directory.")
            return

        # Get file format extension from recorder's settings
        file_extension = getattr(self.audio_recorder, 'file_format', 'wav') # Default to 'wav'

        # Get device indices
        if self.device_48k_combo.currentText() == "System Default Device":
            device_48k = self.audio_recorder.get_system_default_device(mode="input")
        else:
            device_48k = self.device_48k_combo.currentData()
        
        if self.device_8k_combo.currentText() == "System Default Device":
            device_8k = self.audio_recorder.get_system_default_device(mode="input")
        else:
            device_8k = self.device_8k_combo.currentData()
        
        # Get current ID and text
        current_item = self.data_manager.get_current_item()
        if current_item is None:
            self.show_error("No data item selected.")
            return
        text_id = str(current_item.get('id', ''))
        text = str(current_item.get('text', '')) # Use text from data manager

        if not text_id:
            self.show_error("Current item has no ID.")
            return
        if not text:
            self.show_error("Please enter text before recording.")
            return
        
        # Create output file paths WITH extension
        filename_48k = os.path.join(self.output_dir, '48khz', f"{text_id}.{file_extension}")
        filename_8k = os.path.join(self.output_dir, '8khz', f"{text_id}.{file_extension}")

        # Ensure directories exist (AudioRecorder._save_wav also does this, but doesn't hurt)
        os.makedirs(os.path.join(self.output_dir, '48khz'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, '8khz'), exist_ok=True)
        
        # Start recording
        try:
            self.audio_recorder.start_recording(device_48k, device_8k, filename_48k, filename_8k)
            self.recording_panel.set_recording_state(True)
        except Exception as e:
            self.show_error(f"Recording error: {str(e)}")

    def stop_recording(self):
        """Stop current recording and advance to next item."""
        # Store filenames used by the recorder before stopping (stop might clear them)
        filename_48k = getattr(self.audio_recorder, 'filename_48k', None)
        filename_8k = getattr(self.audio_recorder, 'filename_8k', None)
        enable_8k_was_on = getattr(self.audio_recorder, 'enable_8k', False)

        # Stop recording (this triggers saving via callbacks/thread finish)
        self.audio_recorder.stop_recording() # This emits recording_stopped with duration
        self.recording_panel.set_recording_state(False)

        # Duration is passed via the signal, connect to it if needed,
        # or use last_recording_duration if recorder stores it reliably AFTER save.
        # Let's use the stored filenames to check existence and register.

        current_id = self.text_id.text() # Get ID from UI as confirmation
        if not current_id:
            print("Warning: Cannot register recording, no ID in UI field after stop.")
            return

        # Check if files were actually saved (use the paths passed to start_recording)
        # Use the filenames captured *before* calling stop_recording
        final_audio_path_48k = filename_48k if (filename_48k and os.path.exists(filename_48k)) else ''
        final_audio_path_8k = filename_8k if (enable_8k_was_on and filename_8k and os.path.exists(filename_8k)) else ''
        duration = self.audio_recorder.last_recording_duration # Get duration recorded by recorder

        if not final_audio_path_48k:
             self.show_error(f"Recording seemed to stop, but 48kHz file was not found: {filename_48k}")
             # Don't register if primary file failed
             return

        # Update data manager with recorded status and FULL paths
        # Make relative if desired? For now, keep full paths.
        self.data_manager.register_recording(
            final_audio_path_48k,
            final_audio_path_8k,
            duration
        )
        self.recording_panel.set_recorded_indicator(True) # Update record button appearance
        self.recording_panel.set_upload_status(False) # Newly recorded item is not uploaded yet

        # Update progress display
        stats = self.data_manager.get_total_stats()
        self.progress_bar.setValue(int(stats['progress_percent']))

        # Load the newly recorded file into the waveform widget
        if final_audio_path_48k:
            self.waveform_widget.load_audio_file(final_audio_path_48k)
        # Optionally auto-advance:
        # QTimer.singleShot(500, self.next_sentence)

        # After successful recording, update data manager and UI
        if final_audio_path_48k:
            self.waveform_widget.load_audio_file(final_audio_path_48k)
            
            # Auto-upload if enabled in settings
            settings = QSettings()
            auto_upload = settings.value("storage/auto_upload", False, bool)
            if auto_upload:
                QTimer.singleShot(500, self.upload_recording)  # Short delay before upload

    def play_audio(self):
        """Play the audio file associated with the current item."""
        current_item = self.data_manager.get_current_item()
        if current_item is None:
            self.show_error("No current item selected.")
            return

        # Get the full path from the data manager
        audio_file = current_item.get('audio_path_48k', '') # Use 48k for playback

        if audio_file and os.path.exists(audio_file):
            # Pass secondary file path as well for A/B toggle
            secondary_file = current_item.get('audio_path_8k', None)
            if secondary_file and not os.path.exists(secondary_file):
                secondary_file = None # Don't pass non-existent path

            # Load and play
            success = self.audio_player.load_audio_file(audio_file, secondary_file)
            if success:
                self.audio_player.play()
                self.recording_panel.set_playing_state(True)
            # Error handling is done within load_audio_file via signals

        elif audio_file:
            self.show_error(f"Audio file path found in data, but file does not exist: {audio_file}")
        else:
            self.show_error("This item has not been recorded yet or the audio path is missing.")

    def pause_audio(self):
        """Pause/resume audio playback."""
        if self.audio_player.is_currently_playing():
            # If playing and not paused, pause it
            self.audio_player.pause()
            self.recording_panel.set_paused_state(True)
        elif self.audio_player.is_playing and self.audio_player.is_paused:
            # If paused, resume
            self.audio_player.resume()
            self.recording_panel.set_paused_state(False)
        else:
            # Not playing at all, so start playback
            self.play_audio()

    def next_sentence(self):
        """Move to the next item in the dataset."""
        self.data_manager.next_item()
    
    def prev_sentence(self):
        """Move to the previous item in the dataset."""
        self.data_manager.previous_item()
    
    def _set_ui_busy(self, busy, message=""):
        """Helper to enable/disable controls and set status."""
        self.recording_panel.enable_controls(not busy)
        # Optionally disable/enable other controls like menu items if needed
        # self.file_menu.setEnabled(not busy)
        # self.settings_menu.setEnabled(not busy)
        if message:
            self.statusBar().showMessage(message)
        if busy:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
        QApplication.processEvents() # Force UI update

    def trim_audio(self):
        """Trim silence from the current audio file using numpy and soundfile."""
        current_item = self.data_manager.get_current_item()
        if current_item is None:
            self.show_error("No current item selected.")
            return

        audio_file_48k = current_item.get('audio_path_48k', '')
        audio_file_8k = current_item.get('audio_path_8k', '') # Keep handling 8k too
        current_id = current_item.get('id', '')

        if not audio_file_48k or not os.path.exists(audio_file_48k):
            self.show_error(f"Primary audio file not found or not recorded: {audio_file_48k}")
            return

        # --- Start Busy State ---
        self._set_ui_busy(True, f"Trimming {os.path.basename(audio_file_48k)}...")
        # ---

        try:
            # --- Trim 48kHz file ---
            audio_data_48k, samplerate_48k = sf.read(audio_file_48k, always_2d=True) # Read as 2D first

            # Determine original number of channels before potentially making mono
            original_channels = audio_data_48k.shape[1] if audio_data_48k.ndim > 1 else 1

            # Create mono version for analysis
            if original_channels > 1:
                audio_data_48k_mono = audio_data_48k[:, 0]
            else:
                audio_data_48k_mono = audio_data_48k.flatten() # Ensure 1D if already mono

            threshold_db = getattr(self.audio_recorder, 'silence_threshold_db', -40)
            padding_ms = getattr(self.audio_recorder, 'padding_ms', 100)

            # Modify trim_silence_numpy to return indices (or adjust here)
            # Let's assume trim_silence_numpy can be modified or we re-implement the index finding part here
            # For simplicity, let's stick to the current trim_silence_numpy which returns trimmed mono data

            trimmed_data_48k_mono, new_duration_48k = trim_silence_numpy(
                audio_data_48k_mono,
                samplerate_48k,
                threshold_db=threshold_db,
                padding_ms=padding_ms
            )

            trimmed_successfully = False
            if new_duration_48k > 0:
                # Simple approach: Save the trimmed mono result
                # TODO: Implement stereo trimming preservation if needed
                final_data_48k = trimmed_data_48k_mono
                final_samplerate_48k = samplerate_48k
                subtype_48k = getattr(self.audio_recorder, 'subtype', 'PCM_16')

                sf.write(audio_file_48k, final_data_48k, final_samplerate_48k, subtype=subtype_48k)
                print(f"Trimmed and saved (mono): {os.path.basename(audio_file_48k)}")

                self.data_manager.update_trim_status(is_trimmed=True, new_duration=new_duration_48k)
                status_message = f"Trimmed {current_id}. New duration: {new_duration_48k:.2f}s"
                trimmed_successfully = True
            else:
                status_message = f"Trimming resulted in empty audio for {os.path.basename(audio_file_48k)}. File not changed."
                self.data_manager.update_trim_status(is_trimmed=False)

            # --- Trim 8kHz file (if exists) ---
            # (Keep the existing 8kHz trimming logic here, potentially adding status updates)
            if audio_file_8k and os.path.exists(audio_file_8k):
                self._set_ui_busy(True, f"Trimming {os.path.basename(audio_file_8k)}...")
                self.statusBar().showMessage(f"Trimming {os.path.basename(audio_file_8k)}...")
                QApplication.processEvents() # Update UI

                try:
                    audio_data_8k, samplerate_8k = sf.read(audio_file_8k, always_2d=False)
                    if audio_data_8k.ndim > 1: audio_data_8k = audio_data_8k[:, 0]

                    trimmed_data_8k, new_duration_8k = trim_silence_numpy(
                        audio_data_8k,
                        samplerate_8k,
                        threshold_db=threshold_db,
                        padding_ms=padding_ms
                    )

                    if new_duration_8k > 0:
                        subtype_8k = getattr(self.audio_recorder, 'subtype', 'PCM_16') # Use same subtype
                        sf.write(audio_file_8k, trimmed_data_8k, samplerate_8k, subtype=subtype_8k)
                        print(f"Trimmed and saved {os.path.basename(audio_file_8k)}")
                    else:
                        print(f"Warning: Trimming resulted in empty audio for {os.path.basename(audio_file_8k)}. File not changed.")

                except Exception as e_8k:
                     self.show_error(f"Error trimming 8kHz file '{os.path.basename(audio_file_8k)}': {str(e_8k)}")

            # Refresh UI elements related to duration/trim status if needed
            # self.update_ui_with_item(self.data_manager.get_current_item()) # Refresh
            self.waveform_widget.load_audio_file(audio_file_48k)


        except Exception as e:
            self.show_error(f"Error during trimming process: {str(e)}")
            status_message = f"Trimming failed for {current_id}."
            self.data_manager.update_trim_status(is_trimmed=False)
            trimmed_successfully = False # Ensure flag is false on error

        finally:
            # --- End Busy State ---
            self._set_ui_busy(False, status_message)
            # ---
            # Reload waveform only if trimming was successful
            if trimmed_successfully:
                self.waveform_widget.load_audio_file(audio_file_48k)

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

    def on_player_position_changed(self, position, duration=None):
        """Handle player position changed signal to update UI components (Slider, Labels)."""
        # Get duration from audio player if not provided in the signal
        if duration is None:
            duration = self.audio_player.get_duration()
            if duration <= 0:
                return  # Skip updates if we don't have a valid duration

        # --- Update the recording panel's time display ---
        minutes = int(position // 60)
        seconds = int(position % 60)
        current_time = f"{minutes}:{seconds:02d}"

        total_minutes = int(duration // 60)
        total_seconds = int(duration % 60)
        total_time = f"{total_minutes}:{total_seconds:02d}"

        # Call recording panel's method to update labels
        self.recording_panel.update_time_display(current_time, total_time)

        # --- Update the slider position ---
        # Prevent feedback loop if user is dragging slider
        if not self.recording_panel.time_slider.isSliderDown():
             if duration > 0:
                 # Calculate slider value (assuming range 0-1000)
                 slider_value = int((position / duration) * 1000)
                 # Call recording panel's method to update slider position
                 self.recording_panel.update_slider_position(slider_value)
    
    def on_playback_started(self, filename, duration):
        """Handle playback started signal."""
        self.statusBar().showMessage(f"Playing... Duration: {duration:.1f} seconds")
        
        # Set up the waveform widget with the duration
        self.waveform_widget.set_duration(duration)
        
        # Format and set the duration label in recording panel
        total_minutes = int(duration // 60)
        total_seconds = int(duration % 60)
        total_time = f"{total_minutes}:{total_seconds:02d}"
        
        # Update recording panel
        self.recording_panel.update_time_display("0:00", total_time)
        self.recording_panel.set_playing_state(True)
    
    def on_playback_stopped(self):
        """Handle playback stopped signal."""
        self.statusBar().showMessage("Playback stopped")
        self.recording_panel.set_playing_state(False)
        self.recording_panel.set_paused_state(False)
        # Force UI update
        self.recording_panel.update()

        
    def update_level_meter(self, level):
        """Update the level meter in the status bar."""
        self.level_meter.setValue(int(level * 100))
    
    def on_data_loaded(self, dataframe):
        """Handle data loaded signal."""
        count = len(dataframe) if dataframe is not None else 0
        self.statusBar().showMessage(f"Loaded {count} items")
        
        # Populate combo boxes with unique values from the dataframe
        if dataframe is not None:
            # Update language combo
            if 'language' in dataframe.columns:
                self.language_combo.clear()
                self.language_combo.addItem("Select Language")
                for language in dataframe['language'].unique():
                    if pd.notna(language) and language:  # Check if not NaN and not empty
                        self.language_combo.addItem(str(language))
            
            # Update style combo
            if 'style' in dataframe.columns:
                self.style_combo.clear()
                self.style_combo.addItem("Select Style")
                for style in dataframe['style'].unique():
                    if pd.notna(style) and style:  # Check if not NaN and not empty
                        self.style_combo.addItem(str(style))
            
            # Update speaker combo
            if 'speaker' in dataframe.columns:
                self.speaker_combo.clear()
                self.speaker_combo.addItem("Select Speaker")
                for speaker in dataframe['speaker'].unique():
                    if pd.notna(speaker) and speaker:  # Check if not NaN and not empty
                        self.speaker_combo.addItem(str(speaker))
        
        # Update progress display
        stats = self.data_manager.get_total_stats()
        self.progress_bar.setValue(int(stats['progress_percent']))

    def update_ui_with_item(self, item):
        """Update UI with the current data item."""
        if item is not None and not isinstance(item, bool):
            # Convert to dictionary if it's a pandas Series
            if hasattr(item, 'to_dict'):
                item = item.to_dict()
                
            # Update ID and text fields
            self.text_id.setText(str(item.get('id', '')))
            self.text_sentence.setPlainText(str(item.get('text', '')))

            # Load waveform if audio exists for this item
            audio_path = item.get('audio_path_48k', '')
            if audio_path and os.path.exists(audio_path):
                self.waveform_widget.load_audio_file(audio_path)
                # Also update player's duration display if not playing
                if not self.audio_player.is_playing:
                     # Temporarily load to get duration, then maybe unload or just update display
                     # Simpler: just load into waveform, playback will load again if needed
                     pass

            else:
                # Clear waveform if no audio recorded for this item
                self.waveform_widget.set_audio_data(None, 48000) # Clear display

            # Update language, style, and speaker combo boxes if available in the data
            if 'language' in item and item['language']:
                language = str(item.get('language', ''))
                index = self.language_combo.findText(language, Qt.MatchExactly)
                if index < 0 and language:
                    self.language_combo.addItem(language)
                    index = self.language_combo.findText(language, Qt.MatchExactly)
                if index >= 0:
                    self.language_combo.setCurrentIndex(index)
                    
            if 'style' in item and item['style']:
                style = str(item.get('style', ''))
                index = self.style_combo.findText(style, Qt.MatchExactly)
                if index < 0 and style:
                    self.style_combo.addItem(style)
                    index = self.style_combo.findText(style, Qt.MatchExactly)
                if index >= 0:
                    self.style_combo.setCurrentIndex(index)
                    
            if 'speaker' in item and item['speaker']:
                speaker = str(item.get('speaker', ''))
                index = self.speaker_combo.findText(speaker, Qt.MatchExactly)
                if index < 0 and speaker:
                    self.speaker_combo.addItem(speaker)
                    index = self.speaker_combo.findText(speaker, Qt.MatchExactly)
                if index >= 0:
                    self.speaker_combo.setCurrentIndex(index)

            # Update recorded status indicator
            recorded = item.get('recorded', False)
            self.recording_panel.set_recorded_indicator(recorded)

            # --- Update Upload Status Indicator ---
            uploaded = item.get('uploaded', False)
            self.recording_panel.set_upload_status(uploaded)
            # ---

            # Update status bar message
            status_msg = f"Item {item.get('id', '')}"
            if recorded: status_msg += " recorded."
            if item.get('trimmed', False): status_msg += " (Trimmed)"
            if uploaded: status_msg += " (Uploaded)"
            if not recorded: status_msg = f"Ready to record item {item.get('id', '')}"
            self.statusBar().showMessage(status_msg)

        else:
            # Handle case where item is None (e.g., empty CSV)
            self.text_id.clear()
            self.text_sentence.clear()
            self.waveform_widget.set_audio_data(None, 48000)
            self.recording_panel.set_recorded_indicator(False)
            self.statusBar().showMessage("No data loaded or item selected.")
            self.recording_panel.set_recorded_indicator(False)
            self.recording_panel.set_upload_status(False) # Reset upload status
            self.statusBar().showMessage("No data loaded or item selected.")


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
        settings = QSettings()  # Remove organization/app name
        
        # Load last used directory
        last_dir = settings.value("last_directory", "")
        self.audio_recorder.apply_settings(settings) # Ensure settings are applied
        if last_dir and os.path.exists(last_dir):
            self.data_manager.set_base_directory(last_dir)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save settings before closing
        settings = QSettings()  # Remove organization/app name
        settings.setValue("last_directory", self.data_manager.base_dir)
        
        # Accept the close event
        event.accept()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for efficient recording workflow."""
        if event.key() == Qt.Key_R:
            # R key: Start/stop recording
            if not self.recording_panel.is_recording:
                self.start_recording()
            else:
                self.stop_recording()
        elif event.key() == Qt.Key_Space:
            # Space key: Play/pause audio
            if self.recording_panel.is_playing:
                self.pause_audio()
            else:
                self.play_audio()
        elif event.key() == Qt.Key_Right:
            # Right arrow: Next sentence
            self.next_sentence()
        elif event.key() == Qt.Key_Left:
            # Left arrow: Previous sentence
            self.prev_sentence()
        else:
            super().keyPressEvent(event)

    def test_recording_devices(self):
        """Test all available recording devices."""
        # Create progress dialog
        from PyQt5.QtWidgets import QProgressDialog, QApplication
        
        devices = self.audio_recorder.get_available_devices()
        print(devices)
        if not devices:
            QMessageBox.warning(self, "No Devices", "No recording devices detected.")
            return
            
        progress = QProgressDialog("Testing audio devices...", "Cancel", 0, len(devices), self)
        progress.setWindowTitle("Device Test")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        # Test each device
        working_devices = []
        for i, device in enumerate(devices):
            progress.setValue(i)
            progress.setLabelText(f"Testing: {device['name']}")
            if progress.wasCanceled():
                break
                
            QApplication.processEvents()
            success, message = self.audio_recorder.test_recording_device(device['index'])
            
            if success:
                working_devices.append(device)
            
        progress.setValue(len(devices))
        
        # Update devices with working ones first
        self.device_48k_combo.clear()
        self.device_8k_combo.clear()
        
        # Add working devices first
        for device in working_devices:
            device_text = f"✓ {device['name']}"
            if device['is_asio']:
                device_text += " (ASIO)"
            
            self.device_48k_combo.addItem(device_text, device['index'])
            self.device_8k_combo.addItem(device_text, device['index'])
        
        # Add other devices
        for device in devices:
            if device not in working_devices:
                device_text = f"? {device['name']}"
                if device['is_asio']:
                    device_text += " (ASIO)"
                
                self.device_48k_combo.addItem(device_text, device['index'])
                self.device_8k_combo.addItem(device_text, device['index'])
                
        QMessageBox.information(self, "Device Test Complete", 
                            f"Found {len(working_devices)} working devices out of {len(devices)} detected devices.")
