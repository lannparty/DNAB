"""Target loader - loads color targets and bounds from JSON files."""
import os
import json
import numpy as np
from .exclusion_manager import load_excluded_regions


def load_all_targets(instance):
    """Load all color targets from JSON files in the targets directory.
    
    This function:
    1. Loads color data from targets directory
    2. Loads bounds from bounds directory
    3. Ensures unique color fingerprints across targets
    4. Pre-computes color lookup table for fast matching
    5. Loads excluded regions
    
    Args:
        instance: UI instance with attributes:
            - targets_dir: Directory containing target JSON files
            - bounds_dir: Directory containing bounds JSON files
            - exclude_dir: Directory containing exclusion JSON files
            - colors_per_target: Number of colors to use for fingerprinting
            - filter_colors: Will be set to set of all colors across targets
            - color_to_target: Will be set to dict mapping color -> first target
            - target_to_colors: Will be set to dict mapping target -> set of colors
            - target_bounds: Will be set to dict mapping target -> bounds tuple
            - bounds_with_names: Will be set to list of (x1, y1, x2, y2, name) tuples
            - color_lookup: Will be set to boolean array for O(1) color lookup
            - filter_array: Will be set to numpy array of colors
    """
    all_colors = set()
    loaded_files = []
    color_to_target = {}  # Map colors to their target filename (first occurrence)
    color_to_all_targets = {}  # Map colors to list of ALL files containing them
    target_to_colors = {}  # Map target names to their color sets
    target_bounds = {}  # Map target names to their search bounds
    
    try:
        # Get all JSON files in targets directory
        json_files = [f for f in os.listdir(instance.targets_dir) if f.endswith('.json')]
        
        # Load bounds files from bounds directory
        instance.bounds_with_names = []  # List of (x1, y1, x2, y2, name) tuples
        if os.path.exists(instance.bounds_dir):
            bounds_files = [f for f in os.listdir(instance.bounds_dir) if f.endswith('.json')]
            for bounds_file in bounds_files:
                filepath = os.path.join(instance.bounds_dir, bounds_file)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        target_name = data.get('target_name')
                        bounds = data.get('bounds')
                        if target_name and bounds and len(bounds) == 4:
                            target_bounds[target_name] = tuple(bounds)
                            instance.bounds_with_names.append(tuple(bounds) + (target_name,))
                except Exception as e:
                    print(f"Error loading bounds from {bounds_file}: {e}")
        
        for filename in json_files:
            filepath = os.path.join(instance.targets_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    colors = data.get('colors', [])
                    # Remove .json extension for cleaner labels
                    target_name = filename[:-5] if filename.endswith('.json') else filename
                    
                    # Track colors for this target
                    target_colors = set()
                    
                    # Convert colors to tuples and add to set with mapping
                    # Only use the first colors_per_target colors (they're already sorted by prevalence)
                    for i, color in enumerate(colors):
                        if i >= instance.colors_per_target:
                            break
                        color_tuple = tuple(color)
                        all_colors.add(color_tuple)
                        target_colors.add(color_tuple)
                        
                        # Track first occurrence for labeling
                        if color_tuple not in color_to_target:
                            color_to_target[color_tuple] = target_name
                        
                        # Track all occurrences for duplicate detection
                        if color_tuple not in color_to_all_targets:
                            color_to_all_targets[color_tuple] = []
                        color_to_all_targets[color_tuple].append(target_name)
                    
                    target_to_colors[target_name] = target_colors
                    
                    loaded_files.append(filename)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        
        # Ensure unique color fingerprints across targets
        # Each target's N-color combination should be unique to avoid collision
        fingerprint_map = {}  # Maps frozenset of colors -> target_name
        fingerprint_adjusted = []  # Track targets that needed adjustment
        
        # First pass: record all fingerprints
        for filename in sorted(json_files):
            filepath = os.path.join(instance.targets_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    colors = data.get('colors', [])
                    target_name = filename[:-5] if filename.endswith('.json') else filename
                    
                    if target_name not in target_to_colors:
                        continue
                    
                    # Get current fingerprint
                    current_fingerprint = frozenset(target_to_colors[target_name])
                    
                    # Check for collision
                    if current_fingerprint in fingerprint_map:
                        # Collision detected! Try to find alternative N colors
                        existing_target = fingerprint_map[current_fingerprint]
                        original_count = len(current_fingerprint)
                        
                        # Try to build a unique fingerprint by going through available colors
                        available_colors = [tuple(c) for c in colors]
                        used_fingerprints = set(fingerprint_map.keys())
                        
                        # Try different combinations until we find unique one
                        found_unique = False
                        for start_idx in range(len(available_colors)):
                            if len(available_colors) - start_idx < instance.colors_per_target:
                                break
                            
                            # Build a set of N colors starting from this index
                            test_colors = set()
                            for i in range(start_idx, min(start_idx + instance.colors_per_target, len(available_colors))):
                                test_colors.add(available_colors[i])
                            
                            # Check if we have enough colors and if fingerprint is unique
                            if len(test_colors) == instance.colors_per_target:
                                test_fingerprint = frozenset(test_colors)
                                if test_fingerprint not in used_fingerprints:
                                    # Found unique fingerprint!
                                    target_to_colors[target_name] = test_colors
                                    current_fingerprint = test_fingerprint
                                    found_unique = True
                                    fingerprint_adjusted.append((target_name, existing_target, start_idx))
                                    break
                        
                        if not found_unique:
                            print(f"⚠️ Warning: Could not find unique {instance.colors_per_target}-color fingerprint for '{target_name}'")
                    
                    # Record this fingerprint
                    fingerprint_map[current_fingerprint] = target_name
                    
                    # Update all_colors to include any new colors from adjusted fingerprints
                    all_colors.update(target_to_colors[target_name])
                    
            except Exception as e:
                pass
        
        # Report fingerprint adjustments
        if fingerprint_adjusted:
            print(f"\n🔧 Adjusted {len(fingerprint_adjusted)} target(s) to ensure unique fingerprints:")
            for target_name, existing_target, start_idx in fingerprint_adjusted[:5]:
                print(f"  '{target_name}': shifted to colors [{start_idx}:{start_idx+instance.colors_per_target}] (was colliding with '{existing_target}')")
            if len(fingerprint_adjusted) > 5:
                print(f"  ... and {len(fingerprint_adjusted) - 5} more")
            print()
        
        instance.filter_colors = all_colors
        instance.color_to_target = color_to_target
        instance.target_to_colors = target_to_colors
        instance.target_bounds = target_bounds
        
        # Pre-compute filter array for fast matching
        if all_colors:
            instance.filter_array = np.array(list(all_colors), dtype=np.uint8)
            
            # Create lookup table (256x256x256 boolean array = 16MB)
            # This allows O(1) lookup instead of O(N) comparisons per pixel
            instance.color_lookup = np.zeros((256, 256, 256), dtype=bool)
            for b, g, r in all_colors:
                instance.color_lookup[b, g, r] = True
        else:
            instance.filter_array = np.array([], dtype=np.uint8)
            instance.color_lookup = None
        
        if loaded_files:
            print(f"Loaded {len(all_colors)} colors from {len(loaded_files)} target file(s): {', '.join(loaded_files)}")
        else:
            print("No target files found in targets/ directory")
    
    except Exception as e:
        print(f"Error loading targets: {e}")
        instance.filter_colors = set()
        instance.color_to_target = {}
    
    # Load excluded regions
    load_excluded_regions(instance)
