"""Game configuration module - centralized storage for all game parameters."""


class GameConfig:
    """
    Centralized configuration for all game parameters.
    
    Contains all configurable settings for touch timing, detection thresholds,
    display parameters, and game state parameters.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize game configuration with optional custom values.
        
        Args:
            touch_delay_min: Minimum inter-touch delay in seconds (default 0.3)
            touch_delay_max: Maximum inter-touch delay in seconds (default 4.358)
            touch_delay_mean: Mean inter-touch delay in seconds (default 0.8)
            touch_delay_std: Standard deviation of inter-touch delay (default 0.6)
            stability_timer: Seconds target must be stable before touching (default 1.0)
            passing_distance: Pixels target must pass beyond edge to count as passed (default 50)
            pass_pause_duration: Seconds to wait after touching before checking pass (default 3.0)
            auto_target_timeout: Seconds to wait before skipping missing target (default 10.0)
            min_blob_pixels: Minimum blob size in pixels (default 100)
            max_blobs: Maximum blobs to track (0=unlimited, default 0)
            colors_per_target: Number of colors to use for target (default 5)
            plane_size: Size of black square for plane detection (default 20)
            minimap_counter_padding: Padding for grouping minimap counter pixels (default 6)
            xp_brightness_threshold: Brightness threshold for XP OCR (default 170)
            xp_sample_interval: How often to run OCR in seconds (default 1.0)
        """
        # Touch delay settings (in seconds)
        self.touch_delay_min = kwargs.get('touch_delay_min', 0.3)
        self.touch_delay_max = kwargs.get('touch_delay_max', 4.358)
        self.touch_delay_mean = kwargs.get('touch_delay_mean', 0.8)
        self.touch_delay_std = kwargs.get('touch_delay_std', 0.6)
        
        # Target detection settings
        self.stability_timer = kwargs.get('stability_timer', 1.0)
        self.passing_distance = kwargs.get('passing_distance', 50)
        self.pass_pause_duration = kwargs.get('pass_pause_duration', 3.0)
        self.counter_stability_timer = kwargs.get('counter_stability_timer', 2.0)
        self.counter_tolerance = kwargs.get('counter_tolerance', 50)
        
        # Timeout settings
        self.auto_target_timeout = kwargs.get('auto_target_timeout', 10.0)
        
        # Vision settings
        self.min_blob_pixels = kwargs.get('min_blob_pixels', 100)
        self.max_blobs = kwargs.get('max_blobs', 0)
        self.colors_per_target = kwargs.get('colors_per_target', 5)
        
        # Plane detection
        self.plane_size = kwargs.get('plane_size', 20)
        self.minimap_counter_padding = kwargs.get('minimap_counter_padding', 6)
        
        # XP detection
        self.xp_brightness_threshold = kwargs.get('xp_brightness_threshold', 170)
        self.xp_sample_interval = kwargs.get('xp_sample_interval', 1.0)
    
    def to_dict(self):
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary of all configuration parameters
        """
        return {
            'touch_delay_min': self.touch_delay_min,
            'touch_delay_max': self.touch_delay_max,
            'touch_delay_mean': self.touch_delay_mean,
            'touch_delay_std': self.touch_delay_std,
            'stability_timer': self.stability_timer,
            'passing_distance': self.passing_distance,
            'pass_pause_duration': self.pass_pause_duration,
            'auto_target_timeout': self.auto_target_timeout,
            'min_blob_pixels': self.min_blob_pixels,
            'max_blobs': self.max_blobs,
            'colors_per_target': self.colors_per_target,
            'plane_size': self.plane_size,
            'minimap_counter_padding': self.minimap_counter_padding,
            'xp_brightness_threshold': self.xp_brightness_threshold,
            'xp_sample_interval': self.xp_sample_interval,
        }
    
    def apply_to_instance(self, instance):
        """
        Apply configuration settings to an instance object.
        
        Args:
            instance: Object to apply settings to (typically the main app instance)
        """
        instance.touch_delay_min = self.touch_delay_min
        instance.touch_delay_max = self.touch_delay_max
        instance.touch_delay_mean = self.touch_delay_mean
        instance.touch_delay_std = self.touch_delay_std
        instance.stability_timer = self.stability_timer
        instance.passing_distance = self.passing_distance
        instance.pass_pause_duration = self.pass_pause_duration
        instance.auto_target_timeout = self.auto_target_timeout
        instance.min_blob_pixels = self.min_blob_pixels
        instance.max_blobs = self.max_blobs
        instance.colors_per_target = self.colors_per_target
        instance.plane_size = self.plane_size
        instance.minimap_counter_padding = self.minimap_counter_padding
        instance.xp_brightness_threshold = self.xp_brightness_threshold
        instance.xp_sample_interval = self.xp_sample_interval


def create_game_config(instance):
    """
    Create GameConfig from instance attributes.
    
    Extracts all configuration parameters from an instance object and
    creates a new GameConfig with those values.
    
    Args:
        instance: Object with configuration attributes
    
    Returns:
        GameConfig instance with values from the provided instance
    """
    return GameConfig(
        touch_delay_min=instance.touch_delay_min,
        touch_delay_max=instance.touch_delay_max,
        touch_delay_mean=instance.touch_delay_mean,
        touch_delay_std=instance.touch_delay_std,
        stability_timer=instance.stability_timer,
        passing_distance=instance.passing_distance,
        pass_pause_duration=instance.pass_pause_duration,
        auto_target_timeout=instance.auto_target_timeout,
        min_blob_pixels=instance.min_blob_pixels,
        max_blobs=instance.max_blobs,
        colors_per_target=instance.colors_per_target,
        plane_size=instance.plane_size,
        minimap_counter_padding=instance.minimap_counter_padding,
        xp_brightness_threshold=instance.xp_brightness_threshold,
        xp_sample_interval=instance.xp_sample_interval,
    )
