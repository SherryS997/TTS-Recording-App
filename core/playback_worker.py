from PyQt5.QtCore import QObject, pyqtSignal
import time
import sounddevice as sd

class PlaybackWorker(QObject):
    finished = pyqtSignal()           # Emitted when playback finishes
    error_occurred = pyqtSignal(str)  # Emitted if an error happens

    def __init__(self, audio_data, sample_rate, channels, start_position, 
                 get_seek_position_callback, update_position_callback, 
                 stop_flag_getter, is_paused_getter):
        """
        Parameters:
          audio_data: The numpy array containing the audio.
          sample_rate: Playback sample rate.
          channels: Number of channels.
          start_position: Starting sample index.
          get_seek_position_callback: A callable returning the current seek position in seconds (or None if no seek).
          update_position_callback: A callable to update current playback position.
          stop_flag_getter: A callable that returns True when playback should stop.
          is_paused_getter: A callable that returns True if playback is paused.
        """
        super().__init__()
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.channels = channels
        self.start_sample = int(start_position * sample_rate)
        self.get_seek_position = get_seek_position_callback
        self.update_position = update_position_callback
        self.stop_flag_getter = stop_flag_getter
        self.is_paused_getter = is_paused_getter

    def run(self):
        """Runs the blocking playback loop."""
        try:
            current_sample = self.start_sample
            buffer_size = int(self.sample_rate * 0.1)  # 100 ms chunks
            # Create the output stream
            stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16'
            )
            with stream:
                while not self.stop_flag_getter() and current_sample < len(self.audio_data):
                    # Check if playback is paused and if so, wait without advancing playback
                    if self.is_paused_getter():
                        time.sleep(0.1)
                        continue
                    # Check for seek request
                    seek_seconds = self.get_seek_position()
                    if seek_seconds is not None:
                        current_sample = int(seek_seconds * self.sample_rate)
                    # Read the next chunk
                    end_sample = min(current_sample + buffer_size, len(self.audio_data))
                    if self.channels == 1:
                        chunk = self.audio_data[current_sample:end_sample]
                    else:
                        chunk = self.audio_data[current_sample:end_sample, :]
                    # Write chunk to stream
                    stream.write(chunk)
                    current_sample = end_sample
                    # Update the current playback position in seconds
                    self.update_position(current_sample / self.sample_rate)
                # Playback finished normally
            self.finished.emit()
        except Exception as e:
            self.error_occurred.emit(f"Playback error: {str(e)}")
            self.finished.emit()
