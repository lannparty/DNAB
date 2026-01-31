"""UI state management - initialization and state structures."""


def create_ui_state():
    """Create and return a fresh UI state dictionary.
    
    This contains all UI-related state variables including:
    - Mode toggles (target, bounds, exclude, auto, filter)
    - Selection state and rectangles
    - Text input state
    - Field editing state
    - Detection state (plane, XP, targets)
    - Configuration values
    
    Returns:
        dict: A new UI state dictionary with all default values
    """
    return {
        # Display and window settings
        'window_name': 'Pixel 4a (5G)',
        'target_fps': 30,
        'display_scale': 0.5,
        'benchmark': False,
        
        # Filter and display settings
        'show_filtered': False,
        'colors_per_target': 20,
        'min_blob_pixels': 2,
        'max_blobs': 1,
        'show_bounds': False,
        'show_excludes': False,
        'auto_view_mode': False,
        
        # Target selection and mode
        'target_mode': False,
        'bounds_mode': False,
        'exclude_mode': False,
        'unique_only': True,
        'target_name': '',
        
        # Text input
        'text_input_active': False,
        'target_selector_active': False,
        'temp_input': '',
        
        # Selection rectangles (stored as ((x1, y1), (x2, y2)) tuples)
        'selection_start': None,
        'selection_end': None,
        'selecting': False,
        'target_selection_rect': None,
        'bounds_selection_rect': None,
        'exclude_selection_rect': None,
        
        # Color editing
        'editing_colors': False,
        'editing_min_pixels': False,
        'editing_max_blobs': False,
        
        # Delay timer editing
        'editing_delay_min': False,
        'editing_delay_max': False,
        'editing_delay_mean': False,
        'editing_delay_std': False,
        'editing_stability': False,
        'editing_passing_dist': False,
        'editing_xp_brightness': False,
        'editing_xp_sample_interval': False,
        'editing_plane_size': False,
        'editing_minimap_counter_padding': False,
        
        # Plane detection
        'plane_size': 5,
        'higher_plane': False,
        'minimap_counter': 0,
        'minimap_counter_padding': 5,
        'minimap_counter_prev_value': None,
        'minimap_counter_stable_since': None,
        
        # Auto mode state
        'auto_mode': False,
        'state_tracking': False,
        'last_auto_touch': 0,
        'next_touch_interval': 0.8,
        'touch_delay_min': 0.3,
        'touch_delay_max': 4.358,
        'touch_delay_mean': 0.8,
        'touch_delay_std': 0.6,
        'stability_timer': 1.0,
        'passing_distance': 50,
        
        # XP detection
        'xp_last_value': None,
        'xp_current_reading': None,
        'xp_reading_first_seen': None,
        'xp_last_sample_time': 0,
        'xp_sample_interval': 1.0,
        'xp_trigger_time': None,
        'xp_detected': '0',
        'xp_brightness_threshold': 170,
        
        # Auto touch state
        'auto_target_list': [],
        'auto_target_index': 0,
        'auto_target_passed': False,
        'auto_target_touched': False,
        'auto_touched_time': None,
        'auto_target_prev_pos': None,
        'auto_target_stable_since': None,
        'auto_touched_position': None,
        'auto_dot_prev_pos': None,
        'auto_dot_stable_since': None,
        'pass_pause_duration': 3.0,
        'auto_target_last_seen': None,
        'auto_target_timeout': 10.0,
        
        # Data structures
        'filter_colors': set(),
        'unique_colors': set(),
        'detected_targets': {},
        'excluded_regions': [],
        'excluded_regions_with_names': [],
        'bounds_with_names': [],
        'target_bounds': {},
        'color_to_target': {},
        'target_to_colors': {},
    }
