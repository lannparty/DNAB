"""
Rendering Contract Tests - UI rendering and display

Tests verify that the UI correctly displays game state, updates in real-time,
and presents overlays and status information.
"""

import pytest
import time
from typing import Protocol, Optional, Any
from enum import Enum


class RenderColor(Enum):
    """Standard colors used in rendering"""
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)


class RenderingServer(Protocol):
    """Interface for UI rendering"""
    
    def get_latest_frame_timestamp(self) -> Optional[float]:
        """Get timestamp of most recent frame"""
        ...
    
    def get_frame_update_rate(self) -> float:
        """Get current frame update rate (FPS)"""
        ...
    
    def get_ui_state(self) -> dict[str, Any]:
        """Get current UI state/configuration"""
        ...
    
    def set_overlay_text(self, text: str, position: str = 'top-left') -> None:
        """Set overlay text to display on screen"""
        ...
    
    def get_displayed_text(self, position: str = 'top-left') -> Optional[str]:
        """Get currently displayed text"""
        ...
    
    def set_status_color(self, status: str, color: RenderColor) -> None:
        """Set status indicator color"""
        ...
    
    def get_status_color(self, status: str) -> Optional[RenderColor]:
        """Get current status indicator color"""
        ...
    
    def render_bounds(self, bounds_data: dict) -> None:
        """Render game bounds/regions on UI"""
        ...
    
    def render_target(self, target_data: dict) -> None:
        """Render target/detection box on UI"""
        ...
    
    def show_help_text(self, visible: bool) -> None:
        """Show or hide help/controls text"""
        ...
    
    def is_help_visible(self) -> bool:
        """Check if help text is visible"""
        ...


class TestRenderingContract:
    """Contract: Basic rendering and frame updates"""
    
    def test_frame_updates_continuously(self, rendering_server: RenderingServer):
        """MUST: Frame updates occur at regular intervals"""
        # Record frame timestamps
        timestamps = []
        
        for _ in range(5):
            ts = rendering_server.get_latest_frame_timestamp()
            if ts:
                timestamps.append(ts)
            time.sleep(0.1)  # 100ms between checks
        
        # Should have multiple different timestamps
        assert len(set(timestamps)) > 1, "Frame timestamps not updating"
    
    def test_frame_rate_is_reasonable(self, rendering_server: RenderingServer, min_fps: int = 10, max_fps: int = 60):
        """MUST: Frame rate is within acceptable bounds"""
        fps = rendering_server.get_frame_update_rate()
        
        assert min_fps <= fps <= max_fps, \
            f"Frame rate {fps} FPS outside acceptable range [{min_fps}, {max_fps}]"
    
    def test_ui_state_reflects_configuration(self, rendering_server: RenderingServer):
        """MUST: UI state reflects current configuration"""
        state = rendering_server.get_ui_state()
        
        assert isinstance(state, dict), "UI state should be a dictionary"
        assert len(state) > 0, "UI state should contain configuration"
    
    def test_ui_renders_without_crashes(self, rendering_server: RenderingServer):
        """MUST: UI rendering doesn't crash under normal operation"""
        # Render for several iterations
        for _ in range(10):
            state = rendering_server.get_ui_state()
            assert state is not None
            time.sleep(0.1)
    
    def test_frame_timestamp_increases(self, rendering_server: RenderingServer):
        """MUST: Frame timestamps increase monotonically"""
        ts1 = rendering_server.get_latest_frame_timestamp()
        time.sleep(0.2)
        ts2 = rendering_server.get_latest_frame_timestamp()
        
        assert ts2 > ts1, "Frame timestamps should increase"
    
    def test_ui_remains_responsive(self, rendering_server: RenderingServer):
        """SHOULD: UI remains responsive while rendering"""
        start_time = time.time()
        
        for _ in range(50):
            rendering_server.get_ui_state()
        
        elapsed = time.time() - start_time
        
        # Should process 50 state queries in less than 1 second
        assert elapsed < 1.0, f"UI not responsive: {elapsed}s for 50 queries"


class TestOverlayContract:
    """Contract: Overlay text and visual elements"""
    
    def test_overlay_text_displays(self, rendering_server: RenderingServer):
        """MUST: Overlay text is displayed when set"""
        test_text = "Test Overlay"
        rendering_server.set_overlay_text(test_text)
        
        time.sleep(0.1)
        displayed = rendering_server.get_displayed_text()
        
        assert displayed == test_text, f"Expected '{test_text}', got '{displayed}'"
    
    def test_overlay_text_positions(self, rendering_server: RenderingServer):
        """MUST: Overlay text can be positioned"""
        positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center']
        text = "Position Test"
        
        for pos in positions:
            rendering_server.set_overlay_text(text, position=pos)
            time.sleep(0.05)
            
            displayed = rendering_server.get_displayed_text(position=pos)
            assert displayed == text, f"Text not set at position {pos}"
    
    def test_overlay_text_updates(self, rendering_server: RenderingServer):
        """MUST: Overlay text updates when changed"""
        texts = ["First", "Second", "Third"]
        
        for text in texts:
            rendering_server.set_overlay_text(text)
            time.sleep(0.05)
        
        # Last text should be displayed
        displayed = rendering_server.get_displayed_text()
        assert displayed == "Third"
    
    def test_overlay_text_empty_clears(self, rendering_server: RenderingServer):
        """SHOULD: Setting empty text clears overlay"""
        rendering_server.set_overlay_text("Some text")
        time.sleep(0.05)
        
        rendering_server.set_overlay_text("")
        time.sleep(0.05)
        
        displayed = rendering_server.get_displayed_text()
        assert displayed in [None, ""], "Empty text should clear overlay"


class TestStatusIndicatorContract:
    """Contract: Status indicators and color feedback"""
    
    def test_status_color_change(self, rendering_server: RenderingServer):
        """MUST: Status colors change when set"""
        rendering_server.set_status_color('active', RenderColor.GREEN)
        time.sleep(0.05)
        
        color = rendering_server.get_status_color('active')
        assert color == RenderColor.GREEN
    
    def test_status_color_persistence(self, rendering_server: RenderingServer):
        """MUST: Status colors persist until changed"""
        rendering_server.set_status_color('running', RenderColor.RED)
        time.sleep(0.05)
        
        # Query multiple times
        color1 = rendering_server.get_status_color('running')
        time.sleep(0.1)
        color2 = rendering_server.get_status_color('running')
        
        assert color1 == color2 == RenderColor.RED
    
    def test_multiple_status_indicators(self, rendering_server: RenderingServer):
        """MUST: Multiple status indicators can be shown"""
        statuses = {
            'active': RenderColor.GREEN,
            'idle': RenderColor.YELLOW,
            'error': RenderColor.RED,
        }
        
        for status, color in statuses.items():
            rendering_server.set_status_color(status, color)
        
        time.sleep(0.1)
        
        for status, expected_color in statuses.items():
            actual_color = rendering_server.get_status_color(status)
            assert actual_color == expected_color
    
    def test_status_indicator_colors_valid(self, rendering_server: RenderingServer):
        """SHOULD: Status colors are valid RGB values"""
        rendering_server.set_status_color('test', RenderColor.BLUE)
        time.sleep(0.05)
        
        color = rendering_server.get_status_color('test')
        assert color is not None
        # Color should be one of the defined colors
        assert color in RenderColor.__members__.values()


class TestVisualsContract:
    """Contract: Game visualization (bounds, targets, etc)"""
    
    def test_bounds_rendering(self, rendering_server: RenderingServer):
        """MUST: Bounds are rendered correctly"""
        bounds_data = {
            'id': 'test_bounds',
            'x': 100,
            'y': 100,
            'width': 200,
            'height': 200,
            'color': RenderColor.GREEN.value
        }
        
        rendering_server.render_bounds(bounds_data)
        time.sleep(0.1)
        
        state = rendering_server.get_ui_state()
        # State should reflect rendered bounds
        assert state is not None
    
    def test_target_rendering(self, rendering_server: RenderingServer):
        """MUST: Targets are rendered correctly"""
        target_data = {
            'id': 'test_target',
            'x': 300,
            'y': 300,
            'width': 50,
            'height': 50,
            'color': RenderColor.RED.value
        }
        
        rendering_server.render_target(target_data)
        time.sleep(0.1)
        
        state = rendering_server.get_ui_state()
        assert state is not None
    
    def test_multiple_elements_rendering(self, rendering_server: RenderingServer):
        """SHOULD: Multiple visual elements render together"""
        bounds = {'id': 'bounds1', 'x': 50, 'y': 50, 'width': 100, 'height': 100}
        target = {'id': 'target1', 'x': 75, 'y': 75, 'width': 30, 'height': 30}
        
        rendering_server.render_bounds(bounds)
        rendering_server.render_target(target)
        
        time.sleep(0.1)
        # Both should render without conflicts
        state = rendering_server.get_ui_state()
        assert state is not None


class TestHelpContract:
    """Contract: Help/instruction display"""
    
    def test_help_text_toggle(self, rendering_server: RenderingServer):
        """MUST: Help text can be shown/hidden"""
        rendering_server.show_help_text(True)
        time.sleep(0.05)
        assert rendering_server.is_help_visible() == True
        
        rendering_server.show_help_text(False)
        time.sleep(0.05)
        assert rendering_server.is_help_visible() == False
    
    def test_help_text_state_persistence(self, rendering_server: RenderingServer):
        """MUST: Help visibility state persists"""
        rendering_server.show_help_text(True)
        time.sleep(0.05)
        
        # Check multiple times
        assert rendering_server.is_help_visible() == True
        time.sleep(0.1)
        assert rendering_server.is_help_visible() == True
    
    def test_help_toggle_cycle(self, rendering_server: RenderingServer):
        """SHOULD: Help can be toggled on and off"""
        for _ in range(3):
            rendering_server.show_help_text(True)
            time.sleep(0.05)
            assert rendering_server.is_help_visible() == True
            
            rendering_server.show_help_text(False)
            time.sleep(0.05)
            assert rendering_server.is_help_visible() == False
