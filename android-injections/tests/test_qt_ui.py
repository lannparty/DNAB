"""
Qt UI interaction tests for MirrorWindow and related widgets.
Covers construction, signals, user events, and state changes.
"""
import pytest

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# --- Dummy classes for UI testing ---




# Dummy classes for UI testing
class DummyClientWindow:
    def get_geometry(self):
        class DummyGeom:
            width = 1080
            height = 2340
        return DummyGeom()

class DummyConfig:
    colors_per_target = 20
    min_blob_pixels = 2
    max_blobs = 1
    stability_timer = 1.0
    xp_brightness_threshold = 128
    xp_sample_interval = 1.0
    touch_delay_min = 0.3
    touch_delay_max = 5.0
    touch_delay_mean = 1.0
    touch_delay_std = 0.5
    passing_distance = 50
    pass_pause_duration = 1.0
    auto_target_timeout = 10.0
    plane_size = 3
    minimap_counter_padding = 2


# Clean DummyCapture definition
class DummyCapture:
    target_name = ""
    max_blobs = 0
    window_name = "Test Window"
    display_scale = 0.5
    client_window = DummyClientWindow()
    config = DummyConfig()
    target_mode = False
    bounds_mode = False
    exclude_mode = False
    filter_mode = False
    state_tracking = False
    xp_tracking = False
    auto_mode = False
    unique_only = False
    show_bounds = False
    show_excludes = False
    show_filtered = False
    colors_per_target = 0
    min_blob_pixels = 0
    text_input_active = False
    minimap_counter_padding = 2

    def get_frame_for_display(self):
        import numpy as np
        return np.zeros((100, 100, 3), dtype=np.uint8)

@pytest.fixture(scope="module")
def app():
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

@pytest.mark.usefixtures("app")
def test_mirrorwindow_construction(qtbot):
    from android_injections.ui.qt_renderer import MirrorWindow
    # Use a mock or minimal WindowCapture instance if needed
    class DummyGeom:
        width = 1080
        height = 2340
    class DummyClientWindow:
        def get_geometry(self):
            return DummyGeom()
    class DummyConfig:
        colors_per_target = 20
        min_blob_pixels = 2
        max_blobs = 1
        stability_timer = 1.0
        xp_brightness_threshold = 128
        xp_sample_interval = 1.0
        touch_delay_min = 0.3
        touch_delay_max = 5.0
        touch_delay_mean = 1.0
        touch_delay_std = 0.5
        passing_distance = 50
        pass_pause_duration = 1.0
        auto_target_timeout = 10.0
        class DummyGeom:
            width = 1080
            height = 2340

        class DummyClientWindow:
            def get_geometry(self):
                return DummyGeom()

        class DummyConfig:
            colors_per_target = 20
            min_blob_pixels = 2
            max_blobs = 1
            stability_timer = 1.0
            xp_brightness_threshold = 128
            xp_sample_interval = 1.0
            touch_delay_min = 0.3
            touch_delay_max = 5.0
            touch_delay_mean = 1.0
            touch_delay_std = 0.5
            passing_distance = 50
            pass_pause_duration = 1.0
            auto_target_timeout = 10.0
            plane_size = 3
            minimap_counter_padding = 2

        class DummyCapture:
            window_name = "Test Window"
            from android_injections.ui.qt_renderer import MirrorWindow
            window = MirrorWindow(DummyCapture())
            qtbot.addWidget(window)
            assert window.isVisible() is False  # Not shown by default
            assert window.windowTitle() != ""
            minimap_counter_padding = 2

        class DummyCapture:
            window_name = "Test Window"
            from android_injections.ui.qt_renderer import MirrorWindow
            window = MirrorWindow(DummyCapture())
            qtbot.addWidget(window)
            # Find and click the target mode button if it exists
            if hasattr(window, 'toggle_target_mode'):
                window.toggle_target_mode()
                # You may want to assert state changes here
            show_bounds = False
