# utils/audio_utils.py
import numpy as np

def trim_silence_numpy(audio_data, sample_rate, threshold_db=-40, padding_ms=100):
    """
    Trim silence from the beginning and end of a NumPy audio array using a dB threshold.

    Args:
        audio_data (np.ndarray): NumPy array containing audio data (mono).
        sample_rate (int): Sample rate of the audio.
        threshold_db (float): The threshold in dB below which audio is considered silence.
                              Quieter audio (e.g., -50 dB) means a stricter threshold.
        padding_ms (int): Milliseconds of padding to add around the detected audio.

    Returns:
        np.ndarray: The trimmed audio data.
        float: The duration of the trimmed audio in seconds.
    """
    if audio_data.size == 0:
        return audio_data, 0.0

    # Ensure audio_data is float for amplitude calculations
    if not np.issubdtype(audio_data.dtype, np.floating):
        # Convert int16 to float range [-1.0, 1.0]
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32767.0
        else: # Add other integer types if needed
             # Basic fallback: Normalize assuming max possible value
             max_val = np.iinfo(audio_data.dtype).max
             audio_data = audio_data.astype(np.float32) / max_val


    # Convert dB threshold to amplitude threshold
    amplitude_threshold = 10**(threshold_db / 20.0)

    # Calculate absolute amplitude
    amplitude = np.abs(audio_data)

    # Find where audio exceeds threshold
    non_silent_indices = np.where(amplitude > amplitude_threshold)[0]

    # If no non-silent parts found, return original (or empty if desired)
    if len(non_silent_indices) == 0:
        # Decide whether to return original or empty array
        # Returning original might be safer if threshold is too high
        # return audio_data, len(audio_data) / sample_rate
        return np.array([], dtype=audio_data.dtype), 0.0 # Return empty

    # Find start and end indices
    start_idx = non_silent_indices[0]
    end_idx = non_silent_indices[-1]

    # Add padding (convert ms to samples)
    padding_samples = int(padding_ms * sample_rate / 1000)
    start_idx = max(0, start_idx - padding_samples)
    end_idx = min(len(audio_data) - 1, end_idx + padding_samples) # Use len-1 for index

    # Extract the non-silent part
    trimmed_audio = audio_data[start_idx : end_idx + 1] # Slice includes end_idx

    duration = len(trimmed_audio) / sample_rate
    return trimmed_audio, duration