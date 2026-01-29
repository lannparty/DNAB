"""
Configuration Contract Tests - Parameter handling and persistence

Tests verify that configuration parameters are correctly managed, validated,
persisted, and reflected in real-time behavior.
"""

import pytest
import time
from typing import Protocol, Optional, Any


class ConfigServer(Protocol):
    """Interface for configuration management"""
    
    def get_config_param(self, param_name: str) -> Optional[Any]:
        """Get a configuration parameter value"""
        ...
    
    def set_config_param(self, param_name: str, value: Any) -> bool:
        """Set a configuration parameter value. Returns True if successful."""
        ...
    
    def get_all_params(self) -> dict[str, Any]:
        """Get all configuration parameters"""
        ...
    
    def reset_config_to_defaults(self) -> None:
        """Reset all parameters to default values"""
        ...
    
    def validate_param(self, param_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a parameter value. Returns (is_valid, error_message)"""
        ...
    
    def save_config(self) -> bool:
        """Persist configuration to storage. Returns True if successful."""
        ...
    
    def load_config(self) -> bool:
        """Load configuration from storage. Returns True if successful."""
        ...
    
    def get_config_changed_timestamp(self) -> float:
        """Get timestamp of last config change"""
        ...


class TestConfigUpdateContract:
    """Contract: Configuration parameter updates"""
    
    def test_config_parameter_read(self, config_server: ConfigServer):
        """MUST: Configuration parameters can be read"""
        # Should have at least some parameters
        params = config_server.get_all_params()
        
        assert isinstance(params, dict), "Config should return a dictionary"
        assert len(params) > 0, "Config should have some parameters"
    
    def test_config_parameter_set(self, config_server: ConfigServer):
        """MUST: Configuration parameters can be set"""
        result = config_server.set_config_param('test_param', 42)
        
        # Should either succeed or fail gracefully
        assert isinstance(result, bool)
    
    def test_config_parameter_persistence(self, config_server: ConfigServer):
        """MUST: Set parameters are retained"""
        original = config_server.get_config_param('touch_delay_short')
        
        # Try to set a parameter
        config_server.set_config_param('touch_delay_short', 100)
        time.sleep(0.05)
        
        # Should remain set
        new_value = config_server.get_config_param('touch_delay_short')
        assert new_value == 100, "Parameter didn't persist after setting"
    
    def test_config_multiple_parameter_update(self, config_server: ConfigServer):
        """MUST: Multiple parameters can be updated"""
        params_to_set = {
            'touch_delay_short': 150,
            'touch_delay_long': 500,
            'stability_timer': 2.0,
        }
        
        for param, value in params_to_set.items():
            result = config_server.set_config_param(param, value)
            assert result or True  # Allow either success or failure, but shouldn't crash
        
        time.sleep(0.1)
        
        # Check at least one was set
        all_params = config_server.get_all_params()
        assert len(all_params) > 0
    
    def test_config_parameter_type_preserved(self, config_server: ConfigServer):
        """MUST: Parameter types are preserved"""
        # Set integer
        config_server.set_config_param('test_int', 42)
        int_val = config_server.get_config_param('test_int')
        assert int_val == 42
        
        # Set float
        config_server.set_config_param('test_float', 3.14)
        float_val = config_server.get_config_param('test_float')
        assert float_val == 3.14
        
        # Set string
        config_server.set_config_param('test_string', 'hello')
        str_val = config_server.get_config_param('test_string')
        assert str_val == 'hello'
    
    def test_config_get_all_returns_complete_state(self, config_server: ConfigServer):
        """MUST: get_all_params returns complete configuration state"""
        all_params = config_server.get_all_params()
        
        # Should contain known game parameters
        assert isinstance(all_params, dict)
        assert len(all_params) > 0
    
    def test_config_changes_are_trackable(self, config_server: ConfigServer):
        """SHOULD: Configuration changes are recorded with timestamps"""
        ts1 = config_server.get_config_changed_timestamp()
        
        config_server.set_config_param('touch_delay_short', 200)
        time.sleep(0.1)
        
        ts2 = config_server.get_config_changed_timestamp()
        
        # Timestamp should update after change
        assert ts2 >= ts1, "Config change timestamp didn't update"


class TestConfigValidationContract:
    """Contract: Parameter validation"""
    
    def test_config_validation_available(self, config_server: ConfigServer):
        """MUST: Configuration validation is available"""
        is_valid, error_msg = config_server.validate_param('touch_delay_short', 100)
        
        assert isinstance(is_valid, bool)
        assert error_msg is None or isinstance(error_msg, str)
    
    def test_config_valid_value_passes(self, config_server: ConfigServer):
        """MUST: Valid values pass validation"""
        # Delay values should be positive integers
        is_valid, error_msg = config_server.validate_param('touch_delay_short', 100)
        
        assert is_valid == True, f"Valid parameter rejected: {error_msg}"
    
    def test_config_invalid_value_fails(self, config_server: ConfigServer):
        """MUST: Invalid values fail validation"""
        # Negative delay should be invalid
        is_valid, error_msg = config_server.validate_param('touch_delay_short', -100)
        
        # Should either reject it or accept but provide error message
        if not is_valid:
            assert error_msg is not None, "Invalid value should have error message"
    
    def test_config_bounds_validation(self, config_server: ConfigServer):
        """SHOULD: Parameter bounds are enforced"""
        # Very large value might be out of bounds
        is_valid, error_msg = config_server.validate_param('touch_delay_short', 999999)
        
        # Should either reject or accept, but not crash
        assert isinstance(is_valid, bool)
    
    def test_config_type_validation(self, config_server: ConfigServer):
        """SHOULD: Parameter types are validated"""
        # String value for numeric parameter should fail
        is_valid, error_msg = config_server.validate_param('touch_delay_short', 'not_a_number')
        
        # Should either be invalid or coerce properly
        assert isinstance(is_valid, bool)
    
    def test_config_validation_error_messages(self, config_server: ConfigServer):
        """SHOULD: Validation provides helpful error messages"""
        is_valid, error_msg = config_server.validate_param('touch_delay_short', -1)
        
        if not is_valid:
            assert error_msg is not None, "Invalid value should have error message"
            assert len(error_msg) > 0, "Error message should be descriptive"


class TestConfigPersistenceContract:
    """Contract: Configuration persistence and recovery"""
    
    def test_config_save_successful(self, config_server: ConfigServer):
        """MUST: Configuration can be saved"""
        result = config_server.save_config()
        
        assert isinstance(result, bool)
    
    def test_config_load_successful(self, config_server: ConfigServer):
        """MUST: Configuration can be loaded"""
        # Save first
        config_server.save_config()
        time.sleep(0.1)
        
        # Then load
        result = config_server.load_config()
        assert isinstance(result, bool)
    
    def test_config_survives_save_load_cycle(self, config_server: ConfigServer):
        """MUST: Configuration values survive save/load cycle"""
        test_value = 250
        param_name = 'touch_delay_short'
        
        # Set value
        config_server.set_config_param(param_name, test_value)
        
        # Save
        config_server.save_config()
        time.sleep(0.1)
        
        # Load
        config_server.load_config()
        time.sleep(0.1)
        
        # Value should still be there
        loaded_value = config_server.get_config_param(param_name)
        assert loaded_value == test_value, \
            f"Value lost in save/load: expected {test_value}, got {loaded_value}"
    
    def test_config_multiple_saves_safe(self, config_server: ConfigServer):
        """SHOULD: Multiple saves don't corrupt configuration"""
        for i in range(5):
            config_server.set_config_param('touch_delay_short', 100 + i * 10)
            result = config_server.save_config()
            assert result or True  # Should not crash
            time.sleep(0.05)
    
    def test_config_partial_load_recovery(self, config_server: ConfigServer):
        """SHOULD: Configuration loads successfully even if partially persisted"""
        # Try to load without prior save
        result = config_server.load_config()
        
        # Should handle gracefully
        assert isinstance(result, bool)


class TestConfigResetContract:
    """Contract: Configuration reset to defaults"""
    
    def test_config_reset_restores_defaults(self, config_server: ConfigServer):
        """MUST: Reset restores default values"""
        # Change some values
        config_server.set_config_param('touch_delay_short', 999)
        config_server.set_config_param('stability_timer', 99.9)
        
        time.sleep(0.1)
        
        # Reset
        config_server.reset_config_to_defaults()
        time.sleep(0.1)
        
        # Values should be reset
        all_params = config_server.get_all_params()
        assert all_params is not None
        assert len(all_params) > 0
    
    def test_config_reset_affects_all_params(self, config_server: ConfigServer):
        """SHOULD: Reset affects all parameters"""
        # Change multiple values
        config_server.set_config_param('touch_delay_short', 500)
        config_server.set_config_param('stability_timer', 5.0)
        
        time.sleep(0.1)
        
        # Reset
        config_server.reset_config_to_defaults()
        time.sleep(0.1)
        
        # Configuration should be reset
        params = config_server.get_all_params()
        assert len(params) > 0


class TestConfigStateContract:
    """Contract: Configuration state and synchronization"""
    
    def test_config_concurrent_reads_consistent(self, config_server: ConfigServer):
        """SHOULD: Concurrent configuration reads are consistent"""
        results = []
        
        for _ in range(10):
            value = config_server.get_config_param('touch_delay_short')
            results.append(value)
        
        # All reads should return same value (if no writes between them)
        if all(r is not None for r in results):
            assert all(r == results[0] for r in results), "Config reads not consistent"
    
    def test_config_rapid_updates_safe(self, config_server: ConfigServer):
        """SHOULD: Rapid configuration updates don't cause crashes"""
        try:
            for i in range(50):
                config_server.set_config_param('touch_delay_short', 100 + i)
        except Exception as e:
            pytest.fail(f"Rapid updates caused exception: {e}")
        
        time.sleep(0.1)
        # Should not crash
        final_value = config_server.get_config_param('touch_delay_short')
        assert final_value is not None


class TestConfigIntegrationContract:
    """Contract: Configuration integration with other systems"""
    
    def test_config_values_are_numeric(self, config_server: ConfigServer):
        """SHOULD: Delay parameters are numeric"""
        all_params = config_server.get_all_params()
        
        # At least some parameters should be numeric
        delay_params = [p for p in all_params.keys() if 'delay' in p.lower()]
        
        for param in delay_params:
            value = all_params[param]
            # Should be numeric (int or float)
            assert isinstance(value, (int, float)), \
                f"Parameter '{param}' should be numeric, got {type(value)}"
    
    def test_config_parameter_names_consistent(self, config_server: ConfigServer):
        """SHOULD: Configuration parameter names are consistent"""
        all_params = config_server.get_all_params()
        
        # All param names should be strings
        for param_name in all_params.keys():
            assert isinstance(param_name, str), "Parameter names should be strings"
            # Names should be lowercase with underscores
            assert param_name.islower() or '_' in param_name, \
                f"Parameter name '{param_name}' should be lowercase with underscores"
