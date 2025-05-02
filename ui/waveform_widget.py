# ui/waveform_widget.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSlot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import soundfile as sf

class WaveformWidget(QWidget):
    """Widget that displays audio waveforms and allows for seeking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.audio_player = None  # Reference set by MainWindow
        self.time_slider = None   # Reference set by MainWindow
        self.audio_data = None
        self.sample_rate = 48000
        self.current_position_sec = 0 # Store position in seconds
        self.position_line = None # Initialize position line attribute
        self.duration = 0.0 # Store duration

    def set_time_slider(self, slider):
        self.time_slider = slider

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(5, 2), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.axes = self.figure.add_subplot(111)
        # Remove initial plot setup from here, do it in update_waveform

        # Add the position line here initially, will be updated later
        self.position_line = self.axes.axvline(x=0, color='r', linestyle='-', lw=1) # Keep lw small
        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Amplitude')
        self.axes.set_title('Audio Waveform')
        self.figure.tight_layout()

        # Connect mouse events for seeking
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def set_audio_data(self, audio_data, sample_rate):
        """Set audio data and update the waveform display."""
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        if self.audio_data is not None and self.sample_rate > 0:
            self.duration = len(self.audio_data) / self.sample_rate
        else:
            self.duration = 0.0
        self.current_position_sec = 0 # Reset position
        self.update_waveform()
        self.update_waveform_position_line(0) # Reset line position

    def update_waveform(self):
        """Update the displayed waveform data."""
        self.axes.clear() # Clear previous plot

        if self.audio_data is None or len(self.audio_data) == 0:
            # Optionally plot an empty state or just clear
            self.axes.set_xlim(0, 1) # Default limits if no data
            self.axes.set_ylim(-1, 1)
        else:
            # Calculate time axis
            time = np.arange(len(self.audio_data)) / self.sample_rate

            # Plot waveform
            self.axes.plot(time, self.audio_data, linewidth=0.5, color='blue') # Example color

            # Set axis limits
            max_amplitude = np.max(np.abs(self.audio_data)) if len(self.audio_data) > 0 else 1.0
            y_limit = max(max_amplitude * 1.1, 0.1) # Ensure a minimum visible range
            self.axes.set_ylim(-y_limit, y_limit)
            self.axes.set_xlim(0, self.duration)

        # Re-add the position line (it gets cleared with axes.clear())
        self.position_line = self.axes.axvline(x=self.current_position_sec, color='r', linestyle='-', lw=1)

        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Amplitude')
        self.axes.set_title('Audio Waveform')
        # self.figure.tight_layout() # Be careful with tight_layout on frequent updates

        self.canvas.draw_idle() # Use draw_idle for efficiency

    @pyqtSlot(float)
    def update_waveform_position_line(self, current_time_sec):
        """Efficiently updates only the position line."""
        self.current_position_sec = current_time_sec
        if self.position_line:
            # Update the x-coordinate of the existing line
            self.position_line.set_xdata([current_time_sec, current_time_sec])
            # Request a redraw of the canvas
            self.canvas.draw_idle() # Use draw_idle to avoid excessive redraws

    # Keep the existing on_click and load_audio_file methods
    # Add back the other methods from your original file (e.g., on_click, load_audio_file)

    def on_click(self, event):
        """Handle mouse click for seeking."""
        # Ensure click is within the axes and data exists
        if event.inaxes == self.axes and self.audio_data is not None and self.duration > 0:
            # event.xdata gives the clicked position in data coordinates (seconds)
            clicked_position_sec = event.xdata

            # Clamp the position to be within the valid range [0, duration]
            clicked_position_sec = max(0, min(clicked_position_sec, self.duration))

            # Check if we have an audio_player reference
            if self.audio_player:
                # Seek the audio player to this position
                self.audio_player.seek(clicked_position_sec)
                # Immediately update the line position for visual feedback
                self.update_waveform_position_line(clicked_position_sec)
                # Also update the slider and time labels via the main window's handler
                # This requires the main window's handler to be called too.
                # The main window's on_player_position_changed should handle slider/labels.
                # If seeking while paused, manually update slider/labels:
                if self.audio_player.is_paused or not self.audio_player.is_playing:
                     # Calculate slider value (assuming slider max is 1000)
                     slider_value = int((clicked_position_sec / self.duration) * 1000)
                     if self.time_slider:
                         self.time_slider.setValue(slider_value)
                     # Manually trigger the main window's update if needed
                     # (This depends on how on_player_position_changed is structured)
                     # self.parent().on_player_position_changed(clicked_position_sec, self.duration)

    def load_audio_file(self, file_path):
        """Load audio file and update the waveform display."""
        try:
            audio_data, sample_rate = sf.read(file_path, always_2d=False) # Read as 1D if mono

            # Convert to mono if stereo (take the first channel)
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]

            self.set_audio_data(audio_data, sample_rate)
            # Pass duration info to player if needed (though player calculates its own)
            # self.set_duration(self.duration)
            return True
        except Exception as e:
            print(f"Error loading audio file in WaveformWidget: {str(e)}")
            self.set_audio_data(None, 48000) # Clear display on error
            return False

    # Add set_duration back if external components rely on it,
    # though internal duration calculation is preferred.
    def set_duration(self, duration):
        """Set the duration of the audio in seconds."""
        self.duration = float(duration)
        # Update x-axis limits if necessary
        if self.audio_data is not None:
            self.axes.set_xlim(0, self.duration)
            self.canvas.draw_idle()