"""Mouse event handling for UI interactions."""
import cv2


def create_mouse_callback(window_capture_instance):
    """Create a mouse callback function bound to a WindowCapture instance.
    
    This returns a callback function that handles all mouse events including:
    - Button clicks (toggle modes, adjust settings)
    - Rectangle selection (for targets, bounds, exclusions)
    - Number field editing
    - Text input field activation
    
    Args:
        window_capture_instance: The WindowCapture instance to operate on
        
    Returns:
        callable: A mouse callback function suitable for cv2.setMouseCallback
    """
    
    def mouse_callback(event, x, y, flags, param):
        """Handle mouse events for rectangle selection and button clicks."""
        self = window_capture_instance
        
        # Check if we're in the filter button area
        in_button_area = False
        if hasattr(self, 'button_rect'):
            bx, by, bw, bh = self.button_rect
            if bx <= x <= bx + bw and by <= y <= by + bh:
                in_button_area = True
                # Check if click is on colors +/- buttons or number display
                if hasattr(self, 'colors_minus_rect'):
                    mx, my, mw, mh = self.colors_minus_rect
                    if mx <= x <= mx + mw and my <= y <= my + mh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.colors_per_target = max(1, self.colors_per_target - 1)
                            self.load_all_targets()
                            print(f"Colors per target: {self.colors_per_target}")
                        return
                
                if hasattr(self, 'colors_display_rect'):
                    dx, dy, dw, dh = self.colors_display_rect
                    if dx <= x <= dx + dw and dy <= y <= dy + dh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.editing_colors = True
                            self.editing_min_pixels = False
                            self.editing_max_blobs = False
                            self.temp_input = str(self.colors_per_target)
                            print("Editing colors per target - type number and press Enter")
                        return
                
                if hasattr(self, 'colors_plus_rect'):
                    px, py, pw, ph = self.colors_plus_rect
                    if px <= x <= px + pw and py <= y <= py + ph:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.colors_per_target = min(50, self.colors_per_target + 1)
                            self.load_all_targets()
                            print(f"Colors per target: {self.colors_per_target}")
                        return
                
                # Check if click is on pixel threshold +/- buttons or number display
                if hasattr(self, 'pixels_minus_rect'):
                    pmx, pmy, pmw, pmh = self.pixels_minus_rect
                    if pmx <= x <= pmx + pmw and pmy <= y <= pmy + pmh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.min_blob_pixels = max(1, self.min_blob_pixels - 1)
                            print(f"Min blob pixels: {self.min_blob_pixels}")
                        return
                
                if hasattr(self, 'pixels_display_rect'):
                    pdx, pdy, pdw, pdh = self.pixels_display_rect
                    if pdx <= x <= pdx + pdw and pdy <= y <= pdy + pdh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.editing_min_pixels = True
                            self.editing_colors = False
                            self.editing_max_blobs = False
                            self.temp_input = str(self.min_blob_pixels)
                            print("Editing min blob pixels - type number and press Enter")
                        return
                
                if hasattr(self, 'pixels_plus_rect'):
                    ppx, ppy, ppw, pph = self.pixels_plus_rect
                    if ppx <= x <= ppx + ppw and ppy <= y <= ppy + pph:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.min_blob_pixels = min(1000, self.min_blob_pixels + 1)
                            print(f"Min blob pixels: {self.min_blob_pixels}")
                        return
                
                # Check if click is on max_blobs +/- buttons or number display
                if hasattr(self, 'max_blobs_minus_rect'):
                    mbmx, mbmy, mbmw, mbmh = self.max_blobs_minus_rect
                    if mbmx <= x <= mbmx + mbmw and mbmy <= y <= mbmy + mbmh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.max_blobs = max(0, self.max_blobs - 1)
                            print(f"Max blobs: {'unlimited' if self.max_blobs == 0 else self.max_blobs}")
                        return
                
                if hasattr(self, 'max_blobs_display_rect'):
                    mbdx, mbdy, mbdw, mbdh = self.max_blobs_display_rect
                    if mbdx <= x <= mbdx + mbdw and mbdy <= y <= mbdy + mbdh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.editing_max_blobs = True
                            self.editing_colors = False
                            self.editing_min_pixels = False
                            self.temp_input = "0" if self.max_blobs == 0 else str(self.max_blobs)
                            print("Editing max blobs - type number and press Enter (0 = unlimited)")
                        return
                
                if hasattr(self, 'max_blobs_plus_rect'):
                    mbpx, mbpy, mbpw, mbph = self.max_blobs_plus_rect
                    if mbpx <= x <= mbpx + mbpw and mbmy <= y <= mbpy + mbmh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.max_blobs = min(100, self.max_blobs + 1)
                            print(f"Max blobs: {'unlimited' if self.max_blobs == 0 else self.max_blobs}")
                        return
                
                # Check if click is on show_bounds checkbox
                if hasattr(self, 'bounds_checkbox_rect'):
                    bcx, bcy, bcw, bch = self.bounds_checkbox_rect
                    if bcx <= x <= bcx + bcw and bcy <= y <= bcy + bch:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.show_bounds = not self.show_bounds
                            print(f"Show bounds: {self.show_bounds}")
                        return
                
                # Check if click is on show_excludes checkbox
                if hasattr(self, 'excludes_checkbox_rect'):
                    ecx, ecy, ecw, ech = self.excludes_checkbox_rect
                    if ecx <= x <= ecx + ecw and ecy <= y <= ecy + ech:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.show_excludes = not self.show_excludes
                            print(f"Show excludes: {self.show_excludes}")
                        return
                
                # Check if click is on auto_view_mode checkbox
                if hasattr(self, 'auto_view_checkbox_rect'):
                    avx, avy, avw, avh = self.auto_view_checkbox_rect
                    if avx <= x <= avx + avw and avy <= y <= avy + avh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.auto_view_mode = not self.auto_view_mode
                            print(f"Auto view mode: {self.auto_view_mode}")
                        return
                
                # Handle filter button click
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.show_filtered = not self.show_filtered
                    if self.show_filtered:
                        # Reload targets when turning filter on
                        self.load_all_targets()
                        if hasattr(self, 'filter_colors') and self.filter_colors:
                            print(f"Filter ON - Showing {len(self.filter_colors)} colors from targets")
                        else:
                            print("Filter ON - No target files found")
                    else:
                        print("Filter OFF - Showing all colors")
                        # Clear detected targets when filter is off
                        self.detected_targets = {}
                return
        
        # Check if we're in the target mode button area
        if hasattr(self, 'target_mode_button_rect'):
            smx, smy, smw, smh = self.target_mode_button_rect
            if smx <= x <= smx + smw and smy <= y <= smy + smh:
                # Check unique checkbox first
                if hasattr(self, 'unique_checkbox_rect'):
                    ux, uy, uw, uh = self.unique_checkbox_rect
                    if ux <= x <= ux + uw and uy <= y <= uy + uh:
                        if event == cv2.EVENT_LBUTTONDOWN:
                            self.unique_only = not self.unique_only
                            print(f"Capture mode: {'Unique colors only' if self.unique_only else 'All colors in box'}")
                        return
                
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.target_mode = not self.target_mode
                    self.bounds_mode = False  # Turn off bounds when enabling target
                    self.exclude_mode = False  # Turn off exclude when enabling target
                    if self.target_mode:
                        print("Target mode ENABLED - click and drag to select")
                    else:
                        print("Target mode DISABLED")
                        self.selecting = False  # Cancel any active selection
                        self.target_selection_rect = None  # Clear drawn box
                        self.selection_start = None
                        self.selection_end = None
                return
        
        # Check if we're in the exclude mode button area
        if hasattr(self, 'exclude_mode_button_rect'):
            emx, emy, emw, emh = self.exclude_mode_button_rect
            if emx <= x <= emx + emw and emy <= y <= emy + emh:
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.exclude_mode = not self.exclude_mode
                    self.target_mode = False  # Turn off target when enabling exclude
                    self.bounds_mode = False  # Turn off bounds when enabling exclude
                    if self.exclude_mode:
                        print("Exclude mode ENABLED - click and drag to exclude area")
                    else:
                        print("Exclude mode DISABLED")
                        self.selecting = False  # Cancel any active selection
                        self.selection_start = None
                        self.selection_end = None
                return
        
        # Check if we're in the state tracking button area
        if hasattr(self, 'state_tracking_button_rect'):
            stx, sty, stw, sth = self.state_tracking_button_rect
            if stx <= x <= stx + stw and sty <= y <= sty + sth:
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.state_tracking = not self.state_tracking
                    if self.state_tracking:
                        print("State tracking ENABLED")
                    else:
                        print("State tracking DISABLED")
                        # Reset state values
                        self.xp_detected = "0"
                        self.xp_last_value = None
                        self.xp_current_reading = None
                        self.xp_reading_first_seen = None
                        self.xp_trigger_time = None
                        self.higher_plane = False
                        self.minimap_counter = 0
                return
        
        # Check if we're in the capture button area
        if hasattr(self, 'capture_button_rect'):
            cbx, cby, cbw, cbh = self.capture_button_rect
            if cbx <= x <= cbx + cbw and cby <= y <= cby + cbh:
                if event == cv2.EVENT_LBUTTONDOWN:
                    if self.bounds_mode:
                        self.save_bounds()
                    elif self.exclude_mode:
                        self.save_excluded_region()
                    elif self.target_mode:
                        self.save_target()
                return
        
        # Check if we're in the bounds button area
        if hasattr(self, 'bounds_button_rect'):
            bbx, bby, bbw, bbh = self.bounds_button_rect
            if bbx <= x <= bbx + bbw and bby <= y <= bby + bbh:
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.bounds_mode = not self.bounds_mode
                    self.target_mode = False  # Turn off target when enabling bounds
                    self.exclude_mode = False  # Turn off exclude when enabling bounds
                    if self.bounds_mode:
                        print("Bounds mode ENABLED - click and drag to set bounds")
                    else:
                        print("Bounds mode DISABLED")
                        self.selecting = False  # Cancel any active selection
                        self.bounds_selection_rect = None  # Clear drawn box
                        self.selection_start = None
                        self.selection_end = None
                return
        

        # Check if we're in the auto button area
        if hasattr(self, 'auto_button_rect'):
            abx, aby, abw, abh = self.auto_button_rect
            if abx <= x <= abx + abw and aby <= y <= aby + abh:
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.auto_mode = not self.auto_mode
                    if self.auto_mode:
                        # Auto-enable filter and auto view mode when auto mode turns on
                        import time
                        import numpy as np
                        
                        if not self.show_filtered:
                            self.show_filtered = True
                            self.load_all_targets()
                            print("Filter mode auto-enabled")
                        if not self.auto_view_mode:
                            self.auto_view_mode = True
                            print("Auto view mode auto-enabled")
                        if not self.state_tracking:
                            self.state_tracking = True
                            print("State tracking auto-enabled")
                        
                        self.last_auto_touch = time.time()
                        self.next_touch_interval = np.random.normal(self.touch_delay_mean, self.touch_delay_std)
                        self.next_touch_interval = max(self.touch_delay_min, min(self.touch_delay_max, self.next_touch_interval))
                        self.auto_target_passed = False
                        self.auto_target_touched = False
                        current_target = self.get_current_auto_target()
                        if current_target:
                            print(f"Auto mode ON - current target: '{current_target}'")
                        else:
                            print("Auto mode ON - waiting for state detection to determine target")
                    else:
                        print("Auto mode OFF")
                return
        
        # Check if we're in the text field area (capture target name)
        if hasattr(self, 'text_field_rect'):
            tfx, tfy, tfw, tfh = self.text_field_rect
            if tfx <= x <= tfx + tfw and tfy <= y <= tfy + tfh:
                if event == cv2.EVENT_LBUTTONDOWN:
                    self.text_input_active = True
                    self.target_selector_active = False
                    print("Text input active - type target name")
                return
            elif event == cv2.EVENT_LBUTTONDOWN:
                # Clicked outside text field, deactivate
                self.text_input_active = False
        
        # Check if click is on timer text field editors (min/max/mean/std/stable/pass)
        if event == cv2.EVENT_LBUTTONDOWN:
            # Min delay field
            if hasattr(self, 'delay_min_rect'):
                rx, ry, rw, rh = self.delay_min_rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.editing_delay_min = True
                    self.editing_delay_max = False
                    self.editing_delay_mean = False
                    self.editing_delay_std = False
                    self.editing_stability = False
                    self.editing_passing_dist = False
                    self.editing_xp_brightness = False
                    self.temp_input = ""
                    return
            
            # Max delay field
            if hasattr(self, 'delay_max_rect'):
                rx, ry, rw, rh = self.delay_max_rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.editing_delay_min = False
                    self.editing_delay_max = True
                    self.editing_delay_mean = False
                    self.editing_delay_std = False
                    self.editing_stability = False
                    self.editing_passing_dist = False
                    self.editing_xp_brightness = False
                    self.editing_plane_size = False
                    self.editing_xp_sample_interval = False
                    self.editing_minimap_counter_padding = False
                    self.temp_input = ""
                    return
            
            # Mean delay field
            if hasattr(self, 'delay_mean_rect'):
                rx, ry, rw, rh = self.delay_mean_rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.editing_delay_min = False
                    self.editing_delay_max = False
                    self.editing_delay_mean = True
                    self.editing_delay_std = False
                    self.editing_stability = False
                    self.editing_passing_dist = False
                    self.editing_xp_brightness = False
                    self.editing_plane_size = False
                    self.editing_xp_sample_interval = False
                    self.editing_minimap_counter_padding = False
                    self.temp_input = ""
                    return
            
            # Std delay field
            if hasattr(self, 'delay_std_rect'):
                rx, ry, rw, rh = self.delay_std_rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.editing_delay_min = False
                    self.editing_delay_max = False
                    self.editing_delay_mean = False
                    self.editing_delay_std = True
                    self.editing_stability = False
                    self.editing_passing_dist = False
                    self.editing_xp_brightness = False
                    self.editing_plane_size = False
                    self.editing_xp_sample_interval = False
                    self.editing_minimap_counter_padding = False
                    self.temp_input = ""
                    return
            
            # Stability field
            if hasattr(self, 'stability_rect'):
                rx, ry, rw, rh = self.stability_rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.editing_delay_min = False
                    self.editing_delay_max = False
                    self.editing_delay_mean = False
                    self.editing_delay_std = False
                    self.editing_stability = True
                    self.editing_passing_dist = False
                    self.editing_xp_brightness = False
                    self.editing_plane_size = False
                    self.editing_xp_sample_interval = False
                    self.editing_minimap_counter_padding = False
                    self.temp_input = ""
                    return
            
            # Passing distance field
            if hasattr(self, 'passing_dist_rect'):
                pdistx, pdisty, pdistw, pdisth = self.passing_dist_rect
                if pdistx <= x <= pdistx + pdistw and pdisty <= y <= pdisty + pdisth:
                    self.editing_delay_min = False
                    self.editing_delay_max = False
                    self.editing_delay_mean = False
                    self.editing_delay_std = False
                    self.editing_stability = False
                    self.editing_passing_dist = True
                    self.editing_xp_brightness = False
                    self.editing_plane_size = False
                    self.editing_xp_sample_interval = False
                    self.editing_minimap_counter_padding = False
                    self.temp_input = ""
                    return
            
            # XP brightness threshold field
            if hasattr(self, 'xp_brightness_rect'):
                bx, by, bw, bh = self.xp_brightness_rect
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    self.editing_delay_min = False
                    self.editing_delay_max = False
                    self.editing_delay_mean = False
                    self.editing_delay_std = False
                    self.editing_stability = False
                    self.editing_passing_dist = False
                    self.editing_xp_brightness = True
                    self.editing_plane_size = False
                    self.editing_xp_sample_interval = False
                    self.editing_minimap_counter_padding = False
                    self.temp_input = ""
                    return
            
            # Plane size +/- buttons and field
            if hasattr(self, 'plane_size_minus_rect'):
                pmx, pmy, pmw, pmh = self.plane_size_minus_rect
                if pmx <= x <= pmx + pmw and pmy <= y <= pmy + pmh:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.plane_size = max(1, self.plane_size - 1)
                        print(f"Plane size: {self.plane_size}")
                    return
            
            if hasattr(self, 'plane_size_rect'):
                px, py, pw, ph = self.plane_size_rect
                if px <= x <= px + pw and py <= y <= py + ph:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.editing_delay_min = False
                        self.editing_delay_max = False
                        self.editing_delay_mean = False
                        self.editing_delay_std = False
                        self.editing_stability = False
                        self.editing_passing_dist = False
                        self.editing_xp_brightness = False
                        self.editing_plane_size = True
                        self.temp_input = str(self.plane_size)
                        print("Editing plane size - type number and press Enter")
                    return
            
            if hasattr(self, 'plane_size_plus_rect'):
                ppx, ppy, ppw, pph = self.plane_size_plus_rect
                if ppx <= x <= ppx + ppw and ppy <= y <= ppy + pph:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.plane_size = min(50, self.plane_size + 1)
                        print(f"Plane size: {self.plane_size}")
                    return
            
            # XP sample interval +/- buttons and field
            if hasattr(self, 'xp_sample_interval_minus_rect'):
                xsimx, xsimy, xsimw, xsimh = self.xp_sample_interval_minus_rect
                if xsimx <= x <= xsimx + xsimw and xsimy <= y <= xsimy + xsimh:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.xp_sample_interval = max(0.1, self.xp_sample_interval - 0.1)
                        print(f"XP sample interval: {int(self.xp_sample_interval * 1000)}ms")
                    return
            
            if hasattr(self, 'xp_sample_interval_rect'):
                xsix, xsiy, xsiw, xsih = self.xp_sample_interval_rect
                if xsix <= x <= xsix + xsiw and xsiy <= y <= xsiy + xsih:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.editing_delay_min = False
                        self.editing_delay_max = False
                        self.editing_delay_mean = False
                        self.editing_delay_std = False
                        self.editing_stability = False
                        self.editing_passing_dist = False
                        self.editing_xp_brightness = False
                        self.editing_plane_size = False
                        self.editing_xp_sample_interval = True
                        self.temp_input = str(int(self.xp_sample_interval * 1000))
                        print("Editing XP sample interval - type number in ms and press Enter")
                    return
            
            if hasattr(self, 'xp_sample_interval_plus_rect'):
                xsipx, xsipy, xsipw, xsiph = self.xp_sample_interval_plus_rect
                if xsipx <= x <= xsipx + xsipw and xsipy <= y <= xsipy + xsiph:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.xp_sample_interval = min(10.0, self.xp_sample_interval + 0.1)
                        print(f"XP sample interval: {int(self.xp_sample_interval * 1000)}ms")
                    return
            
            # Minimap padding +/- buttons and field
            if hasattr(self, 'minimap_counter_padding_minus_rect'):
                pcpmx, pcpmy, pcpmw, pcpmh = self.minimap_counter_padding_minus_rect
                if pcpmx <= x <= pcpmx + pcpmw and pcpmy <= y <= pcpmy + pcpmh:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.minimap_counter_padding = max(0, self.minimap_counter_padding - 1)
                        print(f"Minimap padding: {self.minimap_counter_padding}")
                    return
            
            if hasattr(self, 'minimap_counter_padding_rect'):
                pcpx, pcpy, pcpw, pcph = self.minimap_counter_padding_rect
                if pcpx <= x <= pcpx + pcpw and pcpy <= y <= pcpy + pcph:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.editing_delay_min = False
                        self.editing_delay_max = False
                        self.editing_delay_mean = False
                        self.editing_delay_std = False
                        self.editing_stability = False
                        self.editing_passing_dist = False
                        self.editing_xp_brightness = False
                        self.editing_plane_size = False
                        self.editing_xp_sample_interval = False
                        self.editing_minimap_counter_padding = True
                        self.temp_input = str(self.minimap_counter_padding)
                        print("Editing minimap padding - type number and press Enter")
                    return
            
            if hasattr(self, 'minimap_counter_padding_plus_rect'):
                pcppx, pcppy, pcppw, pcpph = self.minimap_counter_padding_plus_rect
                if pcppx <= x <= pcppx + pcppw and pcppy <= y <= pcppy + pcpph:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.minimap_counter_padding = min(50, self.minimap_counter_padding + 1)
                        print(f"Minimap padding: {self.minimap_counter_padding}")
                    return
        
        # Only handle rectangle selection if target, bounds, or exclude mode is enabled and not in button/text areas
        if not in_button_area and (self.target_mode or self.bounds_mode or self.exclude_mode):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.selecting = True
                self.selection_start = (x, y)
                self.selection_end = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE:
                if self.selecting:
                    self.selection_end = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                if self.selecting:
                    self.selecting = False
                    self.selection_end = (x, y)
                    
                    if self.exclude_mode:
                        # Save as excluded region (red) - immediately save, don't store
                        self.save_excluded_region()
                    elif self.bounds_mode:
                        # Save as bounds selection (yellow)
                        self.bounds_selection_rect = (self.selection_start, self.selection_end)
                    elif self.target_mode:
                        # Save as target selection (green)
                        self.target_selection_rect = (self.selection_start, self.selection_end)
                        # Analyze colors when selection is complete
                        self.analyze_unique_colors()
    
    return mouse_callback
