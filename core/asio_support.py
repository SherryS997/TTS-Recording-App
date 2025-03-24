import sys
from PyQt5.QtCore import QObject, pyqtSignal

class AsioSupport(QObject):
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._asio_available = sys.platform == 'win32'

    def is_asio_available(self):
        return self._asio_available

    def get_asio_devices(self):
        return []