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
    
    # Determine if we're in multi-target mode (show all targets) or single-target mode
    has_multiple_targets = (hasattr(instance, 'target_to_colors') and 
                           instance.target_to_colors and 
                           len(instance.target_to_colors) > 1)
    
    # Multi-target mode: auto mode, manual 'all', or filter first enabled (no manual target set)
    is_multi_target = (in_auto_mode or 
                      manual_target == 'all' or 
                      (manual_target is None and has_multiple_targets))
    
    # Create a black canvas
    filtered = np.zeros_like(frame)
    h, w = frame.shape[:2]
    t1 = time.time()
    
    # ============================================================================
    # MULTI-TARGET MODE: Detect each target separately for accurate pixel counts
    # ============================================================================
    if is_multi_target and has_multiple_targets:
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
                # Store in original coordinates for ADB touch (always unscaled)
                instance.detected_targets[target_name] = (x, y, w_blob, h_blob)
        
        # Apply max_blobs limit if set (keep N largest blobs across all targets)
        if instance.max_blobs > 0 and len(largest_per_target) > instance.max_blobs:
            # Sort by area (largest first) and keep only top N
            sorted_targets = sorted(largest_per_target.items(), key=lambda item: item[1][4], reverse=True)
            largest_per_target = dict(sorted_targets[:instance.max_blobs])
        
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
        
        # Draw bounding boxes (one per target, no max_blobs filtering across targets)
        for target_name, x, y, w_blob, h_blob, area in scaled_blobs:
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
    
    # ============================================================================
    # SINGLE-TARGET MODE: Show one specific target with original blob detection
    # ============================================================================
    else:
        # Determine which colors to use
        if manual_target and hasattr(instance, 'target_to_colors') and manual_target in instance.target_to_colors:
            active_colors = instance.target_to_colors[manual_target]
        else:
            # Fallback or invalid target - show nothing
            black_frame = np.zeros_like(frame)
            if apply_scale != 1.0:
                black_frame = cv2.resize(black_frame, (int(w * apply_scale), int(h * apply_scale)), 
                                        interpolation=cv2.INTER_AREA)
            return black_frame
        
        # Vectorized color matching using lookup table
        # Create temporary lookup since we're using a specific target's colors
        temp_lookup = np.zeros((256, 256, 256), dtype=bool)
        for b_val, g_val, r_val in active_colors:
            temp_lookup[b_val, g_val, r_val] = True
        b, g, r = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
        mask = temp_lookup[b, g, r].astype(np.uint8) * 255
        
    # Apply excluded regions to mask (set those areas to 0)
    for x_min, y_min, x_max, y_max in instance.excluded_regions:
        # Scale excluded region coordinates to current frame size if needed
        if apply_scale != 1.0:
            ex_min = int(x_min * apply_scale)
            ey_min = int(y_min * apply_scale)
            ex_max = int(x_max * apply_scale)
            ey_max = int(y_max * apply_scale)
        else:
            ex_min, ey_min, ex_max, ey_max = x_min, y_min, x_max, y_max
        
        # Clamp to frame boundaries
        ex_min = max(0, min(w, ex_min))
        ex_max = max(0, min(w, ex_max))
        ey_min = max(0, min(h, ey_min))
        ey_max = max(0, min(h, ey_max))
        
        # Zero out this region in the mask
        mask[ey_min:ey_max, ex_min:ex_max] = 0
    
    # Apply mask to filtered image
    filtered[mask > 0] = frame[mask > 0]
    
    t2 = time.time()
    
    # Find connected components (blobs)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    t3 = time.time()
    
    # Time blob processing if we're in auto mode (for performance logging)
    t_blob_start = time.time()
    
    # Scale the filtered frame for display if needed
    # Skip if apply_scale is 1.0 since get_frame_for_display will scale later
    if apply_scale != 1.0:
        h_scaled = int(h * apply_scale)
        w_scaled = int(w * apply_scale)
        filtered = cv2.resize(filtered, (w_scaled, h_scaled), interpolation=cv2.INTER_AREA)
        # Scale stats for display (x, y, w, h need scaling)
        stats = stats.astype(np.float32)
        stats[:, cv2.CC_STAT_LEFT] *= apply_scale
        stats[:, cv2.CC_STAT_TOP] *= apply_scale
        stats[:, cv2.CC_STAT_WIDTH] *= apply_scale
        stats[:, cv2.CC_STAT_HEIGHT] *= apply_scale
        stats = stats.astype(np.int32)
    
    # Group blobs by target and find the largest blob per target
    if num_labels > 1:
        # Pre-filter: skip blobs smaller than min_blob_pixels to avoid wasted processing
        valid_label_indices = []
        for label_idx in range(1, num_labels):
            area = stats[label_idx, cv2.CC_STAT_AREA]
            if area >= instance.min_blob_pixels:
                valid_label_indices.append(label_idx)
        
        # Dictionary to track largest blob per target: target_name -> (label_idx, area, x, y, w, h)
        largest_per_target = {}
        
        # Cache blob colors for each blob to avoid recomputing for every target
        blob_colors_cache = {}
        
        # Iterate through valid blobs only
        for label_idx in valid_label_indices:
            # Get bounding box of this blob
            x = stats[label_idx, cv2.CC_STAT_LEFT]
            y = stats[label_idx, cv2.CC_STAT_TOP]
            w = stats[label_idx, cv2.CC_STAT_WIDTH]
            h = stats[label_idx, cv2.CC_STAT_HEIGHT]
            area = stats[label_idx, cv2.CC_STAT_AREA]
            
            # Find which target this blob belongs to
            # Use best match based on color intersection count
            target_name = "Unknown"
            if hasattr(instance, 'target_to_colors') and instance.target_to_colors:
                # Collect all colors in this blob ONCE and cache it
                if label_idx not in blob_colors_cache:
                    blob_mask = (labels == label_idx)
                    blob_pixels = frame[blob_mask]
                    
                    # Sample pixels if blob is large (>500 pixels)
                    # Statistical sampling is sufficient for color matching
                    if len(blob_pixels) > 500:
                        # Randomly sample 500 pixels from blob
                        sample_indices = np.random.choice(len(blob_pixels), 500, replace=False)
                        blob_pixels = blob_pixels[sample_indices]
                    
                    # Convert to set of tuples for intersection
                    blob_colors_cache[label_idx] = set(map(tuple, blob_pixels))
                
                blob_colors = blob_colors_cache[label_idx]
                
                # Find best matching target based on color intersection AND bounds
                best_target = None
                best_target_matches = 0
                
                # Calculate blob center in original coordinates for bounds checking
                if apply_scale != 1.0:
                    scale_factor = 1.0 / apply_scale
                    blob_center_x = int((x + w // 2) * scale_factor)
                    blob_center_y = int((y + h // 2) * scale_factor)
                else:
                    blob_center_x = x + w // 2
                    blob_center_y = y + h // 2
                
                # Determine which target(s) to search for
                targets_to_check = instance.target_to_colors.items()
                
                # If manual target is selected (via +/- buttons), only search for that target
                if hasattr(instance, 'manual_target_name') and instance.manual_target_name:
                    # 'all' means search all targets (default behavior)
                    if instance.manual_target_name == 'all':
                        targets_to_check = instance.target_to_colors.items()
                    # 'none' means don't search for any targets (handled earlier, shouldn't reach here)
                    elif instance.manual_target_name == 'none':
                        targets_to_check = []
                    # Specific target selected
                    elif instance.manual_target_name in instance.target_to_colors:
                        targets_to_check = [(instance.manual_target_name, instance.target_to_colors[instance.manual_target_name])]
                    else:
                        # Unknown target, search nothing
                        targets_to_check = []
                
                for tgt_name, tgt_colors in targets_to_check:
                    # If target has bounds, check if blob center is within bounds
                    if hasattr(instance, 'target_bounds') and tgt_name in instance.target_bounds:
                        bx1, by1, bx2, by2 = instance.target_bounds[tgt_name]
                        # Skip this target if blob center is outside its bounds
                        if not (bx1 <= blob_center_x <= bx2 and by1 <= blob_center_y <= by2):
                            continue
                    
                    # Check target color matching
                    target_match_count = len(blob_colors & tgt_colors)
                    
                    # Select target with most color matches (that also satisfies bounds)
                    if target_match_count > best_target_matches:
                        best_target = tgt_name
                        best_target_matches = target_match_count
                        
                        # Early exit: if match quality is >80%, this is clearly the right target
                        # No need to check remaining targets
                        match_quality = target_match_count / len(blob_colors) if blob_colors else 0
                        if match_quality > 0.8:
                            break
                
                # After checking all targets, assign the best match
                if best_target is None:
                    # If no valid match found, skip this blob entirely
                    continue
                
                target_name = best_target
                
                # Check if this is the largest blob for this target
                if target_name not in largest_per_target or area > largest_per_target[target_name][1]:
                    largest_per_target[target_name] = (label_idx, area, x, y, w, h)
        
        t_blob_end = time.time()
        t4 = time.time()
        
        # Store detected target positions (always store at original unscaled coordinates)
        # Filter by min_blob_pixels and max_blobs
        instance.detected_targets = {}
        
        # First, filter by min_blob_pixels
        valid_targets = {}
        for target_name, (label_idx, area, x, y, w, h) in largest_per_target.items():
            if area >= instance.min_blob_pixels:
                if apply_scale != 1.0:
                    # Scale back to original coordinates for ADB touch
                    scale_factor = 1.0 / apply_scale
                    orig_x = int(x * scale_factor)
                    orig_y = int(y * scale_factor)
                    orig_w = int(w * scale_factor)
                    orig_h = int(h * scale_factor)
                    valid_targets[target_name] = (orig_x, orig_y, orig_w, orig_h, area)
                else:
                    valid_targets[target_name] = (x, y, w, h, area)
        
        # Sort by area and apply max_blobs limit
        sorted_valid = sorted(valid_targets.items(), key=lambda item: item[1][4], reverse=True)
        if instance.max_blobs > 0:
            sorted_valid = sorted_valid[:instance.max_blobs]
        
        # Store final filtered targets (without area for compatibility)
        for target_name, (x, y, w, h, area) in sorted_valid:
            instance.detected_targets[target_name] = (x, y, w, h)
        
        # Sort blobs by area (largest first) and limit to max_blobs if set
        sorted_blobs = sorted(largest_per_target.items(), key=lambda item: item[1][1], reverse=True)
        
        # In auto mode, only show the current auto target
        if hasattr(instance, 'auto_mode') and instance.auto_mode:
            current_auto_target = instance.get_current_auto_target()
            if current_auto_target:
                sorted_blobs = [(name, data) for name, data in sorted_blobs if name == current_auto_target]
        elif instance.max_blobs > 0:
            sorted_blobs = sorted_blobs[:instance.max_blobs]
        
        # Draw bounding boxes only for the largest blob of each target (if above threshold)
        for target_name, (label_idx, area, x, y, w, h) in sorted_blobs:
            # Only draw if blob meets minimum pixel threshold
            if area >= instance.min_blob_pixels:
                # Draw bounding box in cyan (neutral color that stands out)
                cv2.rectangle(filtered, (x, y), (x + w, y + h), (255, 255, 0), 2)
                
                # Add label above the box
                label_text = f"{target_name} ({area}px)"
                label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                label_y = max(y - 5, label_size[1] + 5)
                cv2.putText(filtered, label_text, (x, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        t5 = time.time()
        
        # Print timing breakdown if benchmark mode enabled
        if instance.benchmark:
            print(f"Filter timing - Setup: {(t1-t_start)*1000:.1f}ms, "
                  f"Color Match: {(t2-t1)*1000:.1f}ms, "
                  f"Blob Detect: {(t3-t2)*1000:.1f}ms, "
                  f"Blob Vote: {(t4-t3)*1000:.1f}ms, "
                  f"Draw: {(t5-t4)*1000:.1f}ms, "
                  f"TOTAL: {(t5-t_start)*1000:.1f}ms ({num_labels-1} blobs)")
    else:
        t_end = time.time()
        if instance.benchmark:
            print(f"Filter timing - Setup: {(t1-t_start)*1000:.1f}ms, "
                  f"Color Match: {(t2-t1)*1000:.1f}ms, "
                  f"Blob Detect: {(t3-t2)*1000:.1f}ms, "
                  f"TOTAL: {(t_end-t_start)*1000:.1f}ms (no blobs)")
    
    # Log detailed timing to performance logger if in auto mode
    if hasattr(instance, 'auto_mode') and instance.auto_mode:
        try:
            from android_injections.automation.performance_logger import get_logger
            logger = get_logger()
            logger.log_timing("    filter_setup", (t1 - t_start) * 1000)
            logger.log_timing("    filter_color_match", (t2 - t1) * 1000)
            logger.log_timing("    filter_blob_detect", (t3 - t2) * 1000)
            if num_labels > 1:
                logger.log_timing("    filter_blob_processing", (t_blob_end - t_blob_start) * 1000)
                logger.log_timing("    filter_drawing", (t5 - t4) * 1000)
        except:
            pass  # Silently fail if logger not available
    
    return filtered
