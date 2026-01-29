"""Automation module - auto-touch logic, target selection, and delay management."""

from android_injections.automation.auto_target import get_current_auto_target
from android_injections.automation.delay_manager import (
    calculate_next_delay,
    is_delay_ready,
    execute_auto_touch
)
from android_injections.automation.state_manager import reset_auto_state

__all__ = [
    'get_current_auto_target',
    'calculate_next_delay',
    'is_delay_ready',
    'execute_auto_touch',
    'reset_auto_state',
]
