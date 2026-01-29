"""Delay management for auto-touch timing - handles interval calculation and timing checks."""

import subprocess
import numpy as np


def calculate_next_delay(instance):
    """
    Calculate next touch interval using normal distribution with bounds.
    
    Uses a normal distribution centered on touch_delay_mean with touch_delay_std
    standard deviation, clamped to [touch_delay_min, touch_delay_max] bounds.
    
    This simulates human-like clicking patterns with realistic variance.
    
    Args:
        instance: Instance with touch_delay_mean, touch_delay_std, touch_delay_min, touch_delay_max
    
    Returns:
        Next interval in seconds (float)
    """
    interval = np.random.normal(instance.touch_delay_mean, instance.touch_delay_std)
    return max(instance.touch_delay_min, min(instance.touch_delay_max, interval))


def is_delay_ready(instance, current_time):
    """
    Check if enough time has elapsed since last touch to attempt next touch.
    
    Compares time elapsed since last_auto_touch against next_touch_interval.
    Initial state (last_auto_touch=0) always returns True to allow first touch.
    
    Args:
        instance: Instance with last_auto_touch and next_touch_interval
        current_time: Current timestamp (seconds since epoch)
    
    Returns:
        True if delay has elapsed, False otherwise
    """
    time_elapsed = current_time - instance.last_auto_touch
    return time_elapsed >= instance.next_touch_interval


def execute_auto_touch(instance, target_x, target_y, target_name):
    """
    Execute ADB tap command at target position and update timing state.
    
    Sends adb shell input tap command and generates next interval delay.
    Updates instance state to track touch timing for stability checking.
    
    Args:
        instance: Instance with touch delay parameters and tracking state
        target_x: X coordinate to tap
        target_y: Y coordinate to tap
        target_name: Name of target being touched (for logging)
    
    Returns:
        True if touch was successful, False if error occurred
    """
    import time
    
    cmd = f"adb shell input tap {target_x} {target_y}"
    print(f"[Auto] Touching '{target_name}' at ({target_x}, {target_y})")
    try:
        subprocess.run(cmd.split(), check=True, capture_output=True)
    except Exception as e:
        print(f"[Auto] Touch error: {e}")
        return False
    
    # Generate next interval
    current_time = time.time()
    instance.last_auto_touch = current_time
    instance.next_touch_interval = calculate_next_delay(instance)
    
    # Mark that we've touched this target and store the position and time
    instance.auto_target_touched = True
    instance.auto_touched_position = (target_x, target_y)
    instance.auto_touched_time = current_time
    
    # Reset stability tracking after touch
    instance.auto_target_stable_since = None
    
    return True
