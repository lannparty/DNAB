"""Target saver - saves target colors and bounds to JSON files."""
import os
import json
from .target_loader import load_all_targets


def save_target(instance):
    """Save colors sorted by prevalence to a target file.
    
    Args:
        instance: UI instance with attributes:
            - target_selection_rect: ((x1, y1), (x2, y2)) selection
            - target_name: Name of target to save
            - unique_only: If True, save only unique colors; else all colors
            - unique_colors_by_count: List of (color, count) for unique mode
            - all_box_colors_by_count: List of (color, count) for all mode
            - targets_dir: Directory to save target files to
            - colors_per_target: Number of colors to use for fingerprinting
    """
    if not instance.target_selection_rect:
        print("Please select an area first (use Target mode)")
        return
    
    if not instance.target_name:
        print("Please enter a name first")
        return
    
    # Choose which colors to save based on unique_only flag
    if instance.unique_only:
        if not hasattr(instance, 'unique_colors_by_count') or not instance.unique_colors_by_count:
            print("No unique colors to save")
            return
        source_colors = instance.unique_colors_by_count
        mode_text = "unique"
    else:
        if not hasattr(instance, 'all_box_colors_by_count') or not instance.all_box_colors_by_count:
            print("No colors to save")
            return
        source_colors = instance.all_box_colors_by_count
        mode_text = "all"
    
    # Save all colors (duplicates across targets are now allowed)
    selected_colors = [(color, count) for color, count in source_colors]
    
    if not selected_colors:
        print("No colors to save")
        return
    

    # Determine if this is an internal target
    internal_prefixes = ("minimap", "xp", "hit", "miss")
    filename = f"{instance.target_name}.json"
    if instance.target_name.startswith(internal_prefixes) and hasattr(instance, 'internal_targets_dir'):
        filepath = os.path.join(instance.internal_targets_dir, filename)
    else:
        filepath = os.path.join(instance.targets_dir, filename)

    # Load existing colors if file exists
    existing_colors = []
    existing_color_counts = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for color in data.get("colors", []):
                    color_tuple = tuple(color)
                    existing_colors.append(color_tuple)
                    existing_color_counts[color_tuple] = existing_color_counts.get(color_tuple, 0) + 1
        except Exception as e:
            print(f"Warning: Could not load existing target file for merging: {e}")

    # Merge new and existing colors, summing counts for duplicates
    merged_color_counts = {}
    for color, count in selected_colors:
        merged_color_counts[tuple(color)] = merged_color_counts.get(tuple(color), 0) + count
    for color in existing_colors:
        if color not in merged_color_counts:
            merged_color_counts[color] = 1  # Default count if not present in new selection

    # Sort by count descending, then by color value for stability
    merged_colors_sorted = sorted(merged_color_counts.items(), key=lambda x: (-x[1], x[0]))

    # Convert to list format for JSON
    colors_list = [[int(c) for c in color] for color, _ in merged_colors_sorted]
    total_pixels = sum(count for _, count in merged_colors_sorted)

    data = {
        "name": instance.target_name,
        "colors": colors_list,
        "color_count": len(colors_list),
        "pixel_count": total_pixels
    }

    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved target '{instance.target_name}' with {len(colors_list)} merged {mode_text} colors ({total_pixels} total pixels) to {filepath}")
        for i, (color, count) in enumerate(merged_colors_sorted[:10]):  # Show first 10
            print(f"  Color {i+1}: BGR{color} ({count} pixels)")
        if len(merged_colors_sorted) > 10:
            print(f"  ... and {len(merged_colors_sorted) - 10} more")
        # Reload all targets to include this new one
        load_all_targets(instance)
    except Exception as e:
        print(f"Error saving target: {e}")


def save_bounds(instance):
    """Save the current selection as bounds for the target.
    
    Args:
        instance: UI instance with attributes:
            - bounds_selection_rect: ((x1, y1), (x2, y2)) selection
            - target_name: Name of target to save bounds for
            - display_scale: Scale factor for display vs. original frame
            - bounds_dir: Directory to save bounds files to
    """
    if not instance.bounds_selection_rect:
        print("Please select an area first (use Bounds mode)")
        return
    
    if not instance.target_name:
        print("Please enter a name first")
        return
    
    x1, y1 = instance.bounds_selection_rect[0]
    x2, y2 = instance.bounds_selection_rect[1]
    
    # Normalize coordinates
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)
    
    # Coordinates are already in frame space - no scaling needed (consistent with target selection)
    
    # Create bounds filename
    filename = f"{instance.target_name}.json"
    internal_prefixes = ("minimap", "xp", "hit", "miss")
    if instance.target_name.startswith(internal_prefixes) and hasattr(instance, 'internal_bounds_dir'):
        filepath = os.path.join(instance.internal_bounds_dir, filename)
    else:
        filepath = os.path.join(instance.bounds_dir, filename)
    
    # Save bounds to file
    data = {
        "target_name": instance.target_name,
        "bounds": [x_min, y_min, x_max, y_max]
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved bounds for '{instance.target_name}': ({x_min}, {y_min}) to ({x_max}, {y_max})")
        # Reload all targets to include new bounds
        load_all_targets(instance)
    except Exception as e:
        print(f"Error saving bounds: {e}")
