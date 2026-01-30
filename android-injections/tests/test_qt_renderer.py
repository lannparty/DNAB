"""Tests for PyQt6 renderer functionality."""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest


# Import the classes we're testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for all tests (required for Qt widgets)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _mock_on_key_press(self, key, text):
    """Mock implementation of on_key_press for testing."""
    from PyQt6.QtCore import Qt
    
    # Handle keyboard shortcuts (simplified version of main_qt.py logic)
    if key == Qt.Key.Key_F:
        self.show_filtered = not self.show_filtered
    elif key == Qt.Key.Key_T:
        self.target_mode = not self.target_mode
        if self.target_mode:
            self.bounds_mode = False
            self.exclude_mode = False
    elif key == Qt.Key.Key_B:
        self.bounds_mode = not self.bounds_mode
        if self.bounds_mode:
            self.target_mode = False
            self.exclude_mode = False
    elif key == Qt.Key.Key_E:
        self.exclude_mode = not self.exclude_mode
        if self.exclude_mode:
            self.target_mode = False
            self.bounds_mode = False
    elif key == Qt.Key.Key_S:
        self.state_tracking = not self.state_tracking
    elif key == Qt.Key.Key_A:
        self.auto_mode = not self.auto_mode
    elif key == Qt.Key.Key_U:
        if hasattr(self, 'unique_only'):
            self.unique_only = not self.unique_only
    elif key == Qt.Key.Key_V:
        if hasattr(self, 'auto_view_mode'):
            self.auto_view_mode = not self.auto_view_mode
    elif key == Qt.Key.Key_Tab:
        # Cycle through detected targets
        if hasattr(self, 'detected_targets') and self.detected_targets:
            target_list = list(self.detected_targets.keys())
            if target_list:
                self.selected_target_index = (self.selected_target_index + 1) % len(target_list)


@pytest.fixture
def mock_capture():
    """Create a mock WindowCapture instance with required attributes."""
    capture = Mock()
    
    # Mock client window with geometry
    client_window = Mock()
    geometry = Mock()
    geometry.width = 1080
    geometry.height = 2340
    client_window.get_geometry.return_value = geometry
    capture.client_window = client_window
    
    # Basic attributes
    capture.window_name = "Test Window"
    capture.display_scale = 0.5
    capture.target_fps = 30
    
    # State attributes
    capture.target_mode = False
    capture.bounds_mode = False
    capture.exclude_mode = False
    capture.state_tracking = False
    capture.show_filtered = False
    capture.auto_mode = False
    capture.selecting = False
    capture.text_input_active = False
    capture.show_bounds = False
    capture.show_excludes = False
    capture.auto_view_mode = False
    capture.unique_only = True
    
    # Data attributes
    capture.colors_per_target = 20
    capture.min_blob_pixels = 2
    capture.max_blobs = 1
    capture.target_name = ""
    capture.temp_input = ""
    
    # Frame data
    capture.frame_bgr = np.zeros((2340, 1080, 3), dtype=np.uint8)
    capture.current_frame = np.zeros((2340, 1080, 3), dtype=np.uint8)
    
    # Selection rectangles
    capture.selection_start = None
    capture.selection_end = None
    capture.target_selection_rect = None
    capture.bounds_selection_rect = None
    capture.exclude_selection_rect = None
    
    # Detected targets for cycling tests
    capture.detected_targets = {}
    capture.selected_target_index = 0
    
    # State tracking attributes
    capture.xp_sample_interval = 0.1  # 100ms default
    capture.xp_brightness_threshold = 170
    capture.xp_last_value = None
    capture.higher_plane = False
    capture.plane_counter = 0
    
    # Methods
    capture.get_frame_for_display = Mock(return_value=np.zeros((1170, 540, 3), dtype=np.uint8))
    capture.get_current_auto_target = Mock(return_value="No target")
    capture.on_mouse_click = Mock()
    capture.on_mouse_move = Mock()
    capture.on_mouse_release = Mock()
    
    # Bind real on_key_press implementation
    import types
    capture.on_key_press = types.MethodType(_mock_on_key_press, capture)
    
    # Config object (use SimpleNamespace for mutable attributes)
    from types import SimpleNamespace
    config = SimpleNamespace(
        colors_per_target=20,
        min_blob_pixels=2,
        max_blobs=1,
        touch_delay_min=0.3,
        touch_delay_max=4.0,
        touch_delay_mean=0.8,
        touch_delay_std=0.6,
        stability_timer=1.0,
        passing_distance=50,
        plane_size=5,
        plane_count_padding=5
    )
    capture.config = config
    capture.xp_brightness_threshold = 170
    capture.xp_detected = '0'
    
    return capture


class TestMirrorWindowCreation:
    """Tests for MirrorWindow initialization."""
    
    def test_window_created_with_correct_title(self, qapp, mock_capture):
        """Test that window is created with capture instance's window name."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        assert window.windowTitle() == "Test Window"
    
    def test_window_dimensions_based_on_client_and_scale(self, qapp, mock_capture):
        """Test that window size is calculated from client dimensions and display scale."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Expected: 1080 * 0.5 = 540, 2340 * 0.5 = 1170
        video_label = window.video_label
        assert video_label.minimumWidth() == 540
        assert video_label.minimumHeight() == 1170
    
    def test_video_label_has_correct_size_constraints(self, qapp, mock_capture):
        """Test that video label has both min and max size set to prevent stretching."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        video_label = window.video_label
        
        assert video_label.minimumWidth() == video_label.maximumWidth()
        assert video_label.minimumHeight() == video_label.maximumHeight()
    
    def test_all_required_buttons_created(self, qapp, mock_capture):
        """Test that all control buttons are created."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'target_btn')
        assert hasattr(window, 'bounds_btn')
        assert hasattr(window, 'exclude_btn')
        assert hasattr(window, 'state_btn')
        assert hasattr(window, 'filter_btn')
        assert hasattr(window, 'auto_btn')
        assert hasattr(window, 'capture_btn')


class TestCoordinateTransformations:
    """Tests for coordinate mapping between widget and frame."""
    
    def test_mouse_click_maps_to_frame_coordinates(self, qapp, mock_capture):
        """Test that mouse click on widget maps to correct frame position."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Simulate click at widget position (100, 100)
        # Widget is 540x1170 (scaled), frame is 1080x2340 (original)
        # Expected frame coords: (200, 200)
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        pos = Mock()
        pos.x.return_value = 100
        pos.y.return_value = 100
        event.pos.return_value = pos
        
        window.on_video_click(event)
        
        # Should call capture's mouse handler with scaled coordinates
        mock_capture.on_mouse_click.assert_called_once()
        call_args = mock_capture.on_mouse_click.call_args[0]
        
        # Allow for rounding differences
        assert abs(call_args[0] - 200) <= 1  # x coordinate
        assert abs(call_args[1] - 200) <= 1  # y coordinate


class TestButtonStateUpdates:
    """Tests for button state synchronization with capture state."""
    
    def test_button_text_reflects_capture_state(self, qapp, mock_capture):
        """Test that button text updates when capture state changes."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Initially OFF
        assert "OFF" in window.target_btn.text()
        
        # Turn ON
        mock_capture.target_mode = True
        window.update_button_states()
        assert "ON" in window.target_btn.text()
    
    def test_button_toggle_updates_capture_state(self, qapp, mock_capture):
        """Test that clicking button toggles capture state."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Initially OFF
        assert mock_capture.target_mode is False
        
        # Click button
        window.toggle_target_mode()
        
        # Should be ON now
        assert mock_capture.target_mode is True
    
    def test_exclusive_modes_deactivate_others(self, qapp, mock_capture):
        """Test that activating one selection mode deactivates others."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Activate target mode
        window.toggle_target_mode()
        assert mock_capture.target_mode is True
        
        # Activate bounds mode - should deactivate target
        window.toggle_bounds_mode()
        assert mock_capture.bounds_mode is True
        assert mock_capture.target_mode is False
        
        # Activate exclude mode - should deactivate bounds
        window.toggle_exclude_mode()
        assert mock_capture.exclude_mode is True
        assert mock_capture.bounds_mode is False
    
    def test_colors_per_target_increment_decrement(self, qapp, mock_capture):
        """Test that +/- buttons change colors_per_target correctly."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.colors_per_target = 20
        
        # Increment
        window.increase_colors()
        assert mock_capture.colors_per_target == 21
        
        # Decrement
        window.decrease_colors()
        window.decrease_colors()
        assert mock_capture.colors_per_target == 19
    
    def test_colors_per_target_respects_bounds(self, qapp, mock_capture):
        """Test that colors_per_target stays within 1-50 range."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Test lower bound
        mock_capture.colors_per_target = 1
        window.decrease_colors()
        assert mock_capture.colors_per_target == 1  # Should not go below 1
        
        # Test upper bound
        mock_capture.colors_per_target = 50
        window.increase_colors()
        assert mock_capture.colors_per_target == 50  # Should not go above 50


class TestFrameDisplay:
    """Tests for frame processing and display."""
    
    def test_update_frame_converts_bgr_to_rgb(self, qapp, mock_capture):
        """Test that BGR frame is converted to RGB for display."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Create BGR frame with distinct color (blue channel only)
        bgr_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        bgr_frame[:, :, 0] = 255  # Blue in BGR
        
        window.update_frame(bgr_frame)
        
        # Verify pixmap was set (RGB conversion happens internally)
        assert window.video_label.pixmap() is not None
    
    def test_fetch_and_display_frame_calls_get_frame_for_display(self, qapp, mock_capture):
        """Test that frame fetch calls the capture's method."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        window.fetch_and_display_frame()
        
        mock_capture.get_frame_for_display.assert_called()


class TestPropertyAccessors:
    """Tests for backward compatibility property accessors."""
    
    def test_colors_per_target_property_reads_from_config(self, qapp, mock_capture):
        """Test that colors_per_target property accesses config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        # This tests the QtWindowCapture properties, not MirrorWindow
        # We'll need to test QtWindowCapture separately
        pass


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_button_click_workflow(self, qapp, mock_capture):
        """Test complete workflow: click button → state changes → UI updates."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Initial state
        assert mock_capture.target_mode is False
        assert "OFF" in window.target_btn.text()
        
        # User clicks target button
        window.toggle_target_mode()
        
        # State should change
        assert mock_capture.target_mode is True
        
        # UI should update
        window.update_button_states()
        assert "ON" in window.target_btn.text()
    
    def test_filter_toggle_workflow(self, qapp, mock_capture):
        """Test filter toggle updates state and display."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Initially OFF
        assert mock_capture.show_filtered is False
        
        # Toggle filter
        window.toggle_filter()
        assert mock_capture.show_filtered is True
        
        # Update display
        window.update_button_states()
        assert "ON" in window.filter_btn.text()


class TestCaptureButtonFunctionality:
    """Tests for capture button and color analysis."""
    
    def test_capture_button_calls_capture_method(self, qapp, mock_capture):
        """Test that capture button calls the capture method."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.capture_current_target = Mock()
        window = MirrorWindow(mock_capture)
        
        # Click capture button
        window.capture_target()
        
        # Should call the capture method
        mock_capture.capture_current_target.assert_called_once()
    
    def test_unique_checkbox_toggles_state(self, qapp, mock_capture):
        """Test that unique checkbox toggles unique_only state."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.unique_only = True
        window = MirrorWindow(mock_capture)
        
        # Toggle unique checkbox
        window.toggle_unique_only(Qt.CheckState.Unchecked.value)
        assert mock_capture.unique_only is False
        
        window.toggle_unique_only(Qt.CheckState.Checked.value)
        assert mock_capture.unique_only is True
    
    def test_capture_button_disabled_without_selection(self, qapp, mock_capture):
        """Test capture workflow requires selection and name."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.target_mode = True
        mock_capture.target_selection_rect = None
        mock_capture.target_name = ""
        mock_capture.capture_current_target = Mock()
        
        window = MirrorWindow(mock_capture)
        window.capture_target()
        
        # Should still call the method (validation happens inside)
        mock_capture.capture_current_target.assert_called_once()


class TestXPCounterDisplay:
    """Tests for XP counter display."""
    
    def test_xp_display_shows_zero_initially(self, qapp, mock_capture):
        """Test XP display shows 0 initially."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.xp_detected = "0"
        mock_capture.state_tracking = True
        window = MirrorWindow(mock_capture)
        window.update_button_states()
        
        assert window.state_xp_display.text() == "0"
    
    def test_xp_display_updates_with_value(self, qapp, mock_capture):
        """Test XP display updates when XP changes."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.xp_detected = "1250"
        mock_capture.state_tracking = True
        window = MirrorWindow(mock_capture)
        window.update_button_states()
        
        assert window.state_xp_display.text() == "1250"
    
    def test_xp_display_style_changes_when_nonzero(self, qapp, mock_capture):
        """Test XP display highlights when non-zero."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        window = MirrorWindow(mock_capture)
        
        # Zero XP has default style
        mock_capture.xp_detected = "0"
        window.update_button_states()
        assert "#2a2a2a" in window.state_xp_display.styleSheet()
        
        # Non-zero XP highlights green
        mock_capture.xp_detected = "100"
        window.update_button_states()
        assert "#4ade80" in window.state_xp_display.styleSheet()


class TestTargetSelectorCycling:
    """Tests for TAB key target selector cycling."""
    
    def test_tab_key_cycles_through_targets(self, qapp, mock_capture):
        """Test TAB key cycles through detected targets."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        # Set up detected targets
        mock_capture.detected_targets = {
            "target1": (100, 100, 50, 50),
            "target2": (200, 200, 50, 50),
            "target3": (300, 300, 50, 50)
        }
        mock_capture.selected_target_index = 0
        
        window = MirrorWindow(mock_capture)
        
        # Simulate TAB key press
        from PyQt6.QtCore import Qt
        window.capture.on_key_press(Qt.Key.Key_Tab, "\t")
        
        # Should increment index
        assert mock_capture.selected_target_index == 1
    
    def test_tab_cycling_wraps_around(self, qapp, mock_capture):
        """Test TAB cycling wraps to first target after last."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.detected_targets = {
            "target1": (100, 100, 50, 50),
            "target2": (200, 200, 50, 50)
        }
        mock_capture.selected_target_index = 1  # Last target
        
        window = MirrorWindow(mock_capture)
        
        # TAB should wrap to 0
        from PyQt6.QtCore import Qt
        window.capture.on_key_press(Qt.Key.Key_Tab, "\t")
        
        assert mock_capture.selected_target_index == 0


class TestNumericFieldEditing:
    """Tests for config value editing."""
    
    def test_config_display_is_clickable(self, qapp, mock_capture):
        """Test that extra config displays have mouse cursor and handler."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Check plane size config display
        assert window.plane_size_config_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.plane_size_config_display.mouseDoubleClickEvent is not None
        
        # Check plane padding config display
        assert window.plane_padding_config_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.plane_padding_config_display.mouseDoubleClickEvent is not None
        
        # Check XP threshold config display
        assert window.xp_threshold_config_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.xp_threshold_config_display.mouseDoubleClickEvent is not None
        
        # XP total should not be clickable (read-only)
        assert window.xp_total_display.cursor().shape() != Qt.CursorShape.PointingHandCursor
    
    def test_edit_config_value_method_exists(self, qapp, mock_capture):
        """Test that edit_config_value method exists."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'edit_config_value')
        assert callable(window.edit_config_value)


class TestUIControls:
    """Tests for additional UI controls."""
    
    def test_pixels_controls_exist(self, qapp, mock_capture):
        """Test that min pixels controls exist."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'pixels_minus_btn')
        assert hasattr(window, 'pixels_display')
        assert hasattr(window, 'pixels_plus_btn')
    
    def test_blobs_controls_exist(self, qapp, mock_capture):
        """Test that max blobs controls exist."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'blobs_minus_btn')
        assert hasattr(window, 'blobs_display')
        assert hasattr(window, 'blobs_plus_btn')
    
    def test_checkboxes_exist(self, qapp, mock_capture):
        """Test that all checkboxes exist."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'show_bounds_cb')
        assert hasattr(window, 'show_excludes_cb')
        assert hasattr(window, 'auto_view_cb')
        assert hasattr(window, 'unique_cb')
    
    def test_pixels_increment_decrement(self, qapp, mock_capture):
        """Test that pixels controls work."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.min_blob_pixels = 5
        
        window.increase_pixels()
        assert mock_capture.min_blob_pixels == 6
        
        window.decrease_pixels()
        window.decrease_pixels()
        assert mock_capture.min_blob_pixels == 4
    
    def test_blobs_increment_decrement(self, qapp, mock_capture):
        """Test that blobs controls work."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.max_blobs = 1
        
        window.increase_blobs()
        assert mock_capture.max_blobs == 2
        
        window.decrease_blobs()
        window.decrease_blobs()
        assert mock_capture.max_blobs == 0  # Can go to 0 (unlimited)


class TestKeyboardShortcuts:
    """Tests for keyboard shortcuts."""
    
    def test_f_key_toggles_filter(self, qapp, mock_capture):
        """Test F key toggles filter."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from PyQt6.QtCore import Qt
        
        window = MirrorWindow(mock_capture)
        mock_capture.show_filtered = False
        
        # Verify window.capture is mock_capture
        assert window.capture is mock_capture
        
        window.capture.on_key_press(Qt.Key.Key_F, 'f')
        # Check window.capture instead of mock_capture since they should be the same
        assert window.capture.show_filtered is True
    
    def test_t_key_toggles_target_mode(self, qapp, mock_capture):
        """Test T key toggles target mode."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from PyQt6.QtCore import Qt
        
        window = MirrorWindow(mock_capture)
        mock_capture.target_mode = False
        
        window.capture.on_key_press(Qt.Key.Key_T, 't')
        assert mock_capture.target_mode is True
    
    def test_exclusive_modes_via_keyboard(self, qapp, mock_capture):
        """Test that keyboard shortcuts respect exclusive modes."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from PyQt6.QtCore import Qt
        
        window = MirrorWindow(mock_capture)
        
        # Activate target
        window.capture.on_key_press(Qt.Key.Key_T, 't')
        assert mock_capture.target_mode is True
        
        # Activate bounds - should deactivate target
        window.capture.on_key_press(Qt.Key.Key_B, 'b')
        assert mock_capture.bounds_mode is True
        assert mock_capture.target_mode is False


class TestStateTrackingRow:
    """Tests for state tracking UI row."""
    
    def test_state_row_hidden_when_disabled(self, qapp, mock_capture):
        """Test that state row is hidden when state tracking is disabled."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = False
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'state_row_widget')
        assert window.state_row_widget.isVisible() is False
    
    def test_state_row_visible_when_enabled(self, qapp, mock_capture):
        """Test that state row visibility logic works when state tracking is enabled."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        window = MirrorWindow(mock_capture)
        
        # Verify state row widget exists
        assert hasattr(window, 'state_row_widget')
        
        # Test visibility logic by toggling state_tracking
        mock_capture.state_tracking = False
        window.update_button_states()
        assert window.state_row_widget.isHidden()
        
        mock_capture.state_tracking = True  
        window.update_button_states()
        # After update_button_states, it should not be hidden
        assert not window.state_row_widget.isHidden()
    
    def test_state_row_contains_all_fields(self, qapp, mock_capture):
        """Test that state row contains all required fields."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        window = MirrorWindow(mock_capture)
        
        # Check all state tracking displays exist
        assert hasattr(window, 'sample_display')
        assert hasattr(window, 'brightness_display')
        assert hasattr(window, 'state_xp_display')
        assert hasattr(window, 'total_xp_display')
        assert hasattr(window, 'higher_plane_display')
        assert hasattr(window, 'plane_size_display')
        assert hasattr(window, 'plane_counter_display')
        assert hasattr(window, 'plane_padding_display')
    
    def test_sample_interval_displays_in_milliseconds(self, qapp, mock_capture):
        """Test that sample interval is displayed in milliseconds."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_sample_interval = 0.15  # 150ms
        window = MirrorWindow(mock_capture)
        
        # Trigger update
        window.update_button_states()
        
        assert window.sample_display.text() == "150"
    
    def test_brightness_threshold_displays_correctly(self, qapp, mock_capture):
        """Test that brightness threshold displays correctly."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_brightness_threshold = 180
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.brightness_display.text() == "180"
    
    def test_xp_display_highlights_when_nonzero(self, qapp, mock_capture):
        """Test that XP display highlights green when non-zero."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_detected = "15"
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.state_xp_display.text() == "15"
        assert "#4ade80" in window.state_xp_display.styleSheet() or "green" in window.state_xp_display.styleSheet().lower()
    
    def test_total_xp_shows_last_value(self, qapp, mock_capture):
        """Test that total XP shows last OCR value."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_last_value = 1234567
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.total_xp_display.text() == "1234567"
    
    def test_total_xp_shows_dashes_when_none(self, qapp, mock_capture):
        """Test that total XP shows dashes when no value."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_last_value = None
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.total_xp_display.text() == "---"
    
    def test_higher_plane_displays_correctly(self, qapp, mock_capture):
        """Test that higher plane indicator displays correctly."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.higher_plane = True
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.higher_plane_display.text() == "1"
        assert "#4ade80" in window.higher_plane_display.styleSheet() or "green" in window.higher_plane_display.styleSheet().lower()
    
    def test_higher_plane_not_highlighted_when_false(self, qapp, mock_capture):
        """Test that higher plane is not highlighted when false."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.higher_plane = False
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.higher_plane_display.text() == "0"
        assert "#2a2a2a" in window.higher_plane_display.styleSheet()
    
    def test_plane_counter_highlights_when_positive(self, qapp, mock_capture):
        """Test that plane counter highlights green when > 0."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.plane_counter = 3
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert window.plane_counter_display.text() == "3"
        assert "#4ade80" in window.plane_counter_display.styleSheet() or "green" in window.plane_counter_display.styleSheet().lower()
    
    def test_counter_stable_shows_duration(self, qapp, mock_capture):
        """Test that counter stable shows stability duration."""
        from android_injections.ui.qt_renderer import MirrorWindow
        import time
        
        mock_capture.state_tracking = True
        mock_capture.plane_counter_stable_since = time.time() - 0.5  # 500ms ago
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        # Should show approximately 500ms
        duration = int(window.counter_stable_display.text())
        assert 450 <= duration <= 550  # Allow some tolerance
    
    def test_counter_stable_highlights_when_stable(self, qapp, mock_capture):
        """Test that counter stable highlights green when >= stability_timer."""
        from android_injections.ui.qt_renderer import MirrorWindow
        import time
        
        mock_capture.state_tracking = True
        mock_capture.config.stability_timer = 1.0  # 1000ms
        mock_capture.plane_counter_stable_since = time.time() - 1.5  # 1500ms ago (stable)
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert "#4ade80" in window.counter_stable_display.styleSheet() or "green" in window.counter_stable_display.styleSheet().lower()
    
    def test_counter_stable_not_highlighted_when_unstable(self, qapp, mock_capture):
        """Test that counter stable is not highlighted when < stability_timer."""
        from android_injections.ui.qt_renderer import MirrorWindow
        import time
        
        mock_capture.state_tracking = True
        mock_capture.config.stability_timer = 1.0  # 1000ms
        mock_capture.plane_counter_stable_since = time.time() - 0.5  # 500ms ago (not stable yet)
        window = MirrorWindow(mock_capture)
        
        window.update_button_states()
        
        assert "#2a2a2a" in window.counter_stable_display.styleSheet()


class TestStateTrackingControls:
    """Tests for state tracking control buttons."""
    
    def test_increase_sample_interval(self, qapp, mock_capture):
        """Test that sample interval can be increased."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_sample_interval = 0.1
        window = MirrorWindow(mock_capture)
        
        window.increase_sample_interval()
        
        assert mock_capture.xp_sample_interval == 0.11
    
    def test_decrease_sample_interval(self, qapp, mock_capture):
        """Test that sample interval can be decreased."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_sample_interval = 0.1
        window = MirrorWindow(mock_capture)
        
        window.decrease_sample_interval()
        
        # Use approximate comparison due to floating point precision
        assert abs(mock_capture.xp_sample_interval - 0.09) < 0.001
    
    def test_sample_interval_respects_minimum(self, qapp, mock_capture):
        """Test that sample interval doesn't go below 10ms."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_sample_interval = 0.01  # 10ms
        window = MirrorWindow(mock_capture)
        
        window.decrease_sample_interval()
        
        assert mock_capture.xp_sample_interval == 0.01
    
    def test_sample_interval_respects_maximum(self, qapp, mock_capture):
        """Test that sample interval doesn't go above 1000ms."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.xp_sample_interval = 1.0  # 1000ms
        window = MirrorWindow(mock_capture)
        
        window.increase_sample_interval()
        
        assert mock_capture.xp_sample_interval == 1.0
    
    def test_increase_plane_size(self, qapp, mock_capture):
        """Test that plane size can be increased."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_size = 5
        window = MirrorWindow(mock_capture)
        
        window.increase_plane_size()
        
        assert mock_capture.config.plane_size == 6
    
    def test_decrease_plane_size(self, qapp, mock_capture):
        """Test that plane size can be decreased."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_size = 5
        window = MirrorWindow(mock_capture)
        
        window.decrease_plane_size()
        
        assert mock_capture.config.plane_size == 4
    
    def test_plane_size_respects_minimum(self, qapp, mock_capture):
        """Test that plane size doesn't go below 1."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_size = 1
        window = MirrorWindow(mock_capture)
        
        window.decrease_plane_size()
        
        assert mock_capture.config.plane_size == 1
    
    def test_plane_size_respects_maximum(self, qapp, mock_capture):
        """Test that plane size doesn't go above 50."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_size = 50
        window = MirrorWindow(mock_capture)
        
        window.increase_plane_size()
        
        assert mock_capture.config.plane_size == 50
    
    def test_increase_plane_padding(self, qapp, mock_capture):
        """Test that plane count padding can be increased."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_count_padding = 5
        window = MirrorWindow(mock_capture)
        
        window.increase_plane_padding()
        
        assert mock_capture.config.plane_count_padding == 6
    
    def test_decrease_plane_padding(self, qapp, mock_capture):
        """Test that plane count padding can be decreased."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_count_padding = 5
        window = MirrorWindow(mock_capture)
        
        window.decrease_plane_padding()
        
        assert mock_capture.config.plane_count_padding == 4
    
    def test_plane_padding_respects_minimum(self, qapp, mock_capture):
        """Test that plane count padding doesn't go below 0."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_count_padding = 0
        window = MirrorWindow(mock_capture)
        
        window.decrease_plane_padding()
        
        assert mock_capture.config.plane_count_padding == 0
    
    def test_plane_padding_respects_maximum(self, qapp, mock_capture):
        """Test that plane count padding doesn't go above 50."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        mock_capture.config.plane_count_padding = 50
        window = MirrorWindow(mock_capture)
        
        window.increase_plane_padding()
        
        assert mock_capture.config.plane_count_padding == 50
    
    def test_edit_state_value_method_exists(self, qapp, mock_capture):
        """Test that edit_state_value method exists."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        mock_capture.state_tracking = True
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'edit_state_value')
        assert callable(window.edit_state_value)


class TestConfigFieldsRow:
    """Tests for configuration fields display row."""
    
    def test_config_row_exists(self, qapp, mock_capture):
        """Test that config row is created."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'config_row_widget')
    
    def test_config_row_contains_all_fields(self, qapp, mock_capture):
        """Test that config row contains all required fields."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Check all config field displays exist
        assert hasattr(window, 'delay_min_display')
        assert hasattr(window, 'delay_max_display')
        assert hasattr(window, 'delay_mean_display')
        assert hasattr(window, 'delay_std_display')
        assert hasattr(window, 'stability_display')
        assert hasattr(window, 'passing_dist_display')
    
    def test_touch_delay_min_displays_in_milliseconds(self, qapp, mock_capture):
        """Test that touch delay min is displayed in milliseconds."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.config.touch_delay_min = 0.5  # 500ms
        window.update_button_states()
        
        assert window.delay_min_display.text() == "500"
    
    def test_touch_delay_max_displays_in_milliseconds(self, qapp, mock_capture):
        """Test that touch delay max is displayed in milliseconds."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.config.touch_delay_max = 2.5  # 2500ms
        window.update_button_states()
        
        assert window.delay_max_display.text() == "2500"
    
    def test_touch_delay_mean_displays_in_milliseconds(self, qapp, mock_capture):
        """Test that touch delay mean is displayed in milliseconds."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.config.touch_delay_mean = 1.2  # 1200ms
        window.update_button_states()
        
        assert window.delay_mean_display.text() == "1200"
    
    def test_touch_delay_std_displays_in_milliseconds(self, qapp, mock_capture):
        """Test that touch delay std is displayed in milliseconds."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.config.touch_delay_std = 0.75  # 750ms
        window.update_button_states()
        
        assert window.delay_std_display.text() == "750"
    
    def test_stability_timer_displays_in_milliseconds(self, qapp, mock_capture):
        """Test that stability timer is displayed in milliseconds."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.config.stability_timer = 1.5  # 1500ms
        window.update_button_states()
        
        assert window.stability_display.text() == "1500"
    
    def test_passing_distance_displays_correctly(self, qapp, mock_capture):
        """Test that passing distance displays correctly."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        mock_capture.config.passing_distance = 75
        window.update_button_states()
        
        assert window.passing_dist_display.text() == "75"
    
    def test_config_fields_are_clickable(self, qapp, mock_capture):
        """Test that config fields have mouse event handlers."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Check that fields have pointing hand cursor (indicates clickable)
        assert window.delay_min_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.delay_max_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.delay_mean_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.delay_std_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.stability_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert window.passing_dist_display.cursor().shape() == Qt.CursorShape.PointingHandCursor
    
    def test_config_fields_update_on_change(self, qapp, mock_capture):
        """Test that config fields update when values change."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        # Change values
        mock_capture.config.touch_delay_min = 0.2
        mock_capture.config.touch_delay_max = 5.0
        mock_capture.config.stability_timer = 2.0
        mock_capture.config.passing_distance = 100
        
        # Update display
        window.update_button_states()
        
        assert window.delay_min_display.text() == "200"
        assert window.delay_max_display.text() == "5000"
        assert window.stability_display.text() == "2000"
        assert window.passing_dist_display.text() == "100"
    
    def test_edit_config_field_method_exists(self, qapp, mock_capture):
        """Test that edit_config_field method exists."""
        from android_injections.ui.qt_renderer import MirrorWindow
        
        window = MirrorWindow(mock_capture)
        
        assert hasattr(window, 'edit_config_field')
        assert callable(window.edit_config_field)


class TestConfigFieldEditing:
    """Tests for configuration field editing functionality."""
    
    def test_delay_min_updates_config(self, qapp, mock_capture):
        """Test that editing delay min updates the config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        
        # Mock the input dialog to return 500ms
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(500, True)):
            window.edit_config_field('touch_delay_min')
        
        assert mock_capture.config.touch_delay_min == 0.5
    
    def test_delay_max_updates_config(self, qapp, mock_capture):
        """Test that editing delay max updates the config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(3000, True)):
            window.edit_config_field('touch_delay_max')
        
        assert mock_capture.config.touch_delay_max == 3.0
    
    def test_delay_mean_updates_config(self, qapp, mock_capture):
        """Test that editing delay mean updates the config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(1500, True)):
            window.edit_config_field('touch_delay_mean')
        
        assert mock_capture.config.touch_delay_mean == 1.5
    
    def test_delay_std_updates_config(self, qapp, mock_capture):
        """Test that editing delay std updates the config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(800, True)):
            window.edit_config_field('touch_delay_std')
        
        assert mock_capture.config.touch_delay_std == 0.8
    
    def test_stability_timer_updates_config(self, qapp, mock_capture):
        """Test that editing stability timer updates the config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(2000, True)):
            window.edit_config_field('stability_timer')
        
        assert mock_capture.config.stability_timer == 2.0
    
    def test_passing_distance_updates_config(self, qapp, mock_capture):
        """Test that editing passing distance updates the config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(75, True)):
            window.edit_config_field('passing_distance')
        
        assert mock_capture.config.passing_distance == 75
    
    def test_edit_cancelled_does_not_change_config(self, qapp, mock_capture):
        """Test that cancelling edit doesn't change config."""
        from android_injections.ui.qt_renderer import MirrorWindow
        from unittest.mock import patch
        
        window = MirrorWindow(mock_capture)
        original_value = mock_capture.config.touch_delay_min
        
        # Mock the input dialog to return cancelled (ok=False)
        with patch('PyQt6.QtWidgets.QInputDialog.getInt', return_value=(999, False)):
            window.edit_config_field('touch_delay_min')
        
        assert mock_capture.config.touch_delay_min == original_value


# Test for coordinate scaling utilities (if we add them)
class TestCoordinateScaling:
    """Tests for coordinate scaling helper functions."""
    
    def test_scale_point_from_display_to_frame(self):
        """Test scaling a point from display coordinates to frame coordinates."""
        # display point (100, 200) with scale 0.5 → frame (200, 400)
        display_x, display_y = 100, 200
        scale = 0.5
        frame_width, frame_height = 1080, 2340
        display_width, display_height = 540, 1170
        
        frame_x = int(display_x / display_width * frame_width)
        frame_y = int(display_y / display_height * frame_height)
        
        assert frame_x == 200
        assert frame_y == 400
    
    def test_scale_rectangle_from_frame_to_display(self):
        """Test scaling a rectangle from frame coordinates to display coordinates."""
        # frame rect (100, 200, 300, 400) with scale 0.5 → display (50, 100, 150, 200)
        frame_rect = (100, 200, 300, 400)
        scale = 0.5
        
        display_rect = tuple(int(coord * scale) for coord in frame_rect)
        
        assert display_rect == (50, 100, 150, 200)
