#!/usr/bin/env python3
"""
Android Mirror with PyQt6 UI - replaces cv2 window with native PyQt6 interface.

Uses the existing WindowCapture logic but displays through PyQt6 instead of OpenCV.
"""

import argparse
import sys
import os
import signal
import time
import psutil
import subprocess

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from android_injections.main import WindowCapture, detect_desktop_scale, kill_existing_instances
from android_injections.ui.qt_renderer import MirrorWindow
from android_injections.targeting.target_loader import load_all_targets
from android_injections.automation.auto_target import get_current_auto_target


class QtWindowCapture(WindowCapture):
    """Extended WindowCapture that works with PyQt6."""
    
    def __init__(self, *args, **kwargs):
        # Initialize mirror window attribute first
        self.mirror_window = None
        
        # Call parent init (this will create self.config and call load_all_targets)
        super().__init__(*args, **kwargs)
        
        # Initialize CLAHE for XP OCR preprocessing (normally done in run() for cv2 version)
        import cv2
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    # Use properties to provide backward compatibility with code expecting direct attributes
    @property
    def colors_per_target(self):
        return self.config.colors_per_target if hasattr(self, 'config') else 20
    
    @colors_per_target.setter
    def colors_per_target(self, value):
        if hasattr(self, 'config'):
            self.config.colors_per_target = value
    
    @property
    def min_blob_pixels(self):
        return self.config.min_blob_pixels if hasattr(self, 'config') else 2
    
    @min_blob_pixels.setter
    def min_blob_pixels(self, value):
        if hasattr(self, 'config'):
            self.config.min_blob_pixels = value
    
    @property
    def max_blobs(self):
        return self.config.max_blobs if hasattr(self, 'config') else 1
    
    @max_blobs.setter
    def max_blobs(self, value):
        if hasattr(self, 'config'):
            self.config.max_blobs = value
    
    @property
    def xp_sample_interval(self):
        return self.config.xp_sample_interval if hasattr(self, 'config') else 1.0
    
    @xp_sample_interval.setter
    def xp_sample_interval(self, value):
        if hasattr(self, 'config'):
            self.config.xp_sample_interval = value
    
    @property
    def minimap_counter_padding(self):
        return self.config.minimap_counter_padding if hasattr(self, 'config') else 5
    
    @minimap_counter_padding.setter
    def minimap_counter_padding(self, value):
        if hasattr(self, 'config'):
            self.config.minimap_counter_padding = value
    
    @property
    def plane_size(self):
        return self.config.plane_size if hasattr(self, 'config') else 5
    
    @plane_size.setter
    def plane_size(self, value):
        if hasattr(self, 'config'):
            self.config.plane_size = value
    
    @property
    def xp_brightness_threshold(self):
        return self.config.xp_brightness_threshold if hasattr(self, 'config') else 170
    
    @xp_brightness_threshold.setter
    def xp_brightness_threshold(self, value):
        if hasattr(self, 'config'):
            self.config.xp_brightness_threshold = value
    
    def on_mouse_click(self, x, y, button):
        """Handle mouse click events - start rectangle selection."""
        # Start selection if in a selection mode
        if self.target_mode or self.bounds_mode or self.exclude_mode:
            self.selecting = True
            self.selection_start = (x, y)
            self.selection_end = (x, y)
    
    def on_mouse_move(self, x, y):
        """Handle mouse move events - update rectangle selection."""
        if self.selecting:
            self.selection_end = (x, y)
    
    def on_mouse_release(self, x, y):
        """Handle mouse release events - finalize rectangle selection."""
        if self.selecting:
            self.selection_end = (x, y)
            self.selecting = False
            
            # Store the selection in appropriate variable based on mode
            if self.selection_start and self.selection_end:
                if self.target_mode:
                    self.target_selection_rect = (self.selection_start, self.selection_end)
                    # Analyze colors immediately after selection
                    self.analyze_colors_in_selection()
                elif self.bounds_mode:
                    self.bounds_selection_rect = (self.selection_start, self.selection_end)
                elif self.exclude_mode:
                    self.exclude_selection_rect = (self.selection_start, self.selection_end)
    
    def analyze_colors_in_selection(self):
        """Analyze colors in the current target selection."""
        from android_injections.targeting.color_analysis import analyze_unique_colors
        try:
            analyze_unique_colors(self)
            if hasattr(self, 'unique_colors'):
                print(f"Found {len(self.unique_colors)} unique colors in selection")
        except Exception as e:
            print(f"Error analyzing colors: {e}")
    
    def capture_current_target(self):
        """Capture and save current target/bounds/exclusion."""
        from android_injections.targeting.target_saver import save_target, save_bounds
        from android_injections.targeting.exclusion_manager import save_excluded_region
        
        # Auto-commit target name if text input is still active
        if self.text_input_active and self.temp_input:
            self.target_name = self.temp_input
            self.text_input_active = False
            print(f"Target name set to: {self.target_name}")
        
        try:
            if self.target_mode and self.target_selection_rect:
                save_target(self)
            elif self.bounds_mode and self.bounds_selection_rect:
                save_bounds(self)
            elif self.exclude_mode and self.exclude_selection_rect:
                save_excluded_region(self)
            else:
                print("No selection to capture. Select an area first.")
        except Exception as e:
            print(f"Error capturing: {e}")
            import traceback
            traceback.print_exc()
    
    def on_key_press(self, key, text):
        """Handle key press events for text input and shortcuts."""
        from PyQt6.QtCore import Qt
        from android_injections.ui.keyboard_handler import process_keyboard_event
        
        # Map Qt key codes to cv2-style key codes for compatibility
        key_map = {
            Qt.Key.Key_Return: 13,
            Qt.Key.Key_Enter: 13,
            Qt.Key.Key_Escape: 27,
            Qt.Key.Key_Backspace: 8,
            Qt.Key.Key_Delete: 127,
            Qt.Key.Key_F: ord('f'),
            Qt.Key.Key_T: ord('t'),
            Qt.Key.Key_B: ord('b'),
            Qt.Key.Key_E: ord('e'),
            Qt.Key.Key_S: ord('s'),
            Qt.Key.Key_A: ord('a'),
            Qt.Key.Key_U: ord('u'),
            Qt.Key.Key_V: ord('v'),
            Qt.Key.Key_Q: ord('q'),
        }
        
        # Handle text input mode for target name
        if self.text_input_active:
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # Finalize text input
                self.target_name = self.temp_input
                self.text_input_active = False
                self.temp_input = ""
                print(f"Target name set to: {self.target_name}")
            elif key == Qt.Key.Key_Escape:
                # Cancel text input
                self.text_input_active = False
                self.temp_input = ""
            elif key == Qt.Key.Key_Backspace:
                # Remove last character
                self.temp_input = self.temp_input[:-1]
            elif text and text.isprintable():
                # Add character
                self.temp_input += text
        # Handle text input mode for auto target
        elif hasattr(self, 'auto_target_input_active') and self.auto_target_input_active:
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # Finalize auto target input
                self.manual_target_name = self.auto_temp_input
                self.auto_target_input_active = False
                self.auto_temp_input = ""
                # Update index if target exists in list
                import os
                if os.path.exists(self.targets_dir):
                    target_files = sorted([f[:-5] for f in os.listdir(self.targets_dir) 
                                         if f.endswith('.json')])
                    if self.manual_target_name in target_files:
                        self.manual_target_index = target_files.index(self.manual_target_name)
                print(f"Auto target set to: {self.manual_target_name}")
            elif key == Qt.Key.Key_Escape:
                # Cancel auto target input
                self.auto_target_input_active = False
                self.auto_temp_input = ""
            elif key == Qt.Key.Key_Backspace:
                # Remove last character
                self.auto_temp_input = self.auto_temp_input[:-1]
            elif text and text.isprintable():
                # Add character
                self.auto_temp_input += text
        # Handle generic field editing
        elif hasattr(self, 'editing_field') and self.editing_field:
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # Finalize field input
                self._commit_field_edit()
            elif key == Qt.Key.Key_Escape:
                # Cancel field input
                self.editing_field = None
                self.field_temp_input = ""
            elif key == Qt.Key.Key_Backspace:
                # Remove last character
                self.field_temp_input = self.field_temp_input[:-1]
            elif text and (text.isdigit() or text == '.'):
                # Add numeric character or decimal point
                self.field_temp_input += text
        else:
            # Check for numeric field editing first
            if hasattr(self, 'editing_colors') and (
                self.editing_colors or 
                getattr(self, 'editing_min_pixels', False) or 
                getattr(self, 'editing_max_blobs', False) or
                getattr(self, 'editing_delay_min', False) or
                getattr(self, 'editing_delay_max', False) or
                getattr(self, 'editing_delay_mean', False) or
                getattr(self, 'editing_delay_std', False) or
                getattr(self, 'editing_stability', False) or
                getattr(self, 'editing_pass_distance', False) or
                getattr(self, 'editing_plane_size', False) or
                getattr(self, 'editing_minimap_counter_padding', False) or
                getattr(self, 'editing_xp_brightness', False) or
                getattr(self, 'editing_xp_sample_interval', False)
            ):
                # Convert Qt key to cv2-style key code for process_keyboard_event
                cv2_key = key_map.get(key, -1)
                if cv2_key == -1 and text and len(text) == 1:
                    cv2_key = ord(text)
                if cv2_key != -1:
                    process_keyboard_event(self, cv2_key)
            else:
                # Handle keyboard shortcuts
                if key == Qt.Key.Key_F:
                    self.show_filtered = not self.show_filtered
                elif key == Qt.Key.Key_T:
                    self.target_mode = not self.target_mode
                    if self.target_mode:
                        self.bounds_mode = False
                        self.exclude_mode = False
                elif key == Qt.Key.Key_B:
                    self.bounds_mode = not self.bounds_mode
                    if self.bounds_mode:
                        self.target_mode = False
                        self.exclude_mode = False
                elif key == Qt.Key.Key_E:
                    self.exclude_mode = not self.exclude_mode
                    if self.exclude_mode:
                        self.target_mode = False
                        self.bounds_mode = False
                elif key == Qt.Key.Key_S:
                    self.state_tracking = not self.state_tracking
                elif key == Qt.Key.Key_A:
                    self.auto_mode = not self.auto_mode
                elif key == Qt.Key.Key_U:
                    if hasattr(self, 'unique_only'):
                        self.unique_only = not self.unique_only
                elif key == Qt.Key.Key_Q or key == Qt.Key.Key_Escape:
                    # Quit application
                    if self.mirror_window:
                        self.mirror_window.close()
                elif key == Qt.Key.Key_Tab:
                    # Cycle through detected targets
                    if hasattr(self, 'detected_targets') and self.detected_targets:
                        target_list = list(self.detected_targets.keys())
                        if target_list:
                            self.selected_target_index = (self.selected_target_index + 1) % len(target_list)
                            selected_target = target_list[self.selected_target_index]
                            print(f"Selected target: {selected_target}")
                            self.target_selector_active = True
    
    def get_current_auto_target(self):
        """Get the current auto target name based on mode."""
        try:
            from android_injections.automation.auto_target import get_current_auto_target
            return get_current_auto_target(self)
        except:
            return "No target"
    
    def run_qt(self, app):
        """Run capture loop with PyQt6 window instead of cv2."""
        print(f"Searching for window: '{self.window_name}'...")
        
        # Find the target window
        self.window = self.find_window_by_name(self.window_name)
        if not self.window:
            print(f"Error: Window '{self.window_name}' not found!")
            print("Available windows:")
            self.list_windows()
            return False
        
        # Get the client window (without title bar decorations)
        self.client_window = self.get_client_window(self.window)
        print(f"Using {'client window' if self.client_window != self.window else 'main window'} for capture")
        
        # Get geometry from the client window
        client_geom = self.client_window.get_geometry()
        client_width = client_geom.width
        client_height = client_geom.height
        print(f"Client window dimensions: {client_width}x{client_height}")
        
        # Check resolution
        expected_width = 1080
        expected_height = 2340
        leeway = 5
        
        portrait_match = (expected_width - leeway <= client_width <= expected_width + leeway and 
                         expected_height - leeway <= client_height <= expected_height + leeway)
        landscape_match = (expected_height - leeway <= client_width <= expected_height + leeway and 
                          expected_width - leeway <= client_height <= expected_width + leeway)
        
        if not (portrait_match or landscape_match):
            print(f"\n⚠️  ERROR: Window resolution mismatch!")
            print(f"Expected: {expected_width}x{expected_height} or {expected_height}x{expected_width} (±{leeway}px) (Pixel 4a 5G)")
            print(f"Got: {client_width}x{client_height}")
            print(f"\nPlease resize the emulator window to match the phone's resolution.")
            return False
        
        x, y, width, height = self.get_window_geometry(self.window)
        print(f"Found window at: x={x}, y={y}, width={width}, height={height}")
        print(f"Target FPS: {self.target_fps}")
        
        # Initialize state variables (from original run() method)
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        self.target_selection_rect = None
        self.bounds_selection_rect = None
        self.exclude_selection_rect = None
        self.current_frame = None
        self.unique_colors = set()
        self.show_filtered = False
        self.unique_only = True
        self.target_name = ""
        self.text_input_active = False
        self.auto_target_input_active = False
        self.auto_temp_input = ""
        self.target_selector_active = False
        self.selected_target_index = 0
        self.target_mode = False
        self.bounds_mode = False
        self.exclude_mode = False
        self.state_tracking = False
        self.excluded_regions = []
        self.show_bounds = False
        self.show_excludes = False
        self.unique_only = True
        
        # Editing state
        self.editing_colors = False
        self.editing_min_pixels = False
        self.editing_max_blobs = False
        self.temp_input = ""
        
        # Field editing state for inline text input
        self.editing_field = None  # Name of currently editing field
        self.field_temp_input = ""  # Temporary input buffer for field editing
        
        # Plane detection
        self.higher_plane = False
        self.minimap_counter = 0
        self.minimap_counter_prev_value = None
        self.minimap_counter_stable_since = None
        
        # Auto mode
        self.auto_mode = False
        self.last_auto_touch = 0
        self.next_touch_interval = self.config.touch_delay_mean
        self.auto_target_list = []
        self.auto_target_index = 0
        self.auto_target_passed = False
        self.auto_target_touched = False
        self.auto_touched_time = None
        self.auto_target_prev_pos = None
        self.auto_target_stable_since = None
        self.auto_touched_position = None
        self.auto_dot_prev_pos = None
        self.auto_dot_stable_since = None
        self.auto_target_last_seen = None
        self.auto_target_timeout = 10.0
        
        # XP detection
        self.xp_last_value = None
        self.xp_current_reading = None
        self.xp_reading_first_seen = None
        self.xp_last_sample_time = 0
        self.xp_trigger_time = None
        self.xp_detected = "0"
        # xp_brightness_threshold is now a property that accesses config
        
        # Auto target list
        self.auto_target_list = []
        
        # Create mirror window
        self.mirror_window = MirrorWindow(self)
        self.mirror_window.show()
        
        # Load targets if state tracking will be enabled
        self.bounds_with_names = []
        self.excluded_regions_with_names = []
        self.detected_targets = {}
        self.filter_colors = set()
        
        try:
            load_all_targets(self)
        except Exception as e:
            print(f"Warning: Could not load targets: {e}")
        
        print("PyQt6 window created, capture loop running...")
        return True
    
    def _commit_field_edit(self):
        """Commit the current field edit."""
        if not self.editing_field or not self.field_temp_input:
            self.editing_field = None
            self.field_temp_input = ""
            return
        
        try:
            field_name = self.editing_field
            value_str = self.field_temp_input
            
            # Parse value based on field type
            if field_name in ['touch_delay_min', 'touch_delay_max', 'touch_delay_mean', 
                              'touch_delay_std', 'stability_timer', 'counter_stability_timer',
                              'xp_sample_interval']:
                value = float(value_str)
                # Apply field-specific bounds
                if field_name == 'touch_delay_min':
                    value = max(0.001, min(10.0, value))
                    self.config.touch_delay_min = value
                elif field_name == 'touch_delay_max':
                    value = max(0.001, min(20.0, value))
                    self.config.touch_delay_max = value
                elif field_name == 'touch_delay_mean':
                    value = max(0.001, min(10.0, value))
                    self.config.touch_delay_mean = value
                elif field_name == 'touch_delay_std':
                    value = max(0.001, min(5.0, value))
                    self.config.touch_delay_std = value
                elif field_name == 'stability_timer':
                    value = max(0.1, min(10.0, value))
                    self.config.stability_timer = value
                elif field_name == 'counter_stability_timer':
                    value = max(0.1, min(10.0, value))
                    self.config.counter_stability_timer = value
                elif field_name == 'xp_sample_interval':
                    value = max(0.1, min(10.0, value))
                    self.xp_sample_interval = value
                print(f"{field_name} set to {value}")
            elif field_name in ['passing_distance', 'plane_size', 'minimap_counter_padding', 
                               'xp_brightness_threshold']:
                value = int(value_str)
                # Apply field-specific bounds
                if field_name == 'passing_distance':
                    value = max(1, min(500, value))
                    self.config.passing_distance = value
                elif field_name == 'plane_size':
                    value = max(1, min(50, value))
                    self.config.plane_size = value
                elif field_name == 'minimap_counter_padding':
                    value = max(0, min(50, value))
                    self.config.minimap_counter_padding = value
                elif field_name == 'xp_brightness_threshold':
                    value = max(0, min(255, value))
                    self.xp_brightness_threshold = value
                print(f"{field_name} set to {value}")
        except ValueError:
            print(f"Invalid value for {self.editing_field}: {self.field_temp_input}")
        
        # Clear editing state
        self.editing_field = None
        self.field_temp_input = ""
    
    def update_auto_touch(self):
        """Update auto-touch logic (called each frame)."""
        if not self.auto_mode:
            return
        
        print(f"[AUTO] update_auto_touch called, auto_mode={self.auto_mode}")
        
        import time
        from android_injections.automation.auto_target import get_current_auto_target
        from android_injections.automation.delay_manager import is_delay_ready, execute_auto_touch
        from android_injections.automation.state_manager import (
            is_target_stable, is_dot_stable, check_target_passed
        )
        
        current_time = time.time()
        
        # Get current target name based on state
        current_target = get_current_auto_target(self)
        print(f"[AUTO] Current target: {current_target}, Detected: {list(self.detected_targets.keys()) if self.detected_targets else 'none'}")
        
        # Update the target field to show what auto mode is looking for
        if current_target:
            self.manual_target_name = current_target
        
        if current_target and hasattr(self, 'detected_targets') and current_target in self.detected_targets:
            tx, ty, tw, th = self.detected_targets[current_target]
            print(f"[AUTO] Target detected at ({tx}, {ty}), checking stability...")
            
            # Check if target is stable
            target_stable = is_target_stable(self, (tx, ty, tw, th))
            print(f"[AUTO] Target stable: {target_stable}")
            
            # Check if enough time has passed since last touch
            delay_ready = is_delay_ready(self, current_time)
            print(f"[AUTO] Delay ready: {delay_ready}")
            
            # Execute touch if conditions met
            if target_stable and delay_ready:
                center_x = tx + tw // 2
                center_y = ty + th // 2
                print(f"[AUTO] Both conditions met, executing touch at ({center_x}, {center_y})")
                execute_auto_touch(self, center_x, center_y, current_time)
            else:
                print(f"[AUTO] Waiting: stable={target_stable}, delay_ready={delay_ready}")
            
            # Check if target passed (XP gained)
            check_target_passed(self)
    
    def get_frame_for_display(self):
        """Fetch and prepare frame for PyQt6 display with overlays."""
        try:
            frame = self.capture_window_pil(self.client_window)
            if frame is None:
                return None
            
            # Convert to BGR
            import cv2
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.current_frame = frame_bgr.copy()
            self.frame_bgr = frame_bgr.copy()
            
            # Evaluate state if enabled
            if self.state_tracking:
                self.evaluate_state_fields(frame_bgr)
            
            # Apply filter or prepare display frame
            if self.show_filtered:
                display_frame = self.filter_unique_colors(frame_bgr.copy(), apply_scale=self.display_scale)
            else:
                display_frame = frame_bgr.copy()
                
                # Draw selection rectangle if active (only when filter is OFF)
                if self.selecting and self.selection_start and self.selection_end:
                    # Choose color based on mode
                    if self.exclude_mode:
                        color = (0, 0, 255)  # Red
                    elif self.bounds_mode:
                        color = (0, 255, 255)  # Yellow
                    else:
                        color = (0, 255, 0)  # Green
                    cv2.rectangle(display_frame, self.selection_start, self.selection_end, color, 2)
                else:
                    # Show saved selections
                    if self.target_selection_rect:
                        cv2.rectangle(display_frame, self.target_selection_rect[0], 
                                    self.target_selection_rect[1], (0, 255, 0), 2)  # Green
                    if self.bounds_selection_rect:
                        cv2.rectangle(display_frame, self.bounds_selection_rect[0], 
                                    self.bounds_selection_rect[1], (0, 255, 255), 2)  # Yellow
                    if self.exclude_selection_rect:
                        cv2.rectangle(display_frame, self.exclude_selection_rect[0], 
                                    self.exclude_selection_rect[1], (0, 0, 255), 2)  # Red
                
                # Draw all bounds rectangles with labels if enabled
                if hasattr(self, 'show_bounds') and self.show_bounds and hasattr(self, 'bounds_with_names'):
                    for bound in self.bounds_with_names:
                        bx1, by1, bx2, by2, name = bound
                        cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), (0, 255, 255), 2)
                        label_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                        label_y = max(by1 - 5, label_size[1] + 5)
                        cv2.putText(display_frame, name, (bx1, label_y), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Draw all excluded regions with labels if enabled
                if hasattr(self, 'show_excludes') and self.show_excludes and hasattr(self, 'excluded_regions_with_names'):
                    for exclude in self.excluded_regions_with_names:
                        ex1, ey1, ex2, ey2, name = exclude
                        cv2.rectangle(display_frame, (ex1, ey1), (ex2, ey2), (0, 0, 255), 2)
                        label_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                        label_y = max(ey1 - 5, label_size[1] + 5)
                        cv2.putText(display_frame, name, (ex1, label_y), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
                # Draw detected targets if state tracking is on
                if self.state_tracking and hasattr(self, 'detected_targets'):
                    for target_name, (tx, ty, tw, th) in self.detected_targets.items():
                        # Draw rectangle around target
                        cv2.rectangle(display_frame, (tx, ty), (tx + tw, ty + th), (255, 0, 255), 2)
                        # Draw label
                        label_size = cv2.getTextSize(target_name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                        label_y = max(ty - 5, label_size[1] + 5)
                        cv2.putText(display_frame, target_name, (tx, label_y), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
                
                # Draw white center dot
                h, w = display_frame.shape[:2]
                center_x = w // 2
                center_y = h // 2
                cv2.circle(display_frame, (center_x, center_y), 3, (255, 255, 255), -1)
                
                # Scale display frame if needed
                if self.display_scale != 1.0:
                    h, w = display_frame.shape[:2]
                    new_w = int(w * self.display_scale)
                    new_h = int(h * self.display_scale)
                    display_frame = cv2.resize(display_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            return display_frame
        except Exception as e:
            print(f"Error in get_frame_for_display: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    kill_existing_instances()
    
    parser = argparse.ArgumentParser(
        description="Mirror Android window pixels in real-time with PyQt6 UI"
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
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create capture instance
    capture = QtWindowCapture(args.window, args.fps, args.scale, args.benchmark)
    
    # Start the capture with Qt window
    if not capture.run_qt(app):
        sys.exit(1)
    
    # Run Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
