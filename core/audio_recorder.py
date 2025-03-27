# core/audio_recorder.py
import os
import time
import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QApplication
import soundfile as sf
import pyaudio
from utils.audio_utils import trim_silence_numpy # ADD

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

    def __init__(self, parent=None):
        self.format = 'int16' # Or load from settings
        self.silence_threshold_db = -40 # Default, or load from settings
        self.padding_ms = 100 # Default, or load from settings
        self.auto_trim_on_save = False

    def apply_settings(self, settings):
        """Apply settings from the settings dialog."""
        try:
            # ... (bit depth parsing - store subtype for soundfile) ...
            print(settings)

            bit_depth = settings.value("audio/bit_depth", "16-bit")
            if bit_depth == "16-bit":
                self.format = 'int16'
                self.subtype = 'PCM_16' # soundfile subtype
            elif bit_depth == "24-bit":
                self.format = 'int24' # sounddevice format
                self.subtype = 'PCM_24' # soundfile subtype
            elif bit_depth == "32-bit float":
                self.format = 'float32'
                self.subtype = 'FLOAT' # soundfile subtype
            else: # Default
                self.format = 'int16'
                self.subtype = 'PCM_16'

            # Apply buffer size
            buffer_size = settings.value("audio/buffer_size", "1024")
            self.chunk_size = int(buffer_size) # Note: sounddevice callback doesn't use chunk_size directly

            # Trim threshold (needs conversion dB -> linear if needed by trimmer)
            # Assuming settings store dB or similar. Let's store dB.
            # The trim_threshold setting in the dialog is % - this needs rethinking.
            # Let's assume settings store dB for now, matching audio_utils.
            self.silence_threshold_db = settings.value("audio/trim_threshold_db", -40, float) # Example: add a dB setting

            self.padding_ms = settings.value("audio/padding_ms", 100, int)

            # Store file format (used for extension)
            self.file_format = settings.value("storage/file_format", "WAV").lower() # Store as 'wav' or 'flac'

            # Auto-trim setting
            self.auto_trim_on_save = settings.value("audio/auto_trim", True, bool)

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
            # Determine dtype based on self.format
            dtype = self.format if self.format in ['int16', 'int24', 'float32'] else 'int16'

            # Create 48kHz stream (required)
            stream_48k = sd.InputStream(
                device=self.device_48k,
                channels=self.channels,
                samplerate=self.rate_48k,
                callback=self._callback_48k,
                dtype=dtype # Use the selected dtype
            )

            # Only create the 8kHz stream if enabled
            stream_8k = None
            if self.enable_8k and self.device_8k is not None:
                stream_8k = sd.InputStream(
                    device=self.device_8k,
                    channels=self.channels,
                    samplerate=self.rate_8k,
                    callback=self._callback_8k,
                    dtype=dtype # Use the same dtype
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
        """Save audio frames to a WAV file using soundfile, optionally trimming."""
        if not frames:
             print(f"Warning: No frames received for {filepath}. Skipping save.")
             return 0.0

        # Convert list of numpy arrays to a single numpy array
        # Ensure the array is contiguous
        try:
            audio_data = np.concatenate(frames, axis=0)
        except ValueError as e:
            print(f"Error concatenating frames for {filepath}: {e}")
            # Attempt to fix if shapes mismatch slightly (rare with InputStream)
            if frames:
                 max_len = max(f.shape[0] for f in frames)
                 frames_padded = [np.pad(f, ((0, max_len - f.shape[0]), (0, 0)), 'constant') if f.shape[0] < max_len else f for f in frames]
                 try:
                     audio_data = np.concatenate(frames_padded, axis=0)
                     print("Warning: Had to pad frames to concatenate.")
                 except ValueError as e2:
                      self.error_occurred.emit(f"Failed to save {filepath}: Inconsistent audio frame shapes. {e2}")
                      return 0.0
            else: # Should have been caught by the initial 'if not frames'
                 return 0.0
            
        # Apply trimming if enabled
        if False:
             # Ensure audio_data is mono for trimming function
             if audio_data.ndim > 1:
                 audio_data_mono = audio_data[:, 0] # Use first channel
             else:
                 audio_data_mono = audio_data

             trimmed_audio, duration = trim_silence_numpy(
                 audio_data_mono,
                 samplerate,
                 threshold_db=self.silence_threshold_db,
                 padding_ms=self.padding_ms
             )
             if duration == 0:
                 print(f"Warning: Trimming resulted in empty audio for {filepath}. Saving original.")
                 # Optionally save the original untrimmed audio instead of nothing
                 # trimmed_audio = audio_data # Revert to original if trim fails
                 # duration = len(trimmed_audio) / samplerate
                 # Fallback: Save original if trimming removed everything
                 if len(audio_data) > 0:
                    trimmed_audio = audio_data # Save original
                    duration = len(trimmed_audio) / samplerate
                    print("Saving original audio instead after trimming failed.")
                 else:
                    print(f"Error: Original audio was also empty for {filepath}.")
                    return 0.0 # Can't save empty audio
             # If original was stereo, need to handle this - currently trim is mono
             # Simplest: If original was stereo, save the trimmed mono version
             # Better: Trim based on mono energy, apply indices to stereo
             # For now, we save the mono result of trim_silence_numpy
             final_audio_data = trimmed_audio
        else:
             final_audio_data = audio_data
             duration = len(final_audio_data) / samplerate

        # Save using soundfile
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            # Subtype (bit depth) is already stored in self.subtype
            sf.write(filepath, final_audio_data, samplerate, subtype=self.subtype)
            print(f"Saved: {os.path.basename(filepath)}, Duration: {duration:.2f}s, Subtype: {self.subtype}")
            return duration

        except Exception as e:
            self.error_occurred.emit(f"Failed to save audio file '{filepath}': {str(e)}")
            return 0.0

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
