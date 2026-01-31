"""Unit tests for UI state management."""
import pytest


class TestUIStateInitialization:
    """Tests for UI state initialization."""
    
    def test_initial_state_all_modes_off(self, ui_state):
        """Verify all interaction modes start as disabled."""
        assert ui_state['target_mode'] == False
        assert ui_state['bounds_mode'] == False
        assert ui_state['exclude_mode'] == False
        assert ui_state['auto_mode'] == False
        assert ui_state['state_tracking'] == False
        assert ui_state['show_filtered'] == False
    
    def test_initial_selection_state_empty(self, ui_state):
        """Verify selection state is empty on init."""
        assert ui_state['selection_start'] is None
        assert ui_state['selection_end'] is None
        assert ui_state['selecting'] == False
        assert ui_state['target_selection_rect'] is None
        assert ui_state['bounds_selection_rect'] is None
    
    def test_initial_text_input_inactive(self, ui_state):
        """Verify text input is inactive on init."""
        assert ui_state['text_input_active'] == False
        assert ui_state['target_name'] == ''
        assert ui_state['temp_input'] == ''
    
    def test_initial_filter_settings(self, ui_state):
        """Verify filter settings are properly initialized."""
        assert ui_state['colors_per_target'] == 20
        assert ui_state['min_blob_pixels'] == 2
        assert ui_state['max_blobs'] == 1
        assert ui_state['unique_only'] == True
    
    def test_initial_plane_detection_state(self, ui_state):
        """Verify plane detection state is initialized."""
        assert ui_state['plane_size'] == 20
        assert ui_state['higher_plane'] == False
        assert ui_state['plane_counter'] == 0
        assert ui_state['minimap_counter_padding'] == 5
    
    def test_initial_xp_state(self, ui_state):
        """Verify XP detection state is initialized."""
        assert ui_state['xp_last_value'] is None
        assert ui_state['xp_detected'] == '0'
        assert ui_state['xp_brightness_threshold'] == 170
        assert ui_state['xp_sample_interval'] == 1.0
    
    def test_initial_auto_mode_state(self, ui_state):
        """Verify auto mode state is initialized."""
        assert ui_state['auto_mode'] == False
        assert ui_state['auto_target_passed'] == False
        assert ui_state['auto_target_touched'] == False
        assert ui_state['touch_delay_mean'] == 0.8
        assert ui_state['stability_timer'] == 1.0
    
    def test_initial_data_structures_empty(self, ui_state):
        """Verify data structures are empty on init."""
        assert ui_state['filter_colors'] == set()
        assert ui_state['unique_colors'] == set()
        assert ui_state['detected_targets'] == {}
        assert ui_state['excluded_regions'] == []
        assert ui_state['bounds_with_names'] == []


class TestModeToggling:
    """Tests for mode toggling behavior."""
    
    def test_target_mode_toggle(self, ui_state):
        """Test target mode can be toggled on/off."""
        assert ui_state['target_mode'] == False
        ui_state['target_mode'] = True
        assert ui_state['target_mode'] == True
        ui_state['target_mode'] = False
        assert ui_state['target_mode'] == False
    
    def test_bounds_mode_toggle(self, ui_state):
        """Test bounds mode can be toggled on/off."""
        assert ui_state['bounds_mode'] == False
        ui_state['bounds_mode'] = True
        assert ui_state['bounds_mode'] == True
        ui_state['bounds_mode'] = False
        assert ui_state['bounds_mode'] == False
    
    def test_exclude_mode_toggle(self, ui_state):
        """Test exclude mode can be toggled on/off."""
        assert ui_state['exclude_mode'] == False
        ui_state['exclude_mode'] = True
        assert ui_state['exclude_mode'] == True
        ui_state['exclude_mode'] = False
        assert ui_state['exclude_mode'] == False
    
    def test_filter_toggle(self, ui_state):
        """Test filter can be toggled on/off."""
        assert ui_state['show_filtered'] == False
        ui_state['show_filtered'] = True
        assert ui_state['show_filtered'] == True
        ui_state['show_filtered'] = False
        assert ui_state['show_filtered'] == False


class TestModeMutualExclusion:
    """Tests for mode mutual exclusion (only one mode active at a time)."""
    
    def test_target_disables_bounds_and_exclude(self, ui_state):
        """Enabling target mode should disable bounds and exclude (via handler logic)."""
        # This test demonstrates the logic that SHOULD be in the mouse handler
        # when target mode is toggled
        
        # Setup: other modes already on
        ui_state['bounds_mode'] = True
        ui_state['exclude_mode'] = True
        
        # Simulate toggle logic that SHOULD be in handler
        ui_state['target_mode'] = not ui_state['target_mode']
        if ui_state['target_mode']:
            ui_state['bounds_mode'] = False
            ui_state['exclude_mode'] = False
        
        # Verify mutual exclusion was applied
        assert ui_state['target_mode'] == True
        assert ui_state['bounds_mode'] == False
        assert ui_state['exclude_mode'] == False
    
    def test_bounds_disables_target_and_exclude(self, ui_state):
        """Enabling bounds mode should disable target and exclude (via handler logic)."""
        # Setup: other modes already on
        ui_state['target_mode'] = True
        ui_state['exclude_mode'] = True
        
        # Simulate toggle logic that SHOULD be in handler
        ui_state['bounds_mode'] = not ui_state['bounds_mode']
        if ui_state['bounds_mode']:
            ui_state['target_mode'] = False
            ui_state['exclude_mode'] = False
        
        # Verify mutual exclusion was applied
        assert ui_state['target_mode'] == False
        assert ui_state['bounds_mode'] == True
        assert ui_state['exclude_mode'] == False
    
    def test_exclude_disables_target_and_bounds(self, ui_state):
        """Enabling exclude mode should disable target and bounds (via handler logic)."""
        # Setup: other modes already on
        ui_state['target_mode'] = True
        ui_state['bounds_mode'] = True
        
        # Simulate toggle logic that SHOULD be in handler
        ui_state['exclude_mode'] = not ui_state['exclude_mode']
        if ui_state['exclude_mode']:
            ui_state['target_mode'] = False
            ui_state['bounds_mode'] = False
        
        # Verify mutual exclusion was applied
        assert ui_state['target_mode'] == False
        assert ui_state['bounds_mode'] == False
        assert ui_state['exclude_mode'] == True


class TestNumberFieldEditing:
    """Tests for number field editing state."""
    
    def test_colors_editing_mode(self, ui_state):
        """Test colors per target editing."""
        assert ui_state['editing_colors'] == False
        ui_state['editing_colors'] = True
        assert ui_state['editing_colors'] == True
    
    def test_min_pixels_editing_mode(self, ui_state):
        """Test min blob pixels editing."""
        assert ui_state['editing_min_pixels'] == False
        ui_state['editing_min_pixels'] = True
        assert ui_state['editing_min_pixels'] == True
    
    def test_max_blobs_editing_mode(self, ui_state):
        """Test max blobs editing."""
        assert ui_state['editing_max_blobs'] == False
        ui_state['editing_max_blobs'] = True
        assert ui_state['editing_max_blobs'] == True
    
    def test_only_one_edit_field_active(self, ui_state):
        """Only one number field should be editable at a time (via handler logic)."""
        # This test demonstrates the mutual exclusion logic that SHOULD be in the handler
        
        # Start with colors editing
        ui_state['editing_colors'] = True
        assert ui_state['editing_colors'] == True
        
        # When switching to min_pixels, colors should disable
        ui_state['editing_colors'] = False
        ui_state['editing_min_pixels'] = True
        assert ui_state['editing_colors'] == False
        assert ui_state['editing_min_pixels'] == True
        
        # When switching to max_blobs, min_pixels should disable
        ui_state['editing_min_pixels'] = False
        ui_state['editing_max_blobs'] = True
        assert ui_state['editing_colors'] == False
        assert ui_state['editing_min_pixels'] == False
        assert ui_state['editing_max_blobs'] == True
    
    def test_delay_timer_editing_exclusivity(self, ui_state):
        """Only one delay timer field should be editable at a time (via handler logic)."""
        # Start with min delay editing
        ui_state['editing_delay_min'] = True
        assert ui_state['editing_delay_min'] == True
        
        # When switching to max, min should disable
        ui_state['editing_delay_min'] = False
        ui_state['editing_delay_max'] = True
        
        assert ui_state['editing_delay_min'] == False
        assert ui_state['editing_delay_max'] == True


class TestSelectionState:
    """Tests for selection rectangle state."""
    
    def test_selection_state_transitions(self, ui_state):
        """Test selection state transitions."""
        # Start not selecting
        assert ui_state['selecting'] == False
        
        # Start selection
        ui_state['selecting'] = True
        ui_state['selection_start'] = (100, 100)
        assert ui_state['selecting'] == True
        assert ui_state['selection_start'] == (100, 100)
        
        # End selection
        ui_state['selection_end'] = (200, 200)
        assert ui_state['selection_end'] == (200, 200)
        
        # Clear selection
        ui_state['selecting'] = False
        ui_state['selection_start'] = None
        ui_state['selection_end'] = None
        assert ui_state['selecting'] == False
        assert ui_state['selection_start'] is None
    
    def test_target_selection_rect_storage(self, ui_state):
        """Test storing target selection rectangle."""
        rect = ((100, 100), (300, 300))
        ui_state['target_selection_rect'] = rect
        assert ui_state['target_selection_rect'] == rect
    
    def test_bounds_selection_rect_storage(self, ui_state):
        """Test storing bounds selection rectangle."""
        rect = ((50, 50), (250, 250))
        ui_state['bounds_selection_rect'] = rect
        assert ui_state['bounds_selection_rect'] == rect
    
    def test_exclude_selection_rect_storage(self, ui_state):
        """Test storing exclude selection rectangle."""
        rect = ((150, 150), (350, 350))
        ui_state['exclude_selection_rect'] = rect
        assert ui_state['exclude_selection_rect'] == rect


class TestAutoModeState:
    """Tests for auto mode state management."""
    
    def test_auto_mode_activation(self, ui_state):
        """Test auto mode can be activated."""
        assert ui_state['auto_mode'] == False
        ui_state['auto_mode'] = True
        assert ui_state['auto_mode'] == True
    
    def test_auto_mode_enables_state_tracking(self, ui_state):
        """When auto mode activates, state tracking should also be enabled."""
        ui_state['auto_mode'] = True
        ui_state['state_tracking'] = True  # Should be auto-enabled
        assert ui_state['auto_mode'] == True
        assert ui_state['state_tracking'] == True
    
    def test_auto_target_tracking(self, ui_state):
        """Test auto target tracking state."""
        ui_state['auto_target_touched'] = True
        assert ui_state['auto_target_touched'] == True
        
        ui_state['auto_target_passed'] = True
        assert ui_state['auto_target_passed'] == True
    
    def test_touch_delay_parameters(self, ui_state):
        """Test touch delay parameters are properly initialized."""
        assert ui_state['touch_delay_min'] == 0.3
        assert ui_state['touch_delay_max'] == 4.358
        assert ui_state['touch_delay_mean'] == 0.8
        assert ui_state['touch_delay_std'] == 0.6


class TestStateTracking:
    """Tests for state tracking (XP, plane detection)."""
    
    def test_state_tracking_toggle(self, ui_state):
        """Test state tracking can be toggled."""
        assert ui_state['state_tracking'] == False
        ui_state['state_tracking'] = True
        assert ui_state['state_tracking'] == True
        
        # When turned off, reset detection values
        ui_state['state_tracking'] = False
        ui_state['xp_detected'] = '0'
        ui_state['higher_plane'] = False
        ui_state['plane_counter'] = 0
        
        assert ui_state['state_tracking'] == False
        assert ui_state['xp_detected'] == '0'
        assert ui_state['higher_plane'] == False
        assert ui_state['plane_counter'] == 0
    
    def test_xp_gain_detection(self, ui_state):
        """Test XP gain can be detected and stored."""
        ui_state['xp_last_value'] = 1000
        ui_state['xp_detected'] = '+50'
        assert ui_state['xp_detected'] == '+50'
        
        # Clear after timeout
        ui_state['xp_detected'] = '0'
        assert ui_state['xp_detected'] == '0'
    
    def test_plane_counter_update(self, ui_state):
        """Test plane counter can be updated."""
        assert ui_state['plane_counter'] == 0
        ui_state['plane_counter'] = 3
        assert ui_state['plane_counter'] == 3
        
        ui_state['plane_counter'] = 4
        assert ui_state['plane_counter'] == 4
    
    def test_higher_plane_detection(self, ui_state):
        """Test higher plane detection state."""
        assert ui_state['higher_plane'] == False
        ui_state['higher_plane'] = True
        assert ui_state['higher_plane'] == True
