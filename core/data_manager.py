import os
import csv
import pandas as pd
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QSettings

class DataManager(QObject):
    """
    Manages data operations including CSV import/export, audio file tracking,
    and recording session management.
    """
    
    # Define signals
    data_loaded = pyqtSignal(pd.DataFrame)  # Signal emitted when data is loaded
    data_saved = pyqtSignal(str)  # Signal emitted when data is saved (with path)
    current_item_changed = pyqtSignal(pd.Series)  # Signal emitted when current row changes
    error_occurred = pyqtSignal(str)  # Signal emitted when an error occurs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize properties
        self.base_dir = 'data'  # Default base directory
        self.output_dir = None  # Current output directory
        self.dataframe = None   # Pandas dataframe for data
        self.current_index = -1  # Current row index
        self.total_audio_count = 0  # Count of recorded audio files
        self.total_duration = 0.0   # Total duration of all recordings
        self.csv_path = None        # Path to CSV file
        
        # Required columns in CSV
        self.required_columns = ['id', 'text']
        
        # Optional columns with default values
        self.optional_columns = {
            'recorded': False,
            'audio_path_48k': '',
            'audio_path_8k': '',
            'duration': 0.0,
            'trimmed': False
        }
        
        # Load settings
        self._load_settings()
        
    def _load_settings(self):
        """Load settings from QSettings."""
        settings = QSettings()
        self.base_dir = settings.value('data_manager/base_dir', 'data')
        
        # Create base directory if it doesn't exist
        if not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir, exist_ok=True)
            except Exception as e:
                self.error_occurred.emit(f"Could not create base directory: {str(e)}")
    
    def save_settings(self):
        """Save current settings to QSettings."""
        settings = QSettings()
        settings.setValue('data_manager/base_dir', self.base_dir)
    
    def set_base_directory(self, directory):
        """
        Set the base directory for output files.
        
        Args:
            directory (str): Path to base directory
        """
        if os.path.exists(directory) and os.path.isdir(directory):
            self.base_dir = directory
            self.save_settings()
            return True
        else:
            self.error_occurred.emit(f"Invalid directory: {directory}")
            return False
    
    def set_output_directory(self, directory):
        """
        Set the current output directory for recording session.
        
        Args:
            directory (str): Path to output directory
        """
        if os.path.exists(directory) and os.path.isdir(directory):
            self.output_dir = directory
            return True
        else:
            try:
                os.makedirs(directory, exist_ok=True)
                self.output_dir = directory
                return True
            except Exception as e:
                self.error_occurred.emit(f"Could not create output directory: {str(e)}")
                return False
    
    def create_output_directory(self, language, style, speaker):
        """
        Create a new output directory based on date and metadata.
        
        Args:
            language (str): Selected language
            style (str): Selected style
            speaker (str): Selected speaker
            
        Returns:
            str: Path to created directory or None if failed
        """
        try:
            # Create directory name with timestamp
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            timestamp = now.strftime("%H%M%S")
            
            # Create directory name
            dir_name = f"{date_str}_{language}_{style}_{speaker}_{timestamp}"
            dir_path = os.path.join(self.base_dir, dir_name)
            
            # Create directory and subdirectories
            os.makedirs(dir_path, exist_ok=True)
            os.makedirs(os.path.join(dir_path, '48khz'), exist_ok=True)
            os.makedirs(os.path.join(dir_path, '8khz'), exist_ok=True)
            
            # Set as current output directory
            self.output_dir = dir_path
            
            return dir_path
        
        except Exception as e:
            self.error_occurred.emit(f"Failed to create output directory: {str(e)}")
            return None
    
    def load_csv(self, file_path=None):
        """
        Load data from a CSV file.
        
        Args:
            file_path (str, optional): Path to CSV file. If None, opens a file dialog.
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if file_path is None:
                return False
                
            if not os.path.exists(file_path):
                self.error_occurred.emit(f"File not found: {file_path}")
                return False
            
            # Load CSV into dataframe
            df = pd.read_csv(file_path)
            
            # Check for required columns
            for col in self.required_columns:
                if col not in df.columns:
                    self.error_occurred.emit(f"Required column '{col}' missing from CSV")
                    return False
            
            # Add optional columns if missing
            for col, default_value in self.optional_columns.items():
                if col not in df.columns:
                    df[col] = default_value
            
            # Reset index to ensure sequential numbering
            df = df.reset_index(drop=True)
            
            # Store dataframe and update current index
            self.dataframe = df
            self.csv_path = file_path
            self.current_index = 0
            
            # Calculate metrics
            self.total_audio_count = df['recorded'].sum()
            self.total_duration = df['duration'].sum()
            
            # Emit signal with loaded data
            self.data_loaded.emit(df)
            
            # Emit signal with current row
            if not df.empty:
                self.current_item_changed.emit(df.iloc[0])
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error loading CSV: {str(e)}")
            return False
    
    def save_csv(self, file_path=None):
        """
        Save current data to a CSV file.
        
        Args:
            file_path (str, optional): Path to save CSV file. If None, uses current path.
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.dataframe is None:
                self.error_occurred.emit("No data to save")
                return False
                
            # Determine file path
            save_path = file_path or self.csv_path
            if save_path is None:
                self.error_occurred.emit("No save path specified")
                return False
            
            # Save dataframe to CSV
            self.dataframe.to_csv(save_path, index=False)
            
            # Update current path
            self.csv_path = save_path
            
            # Emit signal
            self.data_saved.emit(save_path)
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error saving CSV: {str(e)}")
            return False
    
    def create_new_csv(self, file_path):
        """
        Create a new empty CSV file with required columns.
        
        Args:
            file_path (str): Path to new CSV file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create empty dataframe with required columns
            columns = self.required_columns + list(self.optional_columns.keys())
            df = pd.DataFrame(columns=columns)
            
            # Save to file
            df.to_csv(file_path, index=False)
            
            # Load the new file
            return self.load_csv(file_path)
            
        except Exception as e:
            self.error_occurred.emit(f"Error creating CSV: {str(e)}")
            return False
    
    def next_item(self):
        """
        Move to the next item in the dataframe.
        
        Returns:
            bool: True if successful, False if at end
        """
        if self.dataframe is None or self.dataframe.empty:
            return False
            
        if self.current_index < len(self.dataframe) - 1:
            self.current_index += 1
            self.current_item_changed.emit(self.dataframe.iloc[self.current_index])
            return True
        else:
            return False
    
    def previous_item(self):
        """
        Move to the previous item in the dataframe.
        
        Returns:
            bool: True if successful, False if at beginning
        """
        if self.dataframe is None or self.dataframe.empty:
            return False
            
        if self.current_index > 0:
            self.current_index -= 1
            self.current_item_changed.emit(self.dataframe.iloc[self.current_index])
            return True
        else:
            return False
    
    def jump_to_id(self, id_value):
        """
        Jump to a specific item by ID.
        
        Args:
            id_value (str): ID to search for
            
        Returns:
            bool: True if found, False otherwise
        """
        if self.dataframe is None or self.dataframe.empty:
            return False
            
        # Find index with matching ID
        matches = self.dataframe[self.dataframe['id'] == id_value].index
        if not matches.empty:
            self.current_index = matches[0]
            self.current_item_changed.emit(self.dataframe.iloc[self.current_index])
            return True
        else:
            self.error_occurred.emit(f"ID not found: {id_value}")
            return False
    
    def get_current_item(self):
        """
        Get the current item data.
        
        Returns:
            pd.Series: Current row or None if not available
        """
        if self.dataframe is None or self.dataframe.empty:
            return None
            
        if 0 <= self.current_index < len(self.dataframe):
            return self.dataframe.iloc[self.current_index]
        else:
            return None
    
    def update_current_item(self, data_dict):
        """
        Update the current item with new values.
        
        Args:
            data_dict (dict): Dictionary of column/value pairs
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.dataframe is None or self.dataframe.empty:
            return False
            
        if 0 <= self.current_index < len(self.dataframe):
            # Update values
            for key, value in data_dict.items():
                if key in self.dataframe.columns:
                    self.dataframe.at[self.current_index, key] = value
                    
            # Update metrics
            self.total_audio_count = self.dataframe['recorded'].sum()
            self.total_duration = self.dataframe['duration'].sum()
                    
            # Save changes
            if self.csv_path:
                self.save_csv()
                
            return True
        else:
            return False
    
    def register_recording(self, audio_path_48k, audio_path_8k, duration):
        """
        Register a new audio recording for the current item.
        
        Args:
            audio_path_48k (str): Path to 48kHz audio file
            audio_path_8k (str): Path to 8kHz audio file
            duration (float): Duration in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.dataframe is None or self.dataframe.empty:
            return False
            
        if 0 <= self.current_index < len(self.dataframe):
            # Update record
            update_data = {
                'recorded': True,
                'audio_path_48k': audio_path_48k,
                'audio_path_8k': audio_path_8k,
                'duration': duration,
                'trimmed': False
            }
            
            # Update dataframe
            for key, value in update_data.items():
                if key in self.dataframe.columns:
                    self.dataframe.at[self.current_index, key] = value
                    
            # Update metrics
            self.total_audio_count = self.dataframe['recorded'].sum()
            self.total_duration = self.dataframe['duration'].sum()
            
            # Save changes
            if self.csv_path:
                self.save_csv()
                
            return True
        else:
            return False
    
    def update_trim_status(self, is_trimmed, new_duration=None):
        """
        Update the trim status of the current item.
        
        Args:
            is_trimmed (bool): Whether the audio is trimmed
            new_duration (float, optional): New duration if changed
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.dataframe is None or self.dataframe.empty:
            return False
            
        if 0 <= self.current_index < len(self.dataframe):
            # Update trimmed status
            self.dataframe.at[self.current_index, 'trimmed'] = is_trimmed
            
            # Update duration if provided
            if new_duration is not None:
                old_duration = self.dataframe.at[self.current_index, 'duration']
                self.dataframe.at[self.current_index, 'duration'] = new_duration
                self.total_duration = self.total_duration - old_duration + new_duration
            
            # Save changes
            if self.csv_path:
                self.save_csv()
                
            return True
        else:
            return False
    
    def get_total_stats(self):
        """
        Get statistics about the dataset.
        
        Returns:
            dict: Dictionary with statistics
        """
        if self.dataframe is None:
            return {
                'total_items': 0,
                'recorded_items': 0,
                'total_duration': 0,
                'progress_percent': 0
            }
            
        total_items = len(self.dataframe)
        recorded_items = self.total_audio_count
        progress = 0 if total_items == 0 else (recorded_items / total_items) * 100
        
        return {
            'total_items': total_items,
            'recorded_items': recorded_items,
            'total_duration': self.total_duration,
            'progress_percent': progress
        }
    
    def get_current_progress(self):
        """
        Get the current progress as a percentage.
        
        Returns:
            float: Progress percentage (0-100)
        """
        if self.dataframe is None or self.dataframe.empty:
            return 0
            
        total_items = len(self.dataframe)
        recorded_items = self.total_audio_count
        return 0 if total_items == 0 else (recorded_items / total_items) * 100