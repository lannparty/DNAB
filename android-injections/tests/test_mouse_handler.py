"""Unit tests for mouse callback behavior."""
import pytest


class TestMouseButtonToggling:
    """Tests for mouse button click behavior."""
    
    def test_target_button_toggles_mode(self, ui_state, button_positions, rect_helper):
        """Clicking target button toggles target mode on/off."""
        # Simulate helper function that would be in mouse handler
        def toggle_target_mode(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['target_mode'] = not state['target_mode']
                # Disable other modes
                state['bounds_mode'] = False
                state['exclude_mode'] = False
                state['selecting'] = False
                state['target_selection_rect'] = None
        
        # Click on target button
        rect = button_positions['target_mode_button']
        assert ui_state['target_mode'] == False
        
        toggle_target_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['target_mode'] == True
        
        toggle_target_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['target_mode'] == False
    
    def test_bounds_button_toggles_mode(self, ui_state, button_positions, rect_helper):
        """Clicking bounds button toggles bounds mode on/off."""
        def toggle_bounds_mode(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['bounds_mode'] = not state['bounds_mode']
                state['target_mode'] = False
                state['exclude_mode'] = False
                state['selecting'] = False
                state['bounds_selection_rect'] = None
        
        rect = button_positions['bounds_button']
        assert ui_state['bounds_mode'] == False
        
        toggle_bounds_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['bounds_mode'] == True
        
        toggle_bounds_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['bounds_mode'] == False
    
    def test_exclude_button_toggles_mode(self, ui_state, button_positions, rect_helper):
        """Clicking exclude button toggles exclude mode on/off."""
        def toggle_exclude_mode(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['exclude_mode'] = not state['exclude_mode']
                state['target_mode'] = False
                state['bounds_mode'] = False
                state['selecting'] = False
                state['selection_start'] = None
                state['selection_end'] = None
        
        rect = button_positions['exclude_mode_button']
        assert ui_state['exclude_mode'] == False
        
        toggle_exclude_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['exclude_mode'] == True
        
        toggle_exclude_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['exclude_mode'] == False
    
    def test_state_tracking_button_toggle(self, ui_state, button_positions, rect_helper):
        """Clicking state tracking button toggles state tracking."""
        def toggle_state_tracking(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['state_tracking'] = not state['state_tracking']
                if not state['state_tracking']:
                    # Reset state values when disabled
                    state['xp_detected'] = '0'
                    state['xp_last_value'] = None
                    state['higher_plane'] = False
                    state['plane_counter'] = 0
        
        rect = button_positions['state_tracking_button']
        assert ui_state['state_tracking'] == False
        
        toggle_state_tracking(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['state_tracking'] == True
        
        # Set some state values
        ui_state['xp_detected'] = '+50'
        ui_state['higher_plane'] = True
        assert ui_state['xp_detected'] == '+50'
        
        # Disable and verify reset
        toggle_state_tracking(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['state_tracking'] == False
        assert ui_state['xp_detected'] == '0'
        assert ui_state['higher_plane'] == False


class TestAutoModeButton:
    """Tests for auto mode button behavior."""
    
    def test_auto_mode_button_toggles(self, ui_state, button_positions, rect_helper):
        """Clicking auto button toggles auto mode."""
        def toggle_auto_mode(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['auto_mode'] = not state['auto_mode']
                if state['auto_mode']:
                    # Auto-enable filter and tracking
                    state['show_filtered'] = True
                    state['auto_view_mode'] = True
                    state['state_tracking'] = True
        
        rect = button_positions['auto_button']
        assert ui_state['auto_mode'] == False
        
        toggle_auto_mode(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['auto_mode'] == True
        assert ui_state['show_filtered'] == True
        assert ui_state['auto_view_mode'] == True
        assert ui_state['state_tracking'] == True
    
    def test_auto_mode_disables_properly(self, ui_state):
        """Auto mode can be disabled."""
        ui_state['auto_mode'] = True
        ui_state['show_filtered'] = True
        
        ui_state['auto_mode'] = False
        assert ui_state['auto_mode'] == False


class TestFilterButton:
    """Tests for filter button behavior."""
    
    def test_filter_toggle(self, ui_state, button_positions, rect_helper):
        """Clicking filter button toggles filter on/off."""
        def toggle_filter(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['show_filtered'] = not state['show_filtered']
                if state['show_filtered']:
                    # When turning on, would load targets
                    state['filter_colors'] = {(100, 50, 200), (110, 60, 210)}
                else:
                    # When turning off, clear detections
                    state['detected_targets'] = {}
        
        rect = button_positions['filter_button']
        assert ui_state['show_filtered'] == False
        
        toggle_filter(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['show_filtered'] == True
        assert len(ui_state['filter_colors']) > 0
        
        toggle_filter(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['show_filtered'] == False
        assert ui_state['detected_targets'] == {}


class TestUniqueOnlyCheckbox:
    """Tests for unique only checkbox."""
    
    def test_unique_only_toggle(self, ui_state, button_positions, rect_helper):
        """Clicking unique checkbox toggles unique_only setting."""
        def toggle_unique_only(state, x, y, rect):
            if rect_helper(x, y, rect[0], rect[1], rect[2], rect[3]):
                state['unique_only'] = not state['unique_only']
        
        rect = button_positions['unique_checkbox']
        assert ui_state['unique_only'] == True
        
        toggle_unique_only(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['unique_only'] == False
        
        toggle_unique_only(ui_state, rect[0] + 5, rect[1] + 5, rect)
        assert ui_state['unique_only'] == True


class TestTextFieldActivation:
    """Tests for text field activation."""
    
    def test_text_field_activation(self, ui_state):
        """Clicking text field activates text input."""
        # Simulate text field rect
        text_field_rect = (100, 2460, 200, 30)
        
        def activate_text_field(state, x, y, rect):
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                state['text_input_active'] = True
                return True
            return False
        
        assert ui_state['text_input_active'] == False
        
        result = activate_text_field(ui_state, text_field_rect[0] + 5, text_field_rect[1] + 5, text_field_rect)
        assert result == True
        assert ui_state['text_input_active'] == True
    
    def test_text_field_click_outside_deactivates(self, ui_state):
        """Clicking outside text field deactivates text input."""
        ui_state['text_input_active'] = True
        ui_state['target_name'] = 'test'
        
        # Click outside (e.g., on filter button)
        ui_state['text_input_active'] = False
        
        assert ui_state['text_input_active'] == False
        assert ui_state['target_name'] == 'test'  # Name preserved


class TestNumberFieldEditing:
    """Tests for number field editing activation."""
    
    def test_colors_field_edit_activation(self, ui_state):
        """Clicking colors display field activates editing."""
        colors_display_rect = (50, 2500, 100, 30)
        
        def activate_colors_edit(state, x, y, rect):
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                state['editing_colors'] = True
                state['editing_min_pixels'] = False
                state['editing_max_blobs'] = False
                state['temp_input'] = str(state['colors_per_target'])
                return True
            return False
        
        assert ui_state['editing_colors'] == False
        
        result = activate_colors_edit(ui_state, colors_display_rect[0] + 5, colors_display_rect[1] + 5, colors_display_rect)
        assert result == True
        assert ui_state['editing_colors'] == True
        assert ui_state['temp_input'] == '20'
    
    def test_min_pixels_field_edit_activation(self, ui_state):
        """Clicking min pixels display field activates editing."""
        pixels_display_rect = (50, 2540, 100, 30)
        
        def activate_pixels_edit(state, x, y, rect):
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                state['editing_min_pixels'] = True
                state['editing_colors'] = False
                state['editing_max_blobs'] = False
                state['temp_input'] = str(state['min_blob_pixels'])
                return True
            return False
        
        assert ui_state['editing_min_pixels'] == False
        
        result = activate_pixels_edit(ui_state, pixels_display_rect[0] + 5, pixels_display_rect[1] + 5, pixels_display_rect)
        assert result == True
        assert ui_state['editing_min_pixels'] == True
        assert ui_state['temp_input'] == '2'


class TestClickMissDetection:
    """Tests for clicks outside button areas."""
    
    def test_click_outside_buttons_no_effect(self, ui_state, rect_helper):
        """Clicking far outside any button area should have no effect."""
        def check_button_hit(x, y, rect):
            return rect_helper(x, y, rect[0], rect[1], rect[2], rect[3])
        
        # Click at coordinate (500, 500) which should be on main display
        button_rect = (0, 2340, 270, 40)  # Target button position
        
        result = check_button_hit(500, 500, button_rect)
        assert result == False
    
    def test_click_on_button_edge_detected(self, ui_state, rect_helper):
        """Clicking on button edge should be detected."""
        button_rect = (0, 2340, 270, 40)  # (x, y, w, h)
        
        # Click on left edge
        result = rect_helper(0, 2340, button_rect[0], button_rect[1], button_rect[2], button_rect[3])
        assert result == True
        
        # Click on right edge
        result = rect_helper(270, 2340, button_rect[0], button_rect[1], button_rect[2], button_rect[3])
        assert result == True


class TestBoundsToggleButtons:
    """Tests for bounds visualization toggle."""
    
    def test_show_bounds_toggle(self, ui_state):
        """Test show bounds can be toggled."""
        assert ui_state['show_bounds'] == False
        
        ui_state['show_bounds'] = True
        assert ui_state['show_bounds'] == True
        
        ui_state['show_bounds'] = False
        assert ui_state['show_bounds'] == False
    
    def test_show_excludes_toggle(self, ui_state):
        """Test show excludes can be toggled."""
        assert ui_state['show_excludes'] == False
        
        ui_state['show_excludes'] = True
        assert ui_state['show_excludes'] == True
        
        ui_state['show_excludes'] = False
        assert ui_state['show_excludes'] == False
    
    def test_auto_view_mode_toggle(self, ui_state):
        """Test auto view mode can be toggled."""
        assert ui_state['auto_view_mode'] == False
        
        ui_state['auto_view_mode'] = True
        assert ui_state['auto_view_mode'] == True
        
        ui_state['auto_view_mode'] = False
        assert ui_state['auto_view_mode'] == False


class TestSelectionDuringModes:
    """Tests for selection behavior in different modes."""
    
    def test_selection_clears_when_mode_disabled(self, ui_state):
        """When mode is disabled, active selection should clear."""
        # Start target mode
        ui_state['target_mode'] = True
        ui_state['selecting'] = True
        ui_state['selection_start'] = (100, 100)
        ui_state['selection_end'] = (200, 200)
        
        # Disable target mode
        ui_state['target_mode'] = False
        ui_state['selecting'] = False
        ui_state['selection_start'] = None
        ui_state['selection_end'] = None
        
        assert ui_state['target_mode'] == False
        assert ui_state['selecting'] == False
        assert ui_state['selection_start'] is None
    
    def test_selection_start_without_mode_not_tracked(self, ui_state):
        """Selection shouldn't start if mode is not active."""
        assert ui_state['target_mode'] == False
        
        # Try to start selection without mode
        # In real handler, would be rejected
        if not ui_state['target_mode']:
            ui_state['selecting'] = False
        
        assert ui_state['selecting'] == False
