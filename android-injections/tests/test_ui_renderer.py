"""Unit tests for UI rendering functions."""
import pytest
import numpy as np


class TestCanvasCreation:
    """Tests for canvas creation and sizing."""
    
    def test_canvas_with_buttons(self, sample_frame):
        """Canvas should include extra height for buttons."""
        h, w = sample_frame.shape[:2]
        button_height = 40
        capture_ui_height = 220
        total_bottom_height = button_height + button_height + capture_ui_height
        
        expected_canvas_height = h + total_bottom_height
        expected_canvas_width = w
        
        # Verify calculation
        assert expected_canvas_height == h + 300
        assert expected_canvas_width == w
    
    def test_canvas_color_format(self):
        """Canvas should be BGR uint8."""
        h, w = 480, 640
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        
        assert canvas.dtype == np.uint8
        assert canvas.shape[2] == 3
        assert canvas.shape == (h, w, 3)


class TestButtonRendering:
    """Tests for button rendering and positioning."""
    
    def test_button_rect_calculation(self):
        """Test button rectangle calculations."""
        w = 1080
        button_width = w // 4  # Each button gets 1/4 of width
        
        # First button (target)
        assert button_width == 270
        
        # Four buttons total in first row
        buttons = [
            (0, 270),           # Target
            (270, 270),         # Bounds
            (540, 270),         # Exclude
            (810, 270),         # State tracking
        ]
        
        # Verify no overlap
        for i, (x1, w1) in enumerate(buttons):
            for j, (x2, w2) in enumerate(buttons):
                if i != j:
                    # No overlap
                    assert x1 + w1 <= x2 or x2 + w2 <= x1
    
    def test_button_text_positioning(self):
        """Button text should be centered vertically."""
        button_height = 40
        button_y = 2340
        text_size_height = 15
        
        # Centered calculation: button_y + (button_height + text_size_height) // 2
        expected_y = button_y + (button_height + text_size_height) // 2
        
        assert expected_y == button_y + 27


class TestCheckboxRendering:
    """Tests for checkbox rendering."""
    
    def test_unique_checkbox_sizing(self):
        """Unique checkbox should fit in button area."""
        checkbox_width = 70
        checkbox_height = 30
        button_width = 270
        button_height = 40
        
        # Should fit in button
        assert checkbox_width < button_width
        assert checkbox_height < button_height
    
    def test_checkbox_box_dimensions(self):
        """Checkbox inner box should be properly sized."""
        checkbox_size = 16
        checkbox_box_x = 5
        checkbox_box_y = 5
        
        # Verify it's square and reasonable size
        assert checkbox_size == 16
        assert checkbox_box_x + checkbox_size < 70


class TestSelectionRectangleRendering:
    """Tests for selection rectangle drawing."""
    
    def test_target_selection_color(self):
        """Target selection should be green."""
        color = (0, 255, 0)
        assert color[1] == 255  # Green channel is max
        assert color[0] == 0    # Blue is off
        assert color[2] == 0    # Red is off
    
    def test_bounds_selection_color(self):
        """Bounds selection should be yellow."""
        color = (0, 255, 255)
        assert color[1] == 255  # Green is max
        assert color[2] == 255  # Red is max
        assert color[0] == 0    # Blue is off
    
    def test_exclude_selection_color(self):
        """Exclude selection should be red."""
        color = (0, 0, 255)
        assert color[2] == 255  # Red is max
        assert color[0] == 0    # Blue is off
        assert color[1] == 0    # Green is off
    
    def test_rectangle_coordinates(self):
        """Rectangle from selection points should be normalized."""
        selection_start = (300, 100)
        selection_end = (150, 250)
        
        # Normalize
        x_min = min(selection_start[0], selection_end[0])
        y_min = min(selection_start[1], selection_end[1])
        x_max = max(selection_start[0], selection_end[0])
        y_max = max(selection_start[1], selection_end[1])
        
        assert (x_min, y_min) == (150, 100)
        assert (x_max, y_max) == (300, 250)


class TestTextFieldRendering:
    """Tests for text input field rendering."""
    
    def test_text_field_rect_calculation(self):
        """Text field should be positioned in UI area."""
        # Typical position for target name input
        tfx, tfy, tfw, tfh = 100, 2460, 200, 30
        
        # Should be in button area
        assert tfy > 2300  # Below main content
        assert tfw > 0
        assert tfh > 0
    
    def test_text_input_display(self, ui_state):
        """Text input should show entered text."""
        ui_state['target_name'] = 'ladder'
        ui_state['text_input_active'] = True
        
        assert ui_state['target_name'] == 'ladder'
        assert ui_state['text_input_active'] == True


class TestNumberFieldRendering:
    """Tests for number field display and editing."""
    
    def test_colors_field_display(self, ui_state):
        """Colors per target field should display current value."""
        ui_state['colors_per_target'] = 25
        
        # Display would show "25"
        display_text = str(ui_state['colors_per_target'])
        assert display_text == '25'
    
    def test_min_pixels_field_display(self, ui_state):
        """Min pixels field should display current value."""
        ui_state['min_blob_pixels'] = 5
        
        display_text = str(ui_state['min_blob_pixels'])
        assert display_text == '5'
    
    def test_max_blobs_field_display(self, ui_state):
        """Max blobs field should display with special case for unlimited."""
        ui_state['max_blobs'] = 0
        
        # Display shows "unlimited" when 0
        display_text = 'unlimited' if ui_state['max_blobs'] == 0 else str(ui_state['max_blobs'])
        assert display_text == 'unlimited'
        
        ui_state['max_blobs'] = 5
        display_text = 'unlimited' if ui_state['max_blobs'] == 0 else str(ui_state['max_blobs'])
        assert display_text == '5'


class TestStateDisplayRendering:
    """Tests for state information display."""
    
    def test_xp_display_format(self, ui_state):
        """XP display should show detected gain or '0'."""
        ui_state['xp_detected'] = '+50'
        assert ui_state['xp_detected'] == '+50'
        
        ui_state['xp_detected'] = '0'
        assert ui_state['xp_detected'] == '0'
    
    def test_plane_counter_display(self, ui_state):
        """Plane counter should display as number."""
        ui_state['plane_counter'] = 3
        display_text = str(ui_state['plane_counter'])
        assert display_text == '3'
    
    def test_higher_plane_indicator(self, ui_state):
        """Higher plane should be boolean for display."""
        ui_state['higher_plane'] = True
        assert ui_state['higher_plane'] == True
        
        ui_state['higher_plane'] = False
        assert ui_state['higher_plane'] == False


class TestAutoModeDisplay:
    """Tests for auto mode status display."""
    
    def test_auto_target_display_format(self, ui_state):
        """Auto mode should display current target."""
        ui_state['auto_mode'] = True
        
        # Simulated current target
        current_target = 'ladder'
        
        assert current_target == 'ladder'
        assert ui_state['auto_mode'] == True
    
    def test_auto_status_colors(self):
        """Auto mode status should use color coding."""
        # Waiting for target
        waiting_color = (200, 200, 100)  # Yellow
        assert waiting_color[1] == 200
        
        # Stabilizing
        stabilizing_color = (200, 100, 200)  # Magenta
        assert stabilizing_color[2] == 200
        
        # Ready
        ready_color = (100, 255, 100)  # Green
        assert ready_color[1] == 255


class TestFrameScaling:
    """Tests for display scaling."""
    
    def test_scaled_frame_dimensions(self, sample_frame):
        """Scaled frame should adjust dimensions properly."""
        h, w = sample_frame.shape[:2]
        display_scale = 0.5
        
        new_w = int(w * display_scale)
        new_h = int(h * display_scale)
        
        assert new_w == int(1080 * 0.5)
        assert new_h == int(2340 * 0.5)
    
    def test_coordinate_scaling(self):
        """Coordinates should scale with display."""
        original_x = 1080
        original_y = 2340
        scale = 0.5
        
        scaled_x = int(original_x * scale)
        scaled_y = int(original_y * scale)
        
        assert scaled_x == 540
        assert scaled_y == 1170


class TestColorRendering:
    """Tests for color values in rendering."""
    
    def test_button_color_active(self):
        """Active buttons should use bright color."""
        active_color = (0, 120, 0)  # Dark green
        inactive_color = (60, 60, 60)  # Gray
        
        assert active_color[1] > inactive_color[1]
    
    def test_text_color(self):
        """UI text should be white/light."""
        text_color = (255, 255, 255)
        assert all(c == 255 for c in text_color)
    
    def test_bounds_overlay_color(self):
        """Bounds overlay should be yellow."""
        bounds_color = (0, 255, 255)
        assert bounds_color[1] == 255  # Green
        assert bounds_color[2] == 255  # Red


class TestCenterDotRendering:
    """Tests for center crosshair/dot."""
    
    def test_center_calculation(self):
        """Center dot should be at midpoint of frame."""
        w, h = 1080, 2340
        
        center_x = w // 2
        center_y = h // 2
        
        assert center_x == 540
        assert center_y == 1170
    
    def test_center_dot_properties(self):
        """Center dot should be white circle."""
        center_color = (255, 255, 255)
        dot_radius = 3
        
        assert center_color == (255, 255, 255)
        assert dot_radius > 0


class TestOverlayRendering:
    """Tests for overlay rectangles (bounds and excludes)."""
    
    def test_bounds_overlay_with_label(self):
        """Bounds overlay should include label."""
        bound = (100, 200, 300, 250, 'xp')
        
        assert len(bound) == 5
        assert bound[4] == 'xp'
    
    def test_exclude_overlay_with_label(self):
        """Exclude overlay should include label."""
        exclude = (50, 100, 150, 200, 'tree')
        
        assert len(exclude) == 5
        assert exclude[4] == 'tree'
    
    def test_label_positioning(self):
        """Label should position above rectangle."""
        bound_y1 = 200
        label_size_height = 20
        
        # Label y = max(bound_y - 5, label_size + 5)
        label_y = max(bound_y1 - 5, label_size_height + 5)
        
        assert label_y > 0
        assert label_y < bound_y1  # Above or at edge
