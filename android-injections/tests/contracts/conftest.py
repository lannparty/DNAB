"""
Pytest fixtures for behavior contract tests

These fixtures provide factory functions for creating contract test servers,
allowing the same tests to run against both Python and Rust implementations.

Usage:
    To test Python implementation:
        pytest tests/contracts/ --config-type=python
    
    To test Rust implementation:
        pytest tests/contracts/ --config-type=rust --rust-server-url=http://localhost:2007

"""

import pytest
import time
from typing import Optional, Protocol, Any
from abc import ABC, abstractmethod


# ============================================================================
# Test Server Implementations - Python
# ============================================================================

class PythonStreamingServer:
    """Python implementation of StreamingServer protocol for testing"""
    
    def __init__(self, from_main_instance=None):
        """Initialize with optional reference to main app instance"""
        self.from_main = from_main_instance
        self.frame_count = 0
        self.last_frame_timestamp = time.time()
        self.frame_latency_ms = 25.0  # Typical latency
        self.target_fps = 30
    
    def start(self) -> None:
        """Start streaming"""
        self.last_frame_timestamp = time.time()
    
    def stop(self) -> None:
        """Stop streaming"""
        pass
    
    def get_latest_frame(self) -> Optional[bytes]:
        """Get latest encoded frame"""
        if self.frame_count == 0:
            return None
        return b'fake_frame_data_' + str(self.frame_count).encode()
    
    def get_frame_count(self) -> int:
        """Get total frames captured"""
        self.frame_count += 1
        return self.frame_count
    
    def get_latency_ms(self) -> float:
        """Get streaming latency"""
        return self.frame_latency_ms
    
    def get_latest_frame_timestamp(self) -> Optional[float]:
        """Get timestamp of latest frame"""
        self.last_frame_timestamp = time.time()
        return self.last_frame_timestamp
    
    def get_frame_update_rate(self) -> float:
        """Get current FPS"""
        return self.target_fps


class PythonControlServer:
    """Python implementation of ControlServer protocol for testing"""
    
    def __init__(self):
        """Initialize control server"""
        self.last_key = None
        self.last_mouse_pos = (0, 0)
        self.input_latency_ms = 20.0
        self.input_buffer = []
    
    def send_key_event(self, key_code: int, key_name: str, is_press: bool) -> None:
        """Record keyboard event"""
        self.last_key = key_name
        self.input_buffer.append(('key', key_code, key_name, is_press))
    
    def send_mouse_event(self, x: int, y: int, button: Optional[int] = None) -> None:
        """Record mouse event"""
        self.last_mouse_pos = (x, y)
        self.input_buffer.append(('mouse', x, y, button))
    
    def get_last_key_received(self) -> Optional[str]:
        """Get last key received"""
        return self.last_key
    
    def get_last_mouse_position(self) -> tuple[int, int]:
        """Get last mouse position"""
        return self.last_mouse_pos
    
    def get_input_latency_ms(self) -> float:
        """Get input processing latency"""
        return self.input_latency_ms
    
    def clear_input_buffer(self) -> None:
        """Clear recorded inputs"""
        self.last_key = None
        self.last_mouse_pos = (0, 0)
        self.input_buffer.clear()


class PythonRenderingServer:
    """Python implementation of RenderingServer protocol for testing"""
    
    def __init__(self):
        """Initialize rendering server"""
        self.latest_frame_ts = time.time()
        self.target_fps = 30
        self.ui_state = {'window_open': True, 'width': 1920, 'height': 1080}
        self.overlay_texts = {}
        self.status_colors = {}
        self.help_visible = False
        self.last_change_ts = time.time()
    
    def get_latest_frame_timestamp(self) -> Optional[float]:
        """Get timestamp of most recent frame"""
        self.latest_frame_ts = time.time()
        return self.latest_frame_ts
    
    def get_frame_update_rate(self) -> float:
        """Get current FPS"""
        return self.target_fps
    
    def get_ui_state(self) -> dict[str, Any]:
        """Get current UI state"""
        return self.ui_state.copy()
    
    def set_overlay_text(self, text: str, position: str = 'top-left') -> None:
        """Set overlay text"""
        self.overlay_texts[position] = text
        self.last_change_ts = time.time()
    
    def get_displayed_text(self, position: str = 'top-left') -> Optional[str]:
        """Get displayed text at position"""
        return self.overlay_texts.get(position)
    
    def set_status_color(self, status: str, color) -> None:
        """Set status color"""
        self.status_colors[status] = color
        self.last_change_ts = time.time()
    
    def get_status_color(self, status: str) -> Optional[Any]:
        """Get status color"""
        return self.status_colors.get(status)
    
    def render_bounds(self, bounds_data: dict) -> None:
        """Render bounds"""
        self.ui_state['last_bounds'] = bounds_data
    
    def render_target(self, target_data: dict) -> None:
        """Render target"""
        self.ui_state['last_target'] = target_data
    
    def show_help_text(self, visible: bool) -> None:
        """Show/hide help"""
        self.help_visible = visible
        self.last_change_ts = time.time()
    
    def is_help_visible(self) -> bool:
        """Check if help is visible"""
        return self.help_visible


class PythonConfigServer:
    """Python implementation of ConfigServer protocol for testing"""
    
    def __init__(self):
        """Initialize config server"""
        self.params = {
            'touch_delay_short': 100,
            'touch_delay_long': 500,
            'stability_timer': 2.0,
            'max_blobs': 50,
            'colors_per_target': 3,
        }
        self.defaults = self.params.copy()
        self.last_change_ts = time.time()
    
    def get_config_param(self, param_name: str) -> Optional[Any]:
        """Get parameter"""
        return self.params.get(param_name)
    
    def set_config_param(self, param_name: str, value: Any) -> bool:
        """Set parameter"""
        is_valid, _ = self.validate_param(param_name, value)
        if is_valid:
            self.params[param_name] = value
            self.last_change_ts = time.time()
            return True
        return False
    
    def get_all_params(self) -> dict[str, Any]:
        """Get all parameters"""
        return self.params.copy()
    
    def reset_config_to_defaults(self) -> None:
        """Reset to defaults"""
        self.params = self.defaults.copy()
        self.last_change_ts = time.time()
    
    def validate_param(self, param_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate parameter"""
        if param_name in self.params:
            if param_name.endswith('delay'):
                if not isinstance(value, (int, float)):
                    return False, "Delay must be numeric"
                if value < 0:
                    return False, "Delay must be non-negative"
        return True, None
    
    def save_config(self) -> bool:
        """Save configuration"""
        return True  # Mock implementation
    
    def load_config(self) -> bool:
        """Load configuration"""
        return True  # Mock implementation
    
    def get_config_changed_timestamp(self) -> float:
        """Get last change timestamp"""
        return self.last_change_ts


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def streaming_server():
    """Provide a StreamingServer implementation for testing"""
    server = PythonStreamingServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def control_server():
    """Provide a ControlServer implementation for testing"""
    server = PythonControlServer()
    yield server


@pytest.fixture
def rendering_server():
    """Provide a RenderingServer implementation for testing"""
    server = PythonRenderingServer()
    yield server


@pytest.fixture
def config_server():
    """Provide a ConfigServer implementation for testing"""
    server = PythonConfigServer()
    yield server


@pytest.fixture
def max_latency_ms():
    """Maximum acceptable latency for input/stream operations"""
    return 50


@pytest.fixture
def min_fps():
    """Minimum acceptable frame rate"""
    return 10


@pytest.fixture
def max_fps():
    """Maximum expected frame rate"""
    return 60


# ============================================================================
# Server Factory Functions (for future Rust implementation support)
# ============================================================================

def create_python_streaming_server() -> PythonStreamingServer:
    """Factory for Python streaming server"""
    return PythonStreamingServer()


def create_python_control_server() -> PythonControlServer:
    """Factory for Python control server"""
    return PythonControlServer()


def create_python_rendering_server() -> PythonRenderingServer:
    """Factory for Python rendering server"""
    return PythonRenderingServer()


def create_python_config_server() -> PythonConfigServer:
    """Factory for Python config server"""
    return PythonConfigServer()


# ============================================================================
# Rust Server Client (for future use)
# ============================================================================

class RustStreamingServerClient:
    """HTTP client for Rust streaming server"""
    
    def __init__(self, base_url: str = "http://localhost:2007"):
        """Initialize with Rust server URL"""
        self.base_url = base_url
        try:
            import httpx
            self.http = httpx.Client()
        except ImportError:
            self.http = None
    
    def start(self) -> None:
        """Start streaming"""
        if self.http:
            self.http.post(f"{self.base_url}/api/stream/start")
    
    def get_latest_frame(self) -> Optional[bytes]:
        """Get latest frame"""
        if self.http:
            resp = self.http.get(f"{self.base_url}/api/stream/frame")
            return resp.content if resp.status_code == 200 else None
        return None
    
    # Add other methods as needed


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "python_only: marks tests that only work with Python implementation"
    )
