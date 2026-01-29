"""Exclusion manager - loads and saves excluded regions."""
import os
import json


def load_excluded_regions(instance):
    """Load excluded regions from all files in exclude subdirectory.
    
    Args:
        instance: UI instance with attributes:
            - exclude_dir: Directory containing exclusion JSON files
            - excluded_regions: Will be populated with list of (x1, y1, x2, y2) tuples
            - excluded_regions_with_names: Will be populated with (x1, y1, x2, y2, name) tuples
    """
    instance.excluded_regions = []
    instance.excluded_regions_with_names = []  # List of (x1, y1, x2, y2, name) tuples
    
    if not os.path.exists(instance.exclude_dir):
        return
    
    try:
        # Get all JSON files in exclude directory
        exclude_files = [f for f in os.listdir(instance.exclude_dir) if f.endswith('.json')]
        
        total_regions = 0
        for filename in exclude_files:
            filepath = os.path.join(instance.exclude_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    name = data.get('name', filename[:-5])  # Use name from file or filename without .json
                    regions = data.get('regions', [])
                    # Convert to tuples and add to list
                    for r in regions:
                        instance.excluded_regions.append(tuple(r))
                        instance.excluded_regions_with_names.append(tuple(r) + (name,))
                    total_regions += len(regions)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        
        if total_regions > 0:
            print(f"Loaded {total_regions} excluded region(s) from {len(exclude_files)} file(s)")
    except Exception as e:
        print(f"Error loading exclusion files: {e}")
        instance.excluded_regions = []
        instance.excluded_regions_with_names = []


def save_excluded_region(instance):
    """Save the current selection as an excluded region to named exclusion file.
    
    Args:
        instance: UI instance with attributes:
            - selection_start: (x, y) tuple for selection start
            - selection_end: (x, y) tuple for selection end
            - target_name: Name for the exclusion file
            - display_scale: Scale factor for display vs. original frame
            - exclude_dir: Directory to save exclusion files to
    """
    if not instance.selection_start or not instance.selection_end:
        print("Please select an area first (use Exclude mode)")
        return
    
    if not instance.target_name:
        print("Please enter a name for the exclusion")
        return
    
    x1, y1 = instance.selection_start
    x2, y2 = instance.selection_end
    
    # Normalize coordinates
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)
    
    # Scale back to original coordinates if display is scaled
    if instance.display_scale != 1.0:
        scale_factor = 1.0 / instance.display_scale
        x_min = int(x_min * scale_factor)
        x_max = int(x_max * scale_factor)
        y_min = int(y_min * scale_factor)
        y_max = int(y_max * scale_factor)
    
    # Load existing exclusion file if it exists
    exclude_file = os.path.join(instance.exclude_dir, f"{instance.target_name}.json")
    excluded_regions = []
    if os.path.exists(exclude_file):
        try:
            with open(exclude_file, 'r') as f:
                data = json.load(f)
                excluded_regions = data.get('regions', [])
        except Exception as e:
            print(f"Error loading exclusion file: {e}")
    
    # Add new region
    excluded_regions.append([x_min, y_min, x_max, y_max])
    
    # Save back to file
    try:
        with open(exclude_file, 'w') as f:
            json.dump({
                'name': instance.target_name,
                'regions': excluded_regions
            }, f, indent=2)
        print(f"Added excluded region to '{instance.target_name}': ({x_min}, {y_min}) to ({x_max}, {y_max})")
        print(f"Total regions in '{instance.target_name}': {len(excluded_regions)}")
        # Reload excluded regions
        load_excluded_regions(instance)
    except Exception as e:
        print(f"Error saving exclusion file: {e}")
