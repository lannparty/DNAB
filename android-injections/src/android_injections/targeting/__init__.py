"""Targeting module - target loading, saving, bounds management, and color analysis."""

from .target_loader import load_all_targets
from .target_saver import save_target, save_bounds
from .color_analysis import analyze_unique_colors
from .exclusion_manager import load_excluded_regions, save_excluded_region

__all__ = [
    'load_all_targets',
    'save_target',
    'save_bounds',
    'analyze_unique_colors',
    'load_excluded_regions',
    'save_excluded_region',
]
