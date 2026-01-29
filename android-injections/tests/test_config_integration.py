"""
Comprehensive test suite for GameConfig integration.

Tests cover:
- Configuration initialization and defaults
- Parameter modification and validation
- Bounds checking
- Config persistence concepts
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from android_injections.config.game_config import GameConfig
from android_injections.ui.keyboard_handler import update_field_from_input


class TestGameConfigInitialization:
    """Test GameConfig initialization and defaults."""
    
    def test_config_creation(self):
        """Test that GameConfig can be created with defaults."""
        config = GameConfig()
        assert config is not None
    
    def test_all_parameters_exist(self):
        """Test that all expected parameters are present."""
        config = GameConfig()
        
        # Check all 15 config parameters
        expected_params = [
            'touch_delay_min', 'touch_delay_max', 'touch_delay_mean', 'touch_delay_std',
            'stability_timer', 'passing_distance', 'pass_pause_duration', 'auto_target_timeout',
            'min_blob_pixels', 'max_blobs', 'colors_per_target',
            'plane_size', 'plane_count_padding', 'xp_brightness_threshold', 'xp_sample_interval'
        ]
        
        for param in expected_params:
            assert hasattr(config, param), f"Missing parameter: {param}"
    
    def test_default_values_are_reasonable(self):
        """Test that default values are within expected ranges."""
        config = GameConfig()
        
        # Delays should be positive and in reasonable ranges
        assert 0 < config.touch_delay_min < config.touch_delay_max
        assert config.touch_delay_mean > 0
        assert config.touch_delay_std > 0
        
        # Stability timer should be positive
        assert config.stability_timer > 0
        
        # Colors per target should be positive
        assert config.colors_per_target > 0
        
        # Max blobs can be 0 (unlimited) or positive
        assert config.max_blobs >= 0


class TestGameConfigModification:
    """Test modifying GameConfig parameters."""
    
    def test_modify_touch_delay_min(self):
        """Test modifying touch_delay_min."""
        config = GameConfig()
        original = config.touch_delay_min
        new_value = 0.5
        
        config.touch_delay_min = new_value
        assert config.touch_delay_min == new_value
    
    def test_modify_stability_timer(self):
        """Test modifying stability_timer."""
        config = GameConfig()
        new_value = 3.0
        
        config.stability_timer = new_value
        assert config.stability_timer == new_value
    
    def test_modify_colors_per_target(self):
        """Test modifying colors_per_target."""
        config = GameConfig()
        new_value = 15
        
        config.colors_per_target = new_value
        assert config.colors_per_target == new_value
    
    def test_modify_max_blobs(self):
        """Test modifying max_blobs (can be 0 for unlimited)."""
        config = GameConfig()
        
        # Test setting to a number
        config.max_blobs = 5
        assert config.max_blobs == 5
        
        # Test setting to unlimited
        config.max_blobs = 0
        assert config.max_blobs == 0
    
    def test_modify_multiple_parameters(self):
        """Test modifying multiple parameters at once."""
        config = GameConfig()
        
        config.touch_delay_min = 0.3
        config.touch_delay_max = 1.5
        config.stability_timer = 2.5
        config.colors_per_target = 25
        
        assert config.touch_delay_min == 0.3
        assert config.touch_delay_max == 1.5
        assert config.stability_timer == 2.5
        assert config.colors_per_target == 25


class TestUpdateFieldFromInput:
    """Test the update_field_from_input function."""
    
    @pytest.fixture
    def mock_instance(self):
        """Create a mock instance with GameConfig."""
        class MockInstance:
            def __init__(self):
                self.config = GameConfig()
                self.custom_field = None
        
        return MockInstance()
    
    def test_update_config_field(self, mock_instance):
        """Test updating a config field."""
        original = mock_instance.config.colors_per_target
        
        success, value = update_field_from_input(
            mock_instance, 'colors_per_target', '25', 1, 50, use_config=True
        )
        
        assert success
        assert value == 25
        assert mock_instance.config.colors_per_target == 25
    
    def test_update_instance_field(self, mock_instance):
        """Test updating a non-config field."""
        success, value = update_field_from_input(
            mock_instance, 'custom_field', '42', 0, 100, use_config=False
        )
        
        assert success
        assert value == 42
        assert mock_instance.custom_field == 42
        # Ensure config wasn't modified
        assert mock_instance.config.colors_per_target != 42
    
    def test_clamp_to_max_value(self, mock_instance):
        """Test that values are clamped to maximum."""
        success, value = update_field_from_input(
            mock_instance, 'colors_per_target', '100', 1, 50, use_config=True
        )
        
        assert value <= 50
        assert mock_instance.config.colors_per_target <= 50
    
    def test_clamp_to_min_value(self, mock_instance):
        """Test that values are clamped to minimum."""
        success, value = update_field_from_input(
            mock_instance, 'colors_per_target', '0', 1, 50, use_config=True
        )
        
        assert value >= 1
        assert mock_instance.config.colors_per_target >= 1
    
    def test_invalid_input_returns_false(self, mock_instance):
        """Test that invalid input returns False."""
        success, value = update_field_from_input(
            mock_instance, 'colors_per_target', 'not_a_number', 1, 50, use_config=True
        )
        
        assert not success
        assert value is None
    
    def test_converter_function(self, mock_instance):
        """Test using a custom converter function."""
        success, value = update_field_from_input(
            mock_instance, 'touch_delay_min', '1500', 0.1, 30000,
            converter=lambda x: int(x) / 1000.0, use_config=True
        )
        
        assert success
        assert value == 1.5
        assert abs(mock_instance.config.touch_delay_min - 1.5) < 0.001


class TestParameterBounds:
    """Test that parameter bounds are respected."""
    
    @pytest.fixture
    def mock_instance(self):
        """Create a mock instance."""
        class MockInstance:
            def __init__(self):
                self.config = GameConfig()
        return MockInstance()
    
    @pytest.mark.parametrize("field,input_val,min_val,max_val", [
        ('colors_per_target', '25', 1, 50),
        ('min_blob_pixels', '100', 1, 1000),
        ('max_blobs', '10', 0, 100),
        ('plane_size', '50', 1, 100),
        ('plane_count_padding', '20', 0, 100),
        ('xp_brightness_threshold', '128', 0, 255),
    ])
    def test_parameter_clamping(self, mock_instance, field, input_val, min_val, max_val):
        """Test clamping for various parameters."""
        success, value = update_field_from_input(
            mock_instance, field, input_val, min_val, max_val, use_config=True
        )
        
        assert success
        assert min_val <= value <= max_val


class TestConfigIntegration:
    """Integration tests for GameConfig with keyboard handler."""
    
    def test_config_independent_instances(self):
        """Test that different GameConfig instances are independent."""
        config1 = GameConfig()
        config2 = GameConfig()
        
        config1.colors_per_target = 30
        config2.colors_per_target = 20
        
        assert config1.colors_per_target == 30
        assert config2.colors_per_target == 20
    
    def test_keyboard_handler_integration(self):
        """Test full integration with keyboard handler."""
        class MockInstance:
            def __init__(self):
                self.config = GameConfig()
                self.temp_input = "35"
        
        instance = MockInstance()
        original = instance.config.colors_per_target
        
        # Simulate keyboard handler updating config
        success, value = update_field_from_input(
            instance, 'colors_per_target', instance.temp_input, 1, 50, use_config=True
        )
        
        assert success
        assert instance.config.colors_per_target == 35
    
    @pytest.mark.parametrize("delays", [
        {'min': 0.1, 'max': 0.5},
        {'min': 0.5, 'max': 2.0},
        {'min': 1.0, 'max': 5.0},
    ])
    def test_delay_configurations(self, delays):
        """Test various delay configurations."""
        config = GameConfig()
        config.touch_delay_min = delays['min']
        config.touch_delay_max = delays['max']
        
        assert config.touch_delay_min < config.touch_delay_max
        assert config.touch_delay_min >= 0.1
        assert config.touch_delay_max <= 30.0


class TestConfigDefaults:
    """Test that default values are sensible and useful."""
    
    def test_defaults_sum_is_sane(self):
        """Test that related defaults have sensible relationships."""
        config = GameConfig()
        
        # Min should be less than max
        assert config.touch_delay_min < config.touch_delay_max
        
        # Mean should be between min and max
        assert config.touch_delay_min <= config.touch_delay_mean <= config.touch_delay_max
        
        # Standard deviation should be positive
        assert config.touch_delay_std > 0
    
    def test_blob_detection_defaults(self):
        """Test blob detection parameter defaults."""
        config = GameConfig()
        
        assert config.min_blob_pixels > 0
        assert config.colors_per_target > 0
        assert config.max_blobs >= 0
    
    def test_plane_detection_defaults(self):
        """Test plane detection parameter defaults."""
        config = GameConfig()
        
        assert config.plane_size > 0
        assert config.plane_count_padding >= 0
    
    def test_xp_detection_defaults(self):
        """Test XP detection parameter defaults."""
        config = GameConfig()
        
        assert 0 <= config.xp_brightness_threshold <= 255
        assert config.xp_sample_interval > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
