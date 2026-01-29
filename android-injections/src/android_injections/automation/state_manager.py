"""Auto-touch state management - target stability, passing conditions, and state reset."""

import time


def is_target_stable(instance, current_pos):
    """
    Check if target position has stabilized after movement.
    
    Compares current position against previous position. If position has not changed
    by more than 5 pixels (Manhattan distance), increments stability timer. When timer
    reaches stability_timer threshold, target is considered stable.
    
    Args:
        instance: Instance with auto_target_prev_pos, auto_target_stable_since, stability_timer
        current_pos: Current position tuple (x, y, w, h)
    
    Returns:
        True if target has been stable for stability_timer seconds, False otherwise
    """
    current_time = time.time()
    
    if instance.auto_target_prev_pos is None:
        return False
    
    prev_x, prev_y, _, _ = instance.auto_target_prev_pos
    curr_x, curr_y, _, _ = current_pos
    
    # Consider stable if position hasn't changed by more than 5 pixels
    position_delta = abs(curr_x - prev_x) + abs(curr_y - prev_y)
    
    if position_delta <= 5:
        # Target is in same position
        if instance.auto_target_stable_since is None:
            instance.auto_target_stable_since = current_time
        # Consider stable after configured time of no movement
        elif current_time - instance.auto_target_stable_since >= instance.stability_timer:
            return True
    else:
        # Target moved, reset stability timer
        instance.auto_target_stable_since = None
    
    return False


def is_dot_stable(instance, current_dot_pos, pass_pause_elapsed):
    """
    Check if dot (player) position has stabilized after passing target.
    
    Only checks stability if pass_pause_duration has elapsed since touching target.
    Uses same stability logic as targets (5 pixel threshold, stability_timer duration).
    
    Args:
        instance: Instance with dot tracking state and stability_timer
        current_dot_pos: Current dot position tuple (x, y)
        pass_pause_elapsed: Whether pass_pause_duration has elapsed since touch
    
    Returns:
        True if dot has been stable for stability_timer seconds after pause, False otherwise
    """
    if not pass_pause_elapsed:
        return False
    
    current_time = time.time()
    
    if instance.auto_dot_prev_pos is None:
        return False
    
    prev_dot_x, prev_dot_y = instance.auto_dot_prev_pos
    curr_dot_x, curr_dot_y = current_dot_pos
    
    # Consider stable if position hasn't changed by more than 5 pixels
    dot_position_delta = abs(curr_dot_x - prev_dot_x) + abs(curr_dot_y - prev_dot_y)
    
    if dot_position_delta <= 5:
        # Dot is in same position
        if instance.auto_dot_stable_since is None:
            instance.auto_dot_stable_since = current_time
        # Consider stable after configured time of no movement
        elif current_time - instance.auto_dot_stable_since >= instance.stability_timer:
            return True
    else:
        # Dot moved, reset stability timer
        instance.auto_dot_stable_since = None
    
    return False


def check_target_passed(instance):
    """
    Determine if current target has been passed (completed).
    
    A target is considered passed if:
    1. Player touched the target (auto_target_touched=True)
    2. XP was gained after touching (xp_detected != "0")
    
    Or:
    1. Target was not detected for auto_target_timeout seconds
    
    Args:
        instance: Instance with touch and XP state
    
    Returns:
        True if target should be marked as passed, False otherwise
    """
    # Check XP gain after touch
    if instance.auto_target_touched and instance.xp_detected != "0":
        return True
    
    return False


def check_target_timeout(instance, current_time):
    """
    Check if target detection timeout has been exceeded.
    
    When a target is not detected for auto_target_timeout seconds,
    skip to the next target.
    
    Args:
        instance: Instance with target timeout settings
        current_time: Current timestamp
    
    Returns:
        True if timeout has been exceeded, False otherwise
    """
    if instance.auto_target_last_seen is not None:
        time_since_last_seen = current_time - instance.auto_target_last_seen
        return time_since_last_seen >= instance.auto_target_timeout
    
    return False


def reset_auto_state(instance):
    """
    Reset all auto-touch state after target is passed and moving to next target.
    
    Clears tracking positions, timing markers, and touch state while preserving
    delay parameters. Resets timeout timer for next target detection window.
    
    Args:
        instance: Instance with auto state attributes to reset
    """
    current_time = time.time()
    
    instance.auto_target_passed = False
    instance.auto_target_touched = False
    instance.auto_touched_time = None
    instance.auto_target_prev_pos = None
    instance.auto_target_stable_since = None
    instance.auto_touched_position = None
    instance.auto_dot_prev_pos = None
    instance.auto_dot_stable_since = None
    instance.auto_target_last_seen = current_time  # Reset timeout
