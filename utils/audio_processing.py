import os
import numpy as np
import wave
from pydub import AudioSegment
import librosa
from PyQt5.QtCore import QObject, pyqtSignal

class AudioProcessor(QObject):
    """
    Handles audio processing tasks such as trimming silence, 
    normalizing volume, and sample rate conversion.
    """
    
    # Define signals
    processing_started = pyqtSignal(str)
    processing_finished = pyqtSignal(str)
    progress_updated = pyqtSignal(int)  # 0-100 progress percentage
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Default parameters
        self.silence_threshold = 0.03  # Threshold for silence detection (0.0-1.0)
        self.padding_ms = 100  # Padding around detected audio (milliseconds)
        self.target_loudness = -18.0  # Target loudness in dBFS
    
    def set_silence_threshold(self, threshold):
        """Set threshold for silence detection (0.0-1.0)."""
        self.silence_threshold = max(0.0, min(threshold, 1.0))
    
    def set_padding(self, padding_ms):
        """Set padding around detected audio in milliseconds."""
        self.padding_ms = max(0, padding_ms)
    
    def set_target_loudness(self, loudness_dbfs):
        """Set target loudness for normalization in dBFS."""
        self.target_loudness = loudness_dbfs
    
    def trim_silence(self, input_file, output_file=None):
        """
        Trim silence from the beginning and end of an audio file.
        
        Args:
            input_file (str): Path to input audio file
            output_file (str, optional): Path to save trimmed audio.
                                        If None, overwrites the input file.
        
        Returns:
            tuple: (success, duration_seconds)
        """
        if not output_file:
            output_file = input_file
        
        try:
            self.processing_started.emit("Trimming silence")
            
            # Load audio file
            y, sr = librosa.load(input_file, sr=None, mono=True)
            
            # Calculate amplitude and normalize to 0.0-1.0
            amplitude = np.abs(y)
            max_amp = np.max(amplitude)
            if max_amp > 0:
                amplitude = amplitude / max_amp
            
            # Find where audio exceeds threshold
            non_silent = amplitude > self.silence_threshold
            
            # If no non-silent parts found, return original audio
            if not np.any(non_silent):
                self.processing_finished.emit("No audio found above threshold")
                return False, librosa.get_duration(y=y, sr=sr)
            
            # Find start and end indices
            start_idx = np.where(non_silent)[0][0]
            end_idx = np.where(non_silent)[0][-1]
            
            # Add padding (convert ms to samples)
            padding_samples = int(self.padding_ms * sr / 1000)
            start_idx = max(0, start_idx - padding_samples)
            end_idx = min(len(y), end_idx + padding_samples)
            
            # Extract the non-silent part
            y_trimmed = y[start_idx:end_idx+1]
            
            # Save trimmed audio
            self._save_audio(y_trimmed, sr, output_file)
            
            duration = librosa.get_duration(y=y_trimmed, sr=sr)
            self.processing_finished.emit("Trimming complete")
            return True, duration
            
        except Exception as e:
            self.error_occurred.emit(f"Error trimming audio: {str(e)}")
            return False, 0
    
    def normalize_volume(self, input_file, output_file=None):
        """
        Normalize the volume of an audio file to target loudness.
        
        Args:
            input_file (str): Path to input audio file
            output_file (str, optional): Path to save normalized audio.
                                        If None, overwrites the input file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not output_file:
            output_file = input_file
        
        try:
            self.processing_started.emit("Normalizing volume")
            
            # Load audio
            audio = AudioSegment.from_file(input_file)
            
            # Calculate current loudness
            current_loudness = audio.dBFS
            
            # Calculate gain needed
            gain = self.target_loudness - current_loudness
            
            # Apply gain
            normalized_audio = audio.apply_gain(gain)
            
            # Export normalized audio
            normalized_audio.export(output_file, format="wav")
            
            self.processing_finished.emit("Normalization complete")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error normalizing audio: {str(e)}")
            return False
    
    def convert_sample_rate(self, input_file, output_file, target_sr):
        """
        Convert audio file to a different sample rate.
        
        Args:
            input_file (str): Path to input audio file
            output_file (str): Path to save converted audio
            target_sr (int): Target sample rate (e.g., 8000, 16000, 44100, 48000)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.processing_started.emit(f"Converting to {target_sr}Hz")
            
            # Load audio with original sample rate
            y, sr = librosa.load(input_file, sr=None)
            
            # Resample if needed
            if sr != target_sr:
                y_resampled = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
            else:
                y_resampled = y
            
            # Save resampled audio
            self._save_audio(y_resampled, target_sr, output_file)
            
            self.processing_finished.emit("Conversion complete")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error converting sample rate: {str(e)}")
            return False
    
    def manual_trim(self, input_file, output_file, start_sec, end_sec):
        """
        Manually trim audio file to specified start and end times.
        
        Args:
            input_file (str): Path to input audio file
            output_file (str): Path to save trimmed audio
            start_sec (float): Start time in seconds
            end_sec (float): End time in seconds
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.processing_started.emit("Manual trimming")
            
            # Load audio
            y, sr = librosa.load(input_file, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Validate trim points
            if start_sec < 0:
                start_sec = 0
            if end_sec > duration:
                end_sec = duration
            if start_sec >= end_sec:
                self.error_occurred.emit("Invalid trim points")
                return False
            
            # Convert seconds to samples
            start_sample = int(start_sec * sr)
            end_sample = int(end_sec * sr)
            
            # Trim audio
            y_trimmed = y[start_sample:end_sample]
            
            # Save trimmed audio
            self._save_audio(y_trimmed, sr, output_file)
            
            self.processing_finished.emit("Manual trimming complete")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error during manual trimming: {str(e)}")
            return False
    
    def _save_audio(self, y, sr, output_file):
        """
        Save audio data to file with appropriate format.
        
        Args:
            y (ndarray): Audio data
            sr (int): Sample rate
            output_file (str): Output file path
        """
        # Ensure float64 format for librosa.output.write_wav
        if y.dtype != np.float64:
            y = y.astype(np.float64)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Save as WAV
        librosa.output.write_wav(output_file, y, sr)