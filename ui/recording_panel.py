# ui/recording_panel.py
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel,
    QSlider, QStyle, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QIcon, QFont # Added QFont for potential styling

class RecordingPanel(QWidget):
    """
    Panel that contains recording controls including record, play, stop buttons,
    and playback controls like the time slider.
    """
    
    # Define signals for button clicks
    record_button_clicked = pyqtSignal() # Emitted when record/stop recording is pressed
    stop_button_clicked = pyqtSignal()   # Emitted when dedicated stop playback/recording is pressed
    play_button_clicked = pyqtSignal()   # Emitted when play is pressed
    pause_button_clicked = pyqtSignal()  # Emitted when pause is pressed (from play button toggle)
    next_button_clicked = pyqtSignal()
    prev_button_clicked = pyqtSignal()
    trim_button_clicked = pyqtSignal()
    upload_button_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initial state
        self.audio_player = None # This will be set by MainWindow
        self.is_recording = False
        self.is_playing = False
        self.is_paused = False
        self._is_uploaded = False # Internal flag for upload button state
        
        # Set up the UI
        self.setup_ui()
        self.update_button_states() # Set initial button states

    def set_audio_player(self, audio_player):
        """Set the AudioPlayer instance so that the panel can control playback."""
        self.audio_player = audio_player
        # Connect slider release to audio player seek if player is available
        if self.audio_player:
            self.time_slider.sliderReleased.connect(self.on_slider_released)
    
    def setup_ui(self):
        """Create and arrange the UI elements."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Padding around the panel
        layout.setSpacing(10)                     # Spacing between widgets
        
        # Create transport controls (left side: record, stop, play/pause)
        self.create_transport_controls(layout)
        
        # Create playback controls (center: time labels, time slider)
        self.create_playback_controls(layout)
        
        # Create navigation and utility controls (right side: prev, next, trim, upload)
        self.create_navigation_controls(layout)
        
        # Ensure slider has a fixed resolution for calculations
        self.time_slider.setRange(0, 1000) # Represents 0-100% or 1000 discrete steps
        self.time_slider.setValue(0)
        self.time_slider.setTracking(False) # Only emit sliderReleased when mouse button is released
                                           # sliderMoved can be used for live updates if preferred

    def create_transport_controls(self, layout):
        """Create record, stop, play/pause buttons."""
        # Record button (toggles between Record and Stop Recording)
        self.record_button = QPushButton("⏺")  # Unicode record symbol
        self.record_button.setStyleSheet("color: red; font-size: 24px; font-weight: bold;") # Larger, bolder
        self.record_button.setMinimumSize(QSize(48, 48)) # Make button a bit larger
        self.record_button.setToolTip("Start Recording (*)") # Shortcut reflects MainWindow
        self.record_button.clicked.connect(self.on_record_clicked)
        layout.addWidget(self.record_button)
        
        # Stop button (for stopping playback or active recording - can be redundant if record toggles)
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setIconSize(QSize(36, 36)) # Slightly larger icon
        self.stop_button.setMinimumSize(QSize(48, 48))
        self.stop_button.setToolTip("Stop Playback / Recording (Space)") # Shortcut reflects MainWindow
        self.stop_button.clicked.connect(self.on_stop_clicked)
        layout.addWidget(self.stop_button)
        
        # Play/Pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setIconSize(QSize(36, 36)) # Slightly larger icon
        self.play_button.setMinimumSize(QSize(48, 48))
        self.play_button.setToolTip("Play/Pause (Space or P)") # P is usually a direct play, Spacebar is context sensitive
        self.play_button.clicked.connect(self.on_play_pause_clicked)
        layout.addWidget(self.play_button)
    
    def create_playback_controls(self, layout):
        """Create time slider and time display labels."""
        # Current time label
        self.time_label = QLabel("0:00")
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setMinimumWidth(50)
        font = self.time_label.font()
        font.setPointSize(10) # Slightly larger time font
        self.time_label.setFont(font)
        layout.addWidget(self.time_label)
        
        # Time slider
        self.time_slider = QSlider(Qt.Horizontal)
        # Range is set in setup_ui after creation
        self.time_slider.setTracking(False) # Only update on release
        # sliderMoved can be connected if live seeking feedback is desired before release
        # self.time_slider.sliderMoved.connect(self.on_slider_moved_for_preview) 
        self.time_slider.sliderPressed.connect(self.on_slider_pressed)
        # sliderReleased is connected in set_audio_player once audio_player is available
        self.time_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Expand horizontally
        layout.addWidget(self.time_slider, 1)  # Give slider more stretch factor
        
        # Duration label
        self.duration_label = QLabel("0:00")
        self.duration_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.duration_label.setMinimumWidth(50)
        self.duration_label.setFont(font) # Use same font as time_label
        layout.addWidget(self.duration_label)
    
    def create_navigation_controls(self, layout):
        """Create previous, next, trim, and upload buttons."""
        # Previous button
        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.prev_button.setIconSize(QSize(28, 28))
        self.prev_button.setMinimumSize(QSize(40,40))
        self.prev_button.setToolTip("Previous Item (←)")
        self.prev_button.clicked.connect(self.on_prev_clicked)
        layout.addWidget(self.prev_button)
        
        # Next button
        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.setIconSize(QSize(28, 28))
        self.next_button.setMinimumSize(QSize(40,40))
        self.next_button.setToolTip("Next Item (→)")
        self.next_button.clicked.connect(self.on_next_clicked)
        layout.addWidget(self.next_button)
        
        # Spacer to push Trim and Upload further right if desired, or group them
        # layout.addStretch(1) 

        # Trim button
        self.trim_button = QPushButton("Trim")
        self.trim_button.setMinimumSize(QSize(60, 40))
        self.trim_button.setToolTip("Trim Audio (T - if not used by text input)")
        self.trim_button.clicked.connect(self.on_trim_clicked)
        layout.addWidget(self.trim_button)

        # Upload button
        self.upload_button = QPushButton("Upload")
        self.upload_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.upload_button.setMinimumSize(QSize(80, 40))
        self.upload_button.setToolTip("Upload Audio to Server (Ctrl+S)")
        self.upload_button.clicked.connect(self.on_upload_clicked)
        layout.addWidget(self.upload_button)

    # --- Button State Management ---
    def update_button_states(self):
        """Update enabled/disabled state and icons of buttons based on current player/recorder state."""
        # Record button state
        if self.is_recording:
            self.record_button.setText("■")  # Unicode stop symbol for recording
            self.record_button.setStyleSheet("color: red; font-size: 24px; font-weight: bold;")
            self.record_button.setToolTip("Stop Recording (*)")
        else:
            # If not recording, its appearance depends on whether current item is already recorded
            # This is handled by set_recorded_indicator separately.
            # Here we just set the default record symbol if not actively recording.
            self.record_button.setText("⏺") 
            self.record_button.setToolTip("Start Recording (*)")
            # Style is set by set_recorded_indicator

        # Play/Pause button state
        if self.is_playing:
            if self.is_paused:
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.play_button.setToolTip("Resume Playback (Space or P)")
            else:
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.play_button.setToolTip("Pause Playback (Space or P)")
        else: # Not playing
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_button.setToolTip("Play Audio (Space or P)")
        
        # Enable/Disable logic
        can_play_pause_stop = self.audio_player is not None and self.audio_player.current_file is not None
        
        self.play_button.setEnabled(can_play_pause_stop and not self.is_recording)
        self.stop_button.setEnabled((self.is_playing or self.is_recording) and can_play_pause_stop) # Stop makes sense if playing or recording
        self.time_slider.setEnabled(can_play_pause_stop and not self.is_recording)

        # Record button should generally be enabled unless some other app state prevents it
        # (e.g. no output directory initialized - MainWindow handles that with enable_controls)
        
        # Trim and Upload button enabled state depends on whether an item is loaded and recorded.
        # This is partially handled by enable_controls and set_upload_status.
        # For now, assume MainWindow's enable_controls handles the broader context.
        self.upload_button.setEnabled(self.upload_button.isEnabled() and not self._is_uploaded) # Re-check internal flag

        # Force an update of the button's appearance
        self.play_button.update()
        self.record_button.update()


    # --- Slots for External State Changes ---
    @pyqtSlot(bool)
    def set_recording_state(self, is_recording):
        """Slot to update UI based on external recording state changes."""
        self.is_recording = is_recording
        self.update_button_states()
    
    @pyqtSlot(bool)
    def set_playing_state(self, is_playing):
        """Slot to update UI based on external playback state changes."""
        self.is_playing = is_playing
        self.is_paused = False # Reset pause state when play starts/stops
        self.update_button_states()
    
    @pyqtSlot(bool)
    def set_paused_state(self, is_paused):
        """Slot to update UI based on external pause state changes."""
        if self.is_playing: # Pause only makes sense if already playing
            self.is_paused = is_paused
        self.update_button_states()

    @pyqtSlot(bool)
    def set_recorded_indicator(self, is_recorded_for_current_item):
        """
        Updates the record button's appearance to indicate if the current
        item in the main UI has already been recorded.
        This is different from the `is_recording` active state.
        """
        if not self.is_recording: # Only change if not actively recording
            if is_recorded_for_current_item:
                self.record_button.setStyleSheet("color: green; font-size: 24px; font-weight: bold;") # Green for already recorded
                self.record_button.setToolTip("Already Recorded. Re-record? (*)")
            else:
                self.record_button.setStyleSheet("color: red; font-size: 24px; font-weight: bold;") # Red for ready to record
                self.record_button.setToolTip("Start Recording (*)")
        # If self.is_recording is true, update_button_states will handle the "stop recording" appearance.

    @pyqtSlot(bool)
    def set_upload_status(self, is_uploaded):
        """Update the appearance and enabled state of the upload button."""
        self._is_uploaded = is_uploaded
        if is_uploaded:
            self.upload_button.setText("Uploaded")
            self.upload_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton)) # Checkmark icon
            self.upload_button.setToolTip("Recording already uploaded")
            self.upload_button.setEnabled(False) 
        else:
            self.upload_button.setText("Upload")
            self.upload_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
            self.upload_button.setToolTip("Upload Audio to Server (Ctrl+S)")
            # Enablement here depends on global enable_controls state, so MainWindow should manage that.
            # self.upload_button.setEnabled(True) # Let enable_controls handle this
        self.upload_button.update()

    # --- Signal Emitters for Button Clicks ---
    @pyqtSlot()
    def on_record_clicked(self):
        """Handle record button click. Emits record_button_clicked."""
        self.record_button_clicked.emit()
    
    @pyqtSlot()
    def on_stop_clicked(self):
        """Handle stop button click. Emits stop_button_clicked."""
        self.stop_button_clicked.emit()
    
    @pyqtSlot()
    def on_play_pause_clicked(self):
        """
        Handle play/pause button click.
        If playing and not paused, emit pause_button_clicked.
        Otherwise (paused or stopped), emit play_button_clicked.
        MainWindow will determine if it's a resume or a fresh play.
        """
        if self.is_playing and not self.is_paused:
            self.pause_button_clicked.emit()
        else:
            self.play_button_clicked.emit()

    @pyqtSlot()
    def on_prev_clicked(self):
        self.prev_button_clicked.emit()
    
    @pyqtSlot()
    def on_next_clicked(self):
        self.next_button_clicked.emit()
    
    @pyqtSlot()
    def on_trim_clicked(self):
        self.trim_button_clicked.emit()

    @pyqtSlot()
    def on_upload_clicked(self):
        self.upload_button_clicked.emit()

    # --- Slider Interaction ---
    @pyqtSlot()
    def on_slider_pressed(self):
        """Handle time slider press (user starts seeking)."""
        # If audio is playing, we might want to pause it while seeking.
        # Or, allow seeking while playing. For now, just note the press.
        # MainWindow's on_player_position_changed handles UI updates during drag if sliderMoved is used.
        if self.audio_player and self.is_playing and not self.is_paused:
            # self.audio_player.pause() # Optional: pause during drag
            pass # Let sliderReleased handle the final seek.
    
    @pyqtSlot()
    def on_slider_released(self):
        """Handle seek bar release event. Seeks the audio player."""
        if not self.audio_player:
            print("Error: audio_player is not set in RecordingPanel for slider actions.")
            return
        
        slider_value = self.time_slider.value()
        slider_max = self.time_slider.maximum() # Should be 1000
        
        total_duration_seconds = self.audio_player.get_duration()
        
        if total_duration_seconds > 0 and slider_max > 0:
            # Compute the new position in seconds based on slider value
            new_position_seconds = (slider_value / slider_max) * total_duration_seconds
            self.audio_player.seek(new_position_seconds)
            # If playback was paused due to slider press, resume it.
            # This logic depends on whether you pause during drag.
            # if self.audio_player and self.is_playing and self.is_paused: # Example if paused on press
            #     self.audio_player.resume()

    # --- UI Update Slots ---
    @pyqtSlot(str, str)
    def update_time_display(self, current_time_str, total_duration_str):
        """Update the time display labels (e.g., "1:23", "3:45")."""
        self.time_label.setText(current_time_str)
        self.duration_label.setText(total_duration_str)
    
    @pyqtSlot(int)
    def update_slider_position(self, slider_position_value):
        """
        Update the time slider position without triggering signals that cause seeking.
        'slider_position_value' is expected to be in the slider's range (e.g., 0-1000).
        """
        if not self.time_slider.isSliderDown(): # Only update if user is not dragging
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(slider_position_value)
            self.time_slider.blockSignals(False)
    
    @pyqtSlot(int)
    def set_slider_maximum(self, maximum_value):
        """Set the maximum value of the time slider (typically 1000)."""
        self.time_slider.setMaximum(maximum_value)
    
    @pyqtSlot(bool)
    def enable_controls(self, enabled=True):
        """Enable or disable all relevant controls in this panel."""
        self.record_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled) # Stop logic depends on context (playing/recording)
        self.play_button.setEnabled(enabled)
        self.time_slider.setEnabled(enabled)
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.trim_button.setEnabled(enabled)
        # Upload button enablement also depends on its internal _is_uploaded state
        self.upload_button.setEnabled(enabled and not self._is_uploaded)
        
        if not enabled: # If disabling all, ensure specific states are reset visually
            self.is_playing = False
            self.is_paused = False
            self.is_recording = False # This should be handled by MainWindow more globally
        self.update_button_states()


    def keyPressEvent(self, event):
        """
        Handle keyboard shortcuts relevant to this panel.
        MainWindow usually handles global shortcuts like R, Space, Arrows.
        This method might be redundant if MainWindow captures all keys.
        """
        # This is largely superseded by MainWindow's keyPressEvent for global shortcuts.
        # If specific focus-based shortcuts are needed for the panel, they can go here.
        # For now, let MainWindow handle them.
        super().keyPressEvent(event)