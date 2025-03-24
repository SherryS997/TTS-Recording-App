# core/audio_recorder.py
import os
import time
import wave
import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QApplication
from pydub import AudioSegment
import pyaudio

class RecorderThread(QThread):
    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        
    def run(self):
        self.recorder._record_audio()

class AudioRecorder(QObject):
    """Handles audio recording with support for multiple sample rates and ASIO."""
    
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(float)
    level_meter = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def apply_settings(self, settings):
        """Apply settings from the settings dialog."""
        try:
            # Parse bit depth
            bit_depth = settings.value("audio/bit_depth", "16-bit")
            if bit_depth == "16-bit":
                self.format = 'int16'
            elif bit_depth == "24-bit":
                self.format = 'int24'
            elif bit_depth == "32-bit float":
                self.format = 'float32'
                
            # Apply buffer size
            buffer_size = settings.value("audio/buffer_size", "1024")
            self.chunk_size = int(buffer_size)
            
            # Apply other settings as needed
            trim_threshold = settings.value("audio/trim_threshold", 2, int)
            self.silence_threshold = float(trim_threshold) / 100.0
            
            self.padding_ms = settings.value("audio/padding_ms", 100, int)
        except Exception as e:
            self.error_occurred.emit(f"Failed to apply settings: {str(e)}")

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
        self.last_recording_duration = 0.0
        self.enable_8k = False
    
    def get_available_devices(self, include_asio=True):
        """Returns a list of available audio devices with fallbacks."""
        devices = []
        
        try:
            # Primary method: sounddevice
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_input_channels'] > 0:
                    if include_asio or 'ASIO' not in device['name']:
                        devices.append({
                            'index': i,
                            'name': device['name'],
                            'channels': device['max_input_channels'],
                            'sample_rates': device.get('default_samplerate', 48000),
                            'is_asio': 'ASIO' in device['name']
                        })
            
            # If no devices found, try PyAudio as fallback
            if not devices:
                p = pyaudio.PyAudio()
                for i in range(p.get_device_count()):
                    device_info = p.get_device_info_by_index(i)
                    if device_info.get('maxInputChannels', 0) > 0:
                        devices.append({
                            'index': i,
                            'name': device_info.get('name', f"Input Device {i}"),
                            'channels': device_info.get('maxInputChannels', 1),
                            'sample_rates': int(device_info.get('defaultSampleRate', 48000)),
                            'is_asio': 'ASIO' in device_info.get('name', '')
                        })
                p.terminate()
                
        except Exception as e:
            self.error_occurred.emit(f"Failed to get audio devices: {str(e)}")
        
        return devices
    
    def test_recording_device(self, device_index):
        """Test if a device can actually record audio."""
        try:
            # Create a short test recording
            import numpy as np
            
            duration = 0.5  # seconds
            fs = 48000
            
            # Record audio from the selected device
            recording = sd.rec(int(duration * fs), samplerate=fs, 
                            channels=1, device=device_index, dtype='float32')
            sd.wait()
            
            # Check if recording contains only silence
            amplitude = np.abs(recording).max()
            if amplitude < 0.01:
                return False, "Device detected but not capturing audio"
            
            return True, "Device working correctly"
            
        except Exception as e:
            return False, f"Device test failed: {str(e)}"
    
    @pyqtSlot(int, int, str, str)
    def start_recording(self, device_48k_idx, device_8k_idx, filename_48k=None, filename_8k=None):
        if self.is_recording:
            return
        
        self.device_48k = device_48k_idx
        self.frames_48k = []
        self.filename_48k = filename_48k

        # Check if the UI toggle for 8k recording is enabled.
        if self.enable_8k:
            self.device_8k = device_8k_idx
            self.frames_8k = []
            self.filename_8k = filename_8k
        else:
            self.device_8k = None  # Skip 8k stream if toggle is off
            self.filename_8k = None

        # Start recording in a new thread using RecorderThread
        self.is_recording = True
        self.recording_thread = RecorderThread(self)
        self.recording_thread.started.connect(lambda: None)  # optional: if you need additional setup
        self.recording_thread.start()
        self.recording_started.emit()
    
    @pyqtSlot()
    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.quit()
            if not self.recording_thread.wait(1000):  # Wait up to 1 second
                print("Warning: Recording thread did not terminate in time.")

        duration = 0
        if hasattr(self, 'filename_48k') and self.filename_48k and self.frames_48k:
            if len(self.frames_48k) > 0:
                duration = self._save_wav(self.filename_48k, self.frames_48k, self.rate_48k)
                self.last_recording_duration = duration
        
        if hasattr(self, 'filename_8k') and self.filename_8k and self.frames_8k:
            if len(self.frames_8k) > 0:
                self._save_wav(self.filename_8k, self.frames_8k, self.rate_8k)

        self.recording_stopped.emit(duration)

    
    def _record_audio(self):
        try:
            # Create 48kHz stream (required)
            stream_48k = sd.InputStream(
                device=self.device_48k,
                channels=self.channels,
                samplerate=self.rate_48k,
                callback=self._callback_48k
            )
            
            # Only create the 8kHz stream if an appropriate device is set
            stream_8k = None
            if self.device_8k is not None:
                stream_8k = sd.InputStream(
                    device=self.device_8k,
                    channels=self.channels,
                    samplerate=self.rate_8k,
                    callback=self._callback_8k
                )
            
            # Use different context managers depending on the availability of the 8kHz stream
            if stream_8k is not None:
                with stream_48k, stream_8k:
                    while self.is_recording:
                        time.sleep(0.1)
                        if not self.is_recording: # Check again inside the loop
                            break
            else:
                with stream_48k:
                    while self.is_recording:
                        time.sleep(0.1)
                        if not self.is_recording: # Check again inside the loop
                            break
                        
        except Exception as e:
            self.is_recording = False
            import traceback
            error_details = f"Device: {self.device_48k}, Rate: {self.rate_48k}\n{traceback.format_exc()}"
            self.error_occurred.emit(f"Recording error: {str(e)}\n{error_details}")
    
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
    
    def _save_wav(self, filepath, frames, samplerate):
        """Save audio frames to a WAV file."""
        # Convert list of numpy arrays to a single numpy array
        audio_data = np.concatenate(frames, axis=0)

        # if self.format != 'int16':
        audio_data = (audio_data * 32767).astype(np.int16)
        
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
        
    def get_system_default_device(self, mode="input"):
        """Get the system default audio device in a cross-platform way
        
        Args:
            mode: "input" or "output" to specify recording or playback device
            
        Returns:
            Device index that works on the current platform
        """
        import platform
        
        system = platform.system()
        
        # First try the sounddevice default
        try:
            if mode == "input":
                return sd.default.device[0]  # Default input device
            else:
                return sd.default.device[1]  # Default output device
        except:
            # If that fails, find the first appropriate device
            try:
                devices = sd.query_devices()
                for i, device in enumerate(devices):
                    if (mode == "input" and device['max_input_channels'] > 0) or \
                    (mode == "output" and device['max_output_channels'] > 0):
                        return i
                return 0
            except:
                return 0
