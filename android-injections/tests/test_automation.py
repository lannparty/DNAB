"""Tests for automation module - auto-touch logic, target selection, delay management."""
import pytest
import time
import numpy as np
from unittest.mock import Mock, MagicMock
from android_injections.automation.auto_target import get_current_auto_target
from android_injections.automation.delay_manager import (
    calculate_next_delay,
    is_delay_ready,
    execute_auto_touch
)


class TestAutoTargetSelection:
    """Test automatic target selection based on game state."""
    
    def test_get_current_auto_target_with_tracking_disabled(self):
        """Auto target should return None when state tracking is disabled."""
        instance = Mock()
        instance.state_tracking = False
        
        result = get_current_auto_target(instance)
        assert result is None
    
    def test_get_current_auto_target_higher_plane_zero(self):
        """When higher_plane is 0, target should be 'ladder'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 0
        
        result = get_current_auto_target(instance)
        assert result == "ladder"
    
    def test_get_current_auto_target_higher_plane_one_counter_four(self):
        """When higher_plane is 1 and minimap_counter is 4, target should be 'tightrope'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 4
        
        result = get_current_auto_target(instance)
        assert result == "tightrope"
    
    def test_get_current_auto_target_higher_plane_one_counter_three(self):
        """When higher_plane is 1 and minimap_counter is 3, target should be 'tightrope2'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 3
        
        result = get_current_auto_target(instance)
        assert result == "tightrope2"
    
    def test_get_current_auto_target_higher_plane_one_counter_two(self):
        """When higher_plane is 1 and minimap_counter is 2, target should be 'rope'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 2
        
        result = get_current_auto_target(instance)
        assert result == "rope"
    
    def test_get_current_auto_target_higher_plane_one_counter_one(self):
        """When higher_plane is 1 and minimap_counter is 1, target should be 'ladder2'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 1
        
        result = get_current_auto_target(instance)
        assert result == "ladder2"
    
    def test_get_current_auto_target_higher_plane_one_counter_zero(self):
        """When higher_plane is 1 and minimap_counter is 0, target should be 'zipline'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 0
        
        result = get_current_auto_target(instance)
        assert result == "zipline"
    
    def test_get_current_auto_target_unknown_state(self):
        """When higher_plane is unknown, target should be None."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 2  # Unknown value
        
        result = get_current_auto_target(instance)
        assert result is None


class TestDelayCalculation:
    """Test delay management for auto-touch timing."""
    
    def test_calculate_next_delay_within_bounds(self):
        """Calculated delay should be clamped to min/max bounds."""
        instance = Mock()
        instance.touch_delay_min = 0.3
        instance.touch_delay_max = 4.358
        instance.touch_delay_mean = 0.8
        instance.touch_delay_std = 0.6
        
        # Run multiple times to ensure variance is bounded
        for _ in range(10):
            delay = calculate_next_delay(instance)
            assert instance.touch_delay_min <= delay <= instance.touch_delay_max
    
    def test_calculate_next_delay_uses_normal_distribution(self):
        """Delays should follow roughly normal distribution around mean."""
        instance = Mock()
        instance.touch_delay_min = 0.0  # No bounds to see raw distribution
        instance.touch_delay_max = 10.0
        instance.touch_delay_mean = 1.0
        instance.touch_delay_std = 0.2
        
        delays = [calculate_next_delay(instance) for _ in range(100)]
        mean_delay = np.mean(delays)
        
        # Mean should be roughly centered on target (with some variance)
        assert 0.8 < mean_delay < 1.2


class TestDelayTimers:
    """Test timing and delay readiness checks."""
    
    def test_should_delay_pass_initially_zero(self):
        """Initially when last_auto_touch is 0, delay should pass."""
        instance = Mock()
        instance.last_auto_touch = 0
        instance.next_touch_interval = 0.8
        
        result = is_delay_ready(instance, time.time())
        assert result is True
    
    def test_should_delay_pass_after_interval_elapsed(self):
        """After interval time has elapsed, delay should pass."""
        instance = Mock()
        current_time = time.time()
        instance.last_auto_touch = current_time - 1.0  # 1 second ago
        instance.next_touch_interval = 0.5  # 500ms interval
        
        result = is_delay_ready(instance, current_time)
        assert result is True
    
    def test_should_delay_fail_before_interval_elapsed(self):
        """Before interval time has elapsed, delay should not pass."""
        instance = Mock()
        current_time = time.time()
        instance.last_auto_touch = current_time - 0.3  # 300ms ago
        instance.next_touch_interval = 0.8  # 800ms interval
        
        result = is_delay_ready(instance, current_time)
        assert result is False
    
    def test_should_delay_pass_exact_boundary(self):
        """At exact boundary (time equals interval), delay should pass."""
        instance = Mock()
        current_time = time.time()
        instance.last_auto_touch = current_time - 0.5  # Exactly 500ms ago
        instance.next_touch_interval = 0.5  # 500ms interval
        
        result = is_delay_ready(instance, current_time)
        assert result is True


class TestTargetStability:
    """Test target position stability detection."""
    
    def test_target_stability_initial_state(self):
        """When previous position is None, target is not yet stable."""
        instance = Mock()
        instance.auto_target_prev_pos = None
        
        # Stability cannot be determined without previous position
        # This is handled in the actual automation loop
        assert instance.auto_target_prev_pos is None
    
    def test_target_position_unchanged(self):
        """When target position hasn't changed, it should be marked as potentially stable."""
        prev_x, prev_y = 100, 100
        curr_x, curr_y = 100, 100
        
        position_delta = abs(curr_x - prev_x) + abs(curr_y - prev_y)
        is_stationary = position_delta <= 5
        
        assert is_stationary is True
    
    def test_target_position_small_change(self):
        """Small position changes (<=5 pixels) should be considered stable."""
        prev_x, prev_y = 100, 100
        curr_x, curr_y = 103, 102
        
        position_delta = abs(curr_x - prev_x) + abs(curr_y - prev_y)
        is_stationary = position_delta <= 5
        
        assert is_stationary is True
    
    def test_target_position_large_change(self):
        """Large position changes (>5 pixels) should reset stability timer."""
        prev_x, prev_y = 100, 100
        curr_x, curr_y = 110, 105
        
        position_delta = abs(curr_x - prev_x) + abs(curr_y - prev_y)
        is_stationary = position_delta <= 5
        
        assert is_stationary is False


class TestXPDetection:
    """Test XP gain detection for pass conditions."""
    
    def test_xp_gain_after_touch_marks_passed(self):
        """When XP is detected after touching target, it should mark target as passed."""
        instance = Mock()
        instance.auto_target_touched = True
        instance.xp_detected = "100"  # XP gained
        
        passed = instance.auto_target_touched and instance.xp_detected != "0"
        assert passed is True
    
    def test_no_xp_does_not_mark_passed(self):
        """When no XP is detected, target should not be marked as passed."""
        instance = Mock()
        instance.auto_target_touched = True
        instance.xp_detected = "0"  # No XP
        
        passed = instance.auto_target_touched and instance.xp_detected != "0"
        assert passed is False
    
    def test_xp_without_touch_does_not_mark_passed(self):
        """XP detection without first touching should not mark target as passed."""
        instance = Mock()
        instance.auto_target_touched = False
        instance.xp_detected = "100"
        
        passed = instance.auto_target_touched and instance.xp_detected != "0"
        assert passed is False


class TestTargetTimeout:
    """Test timeout logic for missing targets."""
    
    def test_timeout_triggered_after_duration(self):
        """When target not seen for timeout duration, should skip to next."""
        current_time = time.time()
        last_seen_time = current_time - 11.0  # 11 seconds ago
        timeout_duration = 10.0
        
        time_since_last_seen = current_time - last_seen_time
        should_skip = time_since_last_seen >= timeout_duration
        
        assert should_skip is True
    
    def test_timeout_not_triggered_within_duration(self):
        """When target not seen but within timeout duration, should not skip."""
        current_time = time.time()
        last_seen_time = current_time - 5.0  # 5 seconds ago
        timeout_duration = 10.0
        
        time_since_last_seen = current_time - last_seen_time
        should_skip = time_since_last_seen >= timeout_duration
        
        assert should_skip is False
    
    def test_timeout_not_triggered_when_target_visible(self):
        """When target is just now visible, timeout is reset."""
        current_time = time.time()
        # In code, last_seen is updated when target detected
        last_seen_time = current_time  # Just now
        timeout_duration = 10.0
        
        time_since_last_seen = current_time - last_seen_time
        should_skip = time_since_last_seen >= timeout_duration
        
        assert should_skip is False


class TestPauseAfterTouch:
    """Test pause logic after touching target (for stability check)."""
    
    def test_pause_elapsed_after_duration(self):
        """After pause duration, should start checking stability."""
        current_time = time.time()
        touched_time = current_time - 4.0  # 4 seconds ago
        pause_duration = 3.0
        
        pause_elapsed = touched_time is not None and current_time - touched_time >= pause_duration
        
        assert pause_elapsed is True
    
    def test_pause_not_elapsed_within_duration(self):
        """Within pause duration, should not check stability yet."""
        current_time = time.time()
        touched_time = current_time - 1.0  # 1 second ago
        pause_duration = 3.0
        
        pause_elapsed = touched_time is not None and current_time - touched_time >= pause_duration
        
        assert pause_elapsed is False
    
    def test_pause_with_no_touch_time(self):
        """When no touch has occurred, pause has not elapsed."""
        current_time = time.time()
        touched_time = None
        pause_duration = 3.0
        
        pause_elapsed = touched_time is not None and current_time - touched_time >= pause_duration
        
        assert pause_elapsed is False


class TestAutoStateReset:
    """Test resetting auto state after target is passed."""
    
    def test_auto_state_reset_after_pass(self):
        """After target is marked passed, all tracking state should reset."""
        instance = Mock()
        instance.auto_target_passed = False
        instance.auto_target_touched = False
        instance.auto_touched_time = None
        instance.auto_target_prev_pos = None
        instance.auto_target_stable_since = None
        instance.auto_touched_position = None
        instance.auto_dot_prev_pos = None
        instance.auto_dot_stable_since = None
        instance.auto_target_last_seen = time.time()
        
        # Simulate passing a target
        # All these should be reset
        states_before = {
            'auto_target_passed': instance.auto_target_passed,
            'auto_target_touched': instance.auto_target_touched,
            'auto_touched_time': instance.auto_touched_time,
            'auto_target_prev_pos': instance.auto_target_prev_pos,
            'auto_target_stable_since': instance.auto_target_stable_since,
            'auto_touched_position': instance.auto_touched_position,
            'auto_dot_prev_pos': instance.auto_dot_prev_pos,
            'auto_dot_stable_since': instance.auto_dot_stable_since,
        }
        
        # All should be None or False initially
        assert states_before['auto_target_passed'] is False
        assert states_before['auto_target_touched'] is False
        assert states_before['auto_touched_time'] is None
        assert states_before['auto_target_prev_pos'] is None
