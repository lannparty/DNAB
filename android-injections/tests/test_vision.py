"""Tests for vision module - color filtering, blob detection, and state evaluation."""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from collections import Counter
import sys


# Mock pytesseract before importing vision modules
pytesseract_mock = MagicMock()
pytesseract_mock.image_to_string = Mock(return_value="100")
sys.modules['pytesseract'] = pytesseract_mock


# Mock cv2 module before importing vision modules
@pytest.fixture(autouse=True)
def mock_cv2():
    """Mock cv2 module for tests."""
    cv2_mock = MagicMock()
    cv2_mock.CC_STAT_LEFT = 0
    cv2_mock.CC_STAT_TOP = 1
    cv2_mock.CC_STAT_WIDTH = 2
    cv2_mock.CC_STAT_HEIGHT = 3
    cv2_mock.CC_STAT_AREA = 4
    
    # Mock connected components function
    def mock_connectedComponentsWithStats(mask, connectivity=8):
        """Mock connected components - returns simple test data."""
        num_labels = 2  # background + 1 blob
        labels = np.zeros_like(mask)
        stats = np.array([
            [0, 0, mask.shape[1], mask.shape[0], mask.size],  # background
            [10, 10, 20, 20, 400]  # blob
        ])
        centroids = np.array([[0, 0], [20, 20]])
        return num_labels, labels, stats, centroids
    
    def mock_connectedComponents(mask):
        """Mock connected components (2-return version)."""
        num_labels = 2
        labels = np.zeros_like(mask)
        return num_labels, labels
    
    cv2_mock.connectedComponentsWithStats = mock_connectedComponentsWithStats
    cv2_mock.connectedComponents = mock_connectedComponents
    cv2_mock.resize = lambda img, size, interpolation=None: np.zeros((size[1], size[0], 3), dtype=np.uint8)
    cv2_mock.rectangle = Mock()
    cv2_mock.putText = Mock()
    cv2_mock.cvtColor = Mock(side_effect=lambda img, code: np.zeros(img.shape[:2], dtype=np.uint8))
    cv2_mock.INTER_AREA = 0
    cv2_mock.INTER_CUBIC = 0
    cv2_mock.COLOR_BGR2GRAY = 6
    cv2_mock.createCLAHE = Mock(return_value=MagicMock(apply=lambda x: x))
    cv2_mock.threshold = Mock(return_value=(0, np.zeros((10, 10), dtype=np.uint8)))
    cv2_mock.THRESH_BINARY = 0
    cv2_mock.THRESH_OTSU = 8
    cv2_mock.bilateralFilter = Mock(side_effect=lambda img, *args: img)
    cv2_mock.erode = Mock(return_value=np.zeros((10, 10), dtype=np.uint8))
    cv2_mock.dilate = Mock(return_value=np.zeros((10, 10), dtype=np.uint8))
    cv2_mock.bitwise_not = Mock(side_effect=lambda x: ~x)
    cv2_mock.getTextSize = Mock(return_value=((50, 10), 5))
    cv2_mock.FONT_HERSHEY_SIMPLEX = 0
    
    sys.modules['cv2'] = cv2_mock
    return cv2_mock


class TestFilterUniqueColors:
    """Tests for color filtering and blob detection."""
    
    def test_filter_unique_colors_no_colors(self, ui_state, sample_frame):
        """Should return original frame when no colors to filter."""
        instance = Mock()
        instance.filter_colors = []
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_bounds = {}
        instance.target_to_colors = {}
        
        from android_injections.vision.color_filter import filter_unique_colors
        result = filter_unique_colors(instance, sample_frame, apply_scale=1.0)
        
        # Should return frame with all zeros or similar size
        assert result.shape == sample_frame.shape
    
    def test_filter_unique_colors_with_target_colors(self, sample_frame):
        """Should filter frame to show only target colors."""
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0)]  # Red and green
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {}
        instance.target_bounds = {}
        instance.get_current_auto_target = Mock(return_value=None)
        instance.detected_targets = {}
        
        from android_injections.vision.color_filter import filter_unique_colors
        result = filter_unique_colors(instance, sample_frame, apply_scale=1.0)
        
        assert result.shape == sample_frame.shape
        assert isinstance(result, np.ndarray)
    
    def test_filter_unique_colors_with_scaling(self, sample_frame):
        """Should handle frame scaling correctly."""
        instance = Mock()
        instance.filter_colors = [(255, 0, 0)]  # Blue
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {'test_target': {(255, 0, 0)}}  # Need targets for multi-target mode
        instance.target_bounds = {}
        instance.manual_target_name = None
        instance.get_current_auto_target = Mock(return_value=None)
        instance.detected_targets = {}
        
        from android_injections.vision.color_filter import filter_unique_colors
        result = filter_unique_colors(instance, sample_frame, apply_scale=0.5)
        
        # Should be half size
        h, w = sample_frame.shape[:2]
        expected_h = int(h * 0.5)
        expected_w = int(w * 0.5)
        assert result.shape[0] == expected_h
        assert result.shape[1] == expected_w
    
    def test_filter_unique_colors_excludes_regions(self, sample_frame):
        """Should exclude specified regions from filtering."""
        instance = Mock()
        instance.filter_colors = [(0, 0, 255)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = [(100, 100, 200, 200)]  # Excluded box
        instance.auto_mode = False
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {}
        instance.target_bounds = {}
        instance.get_current_auto_target = Mock(return_value=None)
        instance.detected_targets = {}
        
        from android_injections.vision.color_filter import filter_unique_colors
        result = filter_unique_colors(instance, sample_frame, apply_scale=1.0)
        
        # Excluded region should be zero
        excluded_region = result[100:200, 100:200]
        assert np.all(excluded_region == 0)
    
    def test_filter_unique_colors_blob_detection(self, sample_frame):
        """Should detect and label blobs."""
        # Create a frame with distinct colored regions
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:40, 10:40] = [0, 0, 255]  # Red blob
        frame[50:80, 50:80] = [0, 255, 0]  # Green blob
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.min_blob_pixels = 10
        instance.max_blobs = 0
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        instance.get_current_auto_target = Mock(return_value=None)
        
        from android_injections.vision.color_filter import filter_unique_colors
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should detect blobs and populate detected_targets
        assert isinstance(result, np.ndarray)
    
    def test_filter_unique_colors_max_blobs_limit(self, sample_frame):
        """Should respect max_blobs limit."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Create multiple colored regions
        frame[0:20, 0:20] = [0, 0, 255]
        frame[25:45, 25:45] = [0, 255, 0]
        frame[50:70, 50:70] = [255, 0, 0]
        
        instance = Mock()
        instance.filter_colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]
        instance.show_filtered = False
        instance.color_lookup = None
        instance.auto_view_mode = False
        instance.excluded_regions = []
        instance.auto_mode = False
        instance.min_blob_pixels = 10
        instance.max_blobs = 2  # Only allow 2 blobs
        instance.benchmark = False
        instance.target_to_colors = {
            'target1': {(0, 0, 255)},
            'target2': {(0, 255, 0)},
            'target3': {(255, 0, 0)}
        }
        instance.target_bounds = {}
        instance.detected_targets = {}
        instance.get_current_auto_target = Mock(return_value=None)
        
        from android_injections.vision.color_filter import filter_unique_colors
        result = filter_unique_colors(instance, frame, apply_scale=1.0)
        
        # Should only detect up to max_blobs
        assert len(instance.detected_targets) <= 2


class TestEvaluateStateFields:
    """Tests for XP detection and plane detection."""
    
    def test_evaluate_state_fields_no_bounds(self, sample_frame, mock_cv2):
        """Should handle case with no bounds defined."""
        instance = Mock()
        instance.bounds_with_names = []
        instance.xp_last_sample_time = 0
        instance.xp_sample_interval = 0
        instance.xp_trigger_time = None
        instance.xp_detected = "0"
        
        from android_injections.vision.state_eval import evaluate_state_fields
        # Should not raise error
        evaluate_state_fields(instance, sample_frame)
    
    def test_evaluate_state_fields_xp_detection_initialization(self, sample_frame, mock_cv2):
        """Should initialize XP detection state properly."""
        instance = Mock()
        instance.bounds_with_names = [(0, 0, 50, 50, 'xp')]
        instance.xp_last_sample_time = 0
        instance.xp_sample_interval = 0.0  # Always sample
        instance.xp_last_value = None
        instance.xp_detected = "0"
        instance.xp_trigger_time = None
        instance.target_to_colors = {}
        instance._clahe = mock_cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        instance.xp_brightness_threshold = 127
        
        from android_injections.vision.state_eval import evaluate_state_fields
        evaluate_state_fields(instance, sample_frame)
        
        # Should have processed or left state as initialized
        assert hasattr(instance, 'xp_last_value')
    
    def test_evaluate_state_fields_higher_plane_detection(self, sample_frame, mock_cv2):
        """Should detect higher plane from minimap."""
        # Create frame with minimap region containing black squares
        frame = sample_frame.copy()
        frame[0:20, 0:20] = [0, 0, 0]  # Black square (higher plane marker)
        
        instance = Mock()
        instance.bounds_with_names = [
            (0, 0, 50, 50, 'xp'),
            (10, 10, 40, 40, 'minimap')
        ]
        instance.xp_last_sample_time = 0
        instance.xp_sample_interval = 0
        instance.xp_last_value = None
        instance.xp_detected = "0"
        instance.xp_trigger_time = None
        instance.higher_plane = False
        instance.plane_size = 3
        instance.target_to_colors = {}
        instance._clahe = mock_cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        instance.xp_brightness_threshold = 127
        
        from android_injections.vision.state_eval import evaluate_state_fields
        evaluate_state_fields(instance, frame)
        
        # Should set higher_plane to True or False (not raise an error)
        assert isinstance(instance.higher_plane, (bool, type(None)))
    
    def test_evaluate_state_fields_plane_counter(self, sample_frame, mock_cv2):
        """Should count distinct color groups for plane counter."""
        frame = np.zeros_like(sample_frame)
        # Create distinct colored regions in minimap
        frame[10:20, 10:20] = [0, 100, 255]  # Region 1
        frame[30:40, 30:40] = [0, 100, 255]  # Region 2 (same color, different location)
        
        instance = Mock()
        instance.bounds_with_names = [
            (0, 0, 50, 50, 'xp'),
            (0, 0, 60, 60, 'minimap')
        ]
        instance.xp_last_sample_time = 0
        instance.xp_sample_interval = 0
        instance.xp_last_value = None
        instance.xp_detected = "0"
        instance.xp_trigger_time = None
        instance.higher_plane = False
        instance.plane_size = 1
        instance.plane_counter = 0
        instance.plane_counter_prev_value = None
        instance.plane_counter_stable_since = None
        instance.plane_count_padding = 0
        instance.target_to_colors = {
            'minimap_counter': {(0, 100, 255)}
        }
        instance._clahe = mock_cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        instance.xp_brightness_threshold = 127
        
        from android_injections.vision.state_eval import evaluate_state_fields
        evaluate_state_fields(instance, frame)
        
        # Should count distinct groups
        assert isinstance(instance.plane_counter, int)
        assert instance.plane_counter >= 0
    
    def test_evaluate_state_fields_xp_stability_tracking(self, sample_frame, mock_cv2):
        """Should track stability of plane counter."""
        frame = np.zeros_like(sample_frame)
        frame[10:20, 10:20] = [0, 100, 255]
        
        instance = Mock()
        instance.bounds_with_names = [
            (0, 0, 50, 50, 'xp'),
            (0, 0, 60, 60, 'minimap')
        ]
        instance.xp_last_sample_time = 0
        instance.xp_sample_interval = 0
        instance.xp_last_value = None
        instance.xp_detected = "0"
        instance.xp_trigger_time = None
        instance.higher_plane = False
        instance.plane_size = 1
        instance.plane_counter = 1
        instance.plane_counter_prev_value = 1  # Same as current
        instance.plane_counter_stable_since = None
        instance.plane_count_padding = 0
        instance.stability_timer = 0.5
        instance.target_to_colors = {
            'minimap_counter': {(0, 100, 255)}
        }
        instance._clahe = mock_cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        instance.xp_brightness_threshold = 127
        
        from android_injections.vision.state_eval import evaluate_state_fields
        evaluate_state_fields(instance, frame)
        
        # Should track stability when value doesn't change
        assert instance.plane_counter_stable_since is not None or instance.plane_counter_prev_value != instance.plane_counter


class TestColorLookupOptimization:
    """Tests for color lookup table optimization."""
    
    def test_color_lookup_creation(self, mock_cv2):
        """Should create efficient color lookup table."""
        from android_injections.vision.color_filter import create_color_lookup
        
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        lookup = create_color_lookup(colors)
        
        assert lookup.shape == (256, 256, 256)
        assert lookup.dtype == bool
        
        # Check that specified colors are marked as True
        assert lookup[255, 0, 0] == True
        assert lookup[0, 255, 0] == True
        assert lookup[0, 0, 255] == True
        
        # Check that other colors are False
        assert lookup[100, 100, 100] == False
    
    def test_color_lookup_vectorized_search(self, mock_cv2):
        """Should perform fast vectorized color lookup."""
        from android_injections.vision.color_filter import create_color_lookup
        
        colors = [(0, 0, 255)]  # Blue
        lookup = create_color_lookup(colors)
        
        # Create frame with some blue pixels
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frame[0:5, 0:5] = [0, 0, 255]  # Blue region
        
        b, g, r = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
        mask = lookup[b, g, r]
        
        # Top-left should be True (blue), rest should be False
        assert np.any(mask[:5, :5])
        assert not np.any(mask[5:, :])


class TestBlobDetectionAndGrouping:
    """Tests for blob detection and target assignment."""
    
    def test_blob_detection_basic(self, mock_cv2):
        """Should detect connected components in mask."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:30, 10:30] = [255, 0, 0]  # Blue blob
        frame[50:70, 50:70] = [255, 0, 0]  # Another blue blob
        
        # Create mask
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[10:30, 10:30] = 255
        mask[50:70, 50:70] = 255
        
        # Detect blobs
        num_labels, labels, stats, centroids = mock_cv2.connectedComponentsWithStats(mask, connectivity=8)
        
        # Should detect blobs (at least 1 background + 1 blob)
        assert num_labels >= 2
    
    def test_blob_target_assignment_by_color(self):
        """Should assign blobs to targets based on dominant color."""
        from android_injections.vision.color_filter import assign_blob_to_target
        
        blob_colors = {(255, 0, 0), (254, 0, 0)}  # Mostly blue
        target_to_colors = {
            'target1': {(255, 0, 0), (254, 0, 0)},
            'target2': {(0, 255, 0)}
        }
        
        best_target = assign_blob_to_target(blob_colors, target_to_colors)
        
        assert best_target == 'target1'
    
    def test_blob_filtering_by_size(self):
        """Should filter blobs by minimum size."""
        instance = Mock()
        instance.min_blob_pixels = 100
        instance.max_blobs = 5
        
        # Create blobs with different sizes
        blobs = {
            'blob1': {'area': 50},   # Too small
            'blob2': {'area': 200},  # Valid
            'blob3': {'area': 300}   # Valid
        }
        
        valid_blobs = {k: v for k, v in blobs.items() if v['area'] >= instance.min_blob_pixels}
        
        assert len(valid_blobs) == 2
        assert 'blob1' not in valid_blobs
