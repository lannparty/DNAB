"""Color filtering and blob detection for target identification."""
import time
import numpy as np
import cv2


def create_color_lookup(colors):
    """Create an efficient lookup table for color matching.
    
    Args:
        colors: Iterable of (B, G, R) tuples
        
    Returns:
        Boolean numpy array of shape (256, 256, 256) where lookup[b, g, r] is True
        if (b, g, r) is in colors
    """
    lookup = np.zeros((256, 256, 256), dtype=bool)
    for b_val, g_val, r_val in colors:
        lookup[b_val, g_val, r_val] = True
    return lookup


def assign_blob_to_target(blob_colors, target_to_colors):
    """Assign a blob to the best matching target based on color intersection.
    
    Args:
        blob_colors: Set of (B, G, R) tuples found in the blob
        target_to_colors: Dict mapping target names to sets of (B, G, R) tuples
        
    Returns:
        Best matching target name, or None if no match found
    """
    best_target = None
    best_match_count = 0
    
    for target_name, target_colors in target_to_colors.items():
        match_count = len(blob_colors & target_colors)
        if match_count > best_match_count:
            best_target = target_name
            best_match_count = match_count
    
    return best_target


def filter_unique_colors(instance, frame, apply_scale=1.0):
    """Create a filtered image showing only colors from loaded targets.
    
    This function performs:
    1. Color matching using vectorized lookup (O(1) per pixel)
    2. Connected component analysis for blob detection
    3. Target assignment based on color and bounds
    4. Bounding box rendering for detected targets
    
    Args:
        instance: UI instance with attributes:
            - filter_colors: List of (B, G, R) tuples to match
            - color_lookup: Precomputed lookup table for colors
            - excluded_regions: List of (x_min, y_min, x_max, y_max) to exclude
            - target_to_colors: Dict mapping target names to color sets
            - target_bounds: Dict mapping target names to bounds
            - min_blob_pixels: Minimum blob area to consider
            - max_blobs: Maximum number of blobs to display
            - detected_targets: Will be populated with target positions
            - auto_view_mode: If True, show only current auto target
            - auto_mode: If True, only touch current auto target
            - benchmark: If True, print timing information
        frame: Input image array (H, W, 3) in BGR
        apply_scale: Scale factor for resizing output (for display)
        
    Returns:
        Filtered image with bounding boxes around detected targets
    """
    t_start = time.time()
    
    if not hasattr(instance, 'filter_colors') or not instance.filter_colors:
        return frame
    
    # Determine display mode based on manual_target_name and auto_mode
    # Auto mode always shows all targets; manual mode can show 'none', 'all', or a specific target
    in_auto_mode = hasattr(instance, 'auto_mode') and instance.auto_mode
    manual_target = getattr(instance, 'manual_target_name', None) if not in_auto_mode else None
    
    # Handle special case: 'none' means show nothing
    if manual_target == 'none':
        black_frame = np.zeros_like(frame)
        if apply_scale != 1.0:
            h, w = frame.shape[:2]
            black_frame = cv2.resize(black_frame, (int(w * apply_scale), int(h * apply_scale)), 
                                    interpolation=cv2.INTER_AREA)
        return black_frame
    
    # Determine if we have targets to detect
    has_targets = (hasattr(instance, 'target_to_colors') and 
                   instance.target_to_colors and 
                   len(instance.target_to_colors) > 0)
    
    # Always use multi-target mode if we have targets (even just one)
    # This ensures all targets are detected for auto-targeting
    # Drawing can be filtered separately based on manual_target or auto_mode
    
    # Create a black canvas
    filtered = np.zeros_like(frame)
    h, w = frame.shape[:2]
    t1 = time.time()
    
    # ============================================================================
    # MULTI-TARGET MODE: Detect each target separately for accurate pixel counts
    # ============================================================================
    if has_targets:
        b, g, r = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
        instance.detected_targets = {}
        largest_per_target = {}
        
        # Process each target individually
        for target_name, target_colors in instance.target_to_colors.items():
            # Convert to set to remove duplicate colors
            unique_colors = set(target_colors) if not isinstance(target_colors, set) else target_colors
            
            # Create lookup for this target's colors only
            target_lookup = np.zeros((256, 256, 256), dtype=bool)
            for b_val, g_val, r_val in unique_colors:
                target_lookup[b_val, g_val, r_val] = True
            
            # Create mask for this target
            target_mask = target_lookup[b, g, r].astype(np.uint8) * 255
            
            # Apply bounds restriction if target has bounds
            if hasattr(instance, 'target_bounds') and target_name in instance.target_bounds:
                x1, y1, x2, y2 = instance.target_bounds[target_name]
                x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
                y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))
                bounds_mask = np.zeros((h, w), dtype=np.uint8)
                bounds_mask[y1:y2, x1:x2] = 255
                target_mask = target_mask & bounds_mask
            
            # Apply excluded regions
            for x_min, y_min, x_max, y_max in instance.excluded_regions:
                ex_min, ex_max = max(0, min(w, x_min)), max(0, min(w, x_max))
                ey_min, ey_max = max(0, min(h, y_min)), max(0, min(h, y_max))
                target_mask[ey_min:ey_max, ex_min:ex_max] = 0
            
            # Apply this target's mask to filtered image
            filtered[target_mask > 0] = frame[target_mask > 0]
            
            # Detect blobs in this target's mask
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(target_mask, connectivity=8)
            
            # Find largest blob for this target
            largest_blob = None
            if num_labels > 1:
                for label_idx in range(1, num_labels):
                    area = stats[label_idx, cv2.CC_STAT_AREA]
                    if area >= instance.min_blob_pixels:
                        if largest_blob is None or area > largest_blob[4]:
                            x = stats[label_idx, cv2.CC_STAT_LEFT]
                            y = stats[label_idx, cv2.CC_STAT_TOP]
                            w_blob = stats[label_idx, cv2.CC_STAT_WIDTH]
                            h_blob = stats[label_idx, cv2.CC_STAT_HEIGHT]
                            largest_blob = (x, y, w_blob, h_blob, area)
            
            # Store the largest blob for this target
            if largest_blob is not None:
                x, y, w_blob, h_blob, area = largest_blob
                largest_per_target[target_name] = (x, y, w_blob, h_blob, area)
        
        # Apply max_blobs limit if set (keep N largest blobs across all targets)
        if instance.max_blobs > 0 and len(largest_per_target) > instance.max_blobs:
            # Sort by area (largest first) and keep only top N
            sorted_targets = sorted(largest_per_target.items(), key=lambda item: item[1][4], reverse=True)
            largest_per_target = dict(sorted_targets[:instance.max_blobs])
        
        # Store detected targets after max_blobs filtering
        instance.detected_targets = {}
        for target_name, (x, y, w_blob, h_blob, area) in largest_per_target.items():
            # Store in original coordinates for ADB touch (always unscaled)
            instance.detected_targets[target_name] = (x, y, w_blob, h_blob)
        
        # Scale the filtered frame AND blob coordinates if needed
        if apply_scale != 1.0:
            h_scaled = int(h * apply_scale)
            w_scaled = int(w * apply_scale)
            filtered = cv2.resize(filtered, (w_scaled, h_scaled), interpolation=cv2.INTER_AREA)
            
            # Scale blob coordinates for drawing on the scaled image
            scaled_blobs = []
            for target_name, (x, y, w_blob, h_blob, area) in largest_per_target.items():
                x_scaled = int(x * apply_scale)
                y_scaled = int(y * apply_scale)
                w_scaled_blob = int(w_blob * apply_scale)
                h_scaled_blob = int(h_blob * apply_scale)
                scaled_blobs.append((target_name, x_scaled, y_scaled, w_scaled_blob, h_scaled_blob, area))
        else:
            scaled_blobs = [(name, x, y, w, h, a) for name, (x, y, w, h, a) in largest_per_target.items()]
        
        # Filter which blobs to draw based on mode
        # Determine which target(s) to draw
        draw_target = None
        if in_auto_mode and hasattr(instance, 'get_current_auto_target'):
            # Auto mode: only draw current auto target
            draw_target = instance.get_current_auto_target()
        elif manual_target and manual_target != 'all' and manual_target != 'none':
            # Manual specific target selected
            draw_target = manual_target
        # else: draw_target stays None, meaning draw all
        
        # Filter blobs to draw
        if draw_target:
            blobs_to_draw = [(name, x, y, w, h, a) for name, x, y, w, h, a in scaled_blobs if name == draw_target]
        else:
            blobs_to_draw = scaled_blobs
        
        # Draw bounding boxes
        for target_name, x, y, w_blob, h_blob, area in blobs_to_draw:
            cv2.rectangle(filtered, (x, y), (x + w_blob, y + h_blob), (255, 255, 0), 2)
            label_text = f"{target_name} ({area}px)"
            label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            label_y = max(y - 5, label_size[1] + 5)
            cv2.putText(filtered, label_text, (x, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Performance logging
        if in_auto_mode:
            try:
                from android_injections.automation.performance_logger import get_logger
                get_logger().log_timing("    filter_per_target_mode", (time.time() - t1) * 1000)
            except:
                pass
        return filtered
    else:
        # No targets or single target - return empty frame
        return np.zeros_like(frame)
