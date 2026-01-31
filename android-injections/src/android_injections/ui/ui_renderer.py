"""UI rendering module - handles all display drawing."""
import cv2
import numpy as np
import time


def render_frame(window_capture_instance, display_frame, window_title):
    """Orchestrates all UI drawing and display.
    
    Handles all rendering: selections, bounds, excludes, center dot, buttons,
    controls, text fields, and status displays.
    """
    self = window_capture_instance
    
    # Always scale frame_bgr for drawing selection rectangles
    if self.display_scale != 1.0:
        h, w = display_frame.shape[:2]
        new_w = int(w * self.display_scale)
        new_h = int(h * self.display_scale)
        display_frame = cv2.resize(display_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
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
    capture_ui_height = 220
    total_bottom_height = button_height + button_height + capture_ui_height
    
    # Create canvas with extra space for buttons and capture UI
    canvas = np.zeros((h + total_bottom_height, w, 3), dtype=np.uint8)
    canvas[:h, :] = display_frame
    
    # Draw first buttons row (Target, Bounds, Exclude, State)
    button_y = h
    button_width = w // 4
    
    # Target Mode button
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
    filter_text = "Filter: ON" if self.show_filtered else "Filter: OFF"
    text_size = self.get_text_size_cached(filter_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
    text_x = 10
    text_y = filter_button_y + (button_height + text_size[1]) // 2
    cv2.putText(canvas, filter_text, (text_x, text_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    # Horizontal controls (right side of filter button) - inline controls for colors, pixels, blobs
    controls_y = filter_button_y + 7
    control_h = 25
    controls_start_x = 120
    spacing = 5
    
    # Color count controls
    cv2.putText(canvas, "colors:", (controls_start_x, controls_y + 18), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    minus_x = controls_start_x + 50
    cv2.rectangle(canvas, (minus_x, controls_y), (minus_x + 20, controls_y + control_h), (80, 80, 80), -1)
    cv2.putText(canvas, "-", (minus_x + 6, controls_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    self.colors_minus_rect = (minus_x, controls_y, 20, control_h)
    
    num_x = minus_x + 22
    cv2.rectangle(canvas, (num_x, controls_y), (num_x + 25, controls_y + control_h), (40, 40, 40), -1)
    cv2.putText(canvas, str(self.colors_per_target), (num_x + 7, controls_y + 17), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    self.colors_display_rect = (num_x, controls_y, 25, control_h)
    
    plus_x = num_x + 27
    cv2.rectangle(canvas, (plus_x, controls_y), (plus_x + 20, controls_y + control_h), (80, 80, 80), -1)
    cv2.putText(canvas, "+", (plus_x + 5, controls_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    self.colors_plus_rect = (plus_x, controls_y, 20, control_h)
    
    self.button_rect = (0, filter_button_y, w, button_height)
    
    # Draw capture UI (always visible)
    capture_y = filter_button_y + button_height
    cv2.rectangle(canvas, (0, capture_y), (w, capture_y + capture_ui_height), (40, 40, 40), -1)
    
    # Text field + Capture button
    text_field_x = 10
    text_field_y = capture_y + 5
    text_field_height = 30
    display_text = self.target_name if self.target_name else "name..."
    text_color = (255, 255, 255) if self.target_name else (120, 120, 120)
    cv2.rectangle(canvas, (text_field_x, text_field_y), 
                (text_field_x + 180, text_field_y + text_field_height), 
                (60, 60, 60), -1)
    cv2.putText(canvas, display_text, (text_field_x + 5, text_field_y + 20), 
              cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
    self.text_field_rect = (text_field_x, text_field_y, 180, text_field_height)
    
    # Capture button
    capture_button_x = text_field_x + 190
    capture_button_y = capture_y + 5
    capture_button_h = 30
    has_data = self.target_name and (
        (self.target_mode and (hasattr(self, 'unique_colors') and self.unique_colors if self.unique_only else (hasattr(self, 'all_box_colors_by_count') and self.all_box_colors_by_count))) or
        (self.bounds_mode and self.bounds_selection_rect) or
        (self.exclude_mode and self.selection_start and self.selection_end)
    )
    button_bg_color = (0, 100, 200) if has_data else (50, 50, 50)
    cv2.rectangle(canvas, (capture_button_x, capture_button_y), 
                (capture_button_x + 70, capture_button_y + capture_button_h), 
                button_bg_color, -1)
    cv2.putText(canvas, "Capture", (capture_button_x + 10, capture_button_y + 20), 
              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255) if has_data else (100, 100, 100), 1)
    self.capture_button_rect = (capture_button_x, capture_button_y, 70, capture_button_h)
    
    # Auto target display + button
    auto_display_x = capture_button_x + 80
    auto_button_x = w - 80
    current_auto_target = self.get_current_auto_target()
    auto_field_text = current_auto_target if current_auto_target else "No target"
    cv2.rectangle(canvas, (auto_display_x, capture_button_y), 
                (auto_button_x - 10, capture_button_y + 30),
                (50, 50, 50), -1)
    cv2.putText(canvas, auto_field_text[:30], (auto_display_x + 5, capture_button_y + 20), 
              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # Auto button
    auto_bg_color = (0, 120, 0) if self.auto_mode else (60, 60, 60)
    cv2.rectangle(canvas, (auto_button_x, capture_button_y), 
                (w - 10, capture_button_y + 30),
                auto_bg_color, -1)
    auto_text = "Auto:ON" if self.auto_mode else "Auto:OFF"
    cv2.putText(canvas, auto_text, (auto_button_x + 5, capture_button_y + 20), 
              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    self.auto_button_rect = (auto_button_x, capture_button_y, 70, 30)
    
    # Placeholder rects for other controls to avoid attribute errors
    self.colors_minus_rect = (0, 0, 0, 0)
    self.colors_plus_rect = (0, 0, 0, 0)
    self.pixels_minus_rect = (0, 0, 0, 0)
    self.pixels_plus_rect = (0, 0, 0, 0)
    self.max_blobs_minus_rect = (0, 0, 0, 0)
    self.max_blobs_plus_rect = (0, 0, 0, 0)
    
    # Draw touch feedback (red X marks)
    import time
    draw_touch_feedback(display_frame, self.touch_feedback_positions, self.touch_feedback_duration, time.time())
    
    # Display the frame
    cv2.imshow(window_title, canvas)


def draw_touch_feedback(display_frame, touch_positions, feedback_duration, current_time):
    """Draw red X marks at recent touch positions.
    
    Args:
        display_frame: The frame to draw on
        touch_positions: List of (x, y, timestamp) tuples
        feedback_duration: How long to show feedback in seconds
        current_time: Current time for filtering old touches
    """
    if not touch_positions:
        return
    
    # Filter out old touch positions
    recent_touches = [
        (x, y) for x, y, timestamp in touch_positions 
        if current_time - timestamp <= feedback_duration
    ]
    
    # Draw red X at each recent touch position
    for x, y in recent_touches:
        # Scale coordinates if needed (assuming display_frame is already scaled)
        x_scaled = int(x)
        y_scaled = int(y)
        
        # Draw X with lines
        line_length = 10
        thickness = 2
        
        # Top-left to bottom-right
        cv2.line(display_frame, 
                (x_scaled - line_length, y_scaled - line_length),
                (x_scaled + line_length, y_scaled + line_length),
                (0, 0, 255), thickness)
        
        # Top-right to bottom-left
        cv2.line(display_frame,
                (x_scaled + line_length, y_scaled - line_length),
                (x_scaled - line_length, y_scaled + line_length),
                (0, 0, 255), thickness)
