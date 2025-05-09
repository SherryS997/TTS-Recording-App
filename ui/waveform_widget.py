# ui/waveform_widget.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import soundfile as sf

# Define dark theme colors for the plot
# These can be adjusted to better match your main application's dark theme
DARK_THEME_FIGURE_BG_COLOR = '#2E2E2E'  # Background of the entire figure canvas
DARK_THEME_AXES_BG_COLOR = '#3C3C3C'    # Background of the plotting area
DARK_THEME_TEXT_COLOR = '#E0E0E0'       # Color for title, labels, ticks
DARK_THEME_SPINE_COLOR = '#888888'      # Color for axis lines (spines)
DARK_THEME_WAVEFORM_COLOR = '#569CD6'   # A nice blue for the waveform
DARK_THEME_POSITION_LINE_COLOR = '#D16969' # A reddish color for the position line
DARK_THEME_TICK_COLOR = '#AAAAAA'       # Color for the tick marks themselves

class WaveformWidget(QWidget):
    """Widget that displays audio waveforms and allows for seeking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_player = None  # Reference set by MainWindow
        self.time_slider = None   # Reference set by MainWindow
        self.audio_data = None
        self.sample_rate = 48000
        self.current_position_sec = 0 # Store position in seconds
        self.position_line = None 
        self.duration = 0.0

        self.setup_ui() # setup_ui will now apply initial dark theme settings

    def set_time_slider(self, slider):
        self.time_slider = slider

    def _apply_dark_theme_to_axes(self, axes):
        """Helper function to apply dark theme styles to a Matplotlib Axes object."""
        axes.set_facecolor(DARK_THEME_AXES_BG_COLOR)

        # Style spines (the bounding box lines)
        for spine_pos in ['top', 'right', 'bottom', 'left']:
            axes.spines[spine_pos].set_color(DARK_THEME_SPINE_COLOR)

        # Style ticks (the marks and their labels)
        axes.tick_params(axis='x', colors=DARK_THEME_TICK_COLOR, labelcolor=DARK_THEME_TEXT_COLOR)
        axes.tick_params(axis='y', colors=DARK_THEME_TICK_COLOR, labelcolor=DARK_THEME_TEXT_COLOR)

        # Style labels and title
        axes.xaxis.label.set_color(DARK_THEME_TEXT_COLOR)
        axes.yaxis.label.set_color(DARK_THEME_TEXT_COLOR)
        axes.title.set_color(DARK_THEME_TEXT_COLOR)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(5, 2), dpi=100)
        self.figure.patch.set_facecolor(DARK_THEME_FIGURE_BG_COLOR) # Dark background for the figure

        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.axes = self.figure.add_subplot(111)
        self._apply_dark_theme_to_axes(self.axes) # Apply dark theme styles

        # Set labels (color will be handled by _apply_dark_theme_to_axes)
        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Amplitude')
        self.axes.set_title('Audio Waveform')
        
        # Initialize position line with dark theme color
        self.position_line = self.axes.axvline(x=0, color=DARK_THEME_POSITION_LINE_COLOR, linestyle='-', lw=1.5)
        
        try:
            self.figure.tight_layout() # Adjust plot to prevent labels from being cut off
        except Exception:
            # tight_layout can sometimes fail, especially with frequent updates or specific backends
            print("Warning: tight_layout failed in WaveformWidget setup.")


        # Connect mouse events for seeking
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def set_audio_data(self, audio_data, sample_rate):
        """Set audio data and update the waveform display."""
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        if self.audio_data is not None and self.sample_rate > 0:
            self.duration = len(self.audio_data) / float(self.sample_rate) # Ensure float division
        else:
            self.duration = 0.0
        self.current_position_sec = 0 # Reset position
        self.update_waveform() # This will redraw the waveform
        # Position line is updated via update_waveform or update_waveform_position_line

    def update_waveform(self):
        """Update the displayed waveform data, applying dark theme."""
        self.axes.clear() # Clear previous plot contents

        # Re-apply dark theme styling after clearing
        self._apply_dark_theme_to_axes(self.axes)
        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Amplitude')
        self.axes.set_title('Audio Waveform')

        if self.audio_data is None or len(self.audio_data) == 0:
            self.axes.set_xlim(0, 1) 
            self.axes.set_ylim(-1, 1)
            # Re-add the position line even if no data, at position 0
            self.position_line = self.axes.axvline(x=0, color=DARK_THEME_POSITION_LINE_COLOR, linestyle='-', lw=1.5)
        else:
            time_axis = np.arange(len(self.audio_data)) / float(self.sample_rate)

            # Plot waveform with dark theme color
            self.axes.plot(time_axis, self.audio_data, linewidth=0.7, color=DARK_THEME_WAVEFORM_COLOR)

            max_amplitude = np.max(np.abs(self.audio_data)) if len(self.audio_data) > 0 else 1.0
            y_limit = max(max_amplitude * 1.1, 0.1) 
            self.axes.set_ylim(-y_limit, y_limit)
            self.axes.set_xlim(0, self.duration)

            # Re-add the position line (it gets cleared with axes.clear())
            # Ensure it's drawn on top if multiple lines exist
            self.position_line = self.axes.axvline(x=self.current_position_sec, color=DARK_THEME_POSITION_LINE_COLOR, linestyle='-', lw=1.5, zorder=10)

        try:
            self.figure.tight_layout()
        except Exception:
            print("Warning: tight_layout failed in WaveformWidget update.")
            
        self.canvas.draw_idle()

    @pyqtSlot(float)
    def update_waveform_position_line(self, current_time_sec):
        """Efficiently updates only the position line."""
        self.current_position_sec = current_time_sec
        if self.position_line:
            self.position_line.set_xdata([current_time_sec, current_time_sec])
            self.canvas.draw_idle()

    def on_click(self, event):
        """Handle mouse click for seeking."""
        if event.inaxes == self.axes and self.audio_data is not None and self.duration > 0:
            clicked_position_sec = event.xdata
            clicked_position_sec = max(0, min(clicked_position_sec, self.duration))

            if self.audio_player:
                self.audio_player.seek(clicked_position_sec)
                # The player's position_changed signal will trigger updates for line, slider, labels
                # However, if not playing, manually trigger an update for immediate feedback
                if not self.audio_player.is_currently_playing():
                    self.update_waveform_position_line(clicked_position_sec)
                    if self.time_slider:
                        slider_max = self.time_slider.maximum()
                        if self.duration > 0 and slider_max > 0:
                            slider_value = int((clicked_position_sec / self.duration) * slider_max)
                            # Temporarily block signals if direct setValue on slider causes issues
                            self.time_slider.blockSignals(True)
                            self.time_slider.setValue(slider_value)
                            self.time_slider.blockSignals(False)
                    # If MainWindow needs to update its labels too:
                    if hasattr(self.parent(), 'on_player_position_changed'):
                         self.parent().on_player_position_changed(clicked_position_sec, self.duration)


    def load_audio_file(self, file_path):
        """Load audio file and update the waveform display."""
        try:
            audio_data, sample_rate = sf.read(file_path, always_2d=False) 

            if audio_data.ndim > 1: # Convert to mono
                audio_data = audio_data[:, 0]
            
            # Normalize if integer type for consistent plotting amplitude if desired,
            # or let matplotlib handle it. For waveform display, raw values are usually fine.
            # If int16, values are large. Matplotlib scales y-axis.
            # If float, usually in [-1, 1].
            # Let's assume for now that soundfile gives float data in a reasonable range,
            # or that the y-axis scaling is sufficient for int data.

            self.set_audio_data(audio_data, sample_rate)
            return True
        except Exception as e:
            print(f"Error loading audio file in WaveformWidget: {str(e)}")
            self.set_audio_data(None, 48000) # Clear display on error
            return False

    def set_duration(self, duration_sec):
        """
        Set the duration of the audio in seconds.
        This is mainly used to update the x-axis limit if audio_data is not yet fully processed
        or if duration is known from an external source before data is loaded.
        """
        self.duration = float(duration_sec)
        if self.axes: # Ensure axes exist
            self.axes.set_xlim(0, self.duration if self.duration > 0 else 1)
            self.canvas.draw_idle()