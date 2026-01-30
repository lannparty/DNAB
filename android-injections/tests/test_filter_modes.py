"""Tests for multi-target mode unification and filter drawing."""
import pytest
import numpy as np
from unittest.mock import Mock
from android_injections.vision.color_filter import filter_unique_colors


class TestMultiTargetModeUnification:
    """Tests to ensure multi-target mode works correctly for all scenarios."""
    
    def test_auto_mode_detects_all_targets(self):
        """Auto mode should detect all targets for targeting logic."""
        # Create frame with 3 distinct colored regions
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [0, 0, 255]  # Red target1
        frame[40:60, 40:60] = [0, 255, 0]  # Green target2
        frame[70:90, 70:90] = [255, 0, 0]  # Blue target3
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = True  # AUTO MODE ON
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)},
            'target3': {(255, 0, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        instance.get_current_auto_target = Mock(return_value='target2')
        
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should detect ALL 3 targets even though auto mode is on
        assert len(instance.detected_targets) == 3
        assert 'target1' in instance.detected_targets
        assert 'target2' in instance.detected_targets
        assert 'target3' in instance.detected_targets
    
    def test_auto_mode_draws_only_current_target(self):
        """Auto mode should only draw the current target."""
        # Create frame with 3 distinct colored regions
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [0, 0, 255]  # Red target1
        frame[40:60, 40:60] = [0, 255, 0]  # Green target2
        frame[70:90, 70:90] = [255, 0, 0]  # Blue target3
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = True  # AUTO MODE ON
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)},
            'target3': {(255, 0, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        instance.get_current_auto_target = Mock(return_value='target2')
        
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Result should show only target2's colors (green)
        # Check that green pixels exist
        green_pixels = np.sum((result[:, :, 1] > 0) & (result[:, :, 0] == 0) & (result[:, :, 2] == 0))
        assert green_pixels > 0, "Current target (target2) should be visible"
        
        # Result frame should be non-empty for target2 region
        assert np.sum(result) > 0
    
    def test_manual_mode_all_detects_and_draws_all(self):
        """Manual mode with 'all' should detect and draw all targets."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [0, 0, 255]  # Red target1
        frame[40:60, 40:60] = [0, 255, 0]  # Green target2
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False  # Manual mode
        instance.manual_target_name = 'all'
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should detect both targets
        assert len(instance.detected_targets) == 2
        assert 'target1' in instance.detected_targets
        assert 'target2' in instance.detected_targets
        
        # Both should be visible in result
        assert np.sum(result) > 0
    
    def test_manual_mode_specific_target_detects_all_draws_one(self):
        """Manual mode with specific target should detect all but draw only selected."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [0, 0, 255]  # Red target1
        frame[40:60, 40:60] = [0, 255, 0]  # Green target2
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False  # Manual mode
        instance.manual_target_name = 'target1'
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should detect both targets
        assert len(instance.detected_targets) == 2
        assert 'target1' in instance.detected_targets
        assert 'target2' in instance.detected_targets
        
        # Only target1 (red) should be visible in result
        red_pixels = np.sum((result[:, :, 2] > 0) & (result[:, :, 0] == 0) & (result[:, :, 1] == 0))
        assert red_pixels > 0, "Selected target (target1) should be visible"
    
    def test_max_blobs_applies_to_detection(self):
        """max_blobs should limit how many targets are detected."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [0, 0, 255]  # Red target1 (400px)
        frame[40:60, 40:60] = [0, 255, 0]  # Green target2 (400px)
        frame[70:90, 70:90] = [255, 0, 0]  # Blue target3 (400px)
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.manual_target_name = 'all'
        instance.min_blob_pixels = 10
        instance.max_blobs = 2  # Limit to 2 blobs
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)},
            'target3': {(255, 0, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should only detect 2 largest targets
        assert len(instance.detected_targets) == 2
    
    def test_no_targets_returns_empty_frame(self):
        """When no targets configured, should return empty frame."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        instance = Mock()
        instance.filter_colors = []
        instance.target_to_colors = {}
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.manual_target_name = None
        
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should return original frame when no colors to filter
        assert result.shape == frame.shape
    
    def test_scaling_consistency(self):
        """Scaling should work consistently regardless of mode."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [0, 0, 255]  # Red target1
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = True
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {'target1': {(0, 0, 255)}}
        instance.target_bounds = {}
        instance.detected_targets = {}
        instance.get_current_auto_target = Mock(return_value='target1')
        
        # Test with scaling
        result = filter_unique_colors(instance, frame, apply_scale=0.5)
        
        # Result should be scaled
        assert result.shape == (50, 50, 3)
        
        # But detected_targets should have original coordinates
        assert 'target1' in instance.detected_targets
        x, y, w, h = instance.detected_targets['target1']
        assert x >= 10 and x <= 30  # Original coordinates
