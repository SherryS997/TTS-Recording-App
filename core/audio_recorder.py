# core/audio_recorder.py
import os
import time
import wave
import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from pydub import AudioSegment

class AudioRecorder(QObject):
    """Handles audio recording with support for multiple sample rates and ASIO."""
    
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(float)
    level_meter = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.recording_thread = None
        self.frames_48k = []
        self.frames_8k = []
        self.device_48k = None
        self.device_8k = None
        self.format = 'int16'
        self.channels = 1
        self.rate_48k = 48000
        self.rate_8k = 8000
        self.chunk_size = 1024
    
    def get_available_devices(self, include_asio=True):
        """Returns a list of available audio devices, including ASIO if specified."""
        devices = []
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                # Only include input devices
                if device['max_input_channels'] > 0:
                    # Include ASIO devices if specified
                    if include_asio or 'ASIO' not in device['name']:
                        devices.append({
                            'index': i,
                            'name': device['name'],
                            'channels': device['max_input_channels'],
                            'sample_rates': device.get('default_samplerate', 48000),
                            'is_asio': 'ASIO' in device['name']
                        })
        except Exception as e:
            self.error_occurred.emit(f"Failed to get audio devices: {str(e)}")
        
        return devices
    
    @pyqtSlot(int, int, str, str)
    def start_recording(self, device_48k_idx, device_8k_idx, filename_48k=None, filename_8k=None):
        """Start recording audio at two sample rates simultaneously."""
        if self.is_recording:
            return
            
        self.device_48k = device_48k_idx
        self.device_8k = device_8k_idx
        self.frames_48k = []
        self.frames_8k = []
        self.filename_48k = filename_48k
        self.filename_8k = filename_8k
        
        # Start recording in a separate thread
        self.is_recording = True
        self.recording_thread = QThread()
        self.moveToThread(self.recording_thread)
        self.recording_thread.started.connect(self._record_audio)
        self.recording_thread.start()
        self.recording_started.emit()
    
    @pyqtSlot()
    def stop_recording(self):
        """Stop the recording process and save the files."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.quit()
            self.recording_thread.wait()
        
        # Save the recordings if filenames were provided
        duration = 0
        if hasattr(self, 'filename_48k') and self.filename_48k:
            duration = self._save_wav(self.filename_48k, self.frames_48k, self.rate_48k)
        
        if hasattr(self, 'filename_8k') and self.filename_8k:
            self._save_wav(self.filename_8k, self.frames_8k, self.rate_8k)
        
        self.recording_stopped.emit(duration)
    
    def _record_audio(self):
        """Internal method that performs the actual recording.
        This runs in a separate thread."""
        try:
            # Create streams for both sample rates
            stream_48k = sd.InputStream(
                device=self.device_48k,
                channels=self.channels,
                samplerate=self.rate_48k,
                callback=self._callback_48k
            )
            
            stream_8k = sd.InputStream(
                device=self.device_8k,
                channels=self.channels,
                samplerate=self.rate_8k,
                callback=self._callback_8k
            )
            
            # Start recording
            with stream_48k, stream_8k:
                while self.is_recording:
                    time.sleep(0.1)  # Small sleep to prevent CPU hogging
                    
        except Exception as e:
            self.is_recording = False
            self.error_occurred.emit(f"Recording error: {str(e)}")
    
    def _callback_48k(self, indata, frames, time_info, status):
        """Callback for 48kHz stream."""
        if status:
            print(f"48kHz stream status: {status}")
        
        # Calculate the audio level for the meter
        if len(indata) > 0:
            audio_level = np.max(np.abs(indata)) * 100
            self.level_meter.emit(audio_level)
        
        # Store the audio data
        self.frames_48k.append(indata.copy())
    
    def _callback_8k(self, indata, frames, time_info, status):
        """Callback for 8kHz stream."""
        if status:
            print(f"8kHz stream status: {status}")
        
        # Store the audio data
        self.frames_8k.append(indata.copy())
    
    def save_recording(self, base_path, filename):
        """Save the recorded audio to files."""
        if not self.frames_48k or not self.frames_8k:
            self.error_occurred.emit("No audio data to save")
            return False
        
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.join(base_path, '48khz'), exist_ok=True)
            os.makedirs(os.path.join(base_path, '8khz'), exist_ok=True)
            
            # Save 48kHz recording
            path_48k = os.path.join(base_path, '48khz', f"{filename}.wav")
            self._save_wav(path_48k, self.frames_48k, self.rate_48k)
            
            # Save 8kHz recording
            path_8k = os.path.join(base_path, '8khz', f"{filename}.wav")
            self._save_wav(path_8k, self.frames_8k, self.rate_8k)
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error saving audio: {str(e)}")
            return False
    
    def _save_wav(self, filepath, frames, samplerate):
        """Save audio frames to a WAV file."""
        # Convert list of numpy arrays to a single numpy array
        audio_data = np.concatenate(frames, axis=0)
        
        # Apply trimming to remove silence
        trimmed_audio = self._trim_silence(audio_data, samplerate)
        
        # Save as WAV
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(samplerate)
            wf.writeframes(trimmed_audio.tobytes())
        
        return len(trimmed_audio) / samplerate  # Return duration in seconds
    
    def _trim_silence(self, audio_data, samplerate, threshold=0.02, padding_ms=100):
        """Trim silence from the beginning and end of the audio."""
        # Convert to absolute values
        amplitude = np.abs(audio_data)
        
        # Find where audio exceeds threshold
        non_silent = amplitude > threshold
        
        # Find the first and last non-silent points
        if np.any(non_silent):
            start = np.where(non_silent)[0][0]
            end = np.where(non_silent)[0][-1]
            
            # Add padding
            padding_samples = int(padding_ms * samplerate / 1000)
            start = max(0, start - padding_samples)
            end = min(len(audio_data), end + padding_samples)
            
            return audio_data[start:end]
        else:
            # Return original if no non-silent parts found
            return audio_data