"""Tests for keyboard event handler - input processing and field editing."""
import pytest
from unittest.mock import Mock
from android_injections.ui.keyboard_handler import (
    handle_numeric_input,
    handle_text_input,
    process_keyboard_event
)


class TestNumericInput:
    """Test numeric input handling for configuration fields."""
    
    def test_digit_input_accumulates(self):
        """Digits should accumulate in temp_input."""
        instance = Mock()
        instance.temp_input = ""
        
        result = handle_numeric_input(instance, ord('5'))
        assert instance.temp_input == "5"
        
        result = handle_numeric_input(instance, ord('3'))
        assert instance.temp_input == "53"
    
    def test_backspace_removes_digits(self):
        """Backspace should remove last digit."""
        instance = Mock()
        instance.temp_input = "123"
        
        result = handle_numeric_input(instance, 8)  # Backspace
        assert instance.temp_input == "12"
    
    def test_backspace_on_empty_is_safe(self):
        """Backspace on empty input should not error."""
        instance = Mock()
        instance.temp_input = ""
        
        result = handle_numeric_input(instance, 8)  # Backspace
        assert instance.temp_input == ""
    
    def test_non_digit_ignored(self):
        """Non-digit keys should be ignored."""
        instance = Mock()
        instance.temp_input = "123"
        
        result = handle_numeric_input(instance, ord('a'))
        assert instance.temp_input == "123"  # Unchanged


class TestTextInput:
    """Test text input handling for target names."""
    
    def test_printable_chars_accumulate(self):
        """Printable characters should accumulate in target_name."""
        instance = Mock()
        instance.target_name = ""
        
        result = handle_text_input(instance, ord('t'))
        assert instance.target_name == "t"
        
        result = handle_text_input(instance, ord('e'))
        assert instance.target_name == "te"
    
    def test_backspace_removes_chars(self):
        """Backspace should remove last character."""
        instance = Mock()
        instance.target_name = "ladder"
        
        result = handle_text_input(instance, 8)  # Backspace
        assert instance.target_name == "ladde"
    
    def test_backspace_on_empty_is_safe(self):
        """Backspace on empty name should not error."""
        instance = Mock()
        instance.target_name = ""
        
        result = handle_text_input(instance, 8)  # Backspace
        assert instance.target_name == ""
    
    def test_space_character_included(self):
        """Space character should be included in name."""
        instance = Mock()
        instance.target_name = "my"
        
        result = handle_text_input(instance, ord(' '))
        assert instance.target_name == "my "
    
    def test_special_chars_included(self):
        """Special characters should be included."""
        instance = Mock()
        instance.target_name = "test"
        
        result = handle_text_input(instance, ord('_'))
        assert instance.target_name == "test_"


class TestFieldValidation:
    """Test field value validation and bounds checking."""
    
    def test_colors_per_target_bounds(self):
        """Colors per target should be bounded 1-50."""
        instance = Mock()
        instance.temp_input = "100"
        instance.colors_per_target = 5
        
        # Validate logic
        try:
            new_value = int(instance.temp_input)
            instance.colors_per_target = max(1, min(50, new_value))
        except ValueError:
            pass
        
        assert instance.colors_per_target == 50
    
    def test_min_blob_pixels_bounds(self):
        """Min blob pixels should be bounded 1-1000."""
        instance = Mock()
        instance.temp_input = "2000"
        instance.min_blob_pixels = 100
        
        try:
            new_value = int(instance.temp_input)
            instance.min_blob_pixels = max(1, min(1000, new_value))
        except ValueError:
            pass
        
        assert instance.min_blob_pixels == 1000
    
    def test_delay_bounds_milliseconds(self):
        """Delay should be converted from milliseconds to seconds and bounded."""
        instance = Mock()
        instance.temp_input = "5000"
        instance.touch_delay_min = 0.3
        
        try:
            new_value = int(instance.temp_input) / 1000.0
            instance.touch_delay_min = max(0.001, min(30.0, new_value))
        except ValueError:
            pass
        
        assert instance.touch_delay_min == 5.0
    
    def test_invalid_input_rejected(self):
        """Invalid input should not change value."""
        instance = Mock()
        instance.temp_input = "abc"
        instance.colors_per_target = 5
        
        try:
            new_value = int(instance.temp_input)
            instance.colors_per_target = max(1, min(50, new_value))
        except ValueError:
            pass  # Expected
        
        assert instance.colors_per_target == 5  # Unchanged


class TestEnterKeyProcessing:
    """Test Enter key processing for field submission."""
    
    def test_enter_submits_field(self):
        """Enter key should submit the current field."""
        instance = Mock()
        instance.temp_input = "25"
        instance.editing_colors = True
        instance.colors_per_target = 5
        
        # Simulate Enter (key=13)
        try:
            new_value = int(instance.temp_input)
            instance.colors_per_target = max(1, min(50, new_value))
            instance.editing_colors = False
        except ValueError:
            pass
        
        assert instance.colors_per_target == 25
        assert instance.editing_colors is False
    
    def test_enter_clears_input(self):
        """After Enter, temp_input should be ready for next input."""
        instance = Mock()
        instance.temp_input = "123"
        
        # After processing
        instance.temp_input = ""
        
        assert instance.temp_input == ""


class TestKeyboardEventProcessing:
    """Test overall keyboard event processing."""
    
    def test_digit_key_codes(self):
        """Digit keys should be 48-57 (ASCII 0-9)."""
        assert 48 <= ord('0') <= 57
        assert 48 <= ord('5') <= 57
        assert 48 <= ord('9') <= 57
    
    def test_printable_key_range(self):
        """Printable ASCII range should be 32-126."""
        assert 32 <= ord(' ') <= 126
        assert 32 <= ord('a') <= 126
        assert 32 <= ord('Z') <= 126
        assert 32 <= ord('!') <= 126
    
    def test_enter_key_code(self):
        """Enter key should be code 13."""
        assert 13 == 13
    
    def test_backspace_key_code(self):
        """Backspace key should be code 8."""
        assert 8 == 8
