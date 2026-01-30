"""Pytest configuration and shared fixtures."""
import pytest
import numpy as np
import json
import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def ui_state():
    """Create a fresh UI state dictionary matching WindowCapture class initialization."""
    return {
        # Display and window settings
        'window_name': 'Pixel 4a (5G)',
        'target_fps': 30,
        'display_scale': 0.5,
        'benchmark': False,
        
        # Filter and display settings
        'show_filtered': False,
        'colors_per_target': 20,
        'min_blob_pixels': 2,
        'max_blobs': 1,
        'show_bounds': False,
        'show_excludes': False,
        'auto_view_mode': False,
        
        # Target selection and mode
        'target_mode': False,
        'bounds_mode': False,
        'exclude_mode': False,
        'unique_only': True,
        'target_name': '',
        
        # Text input
        'text_input_active': False,
        'target_selector_active': False,
        'temp_input': '',
        
        # Selection rectangles (stored as ((x1, y1), (x2, y2)) tuples)
        'selection_start': None,
        'selection_end': None,
        'selecting': False,
        'target_selection_rect': None,
        'bounds_selection_rect': None,
        'exclude_selection_rect': None,
        
        # Color editing
        'editing_colors': False,
        'editing_min_pixels': False,
        'editing_max_blobs': False,
        
        # Delay timer editing
        'editing_delay_min': False,
        'editing_delay_max': False,
        'editing_delay_mean': False,
        'editing_delay_std': False,
        'editing_stability': False,
        'editing_passing_dist': False,
        'editing_xp_brightness': False,
        'editing_xp_sample_interval': False,
        'editing_plane_size': False,
        'minimap_counter_padding_editing': False,
        
        # Plane detection
        'plane_size': 5,
        'higher_plane': False,
        'plane_counter': 0,
        'minimap_counter_padding': 5,
        'plane_counter_prev_value': None,
        'plane_counter_stable_since': None,
        
        # Auto mode state
        'auto_mode': False,
        'state_tracking': False,
        'last_auto_touch': 0,
        'next_touch_interval': 0.8,
        'touch_delay_min': 0.3,
        'touch_delay_max': 4.358,
        'touch_delay_mean': 0.8,
        'touch_delay_std': 0.6,
        'stability_timer': 1.0,
        'passing_distance': 50,
        
        # XP detection
        'xp_last_value': None,
        'xp_current_reading': None,
        'xp_reading_first_seen': None,
        'xp_last_sample_time': 0,
        'xp_sample_interval': 1.0,
        'xp_trigger_time': None,
        'xp_detected': '0',
        'xp_brightness_threshold': 170,
        
        # Auto touch state
        'auto_target_list': [],
        'auto_target_index': 0,
        'auto_target_passed': False,
        'auto_target_touched': False,
        'auto_touched_time': None,
        'auto_target_prev_pos': None,
        'auto_target_stable_since': None,
        'auto_touched_position': None,
        'auto_dot_prev_pos': None,
        'auto_dot_stable_since': None,
        'pass_pause_duration': 3.0,
        'auto_target_last_seen': None,
        'auto_target_timeout': 10.0,
        
        # Data structures
        'filter_colors': set(),
        'unique_colors': set(),
        'detected_targets': {},
        'excluded_regions': [],
        'excluded_regions_with_names': [],
        'bounds_with_names': [],
        'target_bounds': {},
        'color_to_target': {},
        'target_to_colors': {},
    }


@pytest.fixture
def sample_frame():
    """Create a sample frame (1080x2340, Pixel 4a 5G portrait)."""
    # BGR format, typical Android screen
    frame = np.zeros((2340, 1080, 3), dtype=np.uint8)
    # Add some variation so it's not pure black
    frame[100:200, 100:200] = [50, 100, 150]  # Some colored pixels
    return frame


@pytest.fixture
def sample_small_frame():
    """Create a smaller test frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def temp_test_dirs():
    """Create temporary directories for targets, bounds, and exclude data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        targets_dir = Path(tmpdir) / 'targets'
        bounds_dir = Path(tmpdir) / 'bounds'
        exclude_dir = Path(tmpdir) / 'exclude'
        
        targets_dir.mkdir()
        bounds_dir.mkdir()
        exclude_dir.mkdir()
        
        yield {
            'root': tmpdir,
            'targets': str(targets_dir),
            'bounds': str(bounds_dir),
            'exclude': str(exclude_dir),
        }


@pytest.fixture
def sample_target_data():
    """Create sample target JSON data."""
    return {
        'name': 'ladder',
        'colors': [[100, 50, 200], [110, 60, 210], [90, 40, 190]],
        'color_count': 3,
        'pixel_count': 1500,
    }


@pytest.fixture
def sample_bounds_data():
    """Create sample bounds JSON data."""
    return {
        'target_name': 'xp',
        'bounds': [100, 200, 300, 250],
    }


@pytest.fixture
def sample_exclude_data():
    """Create sample exclusion JSON data."""
    return {
        'name': 'xp_exclude',
        'regions': [[100, 200, 300, 250], [400, 500, 600, 550]],
    }


@pytest.fixture
def mock_cv2(monkeypatch):
    """Mock common cv2 functions to avoid GUI dependencies."""
    import cv2
    
    # Store original functions
    original_functions = {}
    
    # Mock functions that would interact with display
    mock_functions = {
        'rectangle': lambda *args, **kwargs: None,
        'circle': lambda *args, **kwargs: None,
        'line': lambda *args, **kwargs: None,
        'putText': lambda *args, **kwargs: None,
        'getTextSize': lambda text, font, scale, thickness: (len(text) * 10, 20),
        'resize': lambda img, dsize, **kwargs: np.zeros((dsize[1], dsize[0], img.shape[2]), dtype=img.dtype),
        'cvtColor': lambda src, code: src,
        'threshold': lambda src, thresh, maxval, method: (0, src),
        'connectedComponents': lambda src, **kwargs: (0, np.zeros_like(src)),
        'erode': lambda src, kernel, **kwargs: src,
        'dilate': lambda src, kernel, **kwargs: src,
        'bilateralFilter': lambda src, **kwargs: src,
    }
    
    for func_name, mock_func in mock_functions.items():
        original_functions[func_name] = getattr(cv2, func_name, None)
        monkeypatch.setattr(f'cv2.{func_name}', mock_func)
    
    yield mock_functions
    
    # Restore originals (handled by monkeypatch, but for clarity)
    for func_name, original in original_functions.items():
        if original is not None:
            monkeypatch.setattr(f'cv2.{func_name}', original)


@pytest.fixture
def mock_file_io(monkeypatch):
    """Mock file I/O operations."""
    import builtins
    
    # Store file system state in memory
    file_system = {}
    
    original_open = builtins.open
    
    def mock_open(file, mode='r', *args, **kwargs):
        """Mock file open that stores data in memory."""
        from io import StringIO, BytesIO
        
        # Handle JSON files
        if 'w' in mode:
            # Write mode
            class MockFile:
                def __init__(self, filepath):
                    self.filepath = filepath
                    self.content = StringIO()
                
                def write(self, data):
                    return self.content.write(data)
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args):
                    file_system[self.filepath] = self.content.getvalue()
            
            return MockFile(file)
        elif 'r' in mode:
            # Read mode
            class MockFile:
                def __init__(self, filepath, content=''):
                    self.content = StringIO(content)
                
                def read(self):
                    return self.content.read()
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args):
                    pass
            
            content = file_system.get(file, '')
            return MockFile(file, content)
        else:
            # Fall back to original for other modes
            return original_open(file, mode, *args, **kwargs)
    
    monkeypatch.setattr('builtins.open', mock_open)
    
    return file_system


@pytest.fixture
def button_positions():
    """Standard button positions based on UI layout."""
    return {
        'target_mode_button': (0, 2340, 270, 40),      # (x, y, width, height)
        'bounds_button': (270, 2340, 270, 40),
        'exclude_mode_button': (540, 2340, 270, 40),
        'state_tracking_button': (810, 2340, 270, 40),
        'filter_button': (0, 2380, 1080, 40),
        'capture_button': (0, 2420, 200, 40),
        'auto_button': (200, 2420, 200, 40),
        'unique_checkbox': (200, 2345, 70, 30),
    }


@pytest.fixture
def rect_helper():
    """Helper function to check if point is in rectangle."""
    def is_point_in_rect(x, y, rect_x, rect_y, rect_w, rect_h):
        """Check if point (x, y) is within rectangle."""
        return (rect_x <= x <= rect_x + rect_w and 
                rect_y <= y <= rect_y + rect_h)
    
    return is_point_in_rect
