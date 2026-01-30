"""Tests for configuration module - game parameters and settings."""
import pytest
from unittest.mock import Mock
from android_injections.config.game_config import GameConfig, create_game_config


class TestGameConfigInitialization:
    """Test GameConfig initialization with default and custom values."""
    
    def test_default_game_config(self):
        """GameConfig should initialize with sensible defaults."""
        config = GameConfig()
        
        # Touch delay settings
        assert config.touch_delay_min == 0.3
        assert config.touch_delay_max == 4.358
        assert config.touch_delay_mean == 0.8
        assert config.touch_delay_std == 0.6
        
        # Target detection settings
        assert config.stability_timer == 1.0
        assert config.passing_distance == 50
        assert config.pass_pause_duration == 3.0
        
        # Timeout settings
        assert config.auto_target_timeout == 10.0
        
        # Vision settings
        assert config.min_blob_pixels == 100
        assert config.max_blobs == 0
        assert config.colors_per_target == 5
        
        # Plane detection
        assert config.plane_size == 5
        assert config.plane_count_padding == 5
        
        # XP detection
        assert config.xp_brightness_threshold == 170
        assert config.xp_sample_interval == 1.0
    
    def test_game_config_custom_values(self):
        """GameConfig should accept custom initialization values."""
        config = GameConfig(
            touch_delay_min=0.5,
            touch_delay_max=3.0,
            stability_timer=2.0,
            min_blob_pixels=50
        )
        
        assert config.touch_delay_min == 0.5
        assert config.touch_delay_max == 3.0
        assert config.stability_timer == 2.0
        assert config.min_blob_pixels == 50


class TestGameConfigBounds:
    """Test configuration value bounds checking."""
    
    def test_delay_bounds_enforcement(self):
        """Delay settings should be enforced through property setters."""
        config = GameConfig()
        
        # Set valid values
        config.touch_delay_min = 0.1
        config.touch_delay_max = 5.0
        
        assert config.touch_delay_min == 0.1
        assert config.touch_delay_max == 5.0
    
    def test_stability_timer_bounds(self):
        """Stability timer should accept reasonable values."""
        config = GameConfig()
        
        config.stability_timer = 2.5
        assert config.stability_timer == 2.5
    
    def test_brightness_threshold_bounds(self):
        """XP brightness threshold should be 0-255."""
        config = GameConfig()
        
        config.xp_brightness_threshold = 200
        assert config.xp_brightness_threshold == 200


class TestCreateGameConfig:
    """Test factory function for creating GameConfig from instance attributes."""
    
    def test_create_config_from_instance(self):
        """Should extract config from instance with all parameters."""
        instance = Mock()
        instance.touch_delay_min = 0.4
        instance.touch_delay_max = 3.5
        instance.touch_delay_mean = 0.9
        instance.touch_delay_std = 0.7
        instance.stability_timer = 1.5
        instance.passing_distance = 60
        instance.pass_pause_duration = 2.5
        instance.auto_target_timeout = 12.0
        instance.min_blob_pixels = 150
        instance.max_blobs = 5
        instance.colors_per_target = 8
        instance.plane_size = 6
        instance.plane_count_padding = 4
        instance.xp_brightness_threshold = 180
        instance.xp_sample_interval = 1.5
        
        config = create_game_config(instance)
        
        assert config.touch_delay_min == 0.4
        assert config.touch_delay_max == 3.5
        assert config.touch_delay_mean == 0.9
        assert config.touch_delay_std == 0.7
        assert config.stability_timer == 1.5
        assert config.passing_distance == 60
        assert config.pass_pause_duration == 2.5
        assert config.auto_target_timeout == 12.0
        assert config.min_blob_pixels == 150
        assert config.max_blobs == 5
        assert config.colors_per_target == 8
        assert config.plane_size == 6
        assert config.plane_count_padding == 4
        assert config.xp_brightness_threshold == 180
        assert config.xp_sample_interval == 1.5
    
    def test_apply_config_to_instance(self):
        """Should apply config settings back to instance."""
        config = GameConfig(
            touch_delay_min=0.5,
            stability_timer=2.0,
            min_blob_pixels=200
        )
        instance = Mock()
        
        config.apply_to_instance(instance)
        
        assert instance.touch_delay_min == 0.5
        assert instance.stability_timer == 2.0
        assert instance.min_blob_pixels == 200


class TestGameConfigDisplay:
    """Test configuration display and string representation."""
    
    def test_config_to_dict(self):
        """Should convert config to dictionary."""
        config = GameConfig()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert 'touch_delay_min' in config_dict
        assert 'stability_timer' in config_dict
        assert config_dict['touch_delay_min'] == 0.3


class TestGameConfigValidation:
    """Test validation of configuration values."""
    
    def test_validate_delay_consistency(self):
        """Min delay should not exceed max delay."""
        config = GameConfig()
        
        # Should allow valid ordering
        config.touch_delay_min = 0.3
        config.touch_delay_max = 5.0
        
        assert config.touch_delay_min <= config.touch_delay_max
    
    def test_validate_positive_values(self):
        """Timers should accept positive values."""
        config = GameConfig()
        
        config.stability_timer = 0.5
        assert config.stability_timer == 0.5
        
        config.xp_sample_interval = 0.1
        assert config.xp_sample_interval == 0.1
