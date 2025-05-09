# ui/traffic_light_indicator.py
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QBrush
from PyQt5.QtCore import Qt, QSize

class TrafficLightIndicator(QWidget):
    """
    A widget that displays three circles (red, orange, green) to indicate a status,
    similar to a traffic light.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "off"  # Possible states: "off", "red", "orange", "green"
        
        self.light_diameter = 20  # Diameter of each light circle
        self.padding = 5          # Padding around and between lights

        # Calculate and set a fixed size for the widget
        # Width: 3 diameters + 4 padding segments (sides and between)
        # Height: 1 diameter + 2 padding segments (top and bottom)
        widget_width = (3 * self.light_diameter) + (4 * self.padding)
        widget_height = self.light_diameter + (2 * self.padding)
        self.setFixedSize(QSize(widget_width, widget_height))

    def paintEvent(self, event):
        """Handles the painting of the traffic light."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Define colors for "on" and "off" states
        # Using slightly less intense colors for better appearance, especially on dark themes
        color_red_on = QColor(220, 0, 0)
        color_orange_on = QColor(255, 140, 0)
        color_green_on = QColor(0, 180, 0)
        color_off = QColor(60, 60, 60)  # Dark gray for off state

        # Calculate vertical position for the lights (centered)
        y_pos = self.padding

        # Calculate horizontal positions for each light
        x_red = self.padding
        x_orange = self.padding * 2 + self.light_diameter
        x_green = self.padding * 3 + 2 * self.light_diameter

        # Draw Red Light
        current_brush_red = QBrush(color_red_on if self._state == "red" else color_off)
        painter.setBrush(current_brush_red)
        painter.drawEllipse(x_red, y_pos, self.light_diameter, self.light_diameter)

        # Draw Orange Light
        current_brush_orange = QBrush(color_orange_on if self._state == "orange" else color_off)
        painter.setBrush(current_brush_orange)
        painter.drawEllipse(x_orange, y_pos, self.light_diameter, self.light_diameter)

        # Draw Green Light
        current_brush_green = QBrush(color_green_on if self._state == "green" else color_off)
        painter.setBrush(current_brush_green)
        painter.drawEllipse(x_green, y_pos, self.light_diameter, self.light_diameter)

    def setState(self, state):
        """
        Sets the current state of the traffic light.
        This will determine which light is "on".

        Args:
            state (str): The desired state. Must be one of "off", "red", 
                         "orange", or "green".
        """
        valid_states = ["off", "red", "orange", "green"]
        if state not in valid_states:
            print(f"Warning: Invalid state '{state}' for TrafficLightIndicator. Defaulting to 'off'.")
            state = "off"
        
        if self._state != state:
            self._state = state
            self.update()  # Trigger a repaint to reflect the new state

    def getState(self):
        """
        Returns the current state of the traffic light.

        Returns:
            str: The current state ("off", "red", "orange", or "green").
        """
        return self._state

if __name__ == '__main__':
    # Example usage for testing the TrafficLightIndicator widget
    import sys
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QGroupBox

    app = QApplication(sys.argv)

    # Apply a simple dark theme for testing
    app.setStyleSheet("""
        QWidget { background-color: #2E2E2E; color: #E0E0E0; }
        QPushButton { background-color: #4A4A4A; border: 1px solid #6A6A6A; padding: 5px; }
        QPushButton:hover { background-color: #5A5A5A; }
        QGroupBox { border: 1px solid #4A4A4A; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
    """)

    test_window = QWidget()
    main_layout = QVBoxLayout(test_window)
    test_window.setWindowTitle("Traffic Light Indicator Test")

    indicator_group = QGroupBox("Indicator")
    indicator_layout = QVBoxLayout()
    
    indicator = TrafficLightIndicator()
    indicator_layout.addWidget(indicator, alignment=Qt.AlignCenter) # Center the indicator
    indicator_group.setLayout(indicator_layout)

    main_layout.addWidget(indicator_group)

    # Buttons to control the indicator state
    buttons_layout = QVBoxLayout()
    btn_off = QPushButton("Set State: Off")
    btn_red = QPushButton("Set State: Red (Recording)")
    btn_orange = QPushButton("Set State: Orange (Processing)")
    btn_green = QPushButton("Set State: Green (Success/Uploaded)")

    btn_off.clicked.connect(lambda: indicator.setState("off"))
    btn_red.clicked.connect(lambda: indicator.setState("red"))
    btn_orange.clicked.connect(lambda: indicator.setState("orange"))
    btn_green.clicked.connect(lambda: indicator.setState("green"))

    buttons_layout.addWidget(btn_off)
    buttons_layout.addWidget(btn_red)
    buttons_layout.addWidget(btn_orange)
    buttons_layout.addWidget(btn_green)
    
    main_layout.addLayout(buttons_layout)

    test_window.resize(300, 250)
    test_window.show()
    sys.exit(app.exec_())