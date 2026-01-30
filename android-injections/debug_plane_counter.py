#!/usr/bin/env python3
"""Debug script to check if plane counter detection is working"""
import sys
import os

# Set script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'src'))

from android_injections.targeting.target_loader import load_all_targets

class MockInstance:
    def __init__(self):
        self.targets_dir = os.path.join(script_dir, 'data', 'targets')
        self.bounds_dir = os.path.join(script_dir, 'data', 'bounds')
        self.exclude_dir = os.path.join(script_dir, 'data', 'exclude')
        self.colors_per_target = 20
        self.minimap_counter_padding = 5

instance = MockInstance()
load_all_targets(instance)

print("="*60)
print("LOADED TARGETS:")
print("="*60)
if hasattr(instance, 'target_to_colors'):
    for target_name, colors in instance.target_to_colors.items():
        print(f"  {target_name}: {len(colors)} colors")
        if target_name == 'minimap_counter':
            print(f"    First 5 colors: {list(colors)[:5]}")
else:
    print("  NO target_to_colors attribute!")

print("\n" + "="*60)
print("LOADED BOUNDS:")
print("="*60)
if hasattr(instance, 'bounds_with_names'):
    for bound in instance.bounds_with_names:
        if len(bound) == 5:
            x1, y1, x2, y2, name = bound
            print(f"  {name}: ({x1}, {y1}, {x2}, {y2})")
else:
    print("  NO bounds_with_names attribute!")

print("\n" + "="*60)
print("CHECKING PLANE COUNTER REQUIREMENTS:")
print("="*60)
has_target = hasattr(instance, 'target_to_colors') and 'minimap_counter' in instance.target_to_colors
has_bounds = hasattr(instance, 'bounds_with_names')
minimap_bound_exists = False
if has_bounds:
    for bound in instance.bounds_with_names:
        if len(bound) == 5 and bound[4] == 'minimap':
            minimap_bound_exists = True
            break

print(f"  Has target_to_colors: {hasattr(instance, 'target_to_colors')}")
print(f"  Has 'minimap_counter' in target_to_colors: {has_target}")
print(f"  Has bounds_with_names: {has_bounds}")
print(f"  Has 'minimap' bound: {minimap_bound_exists}")
print(f"  minimap_counter_padding: {instance.minimap_counter_padding}")

if has_target and minimap_bound_exists:
    print("\n✅ All requirements met for plane counter detection!")
else:
    print("\n❌ Missing requirements for plane counter detection")
    if not has_target:
        print("  - Missing minimap_counter target")
    if not minimap_bound_exists:
        print("  - Missing minimap bound")
