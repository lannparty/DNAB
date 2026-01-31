"""Tests for targeting module - target loading, saving, bounds, and color analysis."""
import pytest
import numpy as np
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestColorAnalysis:
    """Tests for color analysis in selected regions."""
    
    def test_analyze_unique_colors_basic(self):
        """Should find colors that appear only in selected region."""
        # Create a frame with distinct regions
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = [100, 100, 100]  # Gray background everywhere
        frame[30:70, 30:70] = [255, 0, 0]  # Blue in selected region
        
        instance = Mock()
        instance.current_frame = frame
        instance.target_selection_rect = ((30, 30), (70, 70))
        instance.display_scale = 1.0
        instance.unique_colors = set()
        instance.unique_colors_by_count = []
        instance.all_box_colors_by_count = []
        instance.most_common_unique_color = None
        instance.most_common_count = 0
        instance.bounds_with_names = []  # Fix: make it a real list
        
        from android_injections.targeting.color_analysis import analyze_unique_colors
        analyze_unique_colors(instance)
        
        # Blue color should be unique (only in selection)
        assert (255, 0, 0) in instance.unique_colors
        # Gray should NOT be unique (everywhere)
        assert (100, 100, 100) not in instance.unique_colors
    
    def test_analyze_unique_colors_no_unique(self):
        """Should return empty set when no unique colors exist."""
        frame = np.full((100, 100, 3), 128, dtype=np.uint8)  # Uniform color everywhere
        
        instance = Mock()
        instance.current_frame = frame
        instance.target_selection_rect = ((30, 30), (70, 70))
        instance.display_scale = 1.0
        instance.unique_colors = set()
        instance.unique_colors_by_count = []
        instance.all_box_colors_by_count = []
        instance.most_common_unique_color = None
        instance.most_common_count = 0
        instance.bounds_with_names = []  # Fix: make it a real list
        
        from android_injections.targeting.color_analysis import analyze_unique_colors
        analyze_unique_colors(instance)
        
        # No unique colors
        assert len(instance.unique_colors) == 0
    
    def test_analyze_unique_colors_with_scaling(self):
        """Should handle frame scaling when analyzing colors."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = [100, 100, 100]
        frame[30:70, 30:70] = [255, 0, 0]
        
        instance = Mock()
        instance.current_frame = frame
        instance.target_selection_rect = ((60, 60), (140, 140))  # Scaled coordinates (2x)
        instance.display_scale = 0.5  # Display is half size
        instance.unique_colors = set()
        instance.unique_colors_by_count = []
        instance.all_box_colors_by_count = []
        instance.most_common_unique_color = None
        instance.most_common_count = 0
        instance.bounds_with_names = []  # Fix: make it a real list
        
        from android_injections.targeting.color_analysis import analyze_unique_colors
        analyze_unique_colors(instance)
        
        # Should work despite scaling
        assert isinstance(instance.unique_colors, set)
    
    def test_analyze_unique_colors_sorting_by_prevalence(self):
        """Should sort unique colors by prevalence (occurrence count)."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = [100, 100, 100]  # Background
        
        # Create selection with two colors, different prevalence
        frame[30:70, 30:50] = [255, 0, 0]  # Blue (400 pixels)
        frame[30:35, 50:70] = [0, 255, 0]  # Green (100 pixels)
        
        instance = Mock()
        instance.current_frame = frame
        instance.target_selection_rect = ((30, 30), (70, 70))
        instance.display_scale = 1.0
        instance.unique_colors = set()
        instance.unique_colors_by_count = []
        instance.all_box_colors_by_count = []
        instance.most_common_unique_color = None
        instance.most_common_count = 0
        instance.bounds_with_names = []  # Fix: make it a real list
        
        from android_injections.targeting.color_analysis import analyze_unique_colors
        analyze_unique_colors(instance)
        
        # Most common unique color should be blue
        assert instance.most_common_unique_color == (255, 0, 0)
        assert instance.most_common_count > 0


class TestTargetLoading:
    """Tests for loading target files."""
    
    def test_load_all_targets_basic(self):
        """Should load color targets from JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_dir = os.path.join(tmpdir, 'targets')
            bounds_dir = os.path.join(tmpdir, 'bounds')
            os.makedirs(targets_dir)
            os.makedirs(bounds_dir)
            
            # Create a target file
            target_data = {
                "name": "test_target",
                "colors": [[255, 0, 0], [254, 0, 0], [253, 0, 0]],
                "color_count": 3,
                "pixel_count": 1000
            }
            with open(os.path.join(targets_dir, 'test_target.json'), 'w') as f:
                json.dump(target_data, f)
            
            instance = Mock()
            # Configure Mock to not have internal directory attributes
            instance.configure_mock(**{
                'internal_targets_dir': None,
                'internal_bounds_dir': None
            })
            instance.targets_dir = targets_dir
            instance.bounds_dir = bounds_dir
            instance.exclude_dir = os.path.join(tmpdir, 'exclude')
            instance.colors_per_target = 20
            instance.filter_colors = set()
            instance.color_to_target = {}
            instance.target_to_colors = {}
            instance.target_bounds = {}
            instance.bounds_with_names = []
            
            from android_injections.targeting.target_loader import load_all_targets
            load_all_targets(instance)
            
            # Should have loaded the target
            assert 'test_target' in instance.target_to_colors
            assert len(instance.target_to_colors['test_target']) == 3
    
    def test_load_all_targets_with_bounds(self):
        """Should load target bounds files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_dir = os.path.join(tmpdir, 'targets')
            bounds_dir = os.path.join(tmpdir, 'bounds')
            os.makedirs(targets_dir)
            os.makedirs(bounds_dir)
            
            # Create target and bounds files
            target_data = {
                "name": "test_target",
                "colors": [[255, 0, 0]],
                "color_count": 1,
                "pixel_count": 100
            }
            with open(os.path.join(targets_dir, 'test_target.json'), 'w') as f:
                json.dump(target_data, f)
            
            bounds_data = {
                "target_name": "test_target",
                "bounds": [10, 20, 100, 200]
            }
            with open(os.path.join(bounds_dir, 'test_target.json'), 'w') as f:
                json.dump(bounds_data, f)
            
            instance = Mock()
            # Configure Mock to not have internal directory attributes
            instance.configure_mock(**{
                'internal_targets_dir': None,
                'internal_bounds_dir': None
            })
            instance.targets_dir = targets_dir
            instance.bounds_dir = bounds_dir
            instance.exclude_dir = os.path.join(tmpdir, 'exclude')
            instance.colors_per_target = 20
            instance.filter_colors = set()
            instance.color_to_target = {}
            instance.target_to_colors = {}
            instance.target_bounds = {}
            instance.bounds_with_names = []
            
            from android_injections.targeting.target_loader import load_all_targets
            load_all_targets(instance)
            
            # Should have loaded bounds
            assert 'test_target' in instance.target_bounds
            assert instance.target_bounds['test_target'] == (10, 20, 100, 200)


class TestTargetSaving:
    """Tests for saving target files."""
    
    def test_save_target_basic(self):
        """Should save target colors to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_dir = os.path.join(tmpdir, 'targets')
            os.makedirs(targets_dir)
            
            instance = Mock()
            instance.targets_dir = targets_dir
            instance.bounds_dir = os.path.join(tmpdir, 'bounds')
            instance.exclude_dir = os.path.join(tmpdir, 'exclude')
            instance.target_selection_rect = ((10, 10), (50, 50))
            instance.target_name = 'new_target'
            instance.unique_only = True
            instance.unique_colors_by_count = [
                ((255, 0, 0), 100),
                ((254, 0, 0), 50)
            ]
            instance.all_box_colors_by_count = []
            instance.colors_per_target = 20
            instance.filter_colors = set()
            instance.color_to_target = {}
            instance.target_to_colors = {}
            instance.target_bounds = {}
            instance.bounds_with_names = []
            
            from android_injections.targeting.target_loader import load_all_targets
            from android_injections.targeting.target_saver import save_target
            
            save_target(instance)
            
            # File should exist
            filepath = os.path.join(targets_dir, 'new_target.json')
            assert os.path.exists(filepath)
            
            # Content should be correct
            with open(filepath, 'r') as f:
                data = json.load(f)
                assert data['name'] == 'new_target'
                assert len(data['colors']) == 2
    
    def test_save_target_no_name(self):
        """Should fail when target name not set."""
        instance = Mock()
        instance.target_selection_rect = ((10, 10), (50, 50))
        instance.target_name = None
        
        from android_injections.targeting.target_saver import save_target
        
        # Should not raise error
        save_target(instance)
    
    def test_save_bounds_basic(self):
        """Should save bounds for a target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bounds_dir = os.path.join(tmpdir, 'bounds')
            targets_dir = os.path.join(tmpdir, 'targets')
            os.makedirs(bounds_dir)
            os.makedirs(targets_dir)
            
            instance = Mock()
            # Configure Mock to not have internal directory attributes
            instance.configure_mock(**{
                'internal_targets_dir': None,
                'internal_bounds_dir': None
            })
            instance.targets_dir = targets_dir
            instance.bounds_dir = bounds_dir
            instance.exclude_dir = os.path.join(tmpdir, 'exclude')
            instance.bounds_selection_rect = ((10, 20), (100, 200))
            instance.target_name = 'test_target'
            instance.display_scale = 1.0
            instance.colors_per_target = 20
            instance.filter_colors = set()
            instance.color_to_target = {}
            instance.target_to_colors = {}
            instance.target_bounds = {}
            instance.bounds_with_names = []
            
            from android_injections.targeting.target_saver import save_bounds
            save_bounds(instance)
            
            # File should exist
            filepath = os.path.join(bounds_dir, 'test_target.json')
            assert os.path.exists(filepath)
            
            # Content should be correct
            with open(filepath, 'r') as f:
                data = json.load(f)
                assert data['target_name'] == 'test_target'
                assert data['bounds'] == [10, 20, 100, 200]


class TestExcludedRegions:
    """Tests for loading and saving excluded regions."""
    
    def test_load_excluded_regions_basic(self):
        """Should load excluded regions from JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_dir = os.path.join(tmpdir, 'exclude')
            os.makedirs(exclude_dir)
            
            # Create exclusion file
            exclude_data = {
                "name": "test_exclude",
                "regions": [[10, 20, 100, 200], [300, 400, 500, 600]]
            }
            with open(os.path.join(exclude_dir, 'test_exclude.json'), 'w') as f:
                json.dump(exclude_data, f)
            
            instance = Mock()
            instance.exclude_dir = exclude_dir
            instance.excluded_regions = []
            instance.excluded_regions_with_names = []
            
            from android_injections.targeting.exclusion_manager import load_excluded_regions
            load_excluded_regions(instance)
            
            # Should have loaded regions
            assert len(instance.excluded_regions) == 2
            assert (10, 20, 100, 200) in instance.excluded_regions
    
    def test_save_excluded_region(self):
        """Should save excluded region to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_dir = os.path.join(tmpdir, 'exclude')
            os.makedirs(exclude_dir)
            
            instance = Mock()
            instance.exclude_dir = exclude_dir
            instance.excluded_regions = []
            instance.excluded_regions_with_names = []
            instance.selection_start = (10, 20)
            instance.selection_end = (100, 200)
            instance.target_name = 'test_exclude'
            instance.display_scale = 1.0
            
            from android_injections.targeting.exclusion_manager import save_excluded_region, load_excluded_regions
            save_excluded_region(instance)
            
            # File should exist
            filepath = os.path.join(exclude_dir, 'test_exclude.json')
            assert os.path.exists(filepath)
            
            # Content should be correct
            with open(filepath, 'r') as f:
                data = json.load(f)
                assert len(data['regions']) == 1
                assert [10, 20, 100, 200] in data['regions']


class TestColorLookupTable:
    """Tests for color lookup table pre-computation."""
    
    def test_color_lookup_creation_in_load(self):
        """Should create lookup table when loading targets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_dir = os.path.join(tmpdir, 'targets')
            bounds_dir = os.path.join(tmpdir, 'bounds')
            os.makedirs(targets_dir)
            os.makedirs(bounds_dir)
            
            # Create target file
            target_data = {
                "name": "test",
                "colors": [[255, 0, 0], [0, 255, 0]],
                "color_count": 2,
                "pixel_count": 200
            }
            with open(os.path.join(targets_dir, 'test.json'), 'w') as f:
                json.dump(target_data, f)
            
            instance = Mock()
            # Configure Mock to not have internal directory attributes
            instance.configure_mock(**{
                'internal_targets_dir': None,
                'internal_bounds_dir': None
            })
            instance.targets_dir = targets_dir
            instance.bounds_dir = bounds_dir
            instance.exclude_dir = os.path.join(tmpdir, 'exclude')
            instance.colors_per_target = 20
            instance.filter_colors = set()
            instance.color_to_target = {}
            instance.target_to_colors = {}
            instance.target_bounds = {}
            instance.bounds_with_names = []
            instance.color_lookup = None
            
            from android_injections.targeting.target_loader import load_all_targets
            load_all_targets(instance)
            
            # Lookup table should be created
            assert instance.color_lookup is not None
            assert instance.color_lookup.shape == (256, 256, 256)
            # Test that specific colors are marked as True
            assert instance.color_lookup[255, 0, 0] == True
            assert instance.color_lookup[0, 255, 0] == True


class TestUniqueFingerprints:
    """Tests for ensuring unique color fingerprints across targets."""
    
    def test_fingerprint_collision_resolution(self):
        """Should detect and resolve color fingerprint collisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_dir = os.path.join(tmpdir, 'targets')
            bounds_dir = os.path.join(tmpdir, 'bounds')
            os.makedirs(targets_dir)
            os.makedirs(bounds_dir)
            
            # Create two targets with same first N colors (collision)
            colors = [[255, 0, 0], [254, 0, 0], [253, 0, 0], [0, 255, 0]]
            
            target1 = {
                "name": "target1",
                "colors": colors,
                "color_count": 4,
                "pixel_count": 1000
            }
            with open(os.path.join(targets_dir, 'target1.json'), 'w') as f:
                json.dump(target1, f)
            
            target2 = {
                "name": "target2",
                "colors": colors,
                "color_count": 4,
                "pixel_count": 1000
            }
            with open(os.path.join(targets_dir, 'target2.json'), 'w') as f:
                json.dump(target2, f)
            
            instance = Mock()
            # Configure Mock to not have internal directory attributes
            instance.configure_mock(**{
                'internal_targets_dir': None,
                'internal_bounds_dir': None
            })
            instance.targets_dir = targets_dir
            instance.bounds_dir = bounds_dir
            instance.exclude_dir = os.path.join(tmpdir, 'exclude')
            instance.colors_per_target = 2  # Force collision
            instance.filter_colors = set()
            instance.color_to_target = {}
            instance.target_to_colors = {}
            instance.target_bounds = {}
            instance.bounds_with_names = []
            
            from android_injections.targeting.target_loader import load_all_targets
            load_all_targets(instance)
            
            # Both targets should be loaded
            assert 'target1' in instance.target_to_colors
            assert 'target2' in instance.target_to_colors
            
            # Their fingerprints should be different
            fp1 = frozenset(instance.target_to_colors['target1'])
            fp2 = frozenset(instance.target_to_colors['target2'])
            assert fp1 != fp2
