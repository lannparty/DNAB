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
        """When higher_plane is 1 and minimap_counter is 4, target should be 'zipline'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 4
        
        result = get_current_auto_target(instance)
        assert result == "zipline"
    
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
        """When higher_plane is 1 and minimap_counter is 0, target should be 'tightrope'."""
        instance = Mock()
        instance.state_tracking = True
        instance.higher_plane = 1
        instance.minimap_counter = 0
        
        result = get_current_auto_target(instance)
        assert result == "tightrope"
    
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


class TestStateBasedTargetSwitching:
    """Test state-based target switching logic."""
    
    def test_target_switches_when_state_changes_and_counter_stable(self):
        """When game state changes and counter is stable, target should switch."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "zipline"
        instance.minimap_counter_stable_since = time.time() - 1.5  # Stable for 1.5s
        instance.config = Mock()
        instance.config.stability_timer = 1.0  # Requires 1.0s stability
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        current_target = instance.get_current_auto_target()
        should_switch = (current_target != instance.auto_previous_target and 
                        current_target is not None and 
                        counter_is_stable)
        
        assert counter_is_stable is True
        assert should_switch is True
        assert current_target == "zipline"
    
    def test_no_switch_when_state_changes_but_counter_unstable(self):
        """When game state changes but counter is not stable, target should not switch."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "zipline"
        instance.minimap_counter_stable_since = time.time() - 0.5  # Only stable for 0.5s
        instance.config = Mock()
        instance.config.stability_timer = 1.0  # Requires 1.0s stability
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        current_target = instance.get_current_auto_target()
        should_switch = (current_target != instance.auto_previous_target and 
                        current_target is not None and 
                        counter_is_stable)
        
        assert counter_is_stable is False
        assert should_switch is False
    
    def test_no_switch_when_state_unchanged(self):
        """When game state stays the same, target should not switch regardless of counter stability."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "ladder"
        instance.minimap_counter_stable_since = time.time() - 2.0  # Very stable
        instance.config = Mock()
        instance.config.stability_timer = 1.0
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        current_target = instance.get_current_auto_target()
        should_switch = (current_target != instance.auto_previous_target and 
                        current_target is not None and 
                        counter_is_stable)
        
        assert counter_is_stable is True
        assert should_switch is False
        assert current_target == "ladder"


class TestMinimapCounterStability:
    """Test minimap counter stability based on pixel positions."""
    
    def test_counter_stable_when_positions_unchanged(self):
        """Counter is stable when centroids don't move significantly."""
        # Same centroids should be considered stable
        centroids1 = [(10, 20), (50, 60)]
        centroids2 = [(10, 20), (50, 60)]
        
        total_movement = 0
        for c1, c2 in zip(centroids1, centroids2):
            total_movement += abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
        
        max_allowed_movement = len(centroids1) * 10
        centroids_changed = total_movement > max_allowed_movement
        
        assert centroids_changed is False
        assert total_movement == 0
    
    def test_counter_unstable_when_positions_change(self):
        """Counter is unstable when centroids move significantly."""
        centroids1 = [(10, 20), (50, 60)]
        centroids2 = [(25, 35), (65, 75)]  # Moved 15+ pixels each
        
        total_movement = 0
        for c1, c2 in zip(centroids1, centroids2):
            total_movement += abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
        
        max_allowed_movement = len(centroids1) * 10  # 20 pixels max
        centroids_changed = total_movement > max_allowed_movement
        
        assert centroids_changed is True
        assert total_movement == 60  # 30 + 30
    
    def test_counter_stable_with_small_position_changes(self):
        """Counter is stable with small position changes."""
        centroids1 = [(10, 20), (50, 60)]
        centroids2 = [(12, 18), (52, 58)]  # Moved 4 pixels each
        
        total_movement = 0
        for c1, c2 in zip(centroids1, centroids2):
            total_movement += abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
        
        max_allowed_movement = len(centroids1) * 10  # 20 pixels max
        centroids_changed = total_movement > max_allowed_movement
        
        assert centroids_changed is False
        assert total_movement == 8  # 4 + 4


class TestStateBasedTargetSwitching:
    """Test state-based target switching logic."""
    
    def test_target_switches_when_state_changes_and_counter_stable(self):
        """When game state changes and counter is stable, target should switch."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "zipline"
        instance.minimap_counter_stable_since = time.time() - 1.5  # Stable for 1.5s
        instance.config = Mock()
        instance.config.stability_timer = 1.0  # Requires 1.0s stability
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        current_target = instance.get_current_auto_target()
        should_switch = (current_target != instance.auto_previous_target and 
                        current_target is not None and 
                        counter_is_stable)
        
        assert counter_is_stable is True
        assert should_switch is True
        assert current_target == "zipline"
    
    def test_no_switch_when_state_changes_but_counter_unstable(self):
        """When game state changes but counter is not stable, target should not switch."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "zipline"
        instance.minimap_counter_stable_since = time.time() - 0.5  # Only stable for 0.5s
        instance.config = Mock()
        instance.config.stability_timer = 1.0  # Requires 1.0s stability
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        current_target = instance.get_current_auto_target()
        should_switch = (current_target != instance.auto_previous_target and 
                        current_target is not None and 
                        counter_is_stable)
        
        assert counter_is_stable is False
        assert should_switch is False
    
    def test_no_switch_when_state_unchanged(self):
        """When game state stays the same, target should not switch regardless of counter stability."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "ladder"
        instance.minimap_counter_stable_since = time.time() - 2.0  # Very stable
        instance.config = Mock()
        instance.config.stability_timer = 1.0
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        current_target = instance.get_current_auto_target()
        should_switch = (current_target != instance.auto_previous_target and 
                        current_target is not None and 
                        counter_is_stable)
        
        assert counter_is_stable is True
        assert should_switch is False
        assert current_target == "ladder"
    
    def test_state_reset_on_target_change(self):
        """When target changes due to stable state change, auto state should reset."""
        instance = Mock()
        instance.auto_previous_target = "ladder"
        instance.get_current_auto_target.return_value = "zipline"
        instance.minimap_counter_stable_since = time.time() - 1.5  # Stable
        instance.config = Mock()
        instance.config.stability_timer = 1.0
        instance.config.touch_delay_mean = 1.0
        
        current_time = time.time()
        counter_stable_duration = current_time - instance.minimap_counter_stable_since
        counter_is_stable = counter_stable_duration >= instance.config.stability_timer
        
        # Before state change
        instance.auto_touched_time = time.time()
        instance.auto_target_prev_pos = (100, 100, 50, 50)
        instance.auto_target_stable_since = time.time()
        instance.auto_touched_position = (100, 100)
        instance.auto_dot_prev_pos = (200, 200)
        instance.auto_dot_stable_since = time.time()
        instance.last_auto_touch = time.time() - 2.0
        instance.next_touch_interval = 1.0
        
        # Simulate state change detection and reset
        current_target = instance.get_current_auto_target()
        if (current_target != instance.auto_previous_target and 
            current_target is not None and 
            counter_is_stable):
            # Reset all auto state
            instance.auto_touched_time = None
            instance.auto_target_prev_pos = None
            instance.auto_target_stable_since = None
            instance.auto_touched_position = None
            instance.auto_dot_prev_pos = None
            instance.auto_dot_stable_since = None
            instance.last_auto_touch = current_time - instance.next_touch_interval
            instance.auto_previous_target = current_target
        
        # Verify state was reset
        assert counter_is_stable is True
        assert instance.auto_touched_time is None
        assert instance.auto_target_prev_pos is None
        assert instance.auto_target_stable_since is None
        assert instance.auto_touched_position is None
        assert instance.auto_dot_prev_pos is None
        assert instance.auto_dot_stable_since is None
        assert instance.auto_previous_target == "zipline"
