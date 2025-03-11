# ui/waveform_widget.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

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
            
            # Emit signal to seek to this position in the audio playback
            self.parent().audio_player.seek(clicked_position)