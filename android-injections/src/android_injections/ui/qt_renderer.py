"""PyQt6-based UI rendering module - replaces cv2 imshow with native window."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSpinBox, QFrame, QGridLayout, QInputDialog
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtCore import QSize
import cv2
import numpy as np
from typing import Callable, Optional, Tuple


class VideoSignalEmitter(QObject):
    """Emits signals for video frame updates without blocking the UI thread."""
    frame_ready = pyqtSignal(np.ndarray)


class MirrorWindow(QMainWindow):
    """PyQt6 main window for Android mirror display with controls."""
    
    def __init__(self, window_capture_instance):
        super().__init__()
        self.capture = window_capture_instance
        self.setWindowTitle(self.capture.window_name)
        
        # Calculate scaled dimensions based on client window and display scale
        client_geom = self.capture.client_window.get_geometry()
        client_width = client_geom.width
        client_height = client_geom.height
        
        # Apply display scale
        scaled_width = int(client_width * self.capture.display_scale)
        scaled_height = int(client_height * self.capture.display_scale)
        
        # Add extra height for UI controls (approx 450px)
        ui_controls_height = 450
        window_width = max(scaled_width, 900)  # Ensure minimum width for labels
        window_height = scaled_height + ui_controls_height
        
        self.setGeometry(100, 100, window_width, window_height)
        
        # Signal emitter for frame updates
        self.signal_emitter = VideoSignalEmitter()
        self.signal_emitter.frame_ready.connect(self.update_frame)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Modern dark theme styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 11px;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #555;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #e0e0e0;
                border-color: #e0e0e0;
            }
        """)
        
        # Video display label (scaled image)
        self.video_label = QLabel()
        self.video_label.setMinimumSize(QSize(scaled_width, scaled_height))
        self.video_label.setMaximumSize(QSize(scaled_width, scaled_height))
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            background-color: #0a0a0a;
        """)
        self.video_label.setScaledContents(False)  # Don't stretch, maintain aspect ratio
        self.video_label.mousePressEvent = self.on_video_click
        self.video_label.mouseMoveEvent = self.on_video_mouse_move
        self.video_label.mouseReleaseEvent = self.on_video_mouse_release
        main_layout.addWidget(self.video_label)
        
        # First button row (Target, Bounds, Exclude, Filter, State)
        button_row1 = QHBoxLayout()
        button_row1.setContentsMargins(8, 8, 8, 4)
        button_row1.setSpacing(6)
        
        self.target_btn = self._create_button("Draw Target: OFF", self.toggle_target_mode)
        self.bounds_btn = self._create_button("Draw Bounds: OFF", self.toggle_bounds_mode)
        self.exclude_btn = self._create_button("Draw Exclude: OFF", self.toggle_exclude_mode)
        self.filter_btn = self._create_button("Filter: OFF", self.toggle_filter)
        self.state_btn = self._create_button("State: OFF", self.toggle_state_tracking)
        self.xp_btn = self._create_button("XP: OFF", self.toggle_xp_tracking)
        
        button_row1.addWidget(self.target_btn)
        button_row1.addWidget(self.bounds_btn)
        button_row1.addWidget(self.exclude_btn)
        button_row1.addWidget(self.filter_btn)
        button_row1.addWidget(self.state_btn)
        button_row1.addWidget(self.xp_btn)
        
        widget_row1 = QWidget()
        widget_row1.setLayout(button_row1)
        widget_row1.setStyleSheet("background-color: #1e1e1e;")
        widget_row1.setMaximumHeight(48)
        # Widget will be added to capture layout
        
        # Second button row (Color controls, pixels, blobs, checkboxes)
        button_row2 = QHBoxLayout()
        button_row2.setContentsMargins(8, 6, 8, 6)
        button_row2.setSpacing(12)
        
        # Color count controls
        button_row2.addWidget(QLabel("target\ncolors"))
        self.colors_minus_btn = self._create_mini_button("-", self.decrease_colors)
        self.colors_display = QLabel("20")
        self.colors_display.setMinimumWidth(35)
        self.colors_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.colors_plus_btn = self._create_mini_button("+", self.increase_colors)
        
        button_row2.addWidget(self.colors_minus_btn)
        button_row2.addWidget(self.colors_display)
        button_row2.addWidget(self.colors_plus_btn)
        
        # Min blob pixels controls
        button_row2.addWidget(QLabel("target min\npixels"))
        self.pixels_minus_btn = self._create_mini_button("-", self.decrease_pixels)
        self.pixels_display = QLabel("2")
        self.pixels_display.setMinimumWidth(35)
        self.pixels_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pixels_plus_btn = self._create_mini_button("+", self.increase_pixels)
        
        button_row2.addWidget(self.pixels_minus_btn)
        button_row2.addWidget(self.pixels_display)
        button_row2.addWidget(self.pixels_plus_btn)
        
        # Max blobs controls
        button_row2.addWidget(QLabel("max\nblobs"))
        self.blobs_minus_btn = self._create_mini_button("-", self.decrease_blobs)
        self.blobs_display = QLabel("1")
        self.blobs_display.setMinimumWidth(35)
        self.blobs_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.blobs_plus_btn = self._create_mini_button("+", self.increase_blobs)
        
        button_row2.addWidget(self.blobs_minus_btn)
        button_row2.addWidget(self.blobs_display)
        button_row2.addWidget(self.blobs_plus_btn)
        
        button_row2.addSpacing(20)
        
        # Checkboxes
        self.show_bounds_cb = QCheckBox("Show Bounds")
        self.show_bounds_cb.stateChanged.connect(self.toggle_show_bounds)
        button_row2.addWidget(self.show_bounds_cb)
        
        self.show_excludes_cb = QCheckBox("Show Excludes")
        self.show_excludes_cb.stateChanged.connect(self.toggle_show_excludes)
        button_row2.addWidget(self.show_excludes_cb)
        
        button_row2.addStretch()
        
        widget_row2 = QWidget()
        widget_row2.setLayout(button_row2)
        widget_row2.setStyleSheet("background-color: #1e1e1e;")
        widget_row2.setMaximumHeight(48)
        # Widget will be added to layout later, after auto row
        
        # Configuration fields row (touch delay, stability, passing distance)
        self.config_row_widget = self._create_config_fields_row()
        # Widget will be added to layout later, after auto row
        
        # Capture UI area
        capture_layout = QVBoxLayout()
        capture_layout.setContentsMargins(12, 12, 12, 12)
        capture_layout.setSpacing(5)
        
        # Add draw buttons row at top
        capture_layout.addWidget(widget_row1)
        
        # Target name input + capture button
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        
        self.target_name_label = QLabel("Data Name")
        self.target_name_label.setStyleSheet("""
            color: #888;
            background-color: #2a2a2a;
            padding: 8px 12px;
            border: 1px solid #444;
            border-radius: 4px;
            font-size: 13px;
        """)
        self.target_name_label.setCursor(Qt.CursorShape.IBeamCursor)
        self.target_name_label.mousePressEvent = lambda e: self.start_text_input()
        input_row.addWidget(self.target_name_label, stretch=1)
        
        # Unique checkbox
        self.unique_cb = QCheckBox("Unique")
        self.unique_cb.setChecked(True)
        self.unique_cb.setToolTip("Save only unique colors (not found elsewhere)")
        self.unique_cb.stateChanged.connect(self.toggle_unique_only)
        input_row.addWidget(self.unique_cb)
        
        self.capture_btn = self._create_button("Capture", self.capture_target)
        self.capture_btn.setMaximumWidth(100)
        input_row.addWidget(self.capture_btn)
        
        capture_layout.addLayout(input_row)
        
        # Auto target display + button with -/+ navigation
        auto_row = QHBoxLayout()
        auto_row.setSpacing(10)
        
        # Previous target button (-)
        self.prev_target_btn = self._create_button("-", self.prev_target)
        self.prev_target_btn.setMaximumWidth(30)
        self.prev_target_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 3px;
                font-weight: bold;
                font-size: 16px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        auto_row.addWidget(self.prev_target_btn)
        
        # Make auto target label editable like target name
        self.auto_target_label = QLabel("Use +/- to select target")
        self.auto_target_label.setStyleSheet("""
            background-color: #2a2a2a;
            padding: 8px 12px;
            border: 1px solid #444;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 13px;
        """)
        self.auto_target_label.setCursor(Qt.CursorShape.IBeamCursor)
        self.auto_target_label.mousePressEvent = lambda event: self.start_auto_target_input()
        auto_row.addWidget(self.auto_target_label, stretch=1)
        
        # Next target button (+)
        self.next_target_btn = self._create_button("+", self.next_target)
        self.next_target_btn.setMaximumWidth(30)
        self.next_target_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 3px;
                font-weight: bold;
                font-size: 16px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        auto_row.addWidget(self.next_target_btn)
        
        self.auto_btn = self._create_button("Auto: OFF", self.toggle_auto_mode)
        self.auto_btn.setMaximumWidth(100)
        auto_row.addWidget(self.auto_btn)
        
        capture_layout.addLayout(auto_row)
        
        # Add target colors and touch delay rows here (between auto and XP rows)
        capture_layout.addWidget(widget_row2)
        capture_layout.addWidget(self.config_row_widget)
        
        # State values row (xp state, total, higher plane, plane size, minimap counter, padding, counter stable)
        state_values_widget = QWidget()
        state_values_row = QHBoxLayout()
        state_values_row.setContentsMargins(10, 0, 10, 0)
        state_values_row.setSpacing(10)
        
        # XP State Display (read-only, green when > 0)
        state_values_row.addWidget(QLabel("xp\nstate"))
        self.state_xp_display = QLabel("0")
        self.state_xp_display.setMinimumWidth(70)
        self.state_xp_display.setMaximumWidth(70)
        self.state_xp_display.setFixedHeight(28)
        self.state_xp_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_xp_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        state_values_row.addWidget(self.state_xp_display)
        
        state_values_row.addSpacing(10)
        
        # Total XP Display (read-only, wider)
        state_values_row.addWidget(QLabel("total"))
        self.total_xp_display = QLabel("---")
        self.total_xp_display.setMinimumWidth(70)
        self.total_xp_display.setMaximumWidth(70)
        self.total_xp_display.setFixedHeight(28)
        self.total_xp_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_xp_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        state_values_row.addWidget(self.total_xp_display)
        
        state_values_row.addSpacing(10)
        
        # XP Sample Rate (editable with +/-)
        state_values_row.addWidget(QLabel("xp sample\nrate"))
        self.sample_minus_btn = self._create_mini_button("-", self.decrease_sample_interval)
        self.sample_display = QLabel("1.0")
        self.sample_display.setMinimumWidth(70)
        self.sample_display.setMaximumWidth(70)
        self.sample_display.setFixedHeight(28)
        self.sample_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sample_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.sample_display.setToolTip("XP sample interval in seconds")
        self.sample_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sample_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('xp_sample_interval', f"{getattr(self.capture, 'xp_sample_interval', 1.0):.2f}")
        self.sample_plus_btn = self._create_mini_button("+", self.increase_sample_interval)
        state_values_row.addWidget(self.sample_minus_btn)
        state_values_row.addWidget(self.sample_display)
        state_values_row.addWidget(QLabel("s"))
        state_values_row.addWidget(self.sample_plus_btn)
        
        state_values_row.addSpacing(10)
        
        # XP Detection Brightness (editable)
        state_values_row.addWidget(QLabel("xp detection\nbrightness"))
        self.brightness_display = QLabel("170")
        self.brightness_display.setMinimumWidth(70)
        self.brightness_display.setMaximumWidth(70)
        self.brightness_display.setFixedHeight(28)
        self.brightness_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brightness_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.brightness_display.setToolTip("XP brightness threshold (double-click to edit)")
        self.brightness_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.brightness_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('xp_brightness_threshold', str(getattr(self.capture, 'xp_brightness_threshold', 170)))
        state_values_row.addWidget(self.brightness_display)
        
        state_values_row.addStretch()
        
        state_values_widget.setLayout(state_values_row)
        state_values_widget.setStyleSheet("background-color: #1e1e1e;")
        state_values_widget.setMaximumHeight(48)
        capture_layout.addWidget(state_values_widget)
        
        # Plane row (higher plane, plane size)
        plane_row_widget = QWidget()
        plane_row = QHBoxLayout()
        plane_row.setContentsMargins(10, 0, 10, 0)
        plane_row.setSpacing(10)
        
        # Higher Plane Display (read-only, green when true)
        plane_row.addWidget(QLabel("higher\nplane"))
        self.higher_plane_display = QLabel("0")
        self.higher_plane_display.setMinimumWidth(70)
        self.higher_plane_display.setMaximumWidth(70)
        self.higher_plane_display.setFixedHeight(28)
        self.higher_plane_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.higher_plane_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        plane_row.addWidget(self.higher_plane_display)
        
        plane_row.addSpacing(10)
        
        # Plane Size (editable with +/-)
        plane_row.addWidget(QLabel("plane\nsize"))
        self.plane_size_minus_btn = self._create_mini_button("-", self.decrease_plane_size)
        self.plane_size_display = QLabel("5")
        self.plane_size_display.setMinimumWidth(70)
        self.plane_size_display.setMaximumWidth(70)
        self.plane_size_display.setFixedHeight(28)
        self.plane_size_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plane_size_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.plane_size_display.setToolTip("Plane size for state evaluation")
        self.plane_size_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plane_size_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('plane_size', str(self.capture.config.plane_size))
        self.plane_size_plus_btn = self._create_mini_button("+", self.increase_plane_size)
        plane_row.addWidget(self.plane_size_minus_btn)
        plane_row.addWidget(self.plane_size_display)
        plane_row.addWidget(self.plane_size_plus_btn)
        
        plane_row.addStretch()
        
        plane_row_widget.setLayout(plane_row)
        plane_row_widget.setStyleSheet("background-color: #1e1e1e;")
        plane_row_widget.setMaximumHeight(48)
        capture_layout.addWidget(plane_row_widget)
        
        # Minimap row (minimap counter, padding, counter stability)
        minimap_row_widget = QWidget()
        minimap_row = QHBoxLayout()
        minimap_row.setContentsMargins(10, 0, 10, 0)
        minimap_row.setSpacing(10)
        
        # Plane Counter Display (read-only, green when > 0)
        minimap_row.addWidget(QLabel("minimap\ncounter"))
        self.minimap_counter_display = QLabel("0")
        self.minimap_counter_display.setMinimumWidth(70)
        self.minimap_counter_display.setMaximumWidth(70)
        self.minimap_counter_display.setFixedHeight(28)
        self.minimap_counter_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minimap_counter_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        minimap_row.addWidget(self.minimap_counter_display)
        
        minimap_row.addSpacing(10)
        
        # Minimap Counter Padding (editable with +/-)
        minimap_row.addWidget(QLabel("padding"))
        self.plane_padding_minus_btn = self._create_mini_button("-", self.decrease_plane_padding)
        self.plane_padding_display = QLabel("5")
        self.plane_padding_display.setMinimumWidth(70)
        self.plane_padding_display.setMaximumWidth(70)
        self.plane_padding_display.setFixedHeight(28)
        self.plane_padding_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plane_padding_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.plane_padding_display.setToolTip("Minimap padding")
        self.plane_padding_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plane_padding_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('minimap_counter_padding', str(self.capture.config.minimap_counter_padding))
        self.plane_padding_plus_btn = self._create_mini_button("+", self.increase_plane_padding)
        minimap_row.addWidget(self.plane_padding_minus_btn)
        minimap_row.addWidget(self.plane_padding_display)
        minimap_row.addWidget(self.plane_padding_plus_btn)
        
        minimap_row.addSpacing(10)
        
        # Counter Stability Timer (editable with +/-)
        minimap_row.addWidget(QLabel("counter\nstability"))
        self.counter_stability_minus_btn = self._create_mini_button("-", self.decrease_counter_stability)
        self.counter_stability_display = QLabel("1.0")
        self.counter_stability_display.setMinimumWidth(70)
        self.counter_stability_display.setMaximumWidth(70)
        self.counter_stability_display.setFixedHeight(28)
        self.counter_stability_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_stability_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.counter_stability_display.setToolTip("Counter stability timer (seconds)")
        self.counter_stability_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.counter_stability_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('counter_stability_timer', f"{self.capture.config.counter_stability_timer:.1f}")
        self.counter_stability_plus_btn = self._create_mini_button("+", self.increase_counter_stability)
        minimap_row.addWidget(self.counter_stability_minus_btn)
        minimap_row.addWidget(self.counter_stability_display)
        minimap_row.addWidget(QLabel("s"))
        minimap_row.addWidget(self.counter_stability_plus_btn)
        
        minimap_row.addStretch()
        
        minimap_row_widget.setLayout(minimap_row)
        minimap_row_widget.setStyleSheet("background-color: #1e1e1e;")
        minimap_row_widget.setMaximumHeight(48)
        capture_layout.addWidget(minimap_row_widget)
        
        capture_widget = QWidget()
        capture_widget.setLayout(capture_layout)
        capture_widget.setStyleSheet("background-color: #1e1e1e;")
        capture_widget.setMinimumHeight(150)
        main_layout.addWidget(capture_widget)
        
        # Timer for frame updates
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.fetch_and_display_frame)
        self.frame_timer.start(33)  # ~30 FPS
        
        # Initialize UI state
        self.update_button_states()
        
        # Store button color states
        self.button_colors = {
            'target': (0, 120, 0),
            'bounds': (100, 100, 0),
            'exclude': (0, 0, 120),
            'state': (120, 0, 120),
            'filter': (0, 120, 0),
            'auto': (0, 120, 0),
            'off': (60, 60, 60),
        }
    
    def _create_button(self, text: str, callback: Callable) -> QPushButton:
        """Create a modern styled button."""
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #555;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        btn.setMinimumHeight(32)
        return btn
    
    def _create_mini_button(self, text: str, callback: Callable) -> QPushButton:
        """Create a modern small inline button for controls."""
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        btn.setMaximumWidth(35)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 4px 8px;
                border-radius: 3px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #454545;
                border-color: #666;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        btn.setMinimumHeight(24)
        return btn
    
    def _create_state_tracking_row(self):
        """Create the state tracking row with all fields."""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        widget.setStyleSheet("background-color: #1e1e1e;")
        widget.setMaximumHeight(42)
        return widget
    
    def _create_config_fields_row(self):
        """Create the configuration fields row (touch delay, stability, passing distance)."""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        # Touch Delay section
        delay_group = QHBoxLayout()
        delay_group.setSpacing(5)
        
        # Min delay
        delay_group.addWidget(QLabel("touch delay\nmin"))
        self.delay_min_display = QLabel("0.3")
        self.delay_min_display.setMinimumWidth(70)
        self.delay_min_display.setMaximumWidth(70)
        self.delay_min_display.setFixedHeight(28)
        self.delay_min_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delay_min_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.delay_min_display.setToolTip("Min touch delay (seconds) - double-click to edit")
        self.delay_min_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delay_min_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('touch_delay_min', f"{self.capture.config.touch_delay_min:.2f}")
        delay_group.addWidget(self.delay_min_display)
        delay_group.addWidget(QLabel("s"))
        
        # Max delay
        delay_group.addWidget(QLabel("touch delay\nmax"))
        self.delay_max_display = QLabel("4.4")
        self.delay_max_display.setMinimumWidth(70)
        self.delay_max_display.setMaximumWidth(70)
        self.delay_max_display.setFixedHeight(28)
        self.delay_max_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delay_max_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.delay_max_display.setToolTip("Max touch delay (seconds) - double-click to edit")
        self.delay_max_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delay_max_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('touch_delay_max', f"{self.capture.config.touch_delay_max:.2f}")
        delay_group.addWidget(self.delay_max_display)
        delay_group.addWidget(QLabel("s"))
        
        # Mean delay
        delay_group.addWidget(QLabel("touch delay\nmean"))
        self.delay_mean_display = QLabel("0.8")
        self.delay_mean_display.setMinimumWidth(70)
        self.delay_mean_display.setMaximumWidth(70)
        self.delay_mean_display.setFixedHeight(28)
        self.delay_mean_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delay_mean_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.delay_mean_display.setToolTip("Mean touch delay (seconds) - double-click to edit")
        self.delay_mean_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delay_mean_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('touch_delay_mean', f"{self.capture.config.touch_delay_mean:.2f}")
        delay_group.addWidget(self.delay_mean_display)
        delay_group.addWidget(QLabel("s"))
        
        # Std delay
        delay_group.addWidget(QLabel("touch delay\nstd"))
        self.delay_std_display = QLabel("0.6")
        self.delay_std_display.setMinimumWidth(70)
        self.delay_std_display.setMaximumWidth(70)
        self.delay_std_display.setFixedHeight(28)
        self.delay_std_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delay_std_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.delay_std_display.setToolTip("Std deviation touch delay (seconds) - double-click to edit")
        self.delay_std_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delay_std_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('touch_delay_std', f"{self.capture.config.touch_delay_std:.2f}")
        delay_group.addWidget(self.delay_std_display)
        delay_group.addWidget(QLabel("s"))
        
        layout.addLayout(delay_group)
        layout.addSpacing(20)
        
        # Stability timer
        layout.addWidget(QLabel("touch target\nstability"))
        self.stability_display = QLabel("1.0")
        self.stability_display.setMinimumWidth(70)
        self.stability_display.setMaximumWidth(70)
        self.stability_display.setFixedHeight(28)
        self.stability_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stability_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.stability_display.setToolTip("Stability timer (seconds) - double-click to edit")
        self.stability_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stability_display.mouseDoubleClickEvent = lambda e: self.start_field_edit('stability_timer', f"{self.capture.config.stability_timer:.1f}")
        layout.addWidget(self.stability_display)
        layout.addWidget(QLabel("s"))
        
        layout.addSpacing(20)
        
        # Passing distance
        layout.addWidget(QLabel("touch target\npassing"))
        self.passing_dist_display = QLabel("50")
        self.passing_dist_display.setMinimumWidth(70)
        self.passing_dist_display.setMaximumWidth(70)
        self.passing_dist_display.setFixedHeight(28)
        self.passing_dist_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.passing_dist_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        self.passing_dist_display.setToolTip("Passing distance (px) - double-click to edit")
        self.passing_dist_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.passing_dist_display.mouseDoubleClickEvent = lambda e: self.edit_config_field('passing_distance')
        layout.addWidget(self.passing_dist_display)
        layout.addWidget(QLabel("px"))
        
        layout.addStretch()
        
        widget.setLayout(layout)
        widget.setStyleSheet("background-color: #1e1e1e;")
        widget.setMaximumHeight(48)
        return widget
    
    def fetch_and_display_frame(self):
        """Fetch frame from capture and emit signal."""
        try:
            # Update auto-touch logic before frame (if method exists)
            if hasattr(self.capture, 'update_auto_touch') and callable(self.capture.update_auto_touch):
                try:
                    self.capture.update_auto_touch()
                except Exception as e:
                    # Don't let auto-touch errors crash frame display
                    print(f"Error in auto-touch update: {e}")
            
            frame = self.capture.get_frame_for_display()
            if frame is not None:
                self.signal_emitter.frame_ready.emit(frame)
        except Exception as e:
            print(f"Error fetching frame: {e}")
    
    def update_frame(self, frame: np.ndarray):
        """Update video label with new frame."""
        # Convert BGR to RGB for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)
        
        # Update button states based on capture state
        self.update_button_states()
    
    def update_button_states(self):
        """Update button states and config field displays."""
        # Update config fields row displays
        if hasattr(self, 'delay_min_display'):
            config = self.capture.config
            # Touch delays and timers (display in seconds)
            self.delay_min_display.setText(f"{config.touch_delay_min:.2f}")
            self.delay_max_display.setText(f"{config.touch_delay_max:.2f}")
            self.delay_mean_display.setText(f"{config.touch_delay_mean:.2f}")
            self.delay_std_display.setText(f"{config.touch_delay_std:.2f}")
            self.stability_display.setText(f"{config.stability_timer:.1f}")
            self.passing_dist_display.setText(str(int(config.passing_distance)))
            
            # Override with editing cursor if field is being edited
            editing_field = getattr(self.capture, 'editing_field', None)
            field_temp_input = getattr(self.capture, 'field_temp_input', '')
            if editing_field:
                editing_style = "background-color: #3a4a5a; padding: 5px 10px; border: 2px solid #4a9eff; border-radius: 3px; color: #e0e0e0; font-weight: 600;"
                normal_style = "background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;"
                
                if editing_field == 'touch_delay_min':
                    self.delay_min_display.setText(field_temp_input + "_")
                    self.delay_min_display.setStyleSheet(editing_style)
                elif editing_field == 'touch_delay_max':
                    self.delay_max_display.setText(field_temp_input + "_")
                    self.delay_max_display.setStyleSheet(editing_style)
                elif editing_field == 'touch_delay_mean':
                    self.delay_mean_display.setText(field_temp_input + "_")
                    self.delay_mean_display.setStyleSheet(editing_style)
                elif editing_field == 'touch_delay_std':
                    self.delay_std_display.setText(field_temp_input + "_")
                    self.delay_std_display.setStyleSheet(editing_style)
                elif editing_field == 'stability_timer':
                    self.stability_display.setText(field_temp_input + "_")
                    self.stability_display.setStyleSheet(editing_style)
                elif editing_field == 'passing_distance':
                    self.passing_dist_display.setText(field_temp_input + "_")
                    self.passing_dist_display.setStyleSheet(editing_style)
        
        # Update config  text and colors based on current state."""
        self.target_btn.setText("Draw Target: ON" if self.capture.target_mode else "Draw Target: OFF")
        self.bounds_btn.setText("Draw Bounds: ON" if self.capture.bounds_mode else "Draw Bounds: OFF")
        self.exclude_btn.setText("Draw Exclude: ON" if self.capture.exclude_mode else "Draw Exclude: OFF")
        self.state_btn.setText("State: ON" if self.capture.state_tracking else "State: OFF")
        self.xp_btn.setText("XP: ON" if self.capture.xp_tracking else "XP: OFF")
        self.filter_btn.setText("Filter: ON" if self.capture.show_filtered else "Filter: OFF")
        self.auto_btn.setText("Auto: ON" if self.capture.auto_mode else "Auto: OFF")
        
        # Update draw button colors to match selection box colors
        if self.capture.target_mode:
            self.target_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00ff00;
                    color: #000000;
                    border: 1px solid #00cc00;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00dd00;
                }
            """)
        else:
            self.target_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
        
        if self.capture.bounds_mode:
            self.bounds_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffff00;
                    color: #000000;
                    border: 1px solid #cccc00;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #dddd00;
                }
            """)
        else:
            self.bounds_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
        
        if self.capture.exclude_mode:
            self.exclude_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff0000;
                    color: #ffffff;
                    border: 1px solid #cc0000;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #dd0000;
                }
            """)
        else:
            self.exclude_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
        
        # Update display labels
        self.colors_display.setText(str(self.capture.colors_per_target))
        self.pixels_display.setText(str(self.capture.min_blob_pixels))
        self.blobs_display.setText(str(self.capture.max_blobs) if self.capture.max_blobs > 0 else "∞")
        
        # Update target name (handle text input mode)
        if self.capture.text_input_active:
            self.target_name_label.setText(self.capture.temp_input + "_")
            self.target_name_label.setStyleSheet("""
                color: #e0e0e0;
                background-color: #3a4a5a;
                padding: 8px 12px;
                border: 2px solid #4a9eff;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 600;
            """)
        else:
            self.target_name_label.setText(self.capture.target_name if self.capture.target_name else "Data Name")
            text_color = "#888" if not self.capture.target_name else "#e0e0e0"
            self.target_name_label.setStyleSheet(f"""
                color: {text_color};
                background-color: #2a2a2a;
                padding: 8px 12px;
                border: 1px solid #444;
                border-radius: 4px;
                font-size: 13px;
            """)
        
        # Update auto target label with text input or manual target selection
        if hasattr(self.capture, 'auto_target_input_active') and self.capture.auto_target_input_active:
            # Show text input mode
            auto_text = self.capture.auto_temp_input + "_"
            self.auto_target_label.setStyleSheet("""
                background-color: #3a4a5a;
                padding: 8px 12px;
                border: 2px solid #4a9eff;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 13px;
                font-weight: 600;
            """)
        elif hasattr(self.capture, 'manual_target_name') and self.capture.manual_target_name:
            auto_text = self.capture.manual_target_name
            self.auto_target_label.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #444; border-radius: 3px; color: #e0e0e0;")
        elif self.capture.state_tracking:
            # State tracking is on - show auto target behavior
            current_auto_target = self.capture.get_current_auto_target()
            if current_auto_target:
                auto_text = current_auto_target
                
                # Add status and timing information if auto mode is on
                if self.capture.auto_mode:
                    import time
                    current_time = time.time()
                    time_until_next = self.capture.next_touch_interval - (current_time - self.capture.last_auto_touch)
                    
                    # Determine current state
                    if getattr(self.capture, 'auto_target_passed', False):
                        status_text = " [passed]"
                        status_color = "#6f6"
                    elif getattr(self.capture, 'auto_target_touched', False):
                        status_text = " [checking pass]"
                        status_color = "#fc6"
                    elif time_until_next > 0:
                        status_text = f" [wait {time_until_next:.1f}s]"
                        status_color = "#cc6"
                    else:
                        # Check if target is stable
                        if hasattr(self.capture, 'auto_target_stable_since') and self.capture.auto_target_stable_since:
                            stable_duration = current_time - self.capture.auto_target_stable_since
                            if stable_duration >= self.capture.config.stability_timer:
                                status_text = " [ready]"
                                status_color = "#6f6"
                            else:
                                remaining = self.capture.config.stability_timer - stable_duration
                                status_text = f" [stabilize {remaining:.1f}s]"
                                status_color = "#c6c"
                        else:
                            status_text = " [stabilizing]"
                            status_color = "#c6c"
                
                    auto_text += status_text
                    self.auto_target_label.setStyleSheet(f"background-color: #333; padding: 5px; color: {status_color};")
                else:
                    self.auto_target_label.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #444; border-radius: 3px; color: #e0e0e0;")
            else:
                auto_text = "No target (enable State)"
                self.auto_target_label.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #444; border-radius: 3px; color: #888;")
        else:
            auto_text = "Use +/- to select target"
            self.auto_target_label.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #444; border-radius: 3px; color: #888;")
        
        self.auto_target_label.setText(auto_text)
        
        # Update checkboxes
        if hasattr(self.capture, 'show_bounds'):
            self.show_bounds_cb.setChecked(self.capture.show_bounds)
        if hasattr(self.capture, 'show_excludes'):
            self.show_excludes_cb.setChecked(self.capture.show_excludes)
        if hasattr(self.capture, 'unique_only'):
            self.unique_cb.setChecked(self.capture.unique_only)
        
        # Check for field editing (outside state tracking condition since fields can be edited anytime)
        editing_field = getattr(self.capture, 'editing_field', None)
        field_temp_input = getattr(self.capture, 'field_temp_input', '')
        editing_style = "background-color: #3a4a5a; padding: 5px 10px; border: 2px solid #4a9eff; border-radius: 3px; color: #e0e0e0; font-weight: 600;"
        
        # Update state tracking displays if state tracking is enabled
        if self.capture.state_tracking and hasattr(self, 'state_xp_display'):
            # Sample interval (don't overwrite if editing)
            if editing_field == 'xp_sample_interval':
                self.sample_display.setText(field_temp_input + "_")
                self.sample_display.setStyleSheet(editing_style)
            else:
                sample_interval = getattr(self.capture, 'xp_sample_interval', 1.0)
                self.sample_display.setText(f"{sample_interval:.2f}")
                self.sample_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
            
            # Brightness threshold (don't overwrite if editing)
            if editing_field == 'xp_brightness_threshold':
                self.brightness_display.setText(field_temp_input + "_")
                self.brightness_display.setStyleSheet(editing_style)
            else:
                brightness = int(getattr(self.capture, 'xp_brightness_threshold', 170))
                self.brightness_display.setText(str(brightness))
                self.brightness_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
            
            # XP detected (green when non-zero)
            xp_detected = getattr(self.capture, 'xp_detected', '0')
            self.state_xp_display.setText(str(xp_detected))
            if xp_detected != '0':
                self.state_xp_display.setStyleSheet("background-color: #064e3b; padding: 4px 8px; border: 1px solid #065f46; border-radius: 3px; color: #4ade80; font-weight: 600;")
            else:
                self.state_xp_display.setStyleSheet("background-color: #2a2a2a; padding: 4px 8px; border: 1px solid #444; border-radius: 3px; color: #e0e0e0;")
            
            # Total XP
            xp_last_value = getattr(self.capture, 'xp_last_value', None)
            self.total_xp_display.setText(str(xp_last_value) if xp_last_value is not None else "---")
            
            # Higher plane (green when true)
            higher_plane = getattr(self.capture, 'higher_plane', False)
            self.higher_plane_display.setText("1" if higher_plane else "0")
            if higher_plane:
                self.higher_plane_display.setStyleSheet("background-color: #064e3b; padding: 4px 8px; border: 1px solid #065f46; border-radius: 3px; color: #4ade80; font-weight: 600;")
            else:
                self.higher_plane_display.setStyleSheet("background-color: #2a2a2a; padding: 4px 8px; border: 1px solid #444; border-radius: 3px; color: #e0e0e0;")
            
            # Plane size (don't overwrite if editing)
            if editing_field == 'plane_size':
                editing_style = "background-color: #3a4a5a; padding: 5px 10px; border: 2px solid #4a9eff; border-radius: 3px; color: #e0e0e0; font-weight: 600;"
                self.plane_size_display.setText(field_temp_input + "_")
                self.plane_size_display.setStyleSheet(editing_style)
            else:
                plane_size = getattr(self.capture.config, 'plane_size', 5)
                self.plane_size_display.setText(str(plane_size))
                self.plane_size_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
            
            # Minimap counter (green when > 0)
            minimap_counter = getattr(self.capture, 'minimap_counter', 0)
            self.minimap_counter_display.setText(str(minimap_counter))
            if minimap_counter > 0:
                self.minimap_counter_display.setStyleSheet("background-color: #064e3b; padding: 4px 8px; border: 1px solid #065f46; border-radius: 3px; color: #4ade80; font-weight: 600;")
            else:
                self.minimap_counter_display.setStyleSheet("background-color: #2a2a2a; padding: 4px 8px; border: 1px solid #444; border-radius: 3px; color: #e0e0e0;")
            
            # Minimap padding (don't overwrite if editing)
            if editing_field == 'minimap_counter_padding':
                editing_style = "background-color: #3a4a5a; padding: 5px 10px; border: 2px solid #4a9eff; border-radius: 3px; color: #e0e0e0; font-weight: 600;"
                self.plane_padding_display.setText(field_temp_input + "_")
                self.plane_padding_display.setStyleSheet(editing_style)
            else:
                plane_padding = getattr(self.capture.config, 'minimap_counter_padding', 5)
                self.plane_padding_display.setText(str(plane_padding))
                self.plane_padding_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
            
            # Counter stability timer (don't overwrite if editing)
            if editing_field == 'counter_stability_timer':
                editing_style = "background-color: #3a4a5a; padding: 5px 10px; border: 2px solid #4a9eff; border-radius: 3px; color: #e0e0e0; font-weight: 600;"
                self.counter_stability_display.setText(field_temp_input + "_")
                self.counter_stability_display.setStyleSheet(editing_style)
            else:
                counter_stability = getattr(self.capture.config, 'counter_stability_timer', 1.0)
                self.counter_stability_display.setText(f"{counter_stability:.1f}")
                self.counter_stability_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        else:
            # State tracking is off, but still update editable fields if being edited
            if editing_field == 'plane_size':
                self.plane_size_display.setText(field_temp_input + "_")
                self.plane_size_display.setStyleSheet(editing_style)
            else:
                plane_size = getattr(self.capture.config, 'plane_size', 5)
                self.plane_size_display.setText(str(plane_size))
                self.plane_size_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
            
            if editing_field == 'minimap_counter_padding':
                self.plane_padding_display.setText(field_temp_input + "_")
                self.plane_padding_display.setStyleSheet(editing_style)
            else:
                plane_padding = getattr(self.capture.config, 'minimap_counter_padding', 5)
                self.plane_padding_display.setText(str(plane_padding))
                self.plane_padding_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
            
            if editing_field == 'counter_stability_timer':
                self.counter_stability_display.setText(field_temp_input + "_")
                self.counter_stability_display.setStyleSheet(editing_style)
            else:
                counter_stability = getattr(self.capture.config, 'counter_stability_timer', 1.0)
                self.counter_stability_display.setText(f"{counter_stability:.1f}")
                self.counter_stability_display.setStyleSheet("background-color: #2a2a2a; padding: 5px 10px; border: 1px solid #555; border-radius: 3px; color: #e0e0e0; font-weight: 600;")
        
        # Update button colors with modern styling
        target_color = "#10b981" if self.capture.target_mode else "#2d2d2d"
        target_border = "#14b8a6" if self.capture.target_mode else "#444"
        self.target_btn.setStyleSheet(f"""
            background-color: {target_color};
            color: #e0e0e0;
            border: 1px solid {target_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
        
        bounds_color = "#eab308" if self.capture.bounds_mode else "#2d2d2d"
        bounds_border = "#f59e0b" if self.capture.bounds_mode else "#444"
        self.bounds_btn.setStyleSheet(f"""
            background-color: {bounds_color};
            color: #e0e0e0;
            border: 1px solid {bounds_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
        
        exclude_color = "#3b82f6" if self.capture.exclude_mode else "#2d2d2d"
        exclude_border = "#60a5fa" if self.capture.exclude_mode else "#444"
        self.exclude_btn.setStyleSheet(f"""
            background-color: {exclude_color};
            color: #e0e0e0;
            border: 1px solid {exclude_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
        
        state_color = "#a855f7" if self.capture.state_tracking else "#2d2d2d"
        state_border = "#c084fc" if self.capture.state_tracking else "#444"
        self.state_btn.setStyleSheet(f"""
            background-color: {state_color};
            color: #e0e0e0;
            border: 1px solid {state_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
        
        xp_color = "#f59e0b" if self.capture.xp_tracking else "#2d2d2d"
        xp_border = "#fbbf24" if self.capture.xp_tracking else "#444"
        self.xp_btn.setStyleSheet(f"""
            background-color: {xp_color};
            color: #e0e0e0;
            border: 1px solid {xp_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
        
        filter_color = "#10b981" if self.capture.show_filtered else "#2d2d2d"
        filter_border = "#14b8a6" if self.capture.show_filtered else "#444"
        self.filter_btn.setStyleSheet(f"""
            background-color: {filter_color};
            color: #e0e0e0;
            border: 1px solid {filter_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
        
        auto_color = "#10b981" if self.capture.auto_mode else "#2d2d2d"
        auto_border = "#14b8a6" if self.capture.auto_mode else "#444"
        self.auto_btn.setStyleSheet(f"""
            background-color: {auto_color};
            color: #e0e0e0;
            border: 1px solid {auto_border};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        """)
    
    # Button callbacks
    def toggle_target_mode(self):
        self.capture.target_mode = not self.capture.target_mode
        if self.capture.target_mode:
            self.capture.bounds_mode = False
            self.capture.exclude_mode = False
            self.capture.selecting = False
            self.capture.target_selection_rect = None
    
    def toggle_bounds_mode(self):
        self.capture.bounds_mode = not self.capture.bounds_mode
        if self.capture.bounds_mode:
            self.capture.target_mode = False
            self.capture.exclude_mode = False
            self.capture.selecting = False
            self.capture.bounds_selection_rect = None
    
    def toggle_exclude_mode(self):
        self.capture.exclude_mode = not self.capture.exclude_mode
        if self.capture.exclude_mode:
            self.capture.target_mode = False
            self.capture.bounds_mode = False
            self.capture.selecting = False
    
    def toggle_state_tracking(self):
        self.capture.state_tracking = not self.capture.state_tracking
    
    def toggle_xp_tracking(self):
        self.capture.xp_tracking = not self.capture.xp_tracking
    
    def toggle_filter(self):
        self.capture.show_filtered = not self.capture.show_filtered
    
    def toggle_auto_mode(self):
        self.capture.auto_mode = not self.capture.auto_mode
        
        # When auto mode turns on, enable filter and state tracking
        if self.capture.auto_mode:
            self.capture.show_filtered = True
            self.capture.state_tracking = True
    
    def prev_target(self):
        """Navigate to previous target in list."""
        # Exit edit mode if active
        if hasattr(self.capture, 'auto_target_input_active') and self.capture.auto_target_input_active:
            self.capture.auto_target_input_active = False
            self.capture.auto_temp_input = ""
        
        # Get list of available targets from data/targets directory
        import os
        target_files = ['all', 'none']  # Special virtual targets
        if os.path.exists(self.capture.targets_dir):
            target_files.extend(sorted([f[:-5] for f in os.listdir(self.capture.targets_dir) 
                                      if f.endswith('.json')]))
        
        if not target_files:
            return
        
        # Initialize manual target index if not set
        if not hasattr(self.capture, 'manual_target_index'):
            self.capture.manual_target_index = 0
        
        # Move to previous target
        self.capture.manual_target_index = (self.capture.manual_target_index - 1) % len(target_files)
        self.capture.manual_target_name = target_files[self.capture.manual_target_index]
    
    def next_target(self):
        """Navigate to next target in list."""
        # Exit edit mode if active
        if hasattr(self.capture, 'auto_target_input_active') and self.capture.auto_target_input_active:
            self.capture.auto_target_input_active = False
            self.capture.auto_temp_input = ""
        
        # Get list of available targets from data/targets directory
        import os
        target_files = ['all', 'none']  # Special virtual targets
        if os.path.exists(self.capture.targets_dir):
            target_files.extend(sorted([f[:-5] for f in os.listdir(self.capture.targets_dir) 
                                      if f.endswith('.json')]))
        
        if not target_files:
            return
        
        # Initialize manual target index if not set
        if not hasattr(self.capture, 'manual_target_index'):
            self.capture.manual_target_index = 0
        
        # Move to next target
        self.capture.manual_target_index = (self.capture.manual_target_index + 1) % len(target_files)
        self.capture.manual_target_name = target_files[self.capture.manual_target_index]
    
    def increase_colors(self):
        self.capture.colors_per_target = min(self.capture.colors_per_target + 1, 50)
    
    def decrease_colors(self):
        self.capture.colors_per_target = max(self.capture.colors_per_target - 1, 1)
    
    def increase_pixels(self):
        self.capture.min_blob_pixels = min(self.capture.min_blob_pixels + 1, 1000)
    
    def decrease_pixels(self):
        self.capture.min_blob_pixels = max(self.capture.min_blob_pixels - 1, 1)
    
    def increase_blobs(self):
        self.capture.max_blobs = min(self.capture.max_blobs + 1, 100)
    
    def decrease_blobs(self):
        self.capture.max_blobs = max(self.capture.max_blobs - 1, 0)
    
    def toggle_show_bounds(self, state):
        if not hasattr(self.capture, 'show_bounds'):
            self.capture.show_bounds = False
        self.capture.show_bounds = (state == Qt.CheckState.Checked.value)
    
    def toggle_show_excludes(self, state):
        if not hasattr(self.capture, 'show_excludes'):
            self.capture.show_excludes = False
        self.capture.show_excludes = (state == Qt.CheckState.Checked.value)
    
    def toggle_unique_only(self, state):
        if not hasattr(self.capture, 'unique_only'):
            self.capture.unique_only = True
        self.capture.unique_only = (state == Qt.CheckState.Checked.value)
        print(f"Unique colors only: {self.capture.unique_only}")
    
    # State tracking control methods
    def increase_sample_interval(self):
        """Increase XP sample interval by 0.1s."""
        current = getattr(self.capture, 'xp_sample_interval', 1.0)
        self.capture.xp_sample_interval = min(current + 0.1, 10.0)  # Max 10s
    
    def decrease_sample_interval(self):
        """Decrease XP sample interval by 0.1s."""
        current = getattr(self.capture, 'xp_sample_interval', 1.0)
        self.capture.xp_sample_interval = max(current - 0.1, 0.1)  # Min 0.1s
    
    def increase_plane_size(self):
        """Increase plane size."""
        self.capture.config.plane_size = min(self.capture.config.plane_size + 1, 50)
    
    def decrease_plane_size(self):
        """Decrease plane size."""
        self.capture.config.plane_size = max(self.capture.config.plane_size - 1, 1)
    
    def increase_plane_padding(self):
        """Increase minimap padding."""
        self.capture.config.minimap_counter_padding = min(self.capture.config.minimap_counter_padding + 1, 50)
    
    def decrease_plane_padding(self):
        """Decrease minimap padding."""
        self.capture.config.minimap_counter_padding = max(self.capture.config.minimap_counter_padding - 1, 0)
    
    def increase_counter_stability(self):
        """Increase counter stability timer by 0.1s."""
        self.capture.config.counter_stability_timer = min(self.capture.config.counter_stability_timer + 0.1, 10.0)
    
    def decrease_counter_stability(self):
        """Decrease counter stability timer by 0.1s."""
        self.capture.config.counter_stability_timer = max(self.capture.config.counter_stability_timer - 0.1, 0.1)
    
    def start_field_edit(self, field_name, current_value):
        """Start inline text editing for a field."""
        self.capture.editing_field = field_name
        self.capture.field_temp_input = current_value
        print(f"Editing {field_name}, press Enter to confirm or Esc to cancel")
    
    def edit_state_value(self, field_name):
        """Edit state tracking field values via dialog."""
        from PyQt6.QtWidgets import QInputDialog
        
        if field_name == 'xp_sample_interval':
            current = getattr(self.capture, 'xp_sample_interval', 1.0)
            value, ok = QInputDialog.getDouble(self, "Edit XP Sample Interval", 
                                              "Sample interval (seconds):", current, 0.1, 10.0, 1)
            if ok:
                self.capture.xp_sample_interval = value
        elif field_name == 'xp_brightness_threshold':
            current = int(getattr(self.capture, 'xp_brightness_threshold', 170))
            value, ok = QInputDialog.getInt(self, "Edit XP Brightness Threshold", 
                                           "Brightness threshold:", current, 0, 255)
            if ok:
                self.capture.xp_brightness_threshold = value
        elif field_name == 'plane_size':
            current = self.capture.config.plane_size
            value, ok = QInputDialog.getInt(self, "Edit Plane Size", 
                                           "Plane size:", current, 1, 50)
            if ok:
                self.capture.config.plane_size = value
        elif field_name == 'minimap_counter_padding':
            current = self.capture.config.minimap_counter_padding
            value, ok = QInputDialog.getInt(self, "Edit Minimap Counter Padding", 
                                           "Minimap padding:", current, 0, 50)
            if ok:
                self.capture.config.minimap_counter_padding = value
        elif field_name == 'counter_stability_timer':
            current = self.capture.config.counter_stability_timer
            value, ok = QInputDialog.getDouble(self, "Edit Counter Stability Timer", 
                                              "Timer (seconds):", current, 0.1, 10.0, 1)
            if ok:
                self.capture.config.counter_stability_timer = value
    
    def edit_config_field(self, field_name):
        """Edit configuration field values via dialog."""
        from PyQt6.QtWidgets import QInputDialog
        
        config = self.capture.config
        
        if field_name == 'touch_delay_min':
            current = config.touch_delay_min
            value, ok = QInputDialog.getDouble(self, "Edit Min Touch Delay", 
                                              "Min delay (seconds):", current, 0.001, 10.0, 3)
            if ok:
                config.touch_delay_min = value
        elif field_name == 'touch_delay_max':
            current = config.touch_delay_max
            value, ok = QInputDialog.getDouble(self, "Edit Max Touch Delay", 
                                              "Max delay (seconds):", current, 0.001, 20.0, 3)
            if ok:
                config.touch_delay_max = value
        elif field_name == 'touch_delay_mean':
            current = config.touch_delay_mean
            value, ok = QInputDialog.getDouble(self, "Edit Mean Touch Delay", 
                                              "Mean delay (seconds):", current, 0.001, 10.0, 3)
            if ok:
                config.touch_delay_mean = value
        elif field_name == 'touch_delay_std':
            current = config.touch_delay_std
            value, ok = QInputDialog.getDouble(self, "Edit Std Touch Delay", 
                                              "Std deviation (seconds):", current, 0.001, 5.0, 3)
            if ok:
                config.touch_delay_std = value
        elif field_name == 'stability_timer':
            current = config.stability_timer
            value, ok = QInputDialog.getDouble(self, "Edit Stability Timer", 
                                              "Stability timer (seconds):", current, 0.1, 10.0, 1)
            if ok:
                config.stability_timer = value
        elif field_name == 'passing_distance':
            current = int(config.passing_distance)
            value, ok = QInputDialog.getInt(self, "Edit Passing Distance", 
                                           "Passing distance (px):", current, 1, 500)
            if ok:
                config.passing_distance = value
    
    def capture_target(self):
        """Capture current target configuration."""
        if hasattr(self.capture, 'capture_current_target'):
            self.capture.capture_current_target()
        else:
            print("Capture functionality not available")
    
    def edit_config_value(self):
        """Show dialog to edit configuration values."""
        items = [
            "Delay Min (seconds)",
            "Delay Max (seconds)",
            "Delay Mean (seconds)",
            "Delay Std (seconds)",
            "Stability Timer (seconds)",
            "Passing Distance (pixels)",
            "Plane Size",
            "Minimap Counter Padding",
            "Counter Stability Timer",
            "XP Brightness Threshold"
        ]
        
        item, ok = QInputDialog.getItem(self, "Edit Configuration", 
                                        "Select value to edit:", items, 0, False)
        
        if not ok:
            return
        
        config = self.capture.config
        
        # Get current value and edit
        if item == "Delay Min (seconds)":
            current = config.touch_delay_min
            value, ok = QInputDialog.getDouble(self, "Edit", "Delay Min (seconds):", 
                                               current, 0.001, 30.0, 3)
            if ok:
                config.touch_delay_min = value
                print(f"Delay min set to {value}s")
        
        elif item == "Delay Max (seconds)":
            current = config.touch_delay_max
            value, ok = QInputDialog.getDouble(self, "Edit", "Delay Max (seconds):", 
                                               current, 0.001, 30.0, 3)
            if ok:
                config.touch_delay_max = value
                print(f"Delay max set to {value}s")
        
        elif item == "Delay Mean (seconds)":
            current = config.touch_delay_mean
            value, ok = QInputDialog.getDouble(self, "Edit", "Delay Mean (seconds):", 
                                               current, 0.001, 30.0, 3)
            if ok:
                config.touch_delay_mean = value
                print(f"Delay mean set to {value}s")
        
        elif item == "Delay Std (seconds)":
            current = config.touch_delay_std
            value, ok = QInputDialog.getDouble(self, "Edit", "Delay Std (seconds):", 
                                               current, 0.001, 30.0, 3)
            if ok:
                config.touch_delay_std = value
                print(f"Delay std set to {value}s")
        
        elif item == "Stability Timer (seconds)":
            current = config.stability_timer
            value, ok = QInputDialog.getDouble(self, "Edit", "Stability Timer (seconds):", 
                                               current, 0.1, 30.0, 1)
            if ok:
                config.stability_timer = value
                print(f"Stability timer set to {value}s")
        
        elif item == "Passing Distance (pixels)":
            current = config.passing_distance
            value, ok = QInputDialog.getInt(self, "Edit", "Passing Distance (pixels):", 
                                            current, 1, 1000)
            if ok:
                config.passing_distance = value
                print(f"Passing distance set to {value}px")
        
        elif item == "Plane Size":
            current = config.plane_size
            value, ok = QInputDialog.getInt(self, "Edit", "Plane Size:", 
                                            current, 1, 100)
            if ok:
                config.plane_size = value
                print(f"Plane size set to {value}")
        
        elif item == "Minimap Counter Padding":
            current = config.minimap_counter_padding
            value, ok = QInputDialog.getInt(self, "Edit", "Minimap Counter Padding:", 
                                            current, 0, 100)
            if ok:
                config.minimap_counter_padding = value
                print(f"Minimap padding set to {value}")
        
        elif item == "Counter Stability Timer":
            current = config.counter_stability_timer
            value, ok = QInputDialog.getDouble(self, "Edit", "Counter Stability Timer (seconds):", 
                                               current, 0.1, 10.0, 1)
            if ok:
                config.counter_stability_timer = value
                print(f"Counter stability timer set to {value}s")
        
        elif item == "XP Brightness Threshold":
            current = getattr(self.capture, 'xp_brightness_threshold', 170)
            value, ok = QInputDialog.getInt(self, "Edit", "XP Brightness Threshold:", 
                                            current, 0, 255)
            if ok:
                self.capture.xp_brightness_threshold = value
                print(f"XP brightness threshold set to {value}")
    
    def start_text_input(self):
        """Start text input for target name."""
        # If already in edit mode and no changes made, restore original and cancel
        if hasattr(self.capture, 'text_input_active') and self.capture.text_input_active:
            if self.capture.temp_input == "":
                # Restore original value
                if hasattr(self.capture, 'target_name_original'):
                    self.capture.target_name = self.capture.target_name_original
                self.capture.text_input_active = False
                self.capture.temp_input = ""
                return
        
        # Store original value before editing
        self.capture.target_name_original = getattr(self.capture, 'target_name', None)
        self.capture.text_input_active = True
        self.capture.temp_input = ""
    
    def start_auto_target_input(self):
        """Start text input for auto target name."""
        # If already in edit mode and no changes made, restore original and cancel
        if hasattr(self.capture, 'auto_target_input_active') and self.capture.auto_target_input_active:
            if self.capture.auto_temp_input == "":
                # Restore original value
                if hasattr(self.capture, 'auto_target_original'):
                    self.capture.manual_target_name = self.capture.auto_target_original
                self.capture.auto_target_input_active = False
                self.capture.auto_temp_input = ""
                return
        
        # Store original value before editing
        self.capture.auto_target_original = getattr(self.capture, 'manual_target_name', None)
        self.capture.auto_target_input_active = True
        self.capture.auto_temp_input = ""
    
    def on_video_click(self, event):
        """Handle mouse click on video label."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert click position to video coordinates
            x = int(event.pos().x() / self.video_label.width() * self.capture.frame_bgr.shape[1])
            y = int(event.pos().y() / self.video_label.height() * self.capture.frame_bgr.shape[0])
            
            # Call existing mouse handler
            self.capture.on_mouse_click(x, y, event.button())
    
    def on_video_mouse_move(self, event):
        """Handle mouse move on video label."""
        x = int(event.pos().x() / self.video_label.width() * self.capture.frame_bgr.shape[1])
        y = int(event.pos().y() / self.video_label.height() * self.capture.frame_bgr.shape[0])
        self.capture.on_mouse_move(x, y)
    
    def on_video_mouse_release(self, event):
        """Handle mouse release on video label."""
        x = int(event.pos().x() / self.video_label.width() * self.capture.frame_bgr.shape[1])
        y = int(event.pos().y() / self.video_label.height() * self.capture.frame_bgr.shape[0])
        self.capture.on_mouse_release(x, y)
    
    def keyPressEvent(self, event):
        """Handle keyboard input."""
        if not event.isAutoRepeat():
            self.capture.on_key_press(event.key(), event.text())
        # Always update UI after key press
        self.update_button_states()
    
    def closeEvent(self, event):
        """Clean up when window closes."""
        self.frame_timer.stop()
        event.accept()
