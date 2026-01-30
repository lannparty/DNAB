#!/usr/bin/env python3
"""
Android Window Mirror - Captures pixels from "Pixel 4a (5G)" window
and displays them in a mirror window positioned below it.

Uses X11 composite extension for efficient window capture.
"""

import argparse
import sys
import time
import os
import signal
import psutil
import subprocess
import json
import numpy as np
import cv2
from typing import Optional, Tuple

from android_injections.ui.mouse_handler import create_mouse_callback
from android_injections.ui.ui_renderer import render_frame
from android_injections.ui.keyboard_handler import process_keyboard_event
from android_injections.vision.color_filter import filter_unique_colors
from android_injections.vision.state_eval import evaluate_state_fields
from android_injections.targeting.target_loader import load_all_targets
from android_injections.targeting.target_saver import save_target, save_bounds
from android_injections.targeting.color_analysis import analyze_unique_colors
from android_injections.targeting.exclusion_manager import load_excluded_regions, save_excluded_region
from android_injections.automation.auto_target import get_current_auto_target
from android_injections.automation.delay_manager import calculate_next_delay, is_delay_ready, execute_auto_touch
from android_injections.automation.state_manager import reset_auto_state, is_target_stable, is_dot_stable, check_target_passed, check_target_timeout
from android_injections.config.game_config import create_game_config, GameConfig

try:
    import Xlib
    import Xlib.display
    import Xlib.X
    import Xlib.protocol.event
    from Xlib.ext import composite
except ImportError:
    print("Error: python-xlib not installed")
    print("Install with: pip install python-xlib")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed")
    print("Install with: pip install Pillow")
    sys.exit(1)

try:
    import pytesseract
except ImportError:
    print("Error: pytesseract not installed")
    print("Install with: pip install pytesseract")
    print("Also install tesseract-ocr: sudo apt install tesseract-ocr")
    sys.exit(1)


class WindowCapture:
    """Captures window content using X11."""
    
    def __init__(self, window_name: str, target_fps: int = 30, display_scale: float = 0.5, benchmark: bool = False):
        self.window_name = window_name
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps
        self.display_scale = display_scale
        self.benchmark = benchmark
        
        # Initialize configuration with default game parameters
        self.config = GameConfig(
            colors_per_target=20,
            min_blob_pixels=2,
            max_blobs=1,
        )
        
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        self.window = None
        self.window_geom = None
        
        # Initialize filter colors (loaded from targets)
        self.filter_colors = set()
        self.target_bounds = {}  # Maps target_name -> (x1, y1, x2, y2) search bounds
        
        # Target selection for ADB touch
        self.selected_target_name = ""
        self.detected_targets = {}  # Maps target_name -> (x, y, w, h) in original coordinates
        
        # Create targets directory if it doesn't exist
        # Data directories are now in root/data/ folder
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.targets_dir = os.path.join(project_root, 'data', 'targets')
        os.makedirs(self.targets_dir, exist_ok=True)
        
        # Create bounds and exclude directories at same level as targets
        self.bounds_dir = os.path.join(project_root, 'data', 'bounds')
        self.exclude_dir = os.path.join(project_root, 'data', 'exclude')
        os.makedirs(self.bounds_dir, exist_ok=True)
        os.makedirs(self.exclude_dir, exist_ok=True)
        
        # Load all targets on startup
        self.load_all_targets()
        
    def find_window_by_name(self, name: str):
        """Find window by name and return the window object."""
        def search_windows(window):
            try:
                window_name = window.get_wm_name()
                if window_name and name in window_name:
                    return window
            except:
                pass
            
            # Search children
            try:
                children = window.query_tree().children
                for child in children:
                    result = search_windows(child)
                    if result:
                        return result
            except:
                pass
            
            return None
        
        return search_windows(self.root)
    
    def get_client_window(self, window):
        """Get the actual client window (without decorations) from a frame window."""
        try:
            # Check if this window has the _NET_FRAME_EXTENTS property (means it has decorations)
            children = window.query_tree().children
            if children:
                # Usually the first child is the actual client window
                for child in children:
                    # Get the child's geometry to verify it's substantial
                    try:
                        child_geom = child.get_geometry()
                        parent_geom = window.get_geometry()
                        # If child is close to parent size, it's likely the client window
                        if child_geom.width > parent_geom.width * 0.8:
                            return child
                    except:
                        pass
        except:
            pass
        
        # If no suitable child found, return original window
        return window
    
    def get_window_geometry(self, window) -> Tuple[int, int, int, int]:
        """Get window geometry (x, y, width, height) with proper screen coordinates."""
        geom = window.get_geometry()
        
        # Get position relative to root window
        coords = window.translate_coords(self.root, 0, 0)
        
        # translate_coords can return negative values, but actual screen position is absolute
        abs_x = abs(coords.x)
        abs_y = abs(coords.y)
        
        # Get screen dimensions
        screen = self.display.screen()
        screen_width = screen.width_in_pixels
        screen_height = screen.height_in_pixels
        screen_width_mm = screen.width_in_mms
        screen_height_mm = screen.height_in_mms
        
        # Calculate DPI to detect scaling
        dpi_x = (screen_width / screen_width_mm) * 25.4
        dpi_y = (screen_height / screen_height_mm) * 25.4
        
        # Typical scale factors: 96 DPI = 100%, 192 DPI = 200%, etc.
        scale_factor = round(dpi_x / 96.0)
        
        print(f"Screen dimensions: {screen_width}x{screen_height}px ({screen_width_mm}x{screen_height_mm}mm)")
        print(f"Screen DPI: {dpi_x:.1f}x{dpi_y:.1f}, Scale factor: {scale_factor}x (detected)")
        
        # Return absolute screen coordinates and store scale
        self.scale_factor = scale_factor
        return (abs_x, abs_y, geom.width, geom.height)
    
    def capture_window_pil(self, window) -> Optional[np.ndarray]:
        """Capture window using PIL and convert to numpy array."""
        try:
            # Get window pixmap
            geom = window.get_geometry()
            raw = window.get_image(0, 0, geom.width, geom.height, Xlib.X.ZPixmap, 0xffffffff)
            
            # Convert to PIL Image
            image = Image.frombytes("RGB", (geom.width, geom.height), raw.data, "raw", "BGRX")
            
            # Convert to numpy array for OpenCV
            return np.array(image)
        except Exception as e:
            print(f"Capture error: {e}")
            return None
    
    # Mouse callback is now in ui.mouse_handler module
    # Created as a factory function that binds to this instance
    
    def save_target(self):
        """Save colors sorted by prevalence to a target file."""
        return save_target(self)
    
    def save_excluded_region(self):
        """Save the current selection as an excluded region to named exclusion file."""
        return save_excluded_region(self)
    
    def load_excluded_regions(self):
        """Load excluded regions from all files in exclude subdirectory."""
        return load_excluded_regions(self)
    
    def load_auto_targets(self):
        """Initialize auto target system. Targets are now determined by state values."""
        print("Auto target system initialized - targets determined by higher_plane and minimap_counter")
    
    def get_text_size_cached(self, text, font, scale, thickness):
        """Get text size with caching to avoid repeated expensive calls."""
        cache_key = (text, font, scale, thickness)
        if cache_key not in self._text_size_cache:
            # Limit cache size to prevent unbounded growth from dynamic text (numbers, timers)
            if len(self._text_size_cache) >= 500:
                # Clear oldest half of cache entries when limit reached
                keys_to_remove = list(self._text_size_cache.keys())[:250]
                for key in keys_to_remove:
                    del self._text_size_cache[key]
            self._text_size_cache[cache_key] = cv2.getTextSize(text, font, scale, thickness)[0]
        return self._text_size_cache[cache_key]
    
    def get_current_auto_target(self):
        """Determine current target based on higher_plane and minimap_counter state values."""
        return get_current_auto_target(self)
    
    def save_bounds(self):
        """Save the current selection as bounds for the target."""
        return save_bounds(self)
    
    def load_all_targets(self):
        """Load all color targets from JSON files in the targets directory."""
        return load_all_targets(self)
    
    def analyze_unique_colors(self):
        """Find RGB colors that appear in the selection box but nowhere else."""
        return analyze_unique_colors(self)
        print()
    
    def evaluate_state_fields(self, frame):
        """Evaluate state fields (XP, higher_plane) regardless of filter status."""
        return evaluate_state_fields(self, frame)
    
    def filter_unique_colors(self, frame, apply_scale=1.0):
        """Create a filtered image showing only colors from loaded targets."""
        return filter_unique_colors(self, frame, apply_scale)
    
    def run(self):
        """Main capture and display loop."""
        print(f"Searching for window: '{self.window_name}'...")
        
        # Find the target window
        self.window = self.find_window_by_name(self.window_name)
        if not self.window:
            print(f"Error: Window '{self.window_name}' not found!")
            print("Available windows:")
            self.list_windows()
            return
        
        # Get the client window (without title bar decorations)
        self.client_window = self.get_client_window(self.window)
        print(f"Using {'client window' if self.client_window != self.window else 'main window'} for capture")
        
        # Get geometry from the client window (the actual capture area without title bar)
        client_geom = self.client_window.get_geometry()
        client_width = client_geom.width
        client_height = client_geom.height
        print(f"Client window dimensions: {client_width}x{client_height}")
        
        # Check if resolution matches Pixel 4a (5G) expected resolution (portrait or landscape)
        expected_width = 1080
        expected_height = 2340
        leeway = 5
        
        # Check portrait orientation (1080x2340)
        portrait_match = (expected_width - leeway <= client_width <= expected_width + leeway and 
                         expected_height - leeway <= client_height <= expected_height + leeway)
        
        # Check landscape orientation (2340x1080)
        landscape_match = (expected_height - leeway <= client_width <= expected_height + leeway and 
                          expected_width - leeway <= client_height <= expected_width + leeway)
        
        if not (portrait_match or landscape_match):
            print(f"\n⚠️  ERROR: Window resolution mismatch!")
            print(f"Expected: {expected_width}x{expected_height} or {expected_height}x{expected_width} (±{leeway}px) (Pixel 4a 5G)")
            print(f"Got: {client_width}x{client_height}")
            print(f"\nPlease resize the emulator window to match the phone's resolution.")
            return
        
        x, y, width, height = self.get_window_geometry(self.window)
        print(f"Found window at: x={x}, y={y}, width={width}, height={height}")
        
        # Calculate position for mirror window - directly below source window
        # Keep same x coordinate (even if negative) to stay aligned
        mirror_x = x
        mirror_y = y + height + 30  # 30 pixels gap for window decorations
        
        # Create display window with NORMAL flag to prevent auto-resizing
        window_title = f"Mirror: {self.window_name}"
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        
        # Set window to be non-resizable to prevent size changes when filter toggles
        cv2.setWindowProperty(window_title, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
        
        print(f"Mirror window will be positioned at: x={mirror_x}, y={mirror_y}")
        print(f"Initial window dimensions: {width}x{height}")
        print(f"Target FPS: {self.target_fps}")
        
        frame_count = 0
        start_time = time.time()
        window_positioned = False
        
        # Rectangle selection state
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        self.target_selection_rect = None  # Selection for target mode
        self.bounds_selection_rect = None  # Selection for bounds mode
        self.exclude_selection_rect = None  # Selection for exclude mode
        self.current_frame = None
        self.unique_colors = set()
        self.show_filtered = False
        self.unique_only = True  # Toggle for capturing only unique colors vs all colors
        self.target_name = ""
        self.text_input_active = False
        self.target_selector_active = False
        self.target_mode = False  # Toggle for target mode
        self.bounds_mode = False  # Toggle for bounds mode
        self.exclude_mode = False  # Toggle for exclude mode
        self.state_tracking = False  # Toggle for state field evaluation
        self.excluded_regions = []  # List of (x1, y1, x2, y2) tuples to exclude from filter
        self.show_bounds = False  # Toggle to show all bounds rectangles
        self.show_excludes = False  # Toggle to show all exclude rectangles
        self.auto_view_mode = False  # Toggle to show only current auto target in blob detection
        
        # Editing state for number fields
        self.editing_colors = False
        self.editing_min_pixels = False
        self.editing_max_blobs = False
        self.editing_delay_min = False
        self.editing_delay_max = False
        self.editing_delay_mean = False
        self.editing_delay_std = False
        self.editing_stability = False
        self.editing_passing_dist = False
        self.temp_input = ""
        
        # Plane detection state
        self.higher_plane = False  # Whether a black square was detected in minimap
        self.minimap_counter = 0  # Number of distinct pixel groups for minimap_counter target
        self.editing_plane_size = False
        self.editing_minimap_counter_padding = False
        
        # Auto-touch state
        self.auto_mode = False
        self.last_auto_touch = 0
        self.next_touch_interval = self.config.touch_delay_mean  # Start with mean
        
        # XP detection state (uses same stability timer as targets)
        self.xp_last_value = None  # Last stable XP value (confirmed for stability_timer seconds)
        self.xp_current_reading = None  # Current OCR reading
        self.xp_reading_first_seen = None  # Timestamp when current reading was first seen
        self.xp_last_sample_time = 0  # Last time we sampled XP with OCR
        self.xp_trigger_time = None  # Timestamp when XP increases
        self.xp_detected = "0"
        self.editing_xp_brightness = False
        self.editing_xp_sample_interval = False
        
        # Create CLAHE object once (reused for all XP OCR preprocessing)
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # Minimap counter stability tracking
        self.minimap_counter_prev_value = None
        self.minimap_counter_stable_since = None
        
        # Cache for text sizes to avoid repeated cv2.getTextSize calls
        self._text_size_cache = {}
        
        self.auto_target_list = []  # List of target names from targets folder
        self.auto_target_index = 0  # Current target index
        self.auto_target_passed = False  # Whether target passed (XP gained)
        self.auto_target_touched = False  # Whether we've touched the current target at least once
        self.auto_touched_time = None  # Time when target was touched (for pass pause)
        self.auto_target_prev_pos = None  # Previous position (x, y, w, h) for motion detection
        self.auto_target_stable_since = None  # Time when target became stable
        self.auto_touched_position = None  # Position (x, y) where target was touched
        self.auto_dot_prev_pos = None  # Previous dot position (x, y) for stability tracking
        self.auto_dot_stable_since = None  # Time when dot became stable
        self.auto_target_last_seen = None  # Last time any target was detected (for timeout)
        self.load_auto_targets()
        
        # Create targets directory if it doesn't exist
        self.targets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'targets')
        os.makedirs(self.targets_dir, exist_ok=True)
        
        # Create bounds and exclude directories at same level as targets
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.bounds_dir = os.path.join(project_root, 'data', 'bounds')
        self.exclude_dir = os.path.join(project_root, 'data', 'exclude')
        os.makedirs(self.bounds_dir, exist_ok=True)
        os.makedirs(self.exclude_dir, exist_ok=True)
        
        # Set mouse callback using the extracted handler factory
        mouse_callback = create_mouse_callback(self)
        cv2.setMouseCallback(window_title, mouse_callback)
        
        while True:
            loop_start = time.time()
            
            # Capture client window (without title bar)
            frame = self.capture_window_pil(self.client_window)
            
            if frame is not None:
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Store current frame as BGR for color analysis
                self.current_frame = frame_bgr.copy()
                
                # Evaluate state fields only if state tracking is enabled
                if self.state_tracking:
                    self.evaluate_state_fields(frame_bgr)
                
                # Apply filter at full resolution before scaling (filter function handles scaling)
                if self.show_filtered:
                    display_frame = self.filter_unique_colors(frame_bgr.copy(), apply_scale=self.display_scale)
                    # Frame is already scaled by filter_unique_colors, skip additional scaling
                else:
                    display_frame = frame_bgr.copy()
                    # Scale down display to match desktop environment scaling
                    if self.display_scale != 1.0:
                        h, w = display_frame.shape[:2]
                        new_w = int(w * self.display_scale)
                        new_h = int(h * self.display_scale)
                        display_frame = cv2.resize(display_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                # Always scale frame_bgr for drawing selection rectangles
                if self.display_scale != 1.0:
                    h, w = frame_bgr.shape[:2]
                    new_w = int(w * self.display_scale)
                    new_h = int(h * self.display_scale)
                    frame_bgr = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                # Draw selection rectangle only when filter is OFF
                if not self.show_filtered:
                    # Draw selection rectangle if active
                    if self.selecting and self.selection_start and self.selection_end:
                        # Red for exclude, yellow for bounds, green for target
                        if self.exclude_mode:
                            color = (0, 0, 255)  # Red
                        elif self.bounds_mode:
                            color = (0, 255, 255)  # Yellow
                        else:
                            color = (0, 255, 0)  # Green
                        cv2.rectangle(display_frame, self.selection_start, self.selection_end, color, 2)
                    else:
                        # Show saved selections in their appropriate colors
                        if self.target_selection_rect:
                            cv2.rectangle(display_frame, self.target_selection_rect[0], self.target_selection_rect[1], (0, 255, 0), 2)  # Green
                        if self.bounds_selection_rect:
                            cv2.rectangle(display_frame, self.bounds_selection_rect[0], self.bounds_selection_rect[1], (0, 255, 255), 2)  # Yellow
                
                # Draw all bounds rectangles with labels if show_bounds is enabled
                if self.show_bounds and hasattr(self, 'bounds_with_names'):
                    for bound in self.bounds_with_names:
                        bx1, by1, bx2, by2, name = bound
                        # Scale to display size
                        if self.display_scale != 1.0:
                            bx1 = int(bx1 * self.display_scale)
                            by1 = int(by1 * self.display_scale)
                            bx2 = int(bx2 * self.display_scale)
                            by2 = int(by2 * self.display_scale)
                        # Draw yellow rectangle
                        cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), (0, 255, 255), 2)
                        # Draw label
                        label_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                        label_y = max(by1 - 5, label_size[1] + 5)
                        cv2.putText(display_frame, name, (bx1, label_y), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Draw all excluded regions with labels if show_excludes is enabled
                if self.show_excludes and hasattr(self, 'excluded_regions_with_names'):
                    for exclude in self.excluded_regions_with_names:
                        ex1, ey1, ex2, ey2, name = exclude
                        # Scale to display size
                        if self.display_scale != 1.0:
                            ex1 = int(ex1 * self.display_scale)
                            ey1 = int(ey1 * self.display_scale)
                            ex2 = int(ex2 * self.display_scale)
                            ey2 = int(ey2 * self.display_scale)
                        # Draw red rectangle
                        cv2.rectangle(display_frame, (ex1, ey1), (ex2, ey2), (0, 0, 255), 2)
                        # Draw label
                        label_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                        label_y = max(ey1 - 5, label_size[1] + 5)
                        cv2.putText(display_frame, name, (ex1, label_y), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
                # Draw white dot in center of screen
                h, w = display_frame.shape[:2]
                center_x = w // 2
                center_y = h // 2
                cv2.circle(display_frame, (center_x, center_y), 3, (255, 255, 255), -1)
                
                # Add button area at bottom
                button_height = 40
                capture_ui_height = 220  # Five sections: capture button + target selector/touch + auto row + timer settings + state row
                total_bottom_height = button_height + button_height + capture_ui_height  # First row buttons + filter button + capture UI
                h, w = display_frame.shape[:2]
                
                # Create canvas with extra space for buttons and capture UI
                canvas = np.zeros((h + total_bottom_height, w, 3), dtype=np.uint8)
                canvas[:h, :] = display_frame
                
                # Draw first buttons row (Target, Bounds, Exclude, State)
                button_y = h
                button_width = w // 4  # 4 buttons in first row
                
                # Target Mode button (first third)
                target_button_color = (0, 120, 0) if self.target_mode else (60, 60, 60)
                cv2.rectangle(canvas, (0, button_y), (button_width, button_y + button_height), target_button_color, -1)
                
                # Target button text (left side)
                target_text = "Target: ON" if self.target_mode else "Target: OFF"
                text_size = self.get_text_size_cached(target_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                text_x = 10
                text_y = button_y + (button_height + text_size[1]) // 2
                cv2.putText(canvas, target_text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Unique checkbox (right side of target button)
                checkbox_width = 70
                checkbox_x = button_width - checkbox_width - 5
                checkbox_y = button_y + 5
                checkbox_h = 30
                
                # Draw checkbox box
                checkbox_size = 16
                checkbox_box_x = checkbox_x + 5
                checkbox_box_y = checkbox_y + (checkbox_h - checkbox_size) // 2
                cv2.rectangle(canvas, (checkbox_box_x, checkbox_box_y), 
                            (checkbox_box_x + checkbox_size, checkbox_box_y + checkbox_size), 
                            (100, 100, 100), 2)
                
                # Draw checkmark if enabled
                if self.unique_only:
                    cv2.line(canvas, (checkbox_box_x + 3, checkbox_box_y + 8), 
                            (checkbox_box_x + 6, checkbox_box_y + 11), (0, 255, 0), 2)
                    cv2.line(canvas, (checkbox_box_x + 6, checkbox_box_y + 11), 
                            (checkbox_box_x + 13, checkbox_box_y + 4), (0, 255, 0), 2)
                
                # Draw label
                label_text = "unique"
                cv2.putText(canvas, label_text, (checkbox_box_x + checkbox_size + 3, checkbox_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                
                self.unique_checkbox_rect = (checkbox_x, checkbox_y, checkbox_width, checkbox_h)
                self.target_mode_button_rect = (0, button_y, button_width, button_height)
                
                # Bounds button (second third)
                cv2.line(canvas, (button_width, button_y), (button_width, button_y + button_height), (30, 30, 30), 2)
                bounds_button_color = (100, 100, 0) if self.bounds_mode else (60, 60, 60)
                cv2.rectangle(canvas, (button_width, button_y), (button_width * 2, button_y + button_height), bounds_button_color, -1)
                
                # Bounds button text (centered)
                bounds_text = "Bounds: ON" if self.bounds_mode else "Bounds: OFF"
                text_size = self.get_text_size_cached(bounds_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                text_x = button_width + (button_width - text_size[0]) // 2
                text_y = button_y + (button_height + text_size[1]) // 2
                cv2.putText(canvas, bounds_text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                self.bounds_button_rect = (button_width, button_y, button_width, button_height)
                
                # Exclude Mode button (third third)
                cv2.line(canvas, (button_width * 2, button_y), (button_width * 2, button_y + button_height), (30, 30, 30), 2)
                exclude_button_color = (0, 0, 120) if self.exclude_mode else (60, 60, 60)
                cv2.rectangle(canvas, (button_width * 2, button_y), (button_width * 3, button_y + button_height), exclude_button_color, -1)
                
                # Exclude button text (centered)
                exclude_text = "Exclude: ON" if self.exclude_mode else "Exclude: OFF"
                text_size = self.get_text_size_cached(exclude_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                text_x = button_width * 2 + (button_width - text_size[0]) // 2
                text_y = button_y + (button_height + text_size[1]) // 2
                cv2.putText(canvas, exclude_text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                self.exclude_mode_button_rect = (button_width * 2, button_y, button_width, button_height)
                
                # State Tracking button (fourth position)
                cv2.line(canvas, (button_width * 3, button_y), (button_width * 3, button_y + button_height), (30, 30, 30), 2)
                state_button_color = (120, 0, 120) if self.state_tracking else (60, 60, 60)
                cv2.rectangle(canvas, (button_width * 3, button_y), (w, button_y + button_height), state_button_color, -1)
                
                # State button text (centered)
                state_text = "State: ON" if self.state_tracking else "State: OFF"
                text_size = self.get_text_size_cached(state_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                text_x = button_width * 3 + (button_width - text_size[0]) // 2
                text_y = button_y + (button_height + text_size[1]) // 2
                cv2.putText(canvas, state_text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                self.state_tracking_button_rect = (button_width * 3, button_y, button_width, button_height)
                
                # Filter button (second row, full width with controls on right)
                filter_button_y = button_y + button_height
                cv2.line(canvas, (0, filter_button_y), (w, filter_button_y), (30, 30, 30), 2)
                filter_button_color = (0, 120, 0) if self.show_filtered else (60, 60, 60)
                cv2.rectangle(canvas, (0, filter_button_y), (w, filter_button_y + button_height), filter_button_color, -1)
                
                # Filter button text (left side)
                if self.show_filtered:
                    filter_text = f"Filter: ON"
                else:
                    filter_text = "Filter: OFF"
                
                text_size = self.get_text_size_cached(filter_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                text_x = 10
                text_y = filter_button_y + (button_height + text_size[1]) // 2
                cv2.putText(canvas, filter_text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Horizontal controls (right side of filter button) - responsive sizing
                controls_y = filter_button_y + 7
                control_h = 25
                checkbox_size = 18
                
                # Calculate available space for controls (leave space for "Filter: OFF" text)
                filter_text_width = 120
                available_width = w - filter_text_width - 20  # 20px margin
                
                # If we have enough space, use normal layout, otherwise scale down
                min_required_width = 544
                
                if available_width >= min_required_width:
                    # Normal full-size layout
                    controls_start_x = filter_text_width + 10
                else:
                    # Compact layout - scale proportionally
                    controls_start_x = filter_text_width + 10
                    # We'll just fit what we can
                
                # === Color count controls ===
                # Label
                color_label_x = controls_start_x
                cv2.putText(canvas, "colors:", (color_label_x, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Minus button
                minus_x = color_label_x + 45
                minus_w = 25
                cv2.rectangle(canvas, (minus_x, controls_y), (minus_x + minus_w, controls_y + control_h), (80, 80, 80), -1)
                cv2.rectangle(canvas, (minus_x, controls_y), (minus_x + minus_w, controls_y + control_h), (120, 120, 120), 1)
                cv2.putText(canvas, "-", (minus_x + 8, controls_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.colors_minus_rect = (minus_x, controls_y, minus_w, control_h)
                
                # Number display
                num_x = minus_x + minus_w + 2
                num_w = 30
                num_bg_color = (60, 90, 60) if self.editing_colors else (40, 40, 40)
                cv2.rectangle(canvas, (num_x, controls_y), (num_x + num_w, controls_y + control_h), num_bg_color, -1)
                cv2.rectangle(canvas, (num_x, controls_y), (num_x + num_w, controls_y + control_h), (100, 100, 100), 1)
                num_text = self.temp_input if self.editing_colors else str(self.config.colors_per_target)
                text_size = cv2.getTextSize(num_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                num_text_x = num_x + (num_w - text_size[0]) // 2
                cv2.putText(canvas, num_text, (num_text_x, controls_y + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                self.colors_display_rect = (num_x, controls_y, num_w, control_h)
                
                # Plus button
                plus_x = num_x + num_w + 2
                plus_w = 25
                cv2.rectangle(canvas, (plus_x, controls_y), (plus_x + plus_w, controls_y + control_h), (80, 80, 80), -1)
                cv2.rectangle(canvas, (plus_x, controls_y), (plus_x + plus_w, controls_y + control_h), (120, 120, 120), 1)
                cv2.putText(canvas, "+", (plus_x + 7, controls_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.colors_plus_rect = (plus_x, controls_y, plus_w, control_h)
                
                # === Pixel threshold controls ===
                pixel_label_x = plus_x + plus_w + 10
                cv2.putText(canvas, "min px:", (pixel_label_x, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Minus button
                pixel_minus_x = pixel_label_x + 45
                pixel_minus_w = 25
                cv2.rectangle(canvas, (pixel_minus_x, controls_y), 
                            (pixel_minus_x + pixel_minus_w, controls_y + control_h), (80, 80, 80), -1)
                cv2.rectangle(canvas, (pixel_minus_x, controls_y), 
                            (pixel_minus_x + pixel_minus_w, controls_y + control_h), (120, 120, 120), 1)
                cv2.putText(canvas, "-", (pixel_minus_x + 8, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.pixels_minus_rect = (pixel_minus_x, controls_y, pixel_minus_w, control_h)
                
                # Number display
                pixel_num_x = pixel_minus_x + pixel_minus_w + 2
                pixel_num_w = 30
                pixel_bg_color = (60, 90, 60) if self.editing_min_pixels else (40, 40, 40)
                cv2.rectangle(canvas, (pixel_num_x, controls_y), 
                            (pixel_num_x + pixel_num_w, controls_y + control_h), pixel_bg_color, -1)
                cv2.rectangle(canvas, (pixel_num_x, controls_y), 
                            (pixel_num_x + pixel_num_w, controls_y + control_h), (100, 100, 100), 1)
                pixel_num_text = self.temp_input if self.editing_min_pixels else str(self.config.min_blob_pixels)
                pixel_text_size = cv2.getTextSize(pixel_num_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                pixel_num_text_x = pixel_num_x + (pixel_num_w - pixel_text_size[0]) // 2
                cv2.putText(canvas, pixel_num_text, (pixel_num_text_x, controls_y + 17), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                self.pixels_display_rect = (pixel_num_x, controls_y, pixel_num_w, control_h)
                
                # Plus button
                pixel_plus_x = pixel_num_x + pixel_num_w + 2
                pixel_plus_w = 25
                cv2.rectangle(canvas, (pixel_plus_x, controls_y), 
                            (pixel_plus_x + pixel_plus_w, controls_y + control_h), (80, 80, 80), -1)
                cv2.rectangle(canvas, (pixel_plus_x, controls_y), 
                            (pixel_plus_x + pixel_plus_w, controls_y + control_h), (120, 120, 120), 1)
                cv2.putText(canvas, "+", (pixel_plus_x + 7, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.pixels_plus_rect = (pixel_plus_x, controls_y, pixel_plus_w, control_h)
                
                # === Max blobs controls ===
                max_blobs_label_x = pixel_plus_x + pixel_plus_w + 10
                cv2.putText(canvas, "blobs:", (max_blobs_label_x, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Minus button
                max_blobs_minus_x = max_blobs_label_x + 38
                max_blobs_minus_w = 25
                cv2.rectangle(canvas, (max_blobs_minus_x, controls_y), 
                            (max_blobs_minus_x + max_blobs_minus_w, controls_y + control_h), (80, 80, 80), -1)
                cv2.rectangle(canvas, (max_blobs_minus_x, controls_y), 
                            (max_blobs_minus_x + max_blobs_minus_w, controls_y + control_h), (120, 120, 120), 1)
                cv2.putText(canvas, "-", (max_blobs_minus_x + 8, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.max_blobs_minus_rect = (max_blobs_minus_x, controls_y, max_blobs_minus_w, control_h)
                
                # Number display
                max_blobs_num_x = max_blobs_minus_x + max_blobs_minus_w + 2
                max_blobs_num_w = 30
                max_blobs_bg_color = (60, 90, 60) if self.editing_max_blobs else (40, 40, 40)
                cv2.rectangle(canvas, (max_blobs_num_x, controls_y), 
                            (max_blobs_num_x + max_blobs_num_w, controls_y + control_h), max_blobs_bg_color, -1)
                cv2.rectangle(canvas, (max_blobs_num_x, controls_y), 
                            (max_blobs_num_x + max_blobs_num_w, controls_y + control_h), (100, 100, 100), 1)
                if self.editing_max_blobs:
                    max_blobs_num_text = self.temp_input
                else:
                    max_blobs_num_text = "∞" if self.config.max_blobs == 0 else str(self.config.max_blobs)
                max_blobs_text_size = cv2.getTextSize(max_blobs_num_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                max_blobs_num_text_x = max_blobs_num_x + (max_blobs_num_w - max_blobs_text_size[0]) // 2
                cv2.putText(canvas, max_blobs_num_text, (max_blobs_num_text_x, controls_y + 17), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                self.max_blobs_display_rect = (max_blobs_num_x, controls_y, max_blobs_num_w, control_h)
                
                # Plus button
                max_blobs_plus_x = max_blobs_num_x + max_blobs_num_w + 2
                max_blobs_plus_w = 25
                cv2.rectangle(canvas, (max_blobs_plus_x, controls_y), 
                            (max_blobs_plus_x + max_blobs_plus_w, controls_y + control_h), (80, 80, 80), -1)
                cv2.rectangle(canvas, (max_blobs_plus_x, controls_y), 
                            (max_blobs_plus_x + max_blobs_plus_w, controls_y + control_h), (120, 120, 120), 1)
                cv2.putText(canvas, "+", (max_blobs_plus_x + 7, controls_y + 18), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.max_blobs_plus_rect = (max_blobs_plus_x, controls_y, max_blobs_plus_w, control_h)
                
                # === Bounds checkbox ===
                bounds_checkbox_x = max_blobs_plus_x + max_blobs_plus_w + 10
                # Make sure checkbox doesn't overflow
                if bounds_checkbox_x + checkbox_size + 50 > w - 10:
                    # Skip bounds if not enough space
                    bounds_checkbox_x = -100  # Off screen
                bounds_checkbox_rect = (bounds_checkbox_x, controls_y + 3, checkbox_size, checkbox_size)
                self.bounds_checkbox_rect = bounds_checkbox_rect
                if bounds_checkbox_x > 0:
                    cv2.rectangle(canvas, (bounds_checkbox_x, controls_y + 3), 
                                 (bounds_checkbox_x + checkbox_size, controls_y + 3 + checkbox_size), (100, 100, 100), 2)
                    if self.show_bounds:
                        cv2.line(canvas, (bounds_checkbox_x + 3, controls_y + 11), 
                                (bounds_checkbox_x + 7, controls_y + 16), (0, 255, 0), 2)
                        cv2.line(canvas, (bounds_checkbox_x + 7, controls_y + 16), 
                                (bounds_checkbox_x + 15, controls_y + 6), (0, 255, 0), 2)
                    cv2.putText(canvas, "Bounds", (bounds_checkbox_x + checkbox_size + 3, controls_y + 18), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # === Excludes checkbox ===
                excludes_checkbox_x = bounds_checkbox_x + checkbox_size + 48
                # Make sure checkbox doesn't overflow
                if excludes_checkbox_x + checkbox_size + 60 > w - 10:
                    # Skip excludes if not enough space
                    excludes_checkbox_x = -100  # Off screen
                excludes_checkbox_rect = (excludes_checkbox_x, controls_y + 3, checkbox_size, checkbox_size)
                self.excludes_checkbox_rect = excludes_checkbox_rect
                if excludes_checkbox_x > 0:
                    cv2.rectangle(canvas, (excludes_checkbox_x, controls_y + 3), 
                                 (excludes_checkbox_x + checkbox_size, controls_y + 3 + checkbox_size), (100, 100, 100), 2)
                    if self.show_excludes:
                        cv2.line(canvas, (excludes_checkbox_x + 3, controls_y + 11), 
                                (excludes_checkbox_x + 7, controls_y + 16), (0, 255, 0), 2)
                        cv2.line(canvas, (excludes_checkbox_x + 7, controls_y + 16), 
                                (excludes_checkbox_x + 15, controls_y + 6), (0, 255, 0), 2)
                    cv2.putText(canvas, "Excludes", (excludes_checkbox_x + checkbox_size + 3, controls_y + 18), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # === Auto View checkbox ===
                auto_view_checkbox_x = excludes_checkbox_x + checkbox_size + 65
                # Make sure checkbox doesn't overflow
                if auto_view_checkbox_x + checkbox_size + 75 > w - 10:
                    # Skip auto view if not enough space
                    auto_view_checkbox_x = -100  # Off screen
                auto_view_checkbox_rect = (auto_view_checkbox_x, controls_y + 3, checkbox_size, checkbox_size)
                self.auto_view_checkbox_rect = auto_view_checkbox_rect
                if auto_view_checkbox_x > 0:
                    cv2.rectangle(canvas, (auto_view_checkbox_x, controls_y + 3), 
                                 (auto_view_checkbox_x + checkbox_size, controls_y + 3 + checkbox_size), (100, 100, 100), 2)
                    if self.auto_view_mode:
                        cv2.line(canvas, (auto_view_checkbox_x + 3, controls_y + 11), 
                                (auto_view_checkbox_x + 7, controls_y + 16), (0, 255, 0), 2)
                        cv2.line(canvas, (auto_view_checkbox_x + 7, controls_y + 16), 
                                (auto_view_checkbox_x + 15, controls_y + 6), (0, 255, 0), 2)
                    cv2.putText(canvas, "Auto View", (auto_view_checkbox_x + checkbox_size + 3, controls_y + 18), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                self.button_rect = (0, filter_button_y, w, button_height)
                
                # Draw capture UI (always visible)
                capture_y = filter_button_y + button_height
                cv2.rectangle(canvas, (0, capture_y), (w, capture_y + capture_ui_height), (40, 40, 40), -1)
                
                # Row 1: Target name text field + Capture button (left half) and Auto controls (right half)
                # Calculate positions with 10px padding between elements
                half_width = w // 2
                capture_button_width = 80
                auto_button_width = 80
                
                # Left half: text field + capture button
                text_field_x = 10
                text_field_y = capture_y + 5
                text_field_height = 30
                capture_button_x = half_width - capture_button_width - 10  # 10px from center
                text_field_width = capture_button_x - text_field_x - 10  # 10px gap before capture button
                
                # Text field background
                field_color = (80, 80, 80) if self.text_input_active else (60, 60, 60)
                cv2.rectangle(canvas, (text_field_x, text_field_y), 
                            (text_field_x + text_field_width, text_field_y + text_field_height), 
                            field_color, -1)
                cv2.rectangle(canvas, (text_field_x, text_field_y), 
                            (text_field_x + text_field_width, text_field_y + text_field_height), 
                            (100, 100, 100), 1)
                
                # Display text
                display_text = self.target_name if self.target_name else "name..."
                text_color = (255, 255, 255) if self.target_name else (120, 120, 120)
                cv2.putText(canvas, display_text, (text_field_x + 5, text_field_y + 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
                
                self.text_field_rect = (text_field_x, text_field_y, text_field_width, text_field_height)
                
                # Capture button (dimmed if no data to save)
                capture_button_y = capture_y + 5
                capture_button_h = 30
                
                # Check if we have something to capture based on mode
                if self.bounds_mode:
                    has_data = self.bounds_selection_rect and self.target_name
                elif self.exclude_mode:
                    has_data = self.selection_start and self.selection_end and self.target_name
                elif self.target_mode:
                    has_data = ((hasattr(self, 'unique_colors') and self.unique_colors) if self.unique_only else (hasattr(self, 'all_box_colors_by_count') and self.all_box_colors_by_count)) and self.target_name
                else:
                    has_data = False
                button_bg_color = (0, 100, 200) if has_data else (50, 50, 50)
                button_border_color = (0, 150, 255) if has_data else (80, 80, 80)
                
                cv2.rectangle(canvas, (capture_button_x, capture_button_y), 
                            (capture_button_x + capture_button_width, capture_button_y + capture_button_h), 
                            button_bg_color, -1)
                cv2.rectangle(canvas, (capture_button_x, capture_button_y), 
                            (capture_button_x + capture_button_width, capture_button_y + capture_button_h), 
                            button_border_color, 2)
                
                capture_text = "Capture"
                text_size = self.get_text_size_cached(capture_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                text_x = capture_button_x + (capture_button_width - text_size[0]) // 2
                text_y = capture_button_y + (capture_button_h + text_size[1]) // 2
                text_color = (255, 255, 255) if has_data else (100, 100, 100)
                cv2.putText(canvas, capture_text, (text_x, text_y), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
                
                self.capture_button_rect = (capture_button_x, capture_button_y, capture_button_width, capture_button_h)
                
                # Right half: Auto target display + Auto button
                auto_row_y = capture_y + 5  # Same y as capture button
                auto_button_x = w - auto_button_width - 10
                
                # Target display field (no +/- buttons, just shows current target based on state)
                control_h = 30
                # Display spans from half_width to auto button with padding
                auto_display_x = half_width + 10
                display_w = auto_button_x - auto_display_x - 10  # 10px gap before auto button
                cv2.rectangle(canvas, (auto_display_x, auto_row_y),
                            (auto_display_x + display_w, auto_row_y + control_h),
                            (50, 50, 50), -1)
                cv2.rectangle(canvas, (auto_display_x, auto_row_y),
                            (auto_display_x + display_w, auto_row_y + control_h),
                            (100, 100, 100), 1)
                
                # Display current auto target based on state
                current_auto_target = self.get_current_auto_target()
                if current_auto_target:
                    auto_field_text = current_auto_target
                    auto_field_color = (255, 255, 255)
                    
                    # Add status and timing information if auto mode is on
                    if self.auto_mode:
                        current_time = time.time()
                        time_until_next = self.next_touch_interval - (current_time - self.last_auto_touch)
                        
                        # Determine current state
                        if self.auto_target_passed:
                            status_text = " [passed]"
                            status_color = (100, 255, 100)
                        elif self.auto_target_touched:
                            status_text = " [checking pass]"
                            status_color = (255, 200, 100)
                        elif time_until_next > 0:
                            status_text = f" [wait {time_until_next:.1f}s]"
                            status_color = (200, 200, 100)
                        else:
                            # Check if target is stable
                            if hasattr(self, 'auto_target_stable_since') and self.auto_target_stable_since:
                                stable_duration = current_time - self.auto_target_stable_since
                                if stable_duration >= self.config.stability_timer:
                                    status_text = " [ready]"
                                    status_color = (100, 255, 100)
                                else:
                                    remaining = self.config.stability_timer - stable_duration
                                    status_text = f" [stabilize {remaining:.1f}s]"
                                    status_color = (200, 100, 200)
                            else:
                                status_text = " [stabilizing]"
                                status_color = (200, 100, 200)
                        
                        # Draw status text next to target name
                        target_text_size = cv2.getTextSize(auto_field_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                        status_x = auto_display_x + 5 + target_text_size[0] + 5
                        cv2.putText(canvas, status_text, (status_x, auto_row_y + 20),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)
                else:
                    auto_field_text = "No target (enable State)"
                    auto_field_color = (120, 120, 120)
                
                cv2.putText(canvas, auto_field_text, (auto_display_x + 5, auto_row_y + 20),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, auto_field_color, 1)
                
                # Auto button
                auto_button_y = auto_row_y
                auto_button_height = 30
                
                auto_bg_color = (0, 120, 0) if self.auto_mode else (60, 60, 60)
                auto_border_color = (0, 200, 0) if self.auto_mode else (100, 100, 100)
                
                cv2.rectangle(canvas, (auto_button_x, auto_button_y),
                            (auto_button_x + auto_button_width, auto_button_y + auto_button_height),
                            auto_bg_color, -1)
                cv2.rectangle(canvas, (auto_button_x, auto_button_y),
                            (auto_button_x + auto_button_width, auto_button_y + auto_button_height),
                            auto_border_color, 2)
                
                auto_text = "Auto: ON" if self.auto_mode else "Auto: OFF"
                text_size = self.get_text_size_cached(auto_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                text_x = auto_button_x + (auto_button_width - text_size[0]) // 2
                text_y = auto_button_y + (auto_button_height + text_size[1]) // 2
                cv2.putText(canvas, auto_text, (text_x, text_y),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                self.auto_button_rect = (auto_button_x, auto_button_y, auto_button_width, auto_button_height)
                
                # Row 4: Timer settings as text fields (below auto row)
                gap_below_auto = 10  # Gap between auto row and touch delay box
                field_height = 25
                field_width = 50
                label_width = 35
                unit_width = 20
                spacing = 5
                
                x_pos = 10
                
                # Calculate the bounding box dimensions for "touch delay" group
                touch_delay_start_x = x_pos - 5  # 5px horizontal padding
                touch_delay_group_width = (label_width + field_width + unit_width + spacing) * 4 - spacing + 20  # 4 fields + 10px padding each side
                
                # Draw "touch delay" bounding box with label
                label_text = "touch delay"
                label_font_scale = 0.3
                label_text_size = self.get_text_size_cached(label_text, cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, 1)
                label_height = label_text_size[1] + 4  # Add 4px for padding around text
                
                # Box starts below auto row with gap, contains label at top then fields below
                box_padding_top = 3  # Padding inside box above label
                box_padding_bottom = 5  # Padding inside box below fields
                label_to_field_gap = 3  # Gap between label and fields
                
                box_top = auto_row_y + control_h + gap_below_auto  # Start after auto row + gap
                box_height = box_padding_top + label_height + label_to_field_gap + field_height + box_padding_bottom
                
                # Position where fields will be drawn (inside the box)
                timer_row_y = box_top + box_padding_top + label_height + label_to_field_gap
                
                cv2.rectangle(canvas, (touch_delay_start_x, box_top), 
                            (touch_delay_start_x + touch_delay_group_width, box_top + box_height), 
                            (80, 80, 80), 1)
                
                # Draw label background and text (inside the box at the top)
                label_bg_x = touch_delay_start_x + 5
                label_bg_y = box_top + box_padding_top
                cv2.rectangle(canvas, (label_bg_x, label_bg_y), (label_bg_x + label_text_size[0] + 4, label_bg_y + label_height), (40, 40, 40), -1)
                cv2.putText(canvas, label_text, (label_bg_x + 2, label_bg_y + label_text_size[1] + 2),
                          cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, (180, 180, 180), 1)
                
                # Min delay field
                min_label_text = "min"
                min_label_width = self.get_text_size_cached(min_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, min_label_text, (x_pos + label_width - min_label_width, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                min_bg_color = (0, 100, 0) if self.editing_delay_min else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), min_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), (100, 100, 100), 1)
                min_text = self.temp_input if self.editing_delay_min else f"{int(self.config.touch_delay_min*1000)}"
                cv2.putText(canvas, min_text, (x_pos + 5, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (x_pos + field_width + 3, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.delay_min_rect = (x_pos, timer_row_y, field_width, field_height)
                x_pos += field_width + unit_width + spacing
                
                # Max delay field
                max_label_text = "max"
                max_label_width = self.get_text_size_cached(max_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, max_label_text, (x_pos + label_width - max_label_width, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                max_bg_color = (0, 100, 0) if self.editing_delay_max else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), max_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), (100, 100, 100), 1)
                max_text = self.temp_input if self.editing_delay_max else f"{int(self.config.touch_delay_max*1000)}"
                cv2.putText(canvas, max_text, (x_pos + 5, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (x_pos + field_width + 3, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.delay_max_rect = (x_pos, timer_row_y, field_width, field_height)
                x_pos += field_width + unit_width + spacing
                
                # Mean delay field
                mean_label_text = "mean"
                mean_label_width = self.get_text_size_cached(mean_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, mean_label_text, (x_pos + label_width - mean_label_width, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                mean_bg_color = (0, 100, 0) if self.editing_delay_mean else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), mean_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), (100, 100, 100), 1)
                mean_text = self.temp_input if self.editing_delay_mean else f"{int(self.config.touch_delay_mean*1000)}"
                cv2.putText(canvas, mean_text, (x_pos + 5, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (x_pos + field_width + 3, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.delay_mean_rect = (x_pos, timer_row_y, field_width, field_height)
                x_pos += field_width + unit_width + spacing
                
                # Std delay field
                std_label_text = "std"
                std_label_width = self.get_text_size_cached(std_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, std_label_text, (x_pos + label_width - std_label_width, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                std_bg_color = (0, 100, 0) if self.editing_delay_std else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), std_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), (100, 100, 100), 1)
                std_text = self.temp_input if self.editing_delay_std else f"{int(self.config.touch_delay_std*1000)}"
                cv2.putText(canvas, std_text, (x_pos + 5, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (x_pos + field_width + 3, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.delay_std_rect = (x_pos, timer_row_y, field_width, field_height)
                x_pos += field_width + unit_width + spacing + 10
                
                # Stability field
                stable_label_text = "stable"
                stable_label_width = self.get_text_size_cached(stable_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, stable_label_text, (x_pos + label_width - stable_label_width, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                stable_bg_color = (0, 100, 0) if self.editing_stability else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), stable_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), (100, 100, 100), 1)
                stable_text = self.temp_input if self.editing_stability else f"{int(self.config.stability_timer*1000)}"
                cv2.putText(canvas, stable_text, (x_pos + 5, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (x_pos + field_width + 3, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.stability_rect = (x_pos, timer_row_y, field_width, field_height)
                x_pos += field_width + unit_width + spacing + 10
                
                # Passing distance field
                pass_label_text = "pass"
                pass_label_width = self.get_text_size_cached(pass_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, pass_label_text, (x_pos + label_width - pass_label_width, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                pass_bg_color = (0, 100, 0) if self.editing_passing_dist else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), pass_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, timer_row_y), (x_pos + field_width, timer_row_y + field_height), (100, 100, 100), 1)
                pass_text = self.temp_input if self.editing_passing_dist else f"{int(self.config.passing_distance)}"
                cv2.putText(canvas, pass_text, (x_pos + 5, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "px", (x_pos + field_width + 3, timer_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.passing_dist_rect = (x_pos, timer_row_y, field_width, field_height)
                
                # State section - new row below touch delay
                gap_below_touch_delay = 5  # Gap between touch delay box and state box
                state_row_y_base = box_top + box_height + gap_below_touch_delay
                state_start_x = touch_delay_start_x
                
                # Calculate state box dimensions - now includes 4 fields (xp, total, higher plane, plane size)
                # xp + total + higher plane + plane size with +/- buttons
                button_width_small = 20
                state_box_width = (label_width - 10 + field_width + spacing + 10) + \
                                 (label_width + 10 + 80 + spacing + 10) + \
                                 (label_width + 30 + field_width + spacing + 10) + \
                                 (label_width + 20 + button_width_small + field_width + button_width_small + spacing) + 20
                state_box_height = box_padding_top + label_height + label_to_field_gap + field_height + box_padding_bottom
                
                # Position where fields will be drawn (inside the state box)
                state_row_y = state_row_y_base + box_padding_top + label_height + label_to_field_gap
                
                # Draw state boundary box
                cv2.rectangle(canvas, (state_start_x, state_row_y_base), 
                            (state_start_x + state_box_width, state_row_y_base + state_box_height),
                            (80, 80, 80), 1)
                
                # State label background and text (inside the box at the top)
                state_label_text = "state"
                state_label_text_size = self.get_text_size_cached(state_label_text, cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, 1)
                state_label_bg_x = state_start_x + 5
                state_label_bg_y = state_row_y_base + box_padding_top
                cv2.rectangle(canvas, (state_label_bg_x, state_label_bg_y), 
                            (state_label_bg_x + state_label_text_size[0] + 4, state_label_bg_y + label_height), 
                            (40, 40, 40), -1)
                cv2.putText(canvas, state_label_text, (state_label_bg_x + 2, state_label_bg_y + state_label_text_size[1] + 2),
                          cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, (180, 180, 180), 1)
                
                # Sample interval field (editable with +/- buttons) - in milliseconds
                x_pos = state_start_x + 10
                sample_label_text = "sample"
                sample_label_width = self.get_text_size_cached(sample_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                label_alloc_width = 50  # Allocated width for right-alignment
                cv2.putText(canvas, sample_label_text, (x_pos + label_alloc_width - sample_label_width, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_alloc_width + 5
                
                # Minus button
                sample_button_width = 20
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + sample_button_width, state_row_y + field_height), (70, 70, 70), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + sample_button_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, "-", (x_pos + 6, state_row_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.xp_sample_interval_minus_rect = (x_pos, state_row_y, sample_button_width, field_height)
                x_pos += sample_button_width + 2
                
                # Sample interval number field (show in ms)
                sample_bg_color = (0, 100, 0) if self.editing_xp_sample_interval else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), sample_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                sample_text = self.temp_input if self.editing_xp_sample_interval else f"{int(self.xp_sample_interval * 1000)}"
                cv2.putText(canvas, sample_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (x_pos + field_width + 3, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                self.xp_sample_interval_rect = (x_pos, state_row_y, field_width, field_height)
                x_pos += field_width + unit_width + 2
                
                # Plus button
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + sample_button_width, state_row_y + field_height), (70, 70, 70), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + sample_button_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, "+", (x_pos + 5, state_row_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.xp_sample_interval_plus_rect = (x_pos, state_row_y, sample_button_width, field_height)
                x_pos += sample_button_width + spacing + 10
                
                # Brightness threshold field
                brightness_label_text = "brightness"
                brightness_label_width = self.get_text_size_cached(brightness_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                brightness_alloc_width = 60  # Allocated width for right-alignment
                cv2.putText(canvas, brightness_label_text, (x_pos + brightness_alloc_width - brightness_label_width, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += brightness_alloc_width + 5
                brightness_bg_color = (0, 100, 0) if self.editing_xp_brightness else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), brightness_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                brightness_text = self.temp_input if self.editing_xp_brightness else f"{int(self.xp_brightness_threshold)}"
                cv2.putText(canvas, brightness_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                self.xp_brightness_rect = (x_pos, state_row_y, field_width, field_height)
                x_pos += field_width + spacing + 10
                
                # XP status display (read-only) - shows XP gained
                xp_label_text = "xp"
                xp_label_width = self.get_text_size_cached(xp_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, xp_label_text, (x_pos + label_width - xp_label_width, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                xp_bg_color = (0, 60, 0) if self.xp_detected != "0" else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), xp_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, self.xp_detected, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                x_pos += field_width + spacing + 10
                
                # Total XP display (read-only) - shows the actual number OCR reads
                total_label_text = "total"
                total_label_width = self.get_text_size_cached(total_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                cv2.putText(canvas, total_label_text, (x_pos + label_width - total_label_width, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += label_width + 5
                total_xp_width = 80  # Wider field for numbers
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + total_xp_width, state_row_y + field_height), (50, 50, 50), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + total_xp_width, state_row_y + field_height), (100, 100, 100), 1)
                total_xp_text = str(self.xp_last_value) if self.xp_last_value is not None else "---"
                cv2.putText(canvas, total_xp_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                x_pos += total_xp_width + spacing + 10
                
                # Higher plane indicator (read-only)
                label_text_1 = "higher"
                label_text_2 = "plane"
                label_1_size = self.get_text_size_cached(label_text_1, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                label_2_size = self.get_text_size_cached(label_text_2, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                max_label_width = max(label_1_size, label_2_size)
                cv2.putText(canvas, label_text_1, (x_pos + max_label_width - label_1_size, state_row_y + 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                cv2.putText(canvas, label_text_2, (x_pos + max_label_width - label_2_size, state_row_y + 22),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += max_label_width + 5
                plane_bg_color = (0, 60, 0) if self.higher_plane else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), plane_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                plane_text = "1" if self.higher_plane else "0"
                cv2.putText(canvas, plane_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                x_pos += field_width + spacing + 10
                
                # Plane size field (editable with +/- buttons)
                label_text_1 = "plane"
                label_text_2 = "size"
                label_1_size = self.get_text_size_cached(label_text_1, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                label_2_size = self.get_text_size_cached(label_text_2, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                max_label_width = max(label_1_size, label_2_size)
                cv2.putText(canvas, label_text_1, (x_pos + max_label_width - label_1_size, state_row_y + 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                cv2.putText(canvas, label_text_2, (x_pos + max_label_width - label_2_size, state_row_y + 22),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += max_label_width + 5
                
                # Minus button
                minus_button_width = 20
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + minus_button_width, state_row_y + field_height), (70, 70, 70), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + minus_button_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, "-", (x_pos + 6, state_row_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.plane_size_minus_rect = (x_pos, state_row_y, minus_button_width, field_height)
                x_pos += minus_button_width + 2
                
                # Plane size number field
                plane_size_bg_color = (0, 100, 0) if self.editing_plane_size else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), plane_size_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                plane_size_text = self.temp_input if self.editing_plane_size else str(self.config.plane_size)
                cv2.putText(canvas, plane_size_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                self.plane_size_rect = (x_pos, state_row_y, field_width, field_height)
                x_pos += field_width + 2
                
                # Plus button
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + minus_button_width, state_row_y + field_height), (70, 70, 70), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + minus_button_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, "+", (x_pos + 5, state_row_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.plane_size_plus_rect = (x_pos, state_row_y, minus_button_width, field_height)
                x_pos += minus_button_width + spacing + 10
                
                # Minimap counter display (read-only) - shows count of distinct groups
                label_text_1 = "plane"
                label_text_2 = "counter"
                label_1_size = self.get_text_size_cached(label_text_1, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                label_2_size = self.get_text_size_cached(label_text_2, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                max_label_width = max(label_1_size, label_2_size)
                cv2.putText(canvas, label_text_1, (x_pos + max_label_width - label_1_size, state_row_y + 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                cv2.putText(canvas, label_text_2, (x_pos + max_label_width - label_2_size, state_row_y + 22),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += max_label_width + 5
                counter_bg_color = (0, 60, 0) if self.minimap_counter > 0 else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), counter_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                counter_text = str(self.minimap_counter)
                cv2.putText(canvas, counter_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                x_pos += field_width + spacing + 10
                
                # Minimap padding field (editable with +/- buttons)
                label_text_1 = "plane"
                label_text_2 = "count"
                label_text_3 = "padding"
                label_1_size = self.get_text_size_cached(label_text_1, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                label_2_size = self.get_text_size_cached(label_text_2, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                label_3_size = self.get_text_size_cached(label_text_3, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                max_label_width = max(label_1_size, label_2_size, label_3_size)
                cv2.putText(canvas, label_text_1, (x_pos + max_label_width - label_1_size, state_row_y + 6),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                cv2.putText(canvas, label_text_2, (x_pos + max_label_width - label_2_size, state_row_y + 16),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                cv2.putText(canvas, label_text_3, (x_pos + max_label_width - label_3_size, state_row_y + 26),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                x_pos += max_label_width + 5
                
                # Minus button
                padding_button_width = 20
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + padding_button_width, state_row_y + field_height), (70, 70, 70), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + padding_button_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, "-", (x_pos + 6, state_row_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.minimap_counter_padding_minus_rect = (x_pos, state_row_y, padding_button_width, field_height)
                x_pos += padding_button_width + 2
                
                # Minimap padding number field
                padding_bg_color = (0, 100, 0) if self.editing_minimap_counter_padding else (50, 50, 50)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), padding_bg_color, -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + field_width, state_row_y + field_height), (100, 100, 100), 1)
                padding_text = self.temp_input if self.editing_minimap_counter_padding else str(self.config.minimap_counter_padding)
                cv2.putText(canvas, padding_text, (x_pos + 5, state_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                self.minimap_counter_padding_rect = (x_pos, state_row_y, field_width, field_height)
                x_pos += field_width + 2
                
                # Plus button
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + padding_button_width, state_row_y + field_height), (70, 70, 70), -1)
                cv2.rectangle(canvas, (x_pos, state_row_y), (x_pos + padding_button_width, state_row_y + field_height), (100, 100, 100), 1)
                cv2.putText(canvas, "+", (x_pos + 5, state_row_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                self.minimap_counter_padding_plus_rect = (x_pos, state_row_y, padding_button_width, field_height)
                
                # Counter stable row (new row below state row)
                counter_stable_row_y = state_row_y + field_height + 10
                counter_stable_x = state_start_x + 10
                
                # Counter stable label
                counter_stable_label_text_1 = "counter"
                counter_stable_label_text_2 = "stable"
                counter_stable_label_1_size = self.get_text_size_cached(counter_stable_label_text_1, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                counter_stable_label_2_size = self.get_text_size_cached(counter_stable_label_text_2, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                max_counter_stable_label_width = max(counter_stable_label_1_size, counter_stable_label_2_size)
                cv2.putText(canvas, counter_stable_label_text_1, (counter_stable_x + max_counter_stable_label_width - counter_stable_label_1_size, counter_stable_row_y + 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                cv2.putText(canvas, counter_stable_label_text_2, (counter_stable_x + max_counter_stable_label_width - counter_stable_label_2_size, counter_stable_row_y + 22),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
                counter_stable_x += max_counter_stable_label_width + 5
                
                # Calculate stability duration (use loop_start for consistent timing)
                counter_stable_duration = 0
                if self.minimap_counter_stable_since is not None:
                    counter_stable_duration = int((loop_start - self.minimap_counter_stable_since) * 1000)  # in ms
                counter_stable_is_stable = counter_stable_duration >= int(self.config.stability_timer * 1000)
                
                # Counter stable display (read-only)
                counter_stable_bg_color = (0, 60, 0) if counter_stable_is_stable else (50, 50, 50)
                cv2.rectangle(canvas, (counter_stable_x, counter_stable_row_y), (counter_stable_x + field_width, counter_stable_row_y + field_height), counter_stable_bg_color, -1)
                cv2.rectangle(canvas, (counter_stable_x, counter_stable_row_y), (counter_stable_x + field_width, counter_stable_row_y + field_height), (100, 100, 100), 1)
                counter_stable_text = f"{counter_stable_duration}"
                cv2.putText(canvas, counter_stable_text, (counter_stable_x + 5, counter_stable_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, "ms", (counter_stable_x + field_width + 3, counter_stable_row_y + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
                
                # Display the frame with button (AUTOSIZE shows at actual pixel dimensions)
                cv2.imshow(window_title, canvas)
                
                # Auto-touch logic
                if self.auto_mode and hasattr(self, 'detected_targets'):
                    current_time = time.time()
                    
                    # Get current target name based on state
                    current_target = self.get_current_auto_target()
                    
                    print(f"[AUTO] Current target: {current_target}, Detected: {list(self.detected_targets.keys()) if self.detected_targets else 'none'}")
                    
                    if current_target:
                        
                        # Get white dot position (screen center in display coordinates)
                        h_display, w_display = display_frame.shape[:2]
                        dot_x = w_display // 2
                        dot_y = h_display // 2
                        
                        # Scale dot position back to original coordinates if needed
                        if self.display_scale != 1.0:
                            scale_factor = 1.0 / self.display_scale
                            dot_x = int(dot_x * scale_factor)
                            dot_y = int(dot_y * scale_factor)
                        
                        # Track dot stability (for distance passing evaluation)
                        # Only start checking stability after pass_pause_duration has elapsed since touch
                        dot_is_stable = False
                        pass_pause_elapsed = (self.auto_touched_time is not None and 
                                             current_time - self.auto_touched_time >= self.config.pass_pause_duration)
                        
                        if self.auto_dot_prev_pos is not None and pass_pause_elapsed:
                            prev_dot_x, prev_dot_y = self.auto_dot_prev_pos
                            # Consider stable if position hasn't changed by more than 5 pixels
                            dot_position_delta = abs(dot_x - prev_dot_x) + abs(dot_y - prev_dot_y)
                            if dot_position_delta <= 5:
                                # Dot is in same position
                                if self.auto_dot_stable_since is None:
                                    self.auto_dot_stable_since = current_time
                                # Consider stable after configured time of no movement
                                elif current_time - self.auto_dot_stable_since >= self.config.stability_timer:
                                    dot_is_stable = True
                            else:
                                # Dot moved, reset stability timer
                                self.auto_dot_stable_since = None
                        
                        # Update previous dot position
                        self.auto_dot_prev_pos = (dot_x, dot_y)
                        
                        # Check if current target is detected
                        if current_target in self.detected_targets:
                            print(f"[AUTO] Target '{current_target}' detected at position")
                            # Update last seen time
                            self.auto_target_last_seen = current_time
                            
                            x_pos, y_pos, w_pos, h_pos = self.detected_targets[current_target]
                            target_center_x = x_pos + w_pos // 2
                            target_center_y = y_pos + h_pos // 2
                            current_pos = (x_pos, y_pos, w_pos, h_pos)
                            
                            # Check if target has moved (compare with previous position)
                            target_is_stable = False
                            if self.auto_target_prev_pos is not None:
                                prev_x, prev_y, prev_w, prev_h = self.auto_target_prev_pos
                                # Consider stable if position hasn't changed by more than 5 pixels
                                position_delta = abs(x_pos - prev_x) + abs(y_pos - prev_y)
                                print(f"[STABILITY] Position delta: {position_delta}px (threshold: 5px)")
                                if position_delta <= 5:
                                    # Target is in same position
                                    if self.auto_target_stable_since is None:
                                        self.auto_target_stable_since = current_time
                                        print(f"[STABILITY] Started stability timer")
                                    # Consider stable after configured time of no movement
                                    else:
                                        elapsed = current_time - self.auto_target_stable_since
                                        print(f"[STABILITY] Elapsed: {elapsed:.3f}s / {self.config.stability_timer}s")
                                        if elapsed >= self.config.stability_timer:
                                            target_is_stable = True
                                            print(f"[STABILITY] Target is STABLE!")
                                else:
                                    # Target moved, reset stability timer
                                    print(f"[STABILITY] Target moved, resetting timer")
                                    self.auto_target_stable_since = None
                            else:
                                print(f"[STABILITY] First detection, no previous position")
                            
                            # Update previous position
                            self.auto_target_prev_pos = current_pos
                            
                            # Check passing condition: XP gained after touching
                            if self.auto_target_touched and self.xp_detected != "0":
                                # XP was gained, target is passed
                                self.auto_target_passed = True
                            
                            # Touch target at interval if not yet passed, time elapsed, and target is stable
                            time_ready = current_time - self.last_auto_touch >= self.next_touch_interval
                            if not self.auto_target_passed and time_ready and target_is_stable:
                                cmd = f"adb shell input tap {target_center_x} {target_center_y}"
                                print(f"[Auto] Touching '{current_target}' at ({target_center_x}, {target_center_y})")
                                try:
                                    subprocess.run(cmd.split(), check=True, capture_output=True)
                                except Exception as e:
                                    print(f"[Auto] Touch error: {e}")
                                
                                # Generate next interval
                                self.last_auto_touch = current_time
                                self.next_touch_interval = np.random.normal(self.config.touch_delay_mean, self.config.touch_delay_std)
                                self.next_touch_interval = max(self.config.touch_delay_min, min(self.config.touch_delay_max, self.next_touch_interval))
                                # Mark that we've touched this target and store the position and time
                                self.auto_target_touched = True
                                self.auto_touched_position = (target_center_x, target_center_y)
                                self.auto_touched_time = current_time
                                # Reset stability tracking after touch
                                self.auto_target_stable_since = None
                        else:
                            # Target not detected
                            # If we've touched and gained XP, mark as passed
                            if self.auto_target_touched and self.xp_detected != "0":
                                self.auto_target_passed = True
                            
                            # Check for timeout - if no target seen for 10 seconds, skip to next
                            if self.auto_target_last_seen is not None:
                                time_since_last_seen = current_time - self.auto_target_last_seen
                                if time_since_last_seen >= self.auto_target_timeout:
                                    print(f"[Auto] Target '{current_target}' not detected for {self.auto_target_timeout}s, skipping to next target")
                                    self.auto_target_passed = True
                            else:
                                # First time in auto mode, initialize last seen time
                                self.auto_target_last_seen = current_time
                            
                            # Reset stability timer but keep previous position
                            # This allows stability to resume if target reappears in same position
                            self.auto_target_stable_since = None
                            # Reset touch cooldown so we can touch immediately when target reappears (after stability)
                            self.last_auto_touch = current_time - self.next_touch_interval
                        
                        # If target has been passed, reset auto state
                        if self.auto_target_passed:
                            self.auto_target_passed = False
                            self.auto_target_touched = False
                            self.auto_touched_time = None
                            self.auto_target_prev_pos = None
                            self.auto_target_stable_since = None
                            self.auto_touched_position = None
                            self.auto_dot_prev_pos = None
                            self.auto_dot_stable_since = None
                            self.auto_target_last_seen = current_time  # Reset timeout
                            new_target = self.get_current_auto_target()
                            if new_target:
                                print(f"[Auto] Target passed, state updated. New target: '{new_target}'")
                            else:
                                print(f"[Auto] Target passed, state updated. Waiting for state detection...")
                
                # Move window after first frame is displayed (ensures window exists)
                if not window_positioned:
                    cv2.moveWindow(window_title, mirror_x, mirror_y)
                    window_positioned = True
                    canvas_h, canvas_w = canvas.shape[:2]
                    print(f"Mirror window positioned at: x={mirror_x}, y={mirror_y}")
                    print(f"Actual frame dimensions: {w}x{h} (+ {button_height}px button = {canvas_h}px total)")
                
                frame_count += 1
            else:
                print("Failed to capture frame, retrying...")
                time.sleep(0.1)
                continue
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            process_keyboard_event(self, key)
            
            # Check if window was closed
            if cv2.getWindowProperty(window_title, cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed by user")
                break
            
            # Frame rate limiting
            elapsed_frame_time = time.time() - loop_start
            sleep_time = self.frame_time - elapsed_frame_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Cleanup
        cv2.destroyAllWindows()
        print(f"\nTotal frames captured: {frame_count}")
        print(f"Average FPS: {frame_count / (time.time() - start_time):.2f}")
    
    def list_windows(self):
        """List all windows with their names."""
        def print_windows(window, depth=0):
            try:
                name = window.get_wm_name()
                if name:
                    print(f"{'  ' * depth}- {name}")
            except:
                pass
            
            try:
                children = window.query_tree().children
                for child in children:
                    print_windows(child, depth + 1)
            except:
                pass
        
        print_windows(self.root)


def detect_desktop_scale() -> float:
    """Detect desktop environment scaling factor."""
    try:
        # Try Xft.dpi from xrdb (works for GNOME and others)
        result = subprocess.run(['xrdb', '-query'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'Xft.dpi' in line:
                dpi = float(line.split(':')[1].strip())
                scale = dpi / 96.0
                print(f"Detected desktop scale from Xft.dpi: {scale:.2f}x ({dpi} DPI)")
                return 1.0 / scale  # Return inverse for display scale
    except:
        pass
    
    try:
        # Try GNOME gsettings
        result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'scaling-factor'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and 'uint32' in result.stdout:
            scale = int(result.stdout.split()[-1])
            if scale > 0:
                print(f"Detected GNOME scaling factor: {scale}x")
                return 1.0 / scale
    except:
        pass
    
    print("Could not detect desktop scaling, using default scale")
    return 0.5  # Default for common 200% scaling


def kill_existing_instances():
    """Kill any existing instances of this script (main.py or main_qt.py)."""
    current_pid = os.getpid()
    current_script = os.path.abspath(__file__)
    
    # Also check for main_qt.py instances
    # main.py is at: android-injections/src/android_injections/main.py
    # main_qt.py is at: android-injections/main_qt.py (3 levels up)
    main_qt_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_script))), 'main_qt.py')
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip current process
            if proc.pid == current_pid:
                continue
            
            # Check if it's a python process running this script or main_qt.py
            cmdline = proc.cmdline()
            if cmdline and len(cmdline) > 1:
                # Check if any of the command line args match our script paths
                for arg in cmdline:
                    arg_abs = os.path.abspath(arg) if os.path.exists(arg) else arg
                    if arg_abs == current_script or arg_abs == main_qt_script:
                        print(f"Killing existing instance (PID: {proc.pid})")
                        proc.terminate()
                        try:
                            proc.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        killed_count += 1
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_count > 0:
        print(f"Killed {killed_count} existing instance(s)")
        time.sleep(0.5)  # Give time for cleanup


def main():
    # Kill any existing instances before starting
    kill_existing_instances()
    
    parser = argparse.ArgumentParser(
        description="Mirror Android window pixels in real-time"
    )
    parser.add_argument(
        "--window",
        type=str,
        default="Pixel 4a (5G)",
        help="Name of the window to capture (default: 'Pixel 4a (5G)')"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Target frames per second (default: 30)"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=None,
        help="Display scale factor for mirror window (auto-detected if not specified)"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Enable benchmark mode to show filter timing information"
    )
    
    args = parser.parse_args()
    
    # Auto-detect scale if not provided
    if args.scale is None:
        args.scale = detect_desktop_scale()
    
    capture = WindowCapture(args.window, args.fps, args.scale, args.benchmark)
    capture.run()


if __name__ == "__main__":
    main()
