from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QProgressBar,
    QSlider, QStyle, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QIcon, QFont

class RecordingPanel(QWidget):
    """
    Panel that contains recording controls including record, play, stop buttons,
    and playback controls like the time slider and volume control.
    """
    
    # Define signals for button clicks
    record_button_clicked = pyqtSignal()
    stop_button_clicked = pyqtSignal()
    play_button_clicked = pyqtSignal()
    pause_button_clicked = pyqtSignal()
    next_button_clicked = pyqtSignal()
    prev_button_clicked = pyqtSignal()
    trim_button_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initial state
        self.is_recording = False
        self.is_playing = False
        self.is_paused = False
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Create and arrange the UI elements."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create transport controls (left side)
        self.create_transport_controls(layout)
        
        # Create playback controls (center)
        self.create_playback_controls(layout)
        
        # Create navigation and utility controls (right side)
        self.create_navigation_controls(layout)
        
        # Set initial button states
        self.update_button_states()
    
    def create_transport_controls(self, layout):
        """Create record, stop, play buttons."""
        # Record button
        self.record_button = QPushButton("⏺")  # Unicode record symbol
        self.record_button.setStyleSheet("color: red; font-size: 20px;")
        self.record_button.setMinimumSize(QSize(40, 40))
        self.record_button.setToolTip("Start Recording (R)")
        self.record_button.clicked.connect(self.on_record_clicked)
        layout.addWidget(self.record_button)
        
        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setIconSize(QSize(32, 32))
        self.stop_button.setToolTip("Stop (Space)")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        layout.addWidget(self.stop_button)
        
        # Play/Pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setIconSize(QSize(32, 32))
        self.play_button.setToolTip("Play (P)")
        self.play_button.clicked.connect(self.on_play_clicked)
        layout.addWidget(self.play_button)
    
    def create_playback_controls(self, layout):
        """Create time slider and labels."""
        # Current time label
        self.time_label = QLabel("0:00")
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setMinimumWidth(50)
        layout.addWidget(self.time_label)
        
        # Time slider
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 1000)
        self.time_slider.setValue(0)
        self.time_slider.setTracking(False)  # Only update on release
        self.time_slider.valueChanged.connect(self.on_slider_value_changed)
        self.time_slider.sliderPressed.connect(self.on_slider_pressed)
        self.time_slider.sliderReleased.connect(self.on_slider_released)
        self.time_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.time_slider, 1)  # Give slider more space
        
        # Duration label
        self.duration_label = QLabel("0:00")
        self.duration_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.duration_label.setMinimumWidth(50)
        layout.addWidget(self.duration_label)
    
    def create_navigation_controls(self, layout):
        """Create previous, next, and trim buttons."""
        # Previous button
        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.prev_button.setIconSize(QSize(24, 24))
        self.prev_button.setToolTip("Previous (←)")
        self.prev_button.clicked.connect(self.on_prev_clicked)
        layout.addWidget(self.prev_button)
        
        # Next button
        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.setIconSize(QSize(24, 24))
        self.next_button.setToolTip("Next (→)")
        self.next_button.clicked.connect(self.on_next_clicked)
        layout.addWidget(self.next_button)
        
        # Trim button
        self.trim_button = QPushButton("Trim")
        self.trim_button.setToolTip("Trim Audio (T)")
        self.trim_button.clicked.connect(self.on_trim_clicked)
        layout.addWidget(self.trim_button)
    
    def update_button_states(self):
        """Update button states based on current application state."""
        # Update record button
        if self.is_recording:
            # Use text instead of icon since SP_MediaRecord doesn't exist
            self.record_button.setText("■")  # Unicode stop symbol
            self.record_button.setStyleSheet("color: red; font-size: 20px;")
            self.record_button.setToolTip("Stop Recording (R)")
            self.play_button.setEnabled(False)
            self.time_slider.setEnabled(False)
        else:
            self.record_button.setText("⏺")  # Unicode record symbol 
            self.record_button.setStyleSheet("color: red; font-size: 20px;")
            self.record_button.setToolTip("Start Recording (R)")
            self.play_button.setEnabled(True)
            self.time_slider.setEnabled(True)
        
        # Update play button
        if self.is_playing:
            if self.is_paused:
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.play_button.setToolTip("Resume (P)")
            else:
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.play_button.setToolTip("Pause (P)")
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_button.setToolTip("Play (P)")
    
    @pyqtSlot()
    def on_record_clicked(self):
        """Handle record button click."""
        self.record_button_clicked.emit()
    
    @pyqtSlot()
    def on_stop_clicked(self):
        """Handle stop button click."""
        self.stop_button_clicked.emit()
    
    @pyqtSlot()
    def on_play_clicked(self):
        """Handle play/pause button click."""
        if self.is_playing and not self.is_paused:
            self.pause_button_clicked.emit()
        else:
            self.play_button_clicked.emit()
    
    @pyqtSlot()
    def on_prev_clicked(self):
        """Handle previous button click."""
        self.prev_button_clicked.emit()
    
    @pyqtSlot()
    def on_next_clicked(self):
        """Handle next button click."""
        self.next_button_clicked.emit()
    
    @pyqtSlot()
    def on_trim_clicked(self):
        """Handle trim button click."""
        self.trim_button_clicked.emit()
    
    @pyqtSlot(int)
    def on_slider_value_changed(self, value):
        """Handle time slider value change."""
        # This will be connected to an external handler
        pass
    
    @pyqtSlot()
    def on_slider_pressed(self):
        """Handle time slider press (user starts seeking)."""
        # This will be connected to an external handler
        pass
    
    @pyqtSlot()
    def on_slider_released(self):
        """Handle time slider release (seek completed)."""
        # This will be connected to an external handler
        pass
    
    @pyqtSlot(bool)
    def set_recording_state(self, is_recording):
        """Update UI to reflect recording state."""
        self.is_recording = is_recording
        self.update_button_states()
    
    @pyqtSlot(bool)
    def set_playing_state(self, is_playing):
        """Update UI to reflect playback state."""
        self.is_playing = is_playing
        self.update_button_states()
    
    @pyqtSlot(bool)
    def set_paused_state(self, is_paused):
        """Update UI to reflect pause state."""
        self.is_paused = is_paused
        self.update_button_states()
    
    @pyqtSlot(str, str)
    def update_time_display(self, current_time, total_duration):
        """Update the time display labels."""
        self.time_label.setText(current_time)
        self.duration_label.setText(total_duration)
    
    @pyqtSlot(int)
    def update_slider_position(self, position):
        """Update the time slider position without triggering the valueChanged signal."""
        self.time_slider.blockSignals(True)
        self.time_slider.setValue(position)
        self.time_slider.blockSignals(False)
    
    @pyqtSlot(int)
    def set_slider_maximum(self, maximum):
        """Set the maximum value of the time slider."""
        self.time_slider.setMaximum(maximum)
    
    @pyqtSlot(bool)
    def enable_controls(self, enabled=True):
        """Enable or disable all controls."""
        self.record_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.play_button.setEnabled(enabled)
        self.time_slider.setEnabled(enabled)
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.trim_button.setEnabled(enabled)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_R:
            self.on_record_clicked()
        elif event.key() == Qt.Key_Space:
            self.on_stop_clicked()
        elif event.key() == Qt.Key_P:
            self.on_play_clicked()
        elif event.key() == Qt.Key_Left:
            self.on_prev_clicked()
        elif event.key() == Qt.Key_Right:
            self.on_next_clicked()
        elif event.key() == Qt.Key_T:
            self.on_trim_clicked()
        else:
            super().keyPressEvent(event)