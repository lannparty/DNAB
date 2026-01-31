"""State field evaluation - XP detection and plane detection."""
import time
import numpy as np
import cv2
import pytesseract
from collections import Counter


def evaluate_state_fields(instance, frame):
    """Evaluate state fields (XP, higher_plane) regardless of filter status.
    
    This function:
    1. Detects XP changes using OCR with Tesseract
    2. Detects higher plane from minimap black square
    3. Counts distinct color groups for minimap counter
    4. Tracks state stability and transitions
    
    Args:
        instance: UI instance with attributes:
            - bounds_with_names: List of (x1, y1, x2, y2, name) bounds
            - xp_last_sample_time: Last time XP was sampled
            - xp_sample_interval: Minimum time between samples
            - xp_last_value: Previous XP value detected
            - xp_detected: Current XP string to display
            - xp_trigger_time: When XP change was detected
            - xp_brightness_threshold: Manual threshold for OCR
            - higher_plane: Boolean flag for higher plane status
            - plane_size: Kernel size for black square detection
            - minimap_counter: Number of distinct groups in minimap
            - minimap_counter_prev_value: Previous counter value
            - minimap_counter_prev_centroids: Previous centroids for position stability
            - minimap_counter_stable_since: When counter became stable
            - minimap_counter_padding: Padding for connecting nearby pixels
            - stability_timer: Stability check interval
            - target_to_colors: Dict mapping target names to color sets
            - _clahe: CLAHE preprocessor object
        frame: Input image (H, W, 3) in BGR
    """
    # Check for XP changes using OCR within xp bound
    # Sample at configurable interval to reduce CPU load
    # Only run if xp_tracking is enabled
    current_time = time.time()
    if hasattr(instance, 'xp_tracking') and instance.xp_tracking and hasattr(instance, 'bounds_with_names') and instance.bounds_with_names:
        # Only sample if enough time has passed since last sample
        if current_time - instance.xp_last_sample_time >= instance.xp_sample_interval:
            instance.xp_last_sample_time = current_time
            
            for bound in instance.bounds_with_names:
                if len(bound) == 5 and bound[4] == 'xp':
                    x1, y1, x2, y2, name = bound
                    # Extract region
                    xp_region = frame[y1:y2, x1:x2]
                    if xp_region.size > 0:
                        try:
                            # Convert to grayscale (handles all colors: white, yellow, cyan, etc.)
                            gray = cv2.cvtColor(xp_region, cv2.COLOR_BGR2GRAY)
                            
                            # Enhance contrast using CLAHE (reuse pre-created object)
                            gray = instance._clahe.apply(gray)
                            
                            # Upscale for better OCR accuracy (3x scale)
                            scale_factor = 3
                            gray_scaled = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, 
                                                    interpolation=cv2.INTER_CUBIC)
                            
                            # Apply bilateral filter to reduce noise while preserving edges
                            gray_filtered = cv2.bilateralFilter(gray_scaled, 5, 50, 50)
                            
                            # Try best-performing preprocessing methods only
                            results = []
                            
                            # Method 1: Otsu's thresholding (usually best for varying backgrounds)
                            _, thresh_otsu = cv2.threshold(gray_filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                            thresh_otsu_inv = cv2.bitwise_not(thresh_otsu)
                            
                            # Method 2: Simple threshold with configured brightness (fallback)
                            _, thresh_simple = cv2.threshold(gray_filtered, instance.xp_brightness_threshold, 255, cv2.THRESH_BINARY)
                            thresh_simple_inv = cv2.bitwise_not(thresh_simple)
                            
                            # Config: digits only, single line, PSM 7 for single text line
                            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
                            
                            # Try both methods and collect valid results
                            for method_img in [thresh_otsu_inv, thresh_otsu, thresh_simple_inv, thresh_simple]:
                                try:
                                    text = pytesseract.image_to_string(method_img, config=custom_config)
                                    text = text.strip().replace(' ', '').replace(',', '')
                                    if text and text.isdigit():
                                        results.append(int(text))
                                except:
                                    pass
                            
                            # Use the most common result (mode) if we have multiple valid readings
                            current_xp = None
                            if results:
                                # Count occurrences and pick most common
                                counter = Counter(results)
                                current_xp = counter.most_common(1)[0][0]
                            
                            # Accept reading immediately if valid
                            if current_xp is not None:
                                # Check if XP value changed
                                if instance.xp_last_value is None or current_xp != instance.xp_last_value:
                                    # Check if XP increased
                                    if instance.xp_last_value is not None and current_xp > instance.xp_last_value:
                                        # XP increased!
                                        xp_gain = current_xp - instance.xp_last_value
                                        instance.xp_trigger_time = time.time()
                                        instance.xp_detected = f"+{xp_gain}"  # Store the gain amount
                                    
                                    # Update value
                                    instance.xp_last_value = current_xp
                            
                        except Exception as e:
                            print(f"XP OCR error: {e}")
                    break
    
    # Check for black square in minimap bounds for higher plane detection (outside XP block)
    if hasattr(instance, 'bounds_with_names'):
        for bound in instance.bounds_with_names:
            if len(bound) == 5 and bound[4] == 'minimap':
                x1, y1, x2, y2, name = bound
                minimap_region = frame[y1:y2, x1:x2]
                if minimap_region.size > 0:
                    try:
                        # Check for contiguous black squares (0,0,0)
                        # Create mask of black pixels
                        black_mask = np.all(minimap_region == [0, 0, 0], axis=2).astype(np.uint8)
                        
                        # Use morphological operations to find connected regions
                        kernel = np.ones((instance.plane_size, instance.plane_size), np.uint8)
                        eroded = cv2.erode(black_mask, kernel, iterations=1)
                        
                        # If any pixels remain after erosion, there's at least one nxn black square
                        if np.any(eroded):
                            instance.higher_plane = True
                        else:
                            instance.higher_plane = False
                    except Exception as e:
                        instance.higher_plane = False
                break
    
    # Count distinct pixel groups for minimap_counter target (outside XP block)
    instance.minimap_counter = 0
    if hasattr(instance, 'target_to_colors') and 'minimap_counter' in instance.target_to_colors:
        minimap_bound_found = False
        for bound in instance.bounds_with_names:
            if len(bound) == 5 and bound[4] == 'minimap':
                minimap_bound_found = True
                x1, y1, x2, y2, name = bound
                minimap_region = frame[y1:y2, x1:x2]
                if minimap_region.size > 0:
                    try:
                        # Get colors for minimap_counter target
                        counter_colors = instance.target_to_colors['minimap_counter']
                        
                        # Create mask for matching pixels
                        h, w = minimap_region.shape[:2]
                        tolerance = getattr(instance.config, 'counter_tolerance', 0)
                        
                        if tolerance == 0:
                            # Use fast lookup table for exact matching
                            counter_lookup = np.zeros((256, 256, 256), dtype=bool)
                            for b, g, r in counter_colors:
                                counter_lookup[b, g, r] = True
                            
                            # Use vectorized lookup (much faster than loop)
                            b, g, r = minimap_region[:, :, 0], minimap_region[:, :, 1], minimap_region[:, :, 2]
                            mask = counter_lookup[b, g, r].astype(np.uint8) * 255
                        else:
                            # Use tolerance-based matching (slower but more flexible)
                            mask = np.zeros((h, w), dtype=np.uint8)
                            for target_b, target_g, target_r in counter_colors:
                                # Calculate color distance for all pixels
                                b_diff = np.abs(minimap_region[:, :, 0].astype(np.int16) - target_b)
                                g_diff = np.abs(minimap_region[:, :, 1].astype(np.int16) - target_g)
                                r_diff = np.abs(minimap_region[:, :, 2].astype(np.int16) - target_r)
                                
                                # Mark pixels within tolerance
                                within_tolerance = (b_diff <= tolerance) & (g_diff <= tolerance) & (r_diff <= tolerance)
                                mask[within_tolerance] = 255
                        
                        # Count non-zero pixels before dilation
                        pixels_before = np.count_nonzero(mask)
                        
                        # Apply dilation to connect pixels within padding distance
                        if instance.minimap_counter_padding > 0:
                            kernel = np.ones((instance.minimap_counter_padding * 2 + 1, instance.minimap_counter_padding * 2 + 1), np.uint8)
                            mask = cv2.dilate(mask, kernel, iterations=1)
                        
                        # Count non-zero pixels after dilation
                        pixels_after = np.count_nonzero(mask)
                        
                        # Find connected components
                        num_labels, labels = cv2.connectedComponents(mask)
                        # Subtract 1 because label 0 is background
                        new_counter_value = num_labels - 1
                        
                        # Calculate centroids of connected components for position stability
                        centroids = []
                        if new_counter_value > 0:
                            for label in range(1, num_labels):  # Skip background (0)
                                component_mask = (labels == label)
                                # Calculate centroid
                                moments = cv2.moments(component_mask.astype(np.uint8))
                                if moments['m00'] != 0:
                                    cx = int(moments['m10'] / moments['m00'])
                                    cy = int(moments['m01'] / moments['m00'])
                                    centroids.append((cx, cy))
                        
                        # Store mask and minimap bounds for visualization
                        instance.minimap_counter_mask = mask
                        instance.minimap_counter_bounds = (x1, y1, x2, y2)
                        
                        # Track stability of minimap_counter pixel positions (not just count)
                        current_time = time.time()
                        centroids_changed = False
                        
                        if instance.minimap_counter_prev_centroids is not None:
                            # Check if centroids have changed significantly
                            if len(centroids) == len(instance.minimap_counter_prev_centroids):
                                # Same number of components, check if positions are similar
                                total_movement = 0
                                for curr_centroid, prev_centroid in zip(centroids, instance.minimap_counter_prev_centroids):
                                    cx1, cy1 = curr_centroid
                                    cx2, cy2 = prev_centroid
                                    movement = abs(cx1 - cx2) + abs(cy1 - cy2)
                                    total_movement += movement
                                
                                # Consider stable if total movement is small (less than 10 pixels per component)
                                max_allowed_movement = len(centroids) * 10
                                centroids_changed = total_movement > max_allowed_movement
                            else:
                                # Different number of components
                                centroids_changed = True
                        else:
                            # First detection
                            centroids_changed = False
                        
                        if not centroids_changed:
                            # Positions unchanged or minimally changed
                            if instance.minimap_counter_stable_since is None:
                                instance.minimap_counter_stable_since = current_time
                        else:
                            # Positions changed significantly, reset stability
                            instance.minimap_counter_stable_since = None
                        
                        instance.minimap_counter = new_counter_value
                        instance.minimap_counter_prev_value = new_counter_value
                        instance.minimap_counter_prev_centroids = centroids
                    except Exception as e:
                        instance.minimap_counter = 0
                        instance.minimap_counter_prev_value = None
                        instance.minimap_counter_stable_since = None
                        instance.minimap_counter_prev_centroids = None
                break
        
        if not minimap_bound_found:
            pass  # Minimap bound not found
    # Check if we're within 500ms of trigger time
    if instance.xp_trigger_time is not None:
        elapsed = (time.time() - instance.xp_trigger_time) * 1000  # Convert to ms
        if elapsed >= 500:
            instance.xp_detected = "0"
            # Reset trigger after 500ms
            instance.xp_trigger_time = None
        # else: keep showing the XP gain amount
    else:
        instance.xp_detected = "0"
