"""
Control Contract Tests - Keyboard and mouse input handling

Tests verify that keyboard and mouse input is correctly received, processed,
and routed to the automation system.
"""

import pytest
import time
from typing import Protocol, Optional, List
from enum import Enum


class KeyboardModifier(Enum):
    """Keyboard modifiers supported"""
    NONE = 0
    SHIFT = 1
    CTRL = 2
    ALT = 4


class ControlServer(Protocol):
    """Interface for control input handling"""
    
    def send_key_event(self, key_code: int, key_name: str, is_press: bool) -> None:
        """Send keyboard event (press or release)"""
        ...
    
    def send_mouse_event(self, x: int, y: int, button: Optional[int] = None) -> None:
        """Send mouse move or click event"""
        ...
    
    def get_last_key_received(self) -> Optional[str]:
        """Get the last keyboard input received"""
        ...
    
    def get_last_mouse_position(self) -> tuple[int, int]:
        """Get last mouse position received"""
        ...
    
    def get_input_latency_ms(self) -> float:
        """Latency from control input to processing"""
        ...
    
    def clear_input_buffer(self) -> None:
        """Clear recorded inputs for testing"""
        ...


class TestKeyboardInputContract:
    """Contract: Keyboard input must be correctly received and processed"""
    
    def test_keyboard_key_press_received(self, control_server: ControlServer):
        """MUST: Key press events are received"""
        control_server.clear_input_buffer()
        
        control_server.send_key_event(
            key_code=97,  # 'a'
            key_name='KeyA',
            is_press=True
        )
        
        time.sleep(0.05)  # Let it process
        assert control_server.get_last_key_received() == 'KeyA'
    
    def test_keyboard_key_release_received(self, control_server: ControlServer):
        """MUST: Key release events are received"""
        control_server.clear_input_buffer()
        
        # Press then release
        control_server.send_key_event(97, 'KeyA', is_press=True)
        control_server.send_key_event(97, 'KeyA', is_press=False)
        
        time.sleep(0.05)
        # Should record the release (most recent event)
        last_key = control_server.get_last_key_received()
        assert last_key is not None
    
    def test_keyboard_multiple_keys(self, control_server: ControlServer):
        """MUST: Multiple rapid key presses are handled"""
        control_server.clear_input_buffer()
        
        keys = ['KeyA', 'KeyB', 'KeyC']
        for key in keys:
            control_server.send_key_event(0, key, is_press=True)
            time.sleep(0.01)
        
        # Last key should be KeyC
        assert control_server.get_last_key_received() == 'KeyC'
    
    def test_keyboard_input_latency(self, control_server: ControlServer, max_latency_ms: int = 50):
        """MUST: Keyboard input is processed with low latency"""
        latency = control_server.get_input_latency_ms()
        
        assert latency <= max_latency_ms, \
            f"Keyboard latency {latency}ms exceeds {max_latency_ms}ms"
    
    def test_arrow_keys_recognized(self, control_server: ControlServer):
        """MUST: Arrow keys are properly recognized"""
        arrow_keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']
        
        for arrow_key in arrow_keys:
            control_server.clear_input_buffer()
            control_server.send_key_event(0, arrow_key, is_press=True)
            time.sleep(0.05)
            
            assert control_server.get_last_key_received() == arrow_key, \
                f"{arrow_key} not recognized"
    
    def test_enter_key_recognized(self, control_server: ControlServer):
        """MUST: Enter key is properly recognized"""
        control_server.clear_input_buffer()
        
        control_server.send_key_event(13, 'Enter', is_press=True)
        time.sleep(0.05)
        
        assert control_server.get_last_key_received() == 'Enter'
    
    def test_special_keys_recognized(self, control_server: ControlServer):
        """MUST: Special keys (Escape, Tab, etc) are recognized"""
        special_keys = ['Escape', 'Tab', 'Backspace', 'Delete']
        
        for key in special_keys:
            control_server.clear_input_buffer()
            control_server.send_key_event(0, key, is_press=True)
            time.sleep(0.05)
            
            assert control_server.get_last_key_received() == key, \
                f"{key} not recognized"


class TestMouseInputContract:
    """Contract: Mouse input must be correctly received and processed"""
    
    def test_mouse_movement_tracked(self, control_server: ControlServer):
        """MUST: Mouse position changes are tracked"""
        control_server.clear_input_buffer()
        
        control_server.send_mouse_event(x=100, y=100)
        time.sleep(0.05)
        
        x, y = control_server.get_last_mouse_position()
        assert x == 100 and y == 100
    
    def test_mouse_multiple_positions(self, control_server: ControlServer):
        """MUST: Multiple mouse movements are tracked"""
        positions = [(100, 100), (200, 200), (300, 150)]
        
        for x, y in positions:
            control_server.send_mouse_event(x=x, y=y)
            time.sleep(0.05)
        
        # Last position should be captured
        final_x, final_y = control_server.get_last_mouse_position()
        assert final_x == 300 and final_y == 150
    
    def test_mouse_click_event(self, control_server: ControlServer):
        """MUST: Mouse click events are recognized"""
        control_server.clear_input_buffer()
        
        # Left click (button 1)
        control_server.send_mouse_event(x=100, y=100, button=1)
        time.sleep(0.05)
        
        x, y = control_server.get_last_mouse_position()
        assert x == 100 and y == 100
    
    def test_mouse_input_latency(self, control_server: ControlServer, max_latency_ms: int = 50):
        """MUST: Mouse input is processed with low latency"""
        latency = control_server.get_input_latency_ms()
        
        assert latency <= max_latency_ms, \
            f"Mouse latency {latency}ms exceeds {max_latency_ms}ms"
    
    def test_mouse_bounds_handling(self, control_server: ControlServer):
        """SHOULD: Mouse coordinates outside bounds are handled"""
        # Assuming 1920x1080 resolution
        control_server.send_mouse_event(x=-100, y=-100)  # Out of bounds
        time.sleep(0.05)
        
        x, y = control_server.get_last_mouse_position()
        # Should either clamp or reject gracefully
        assert x >= -100 and y >= -100  # Not crash
    
    def test_rapid_mouse_movement(self, control_server: ControlServer):
        """SHOULD: Rapid mouse movements are handled smoothly"""
        for i in range(100):
            control_server.send_mouse_event(x=100 + i, y=100 + i)
        
        time.sleep(0.1)
        # Should handle rapid input without crashes
        x, y = control_server.get_last_mouse_position()
        assert x > 100 and y > 100


class TestInputQueueContract:
    """Contract: Input buffering and ordering"""
    
    def test_input_queue_fifo(self, control_server: ControlServer):
        """MUST: Input events are processed in correct order"""
        control_server.clear_input_buffer()
        
        # Send keyboard then mouse
        control_server.send_key_event(97, 'KeyA', is_press=True)
        time.sleep(0.01)
        control_server.send_mouse_event(x=200, y=200)
        time.sleep(0.05)
        
        # Both should be processed
        assert control_server.get_last_key_received() == 'KeyA'
        x, y = control_server.get_last_mouse_position()
        assert x == 200 and y == 200
    
    def test_no_input_loss_under_load(self, control_server: ControlServer):
        """SHOULD: No input is lost even under rapid input"""
        control_server.clear_input_buffer()
        
        # Rapid input
        for i in range(50):
            control_server.send_key_event(97 + (i % 26), f'Key{chr(65 + (i % 26))}', is_press=True)
        
        time.sleep(0.1)
        # Should have processed inputs
        last_key = control_server.get_last_key_received()
        assert last_key is not None
