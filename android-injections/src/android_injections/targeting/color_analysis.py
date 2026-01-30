"""Color analysis for identifying unique colors in selected regions."""
import numpy as np


def analyze_unique_colors(instance):
    """Find RGB colors that appear in the selection box but nowhere else.
    
    This function analyzes a selected region and identifies colors that are unique to
    that region. If the selection is within a defined bound, it compares against that
    bound only (useful for minimap selections). Otherwise compares against whole window.
    
    Args:
        instance: UI instance with attributes:
            - current_frame: Input image (H, W, 3) in BGR
            - target_selection_rect: ((x1, y1), (x2, y2)) selection coordinates
            - display_scale: Scale factor for display vs. original frame
            - bounds_with_names: List of (x1, y1, x2, y2, name) bound tuples
            - unique_colors: Will be populated with set of unique colors
            - unique_colors_by_count: Will be populated with sorted (color, count) tuples
            - all_box_colors_by_count: Will be populated with all colors in box
            - most_common_unique_color: Will be set to most prevalent unique color
            - most_common_count: Will be set to count of most common unique color
    """
    if instance.current_frame is None or instance.target_selection_rect is None:
        return
    
    x1, y1 = instance.target_selection_rect[0]
    x2, y2 = instance.target_selection_rect[1]
    
    print(f"[DEBUG] Raw selection: ({x1}, {y1}) to ({x2}, {y2})")
    
    # Normalize coordinates
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)
    
    print(f"[DEBUG] After normalize: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    
    if x_min == x_max or y_min == y_max:
        return
    
    # Mouse coordinates are captured directly from the display frame,
    # which is the same as current_frame (no scaling applied in PyQt mode)
    # So coordinates are already in frame space - no conversion needed
    
    h, w = instance.current_frame.shape[:2]
    print(f"[DEBUG] Frame dimensions: {w}x{h}")
    x_min, x_max = max(0, x_min), min(w, x_max)
    y_min, y_max = max(0, y_min), min(h, y_max)
    
    # Debug selection coordinates
    print(f"[DEBUG] Final coords (after clipping): ({x_min}, {y_min}) to ({x_max}, {y_max})")
    print(f"[DEBUG] Selection dimensions: {x_max - x_min} x {y_max - y_min}")
    
    # Check if selection is within any bound (bounds are in frame coordinates)
    containing_bound = None
    if hasattr(instance, 'bounds_with_names') and instance.bounds_with_names:
        print(f"[DEBUG] Checking {len(instance.bounds_with_names)} bounds (in frame coordinates):")
        for bound in instance.bounds_with_names:
            if len(bound) == 5:
                bx1, by1, bx2, by2, name = bound
                print(f"[DEBUG]   Bound '{name}': ({bx1}, {by1}) to ({bx2}, {by2})")
                print(f"[DEBUG]     x check: {bx1} <= {x_min} and {x_max} <= {bx2} = {bx1 <= x_min and x_max <= bx2}")
                print(f"[DEBUG]     y check: {by1} <= {y_min} and {y_max} <= {by2} = {by1 <= y_min and y_max <= by2}")
                # Check if selection is fully contained within this bound
                if bx1 <= x_min and x_max <= bx2 and by1 <= y_min and y_max <= by2:
                    containing_bound = (bx1, by1, bx2, by2, name)
                    print(f"✓ Selection within bound '{name}' - comparing uniqueness against bound only")
                    break
    else:
        if not hasattr(instance, 'bounds_with_names'):
            print("[DEBUG] No bounds_with_names attribute!")
        elif not instance.bounds_with_names:
            print("[DEBUG] bounds_with_names is empty!")
    
    # Get colors in the box
    box_region = instance.current_frame[y_min:y_max, x_min:x_max]
    box_colors = set()
    box_color_counts = {}  # Track occurrence count of each color
    
    # Collect colors from box
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            pixel = tuple(instance.current_frame[y, x])
            box_colors.add(pixel)
            # Count occurrences
            if pixel not in box_color_counts:
                box_color_counts[pixel] = 0
            box_color_counts[pixel] += 1
    
    # Get colors outside the box (or outside the containing bound if selection is within one)
    outside_colors = set()
    
    if containing_bound:
        # Compare against bound region only
        bx1, by1, bx2, by2, name = containing_bound
        # Top region within bound
        if y_min > by1:
            top_region = instance.current_frame[by1:y_min, bx1:bx2]
            for row in top_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
        # Bottom region within bound
        if y_max < by2:
            bottom_region = instance.current_frame[y_max:by2, bx1:bx2]
            for row in bottom_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
        # Left region within bound
        if x_min > bx1:
            left_region = instance.current_frame[y_min:y_max, bx1:x_min]
            for row in left_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
        # Right region within bound
        if x_max < bx2:
            right_region = instance.current_frame[y_min:y_max, x_max:bx2]
            for row in right_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
    else:
        # Compare against entire window (original behavior)
        # Top region (full width, everything above box)
        if y_min > 0:
            top_region = instance.current_frame[0:y_min, :]
            for row in top_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
        # Bottom region (full width, everything below box)
        if y_max < h:
            bottom_region = instance.current_frame[y_max:h, :]
            for row in bottom_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
        # Left region (box height only, to avoid double-counting corners)
        if x_min > 0:
            left_region = instance.current_frame[y_min:y_max, 0:x_min]
            for row in left_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
        # Right region (box height only, to avoid double-counting corners)
        if x_max < w:
            right_region = instance.current_frame[y_min:y_max, x_max:w]
            for row in right_region:
                for pixel in row:
                    outside_colors.add(tuple(pixel))
    
    # Find unique colors (in box but not outside)
    instance.unique_colors = box_colors - outside_colors
    
    # Store all box colors sorted by prevalence (for non-unique mode)
    instance.all_box_colors_by_count = [(color, box_color_counts.get(color, 0)) for color in box_colors]
    instance.all_box_colors_by_count.sort(key=lambda x: x[1], reverse=True)
    
    # Sort unique colors by prevalence (count)
    instance.unique_colors_by_count = []
    if instance.unique_colors:
        # Create list of (color, count) tuples and sort by count descending
        color_count_pairs = [(color, box_color_counts.get(color, 0)) for color in instance.unique_colors]
        color_count_pairs.sort(key=lambda x: x[1], reverse=True)
        instance.unique_colors_by_count = color_count_pairs
        
        # Keep most common for backward compatibility
        instance.most_common_unique_color = color_count_pairs[0][0]
        instance.most_common_count = color_count_pairs[0][1]
    else:
        instance.most_common_unique_color = None
        instance.most_common_count = 0
    
    print(f"\n=== Color Analysis for region ({x_min},{y_min}) to ({x_max},{y_max}) ===")
    print(f"Total colors in box: {len(box_colors)}")
    print(f"Total colors outside box: {len(outside_colors)}")
    print(f"Unique colors (only in box): {len(instance.unique_colors)}")
    
    if instance.most_common_unique_color:
        print(f"\nMost prevalent unique color: BGR{instance.most_common_unique_color} ({instance.most_common_count} pixels)")
    elif instance.unique_colors:
        print(f"\nUnique BGR colors (appear only in selected region):")
        for i, color in enumerate(sorted(instance.unique_colors)[:50]):  # Limit to first 50
            print(f"  BGR{color}")
        if len(instance.unique_colors) > 50:
            print(f"  ... and {len(instance.unique_colors) - 50} more")
    else:
        print("No unique colors found - all colors in box also appear outside.")
