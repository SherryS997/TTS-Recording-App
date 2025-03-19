import os
import wave
import time
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from PyQt5.QtMultimedia import QAudioOutput, QAudioFormat, QAudioDeviceInfo, QAudio
import sounddevice as sd

class AudioPlayer(QObject):
    """
    Handles audio playback with seeking capabilities and playback visualization support.
    Emits signals for UI components to respond to playback events.
    """
    
    # Define signals
    playback_started = pyqtSignal(str, float)  # Signal emitted when playback starts (with filename)
    playback_stopped = pyqtSignal()     # Signal emitted when playback stops
    playback_paused = pyqtSignal()      # Signal emitted when playback is paused
    playback_resumed = pyqtSignal()     # Signal emitted when playback is resumed
    position_changed = pyqtSignal(float)  # Signal emitted when playback position changes (in seconds)
    duration_changed = pyqtSignal(float)  # Signal emitted when a new file with different duration is loaded
    error_occurred = pyqtSignal(str)    # Signal emitted when an error occurs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Player state
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0     # Current position in seconds
        self.duration = 0.0             # Duration of current audio in seconds
        self.current_file = None        # Path to currently loaded audio file
        self.sample_rate = 48000        # Default sample rate
        self.playback_thread = None     # Thread for playback
        
        # Audio data
        self.audio_data = None          # NumPy array of audio samples
        self.audio_data_8k = None       # 8kHz version for comparison
        
        # Position tracking timer
        self.position_timer = QTimer()
        self.position_timer.setInterval(50)  # Update position 20 times per second
        self.position_timer.timeout.connect(self._update_position)
        
        # For seeking
        self.seek_position = None
        
    def load_audio_file(self, file_path, secondary_file_path=None):
        """
        Load an audio file for playback.
        Optionally load a secondary file (e.g., 8kHz version for comparison)
        
        Args:
            file_path (str): Path to the primary audio file (typically 48kHz)
            secondary_file_path (str, optional): Path to secondary file (8kHz)
            
        Returns:
            bool: True if successful, False if an error occurred
        """
        try:
            if not os.path.exists(file_path):
                self.error_occurred.emit(f"File not found: {file_path}")
                return False
                
            # Load the audio file using wave
            with wave.open(file_path, 'rb') as wf:
                self.sample_rate = wf.getframerate()
                self.channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                
                # Read all frames and convert to numpy array
                raw_data = wf.readframes(wf.getnframes())
                
                # Convert to numpy array based on sample width
                if sample_width == 2:  # 16-bit audio
                    data = np.frombuffer(raw_data, dtype=np.int16)
                elif sample_width == 4:  # 32-bit audio
                    data = np.frombuffer(raw_data, dtype=np.int32)
                else:
                    data = np.frombuffer(raw_data, dtype=np.uint8)
                    
                # Reshape if stereo
                if self.channels == 2:
                    data = data.reshape(-1, 2)
            
            # Store audio data
            self.audio_data = data
            self.current_file = file_path
            self.duration = len(data) / self.sample_rate
            self.current_position = 0.0
            
            # Load secondary file if provided
            if secondary_file_path and os.path.exists(secondary_file_path):
                with wave.open(secondary_file_path, 'rb') as wf:
                    secondary_rate = wf.getframerate()
                    secondary_raw_data = wf.readframes(wf.getnframes())
                    secondary_data = np.frombuffer(secondary_raw_data, dtype=np.int16)
                    self.audio_data_8k = secondary_data
            
            # Emit signal with new duration
            self.duration_changed.emit(self.duration)
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error loading audio file: {str(e)}")
            return False
    
    @pyqtSlot(str)
    def play(self, file_path=None):
        """Start or resume playback of an audio file."""
        if file_path and file_path != self.current_file:
            # Load a new file
            if not self.load_audio_file(file_path):
                return False
        
        if self.audio_data is None:
            self.error_occurred.emit("No audio file loaded")
            return False
            
        if self.is_paused:
            return self.resume()
            
        if self.is_playing:
            return True
        
        # Start playback in a separate thread
        self.is_playing = True
        self.is_paused = False
        
        # Create and start playback thread
        self.playback_thread = QThread()
        self.moveToThread(self.playback_thread)
        self.playback_thread.started.connect(self._playback_worker)
        self.playback_thread.start()
        
        # Start position update timer
        self.position_timer.start()
        
        # Emit signal
        self.playback_started.emit(os.path.basename(self.current_file), self.duration)

        return True
    
    def is_currently_playing(self):
        """Check if audio is currently playing."""
        return self.is_playing and not self.is_paused
    
    @pyqtSlot()
    def stop(self):
        """Stop playback."""
        if not self.is_playing:
            return
            
        self.is_playing = False
        self.is_paused = False
        
        # Stop position timer
        self.position_timer.stop()
        
        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.isRunning():
            self.playback_thread.quit()
            self.playback_thread.wait()
        
        # Reset position
        self.current_position = 0.0
        self.position_changed.emit(self.current_position)
        
        # Emit signal
        self.playback_stopped.emit()
    
    @pyqtSlot()
    def pause(self):
        """Pause playback."""
        if not self.is_playing or self.is_paused:
            return
            
        self.is_paused = True
        
        # Emit signal
        self.playback_paused.emit()
    
    @pyqtSlot()
    def resume(self):
        """Resume playback after pause."""
        if not self.is_playing or not self.is_paused:
            return
            
        self.is_paused = False
        
        # Emit signal
        self.playback_resumed.emit()
    
    @pyqtSlot(float)
    def seek(self, position_seconds):
        """
        Seek to a specific position in the audio file.
        
        Args:
            position_seconds (float): Position to seek to in seconds
        """
        if self.audio_data is None:
            return
            
        # Clamp position between 0 and duration
        position_seconds = max(0, min(position_seconds, self.duration))
        
        if self.is_playing and not self.is_paused:
            # If playing, set seek position and let playback loop handle it
            self.seek_position = position_seconds
        else:
            # If not playing, just update position
            self.current_position = position_seconds
            self.position_changed.emit(position_seconds)
    
    def get_position(self):
        """Get current playback position in seconds."""
        return self.current_position
    
    def get_duration(self):
        """Get audio duration in seconds."""
        return self.duration
    
    def _playback_worker(self):
        """Worker method for audio playback thread."""
        try:
            # Calculate start position in samples
            start_sample = int(self.current_position * self.sample_rate)
            
            # Create an output stream
            stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16'
            )
            
            with stream:
                # Buffer size for each chunk (100ms)
                buffer_size = int(self.sample_rate * 0.1)
                
                # Play audio in chunks
                current_sample = start_sample
                
                while self.is_playing and current_sample < len(self.audio_data):
                    # Check for seek request
                    if self.seek_position is not None:
                        current_sample = int(self.seek_position * self.sample_rate)
                        self.seek_position = None
                    
                    # Check if paused
                    if self.is_paused:
                        time.sleep(0.1)
                        continue
                    
                    # Calculate end of chunk
                    end_sample = min(current_sample + buffer_size, len(self.audio_data))
                    
                    # Get audio chunk
                    if self.channels == 1:
                        chunk = self.audio_data[current_sample:end_sample]
                    else:
                        chunk = self.audio_data[current_sample:end_sample, :]
                    
                    # Write to output stream
                    stream.write(chunk)
                    
                    # Update position
                    current_sample = end_sample
                    self.current_position = current_sample / self.sample_rate
                    
                # Playback finished
                if current_sample >= len(self.audio_data) and self.is_playing:
                    self.is_playing = False
                    self.current_position = 0.0
                    self.position_timer.stop()
                    self.playback_stopped.emit()
                    
        except Exception as e:
            self.is_playing = False
            self.error_occurred.emit(f"Playback error: {str(e)}")
            self.playback_stopped.emit()
    
    def _update_position(self):
        """Update position timer callback."""
        if self.is_playing and not self.is_paused:
            self.position_changed.emit(self.current_position)
    
    def get_audio_data(self):
        """
        Get the audio data as numpy array for visualization.
        
        Returns:
            tuple: (audio_data, sample_rate) or (None, None) if no data loaded
        """
        if self.audio_data is None:
            return None, None
        return self.audio_data, self.sample_rate
    
    def toggle_sample_rate(self):
        """Toggle between 48kHz and 8kHz for A/B comparison."""
        if self.audio_data_8k is not None and self.is_playing:
            # Stop current playback
            self.stop()
            
            # Toggle between high and low sample rate
            if self.sample_rate == 48000 and self.audio_data_8k is not None:
                # Switch to 8kHz
                temp = self.audio_data
                self.audio_data = self.audio_data_8k
                self.audio_data_8k = temp
                self.sample_rate = 8000
            else:
                # Switch back to 48kHz
                temp = self.audio_data
                self.audio_data = self.audio_data_8k
                self.audio_data_8k = temp
                self.sample_rate = 48000
                
            # Restart playback
            self.play()
    
    def cleanup(self):
        """Clean up resources before destruction."""
        self.stop()
        self.position_timer.stop()