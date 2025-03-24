import sounddevice as sd
import numpy as np
import wave
import os
import time
from datetime import datetime

def test_recording():
    # Recording parameters
    sample_rate = 48000  # 48kHz
    channels = 1  # Mono
    duration = 5  # 5 seconds
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_recording_{timestamp}.wav"
    
    print(f"Starting recording for {duration} seconds...")
    
    # Start recording
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate,
                      channels=channels,
                      dtype='int16')
    
    # Display countdown
    for i in range(duration, 0, -1):
        print(f"Recording... {i} seconds remaining")
        time.sleep(1)
    
    # Wait for recording to complete
    sd.wait()
    
    print("Recording finished!")

    print(recording.shape, recording)
    
    # Save recording to WAV file
    with wave.open(output_file, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(sample_rate)
        wf.writeframes(recording.tobytes())
    
    file_path = os.path.abspath(output_file)
    print(f"Recording saved to: {file_path}")
    print(f"File size: {os.path.getsize(output_file) / 1024:.2f} KB")

    #         # Apply the custom styles
    #     self.apply_custom_styles()

    # def apply_custom_styles(self):
    #     style = """
    #     /* Main Window Background */
    #     QMainWindow {
    #         background-color: #f0f0f0;
    #     }
        
    #     /* General Widgets */
    #     QWidget {
    #         font-family: "Noto Sans";
    #         font-size: 10pt;
    #         color: #333;
    #     }
        
    #     /* Push Buttons */
    #     QPushButton {
    #         background-color: #4CAF50;
    #         border: none;
    #         border-radius: 4px;
    #         padding: 8px 16px;
    #         color: white;
    #     }
    #     QPushButton:hover {
    #         background-color: #45a049;
    #     }
    #     QPushButton:pressed {
    #         background-color: #3e8e41;
    #     }
        
    #     /* Labels */
    #     QLabel {
    #         font-size: 10pt;
    #     }
        
    #     /* QLineEdit and QTextEdit */
    #     QLineEdit, QTextEdit {
    #         background-color: white;
    #         border: 1px solid #ccc;
    #         border-radius: 4px;
    #         padding: 4px;
    #     }
        
    #     /* QComboBox */
    #     QComboBox {
    #         background-color: white;
    #         border: 1px solid #ccc;
    #         border-radius: 4px;
    #         padding: 4px;
    #     }
        
    #     /* QProgressBar */
    #     QProgressBar {
    #         text-align: center;
    #         border: 1px solid #aaa;
    #         border-radius: 4px;
    #         background-color: #eee;
    #     }
    #     QProgressBar::chunk {
    #         background-color: #4CAF50;
    #         width: 10px;
    #         margin: 0.5px;
    #     }
    #     """
    #     self.setStyleSheet(style)


if __name__ == "__main__":
    test_recording()
