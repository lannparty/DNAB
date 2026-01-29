"""Keyboard event handler for field editing and text input."""


def handle_numeric_input(instance, key_code):
    """
    Handle numeric input for numeric fields (colors, delay, brightness, etc).
    
    Processes digits (0-9), backspace, and ignores other keys.
    Accumulates digits in instance.temp_input.
    
    Args:
        instance: Instance with temp_input and field state
        key_code: Key code from cv2.waitKey (0-255)
    
    Returns:
        True if key was handled, False otherwise
    """
    if 48 <= key_code <= 57:  # Digits 0-9
        instance.temp_input += chr(key_code)
        return True
    elif key_code == 8:  # Backspace
        instance.temp_input = instance.temp_input[:-1]
        return True
    
    return False


def handle_text_input(instance, key_code):
    """
    Handle text input for target names.
    
    Processes printable characters (32-126) and backspace.
    Accumulates characters in instance.target_name.
    
    Args:
        instance: Instance with target_name attribute
        key_code: Key code from cv2.waitKey (0-255)
    
    Returns:
        True if key was handled, False otherwise
    """
    if 32 <= key_code <= 126:  # Printable ASCII characters
        instance.target_name += chr(key_code)
        return True
    elif key_code == 8:  # Backspace
        instance.target_name = instance.target_name[:-1]
        return True
    
    return False


def update_field_from_input(instance, field_name, new_value_str, min_val=None, max_val=None, converter=int, use_config=False):
    """
    Update a field with value from temp_input, with bounds checking.
    
    Converts temp_input using converter function, applies min/max bounds,
    and updates the field if conversion succeeds. Can update config properties
    or direct instance attributes.
    
    Args:
        instance: Instance to update
        field_name: Name of field attribute to update
        new_value_str: String to convert
        min_val: Minimum allowed value (or None for no minimum)
        max_val: Maximum allowed value (or None for no maximum)
        converter: Function to convert string to value (default int)
        use_config: If True, update instance.config.field_name instead of instance.field_name
    
    Returns:
        Tuple of (success: bool, value: converted value or None)
    """
    try:
        value = converter(new_value_str)
        
        if min_val is not None:
            value = max(min_val, value)
        if max_val is not None:
            value = min(max_val, value)
        
        if use_config:
            setattr(instance.config, field_name, value)
        else:
            setattr(instance, field_name, value)
        return True, value
    except ValueError:
        return False, None


def process_keyboard_event(instance, key_code):
    """
    Process keyboard event and update corresponding field.
    
    Routes keyboard input to appropriate handler based on current editing state.
    Supports numeric input for config fields and text input for target names.
    
    Args:
        instance: Instance with editing state and field attributes
        key_code: Key code from cv2.waitKey (0-255)
    
    Returns:
        True if event was handled, False otherwise
    """
    # Handle numeric field editing
    if instance.editing_colors:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'colors_per_target', instance.temp_input, 1, 50, use_config=True)
            if success:
                instance.load_all_targets()
                print(f"Colors per target set to: {value}")
            else:
                print("Invalid number")
            instance.editing_colors = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_min_pixels:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'min_blob_pixels', instance.temp_input, 1, 1000, use_config=True)
            if success:
                print(f"Min blob pixels set to: {value}")
            else:
                print("Invalid number")
            instance.editing_min_pixels = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_max_blobs:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'max_blobs', instance.temp_input, 0, 100, use_config=True)
            if success:
                print(f"Max blobs set to: {'unlimited' if value == 0 else value}")
            else:
                print("Invalid number")
            instance.editing_max_blobs = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_delay_min:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'touch_delay_min', instance.temp_input, 1, 30000, converter=lambda x: int(x) / 1000.0, use_config=True)
            if success:
                print(f"Min delay set to: {int(value*1000)}ms")
            else:
                print("Invalid number")
            instance.editing_delay_min = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_delay_max:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'touch_delay_max', instance.temp_input, 1, 30000, converter=lambda x: int(x) / 1000.0, use_config=True)
            if success:
                print(f"Max delay set to: {int(value*1000)}ms")
            else:
                print("Invalid number")
            instance.editing_delay_max = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_delay_mean:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'touch_delay_mean', instance.temp_input, 1, 30000, converter=lambda x: int(x) / 1000.0, use_config=True)
            if success:
                print(f"Mean delay set to: {int(value*1000)}ms")
            else:
                print("Invalid number")
            instance.editing_delay_mean = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_delay_std:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'touch_delay_std', instance.temp_input, 1, 30000, converter=lambda x: int(x) / 1000.0, use_config=True)
            if success:
                print(f"Std delay set to: {int(value*1000)}ms")
            else:
                print("Invalid number")
            instance.editing_delay_std = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_stability:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'stability_timer', instance.temp_input, 1, 30000, converter=lambda x: int(x) / 1000.0, use_config=True)
            if success:
                print(f"Stability timer set to: {int(value*1000)}ms")
            else:
                print("Invalid number")
            instance.editing_stability = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_passing_dist:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'passing_distance', instance.temp_input, 0, 500, use_config=True)
            if success:
                print(f"Passing distance set to: {value}px")
            else:
                print("Invalid number")
            instance.editing_passing_dist = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_xp_brightness:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'xp_brightness_threshold', instance.temp_input, 0, 255, use_config=True)
            if success:
                print(f"XP brightness threshold set to: {value}")
            else:
                print("Invalid number")
            instance.editing_xp_brightness = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_plane_size:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'plane_size', instance.temp_input, 1, 100, use_config=True)
            if success:
                print(f"Plane size set to: {value}")
            else:
                print("Invalid number")
            instance.editing_plane_size = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_xp_sample_interval:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'xp_sample_interval', instance.temp_input, 100, 10000, converter=lambda x: int(x) / 1000.0, use_config=True)
            if success:
                print(f"XP sample interval set to: {int(value * 1000)}ms")
            else:
                print("Invalid number")
            instance.editing_xp_sample_interval = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    elif instance.editing_plane_count_padding:
        if key_code == 13:  # Enter
            success, value = update_field_from_input(instance, 'plane_count_padding', instance.temp_input, 0, 100, use_config=True)
            if success:
                print(f"Plane count padding set to: {value}")
            else:
                print("Invalid number")
            instance.editing_plane_count_padding = False
            instance.temp_input = ""
        else:
            handle_numeric_input(instance, key_code)
        return True
    
    # Handle text input for target names
    elif instance.text_input_active:
        if key_code == 8:  # Backspace
            instance.target_name = instance.target_name[:-1]
        elif 32 <= key_code <= 126:  # Printable characters
            instance.target_name += chr(key_code)
        return True
    
    return False
