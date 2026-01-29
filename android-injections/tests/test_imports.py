"""
Test that all imports work correctly with the new src/ structure.

This ensures the package reorganization doesn't break any dependencies.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestImports:
    """Test that all modules can be imported correctly."""
    
    def test_import_game_config(self):
        """Test importing GameConfig."""
        from android_injections.config.game_config import GameConfig
        assert GameConfig is not None
    
    def test_import_ui_modules(self):
        """Test importing UI modules."""
        from android_injections.ui.keyboard_handler import process_keyboard_event
        from android_injections.ui.mouse_handler import create_mouse_callback
        from android_injections.ui.ui_renderer import render_frame
        from android_injections.ui.ui_state import create_ui_state
        
        assert process_keyboard_event is not None
        assert create_mouse_callback is not None
        assert render_frame is not None
        assert create_ui_state is not None
    
    def test_import_vision_modules(self):
        """Test importing vision modules."""
        from android_injections.vision.color_filter import filter_unique_colors
        from android_injections.vision.state_eval import evaluate_state_fields
        
        assert filter_unique_colors is not None
        assert evaluate_state_fields is not None
    
    def test_import_targeting_modules(self):
        """Test importing targeting modules."""
        from android_injections.targeting.target_loader import load_all_targets
        from android_injections.targeting.target_saver import save_target, save_bounds
        from android_injections.targeting.color_analysis import analyze_unique_colors
        from android_injections.targeting.exclusion_manager import load_excluded_regions
        
        assert load_all_targets is not None
        assert save_target is not None
        assert save_bounds is not None
        assert analyze_unique_colors is not None
        assert load_excluded_regions is not None
    
    def test_import_automation_modules(self):
        """Test importing automation modules."""
        from android_injections.automation.auto_target import get_current_auto_target
        from android_injections.automation.delay_manager import calculate_next_delay
        from android_injections.automation.state_manager import reset_auto_state
        
        assert get_current_auto_target is not None
        assert calculate_next_delay is not None
        assert reset_auto_state is not None
    
    def test_import_main(self):
        """Test importing main module."""
        from android_injections.main import WindowCapture
        assert WindowCapture is not None
    
    def test_import_package(self):
        """Test importing from package root."""
        import android_injections
        assert hasattr(android_injections, 'WindowCapture')


class TestModuleStructure:
    """Test that modules have expected structure."""
    
    def test_config_module_exports(self):
        """Test that config module exports expected items."""
        from android_injections import config
        
        assert hasattr(config, 'GameConfig')
        assert hasattr(config, 'create_game_config')
    
    def test_automation_module_exports(self):
        """Test that automation module exports expected items."""
        from android_injections import automation
        
        expected_items = [
            'get_current_auto_target',
            'calculate_next_delay',
            'is_delay_ready',
            'execute_auto_touch',
            'reset_auto_state',
        ]
        
        for item in expected_items:
            assert hasattr(automation, item), f"Missing {item} in automation module"


class TestCircularImports:
    """Test that there are no circular import issues."""
    
    def test_no_circular_imports_main(self):
        """Test that main can be imported without circular import errors."""
        try:
            from android_injections.main import WindowCapture
            # If we get here, no circular import occurred
            assert True
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
            # Other import errors are acceptable (e.g., missing optional deps)
    
    def test_no_circular_imports_config(self):
        """Test that config has no circular imports."""
        try:
            from android_injections.config.game_config import GameConfig
            assert True
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")


class TestPackageInitialization:
    """Test package initialization."""
    
    def test_package_has_version(self):
        """Test that package has version info."""
        import android_injections
        assert hasattr(android_injections, '__version__')
    
    def test_package_has_author(self):
        """Test that package has author info."""
        import android_injections
        assert hasattr(android_injections, '__author__')
    
    def test_package_all_exports(self):
        """Test that package __all__ is defined."""
        import android_injections
        assert hasattr(android_injections, '__all__')
        assert 'WindowCapture' in android_injections.__all__


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
