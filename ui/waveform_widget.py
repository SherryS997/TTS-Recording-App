# ui/waveform_widget.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import soundfile as sf

class WaveformWidget(QWidget):
    """Widget that displays audio waveforms and allows for seeking."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.audio_data = None
        self.sample_rate = 48000
        self.current_position = 0
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.axes = self.figure.add_subplot(111)
        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Amplitude')
        self.axes.set_title('Audio Waveform')
        self.figure.tight_layout()
        
        # Line to show current position
        self.position_line = None
        
        # Connect mouse events for seeking
        self.canvas.mpl_connect('button_press_event', self.on_click)
        
    def set_audio_data(self, audio_data, sample_rate):
        """Set audio data and update the waveform display."""
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.update_waveform()
    
    def update_waveform(self):
        """Update the displayed waveform."""
        if self.audio_data is None:
            return
            
        self.axes.clear()
        
        # Calculate time axis
        time = np.arange(0, len(self.audio_data)) / self.sample_rate
        
        # Plot waveform
        self.axes.plot(time, self.audio_data, linewidth=0.5)
        
        # Set axis limits
        max_amplitude = np.max(np.abs(self.audio_data)) * 1.1
        self.axes.set_ylim(-max_amplitude, max_amplitude)
        self.axes.set_xlim(0, len(self.audio_data) / self.sample_rate)
        
        # Add position line
        if self.position_line:
            self.position_line.remove()
        self.position_line = self.axes.axvline(x=self.current_position, color='r', linestyle='-')
        
        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Amplitude')
        self.axes.set_title('Audio Waveform')
        self.figure.tight_layout()
        
        self.canvas.draw()
        
    @pyqtSlot(float)
    def update_position(self, position):
        """Update the current position indicator."""
        self.current_position = position
        
        if self.position_line and self.audio_data is not None:
            self.position_line.set_xdata(position)
            self.canvas.draw_idle()  # More efficient than full redraw
    
    def on_click(self, event):
        """Handle mouse click for seeking."""
        if event.inaxes == self.axes and self.audio_data is not None:
            # Calculate position in seconds
            clicked_position = event.xdata
            
            # Check if we have an audio_player reference
            if hasattr(self, 'audio_player') and self.audio_player:
                # Seek to this position in the audio playback
                self.audio_player.seek(clicked_position)

    def load_audio_file(self, file_path):
        """Load audio file and update the waveform display."""
        try:
            import soundfile as sf
            
            # Load the audio file
            audio_data, sample_rate = sf.read(file_path)
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = audio_data[:, 0]
                
            self.set_audio_data(audio_data, sample_rate)
            return True
        except Exception as e:
            print(f"Error loading audio file: {str(e)}")
            return False

    def set_duration(self, duration):
        """Set the duration of the audio in seconds."""
        self.duration = float(duration)
        
        # If you need to update the display based on duration
        # For example, update the x-axis limits
        if hasattr(self, 'axes') and self.audio_data is not None:
            self.axes.set_xlim(0, self.duration)
            self.canvas.draw_idle()
