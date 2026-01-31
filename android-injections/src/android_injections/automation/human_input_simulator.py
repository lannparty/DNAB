"""
Human Input Simulator Module

This module provides realistic human-like touch simulation for Android devices.
It generates input events that mimic natural human touch patterns, incorporating
variations in pressure, size, timing, and movement that real human touches exhibit.

DESIGN PHILOSOPHY:
Humans are not precise machines. Real touch input includes:
- Variable pressure (not constant max pressure)
- Touch size variation (finger contact area changes)
- Micro-movements and jitter during touch
- Non-linear timing (reaction delays, hesitation)
- Orientation changes (finger rotation)
# - Natural swipe curves (not straight lines)
- Pressure buildup/decay (gradual press/release)

This module generates raw input events using sendevent commands to achieve
hardware-level simulation that bypasses Android's high-level input APIs,
providing more realistic touch characteristics.

KEY FEATURES:
- Automatic coordinate rotation to match display orientation (like ADB input)
- Hardware-level touch simulation with full control over touch properties
- Human-like variations in pressure, timing, and movement
- SELinux bypass for direct kernel event injection

KEY HUMAN FACTORS SIMULATED:

1. PRESSURE VARIATION:
   - Real touches build pressure gradually
   - Pressure fluctuates slightly during hold
   - Release pressure decays naturally
   - Range: 0-127 (hardware maximum)

2. TOUCH SIZE VARIATION:
   - Finger contact area changes with pressure/angle
   - Major axis: primary contact dimension
   - Minor axis: secondary contact dimension
   - Natural range: 50-120 units

3. POSITION JITTER:
   - Micro-movements during touch (1-3 pixels)
   - More pronounced during longer holds
   - Simulates natural hand tremor

4. TIMING VARIATION:
   - Pressure buildup: 50-150ms
   - Hold stability: variable duration
   - Release decay: 30-100ms
   - Human reaction time: 100-300ms delays

5. ORIENTATION VARIATION:
   - Finger rotation during touch
   - Affects touch shape and pressure distribution
   - Range: -0.5 to 0.5 radians

# 6. SWIPE CURVES:
#    - Natural hand movement isn't perfectly straight
#    - Slight curves and acceleration changes
#    - Variable velocity profiles

USAGE:
    simulator = HumanInputSimulator()
    # Generate a realistic tap
    events = simulator.generate_realistic_tap(500, 800)

    # Generate a natural swipe
    # events = simulator.generate_natural_swipe(100, 500, 900, 500, duration=300)

    # Execute events
    simulator.execute_events(events)
"""

import random
import time
import subprocess
import math
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class TouchPoint:
    """Represents a single touch point with all hardware properties."""
    x: int
    y: int
    pressure: int  # 0-127
    touch_major: int  # Primary touch size
    touch_minor: int  # Secondary touch size
    orientation: float  # Rotation in radians
    distance: int  # Proximity distance
    tracking_id: int


@dataclass
class InputEvent:
    """Raw input event for sendevent command."""
    device: str
    event_type: int
    event_code: int
    event_value: int


class HumanInputSimulator:
    """
    Generates human-like touch input events for Android devices.

    Uses raw sendevent commands to simulate realistic touch characteristics
    that mimic natural human interaction patterns.
    """

    def __init__(self, device: str = "/dev/input/event2", variation_level: float = 1.0):
        """
        Initialize the human input simulator.

        Args:
            device: Input device path (default: touchscreen event2)
            variation_level: Multiplier for human variation (0.0-2.0)
                          0.0 = machine perfect, 2.0 = very human-like
        """
        self.device = device
        self.variation_level = max(0.0, min(2.0, variation_level))

        # Hardware constants from device capabilities
        self.MAX_PRESSURE = 127
        self.MAX_TOUCH_SIZE = 127
        self.MAX_ORIENTATION = math.pi / 2  # 90 degrees
        self.MAX_DISTANCE = 127

        # Display properties for coordinate rotation
        self.display_width = 1080   # Physical touchscreen width
        self.display_height = 2340  # Physical touchscreen height
        self.display_rotation = 0   # Current display rotation (0, 1, 2, 3)

        # Human variation ranges (scaled by variation_level)
        self.PRESSURE_BUILDUP_TIME = (50, 150)  # ms
        self.PRESSURE_DECAY_TIME = (30, 100)    # ms
        self.POSITION_JITTER = (1, 3)           # pixels
        self.TOUCH_SIZE_VARIATION = (50, 120)   # touch size units
        self.HUMAN_REACTION_TIME = (100, 300)   # ms delay
        # self.SWIPE_CURVE_FACTOR = (0.1, 0.3)    # curve intensity

    def _get_display_rotation(self) -> int:
        """
        Get the current display rotation from Android.

        Returns:
            Rotation value: 0=0°, 1=90°, 2=180°, 3=270°
        """
        try:
            # Query display rotation via dumpsys
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'display'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Look for orientation in the output
                for line in result.stdout.split('\n'):
                    if 'orientation=' in line:
                        # Extract the orientation value
                        orientation_str = line.split('orientation=')[1].split(',')[0]
                        try:
                            orientation = int(orientation_str)
                            self.display_rotation = orientation
                            return orientation
                        except ValueError:
                            pass
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass

        # Fallback to 0 if detection fails
        return 0

    def _rotate_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """
        Rotate coordinates to match display orientation.

        Android's input system automatically rotates coordinates based on display
        orientation, but our raw sendevent needs to account for this manually.

        Args:
            x, y: Input coordinates (in current display orientation)

        Returns:
            Rotated coordinates for touchscreen hardware
        """
        rotation = self._get_display_rotation()

        if rotation == 0:
            # No rotation
            return x, y
        elif rotation == 1:
            # 90° clockwise: (x, y) -> (height - y, x)
            return self.display_height - y, x
        elif rotation == 2:
            # 180°: (x, y) -> (width - x, height - y)
            return self.display_width - x, self.display_height - y
        elif rotation == 3:
            # 270° clockwise (90° counter-clockwise): (x, y) -> (y, width - x)
            return y, self.display_width - x
        else:
            # Unknown rotation, return as-is
            return x, y

    def _scale_variation(self, value_range: Tuple[float, float]) -> Tuple[int, int]:
        """Scale variation range based on variation_level."""
        min_val, max_val = value_range
        center = (min_val + max_val) / 2
        radius = (max_val - min_val) / 2
        scaled_radius = radius * self.variation_level

        return (int(center - scaled_radius), int(center + scaled_radius))

    def _generate_pressure_curve(self, duration_ms: int, max_pressure: int = None) -> List[int]:
        """
        Generate a realistic pressure curve over time.

        Human touches don't instantly reach max pressure - they build up
        and may fluctuate slightly during the hold.
        """
        if max_pressure is None:
            max_pressure = int(self.MAX_PRESSURE * random.uniform(0.7, 1.0))

        # Buildup phase
        buildup_time = random.randint(*self._scale_variation(self.PRESSURE_BUILDUP_TIME))
        buildup_steps = max(1, buildup_time // 10)  # 10ms resolution

        # Decay phase
        decay_time = random.randint(*self._scale_variation(self.PRESSURE_DECAY_TIME))
        decay_steps = max(1, decay_time // 10)

        # Hold phase
        hold_time = max(0, duration_ms - buildup_time - decay_time)
        hold_steps = max(1, hold_time // 50)  # Less frequent during hold

        pressure_curve = []

        # Buildup (exponential rise)
        for i in range(buildup_steps):
            progress = i / buildup_steps
            # Exponential buildup feels more natural
            pressure = int(max_pressure * (1 - math.exp(-3 * progress)))
            pressure_curve.append(pressure)

        # Hold with slight variation
        base_pressure = pressure_curve[-1] if pressure_curve else max_pressure
        for i in range(hold_steps):
            # Add small random variation during hold (±5%)
            variation = random.uniform(-0.05, 0.05) * self.variation_level
            pressure = int(base_pressure * (1 + variation))
            pressure = max(0, min(self.MAX_PRESSURE, pressure))
            pressure_curve.append(pressure)

        # Decay (exponential fall)
        final_pressure = pressure_curve[-1] if pressure_curve else max_pressure
        for i in range(decay_steps):
            progress = i / decay_steps
            # Exponential decay
            pressure = int(final_pressure * math.exp(-2 * progress))
            pressure_curve.append(pressure)

        return pressure_curve

    def _generate_touch_size(self, pressure: int) -> Tuple[int, int]:
        """
        Generate realistic touch size based on pressure.

        Higher pressure generally means larger contact area, but with variation.
        """
        # Base size correlates with pressure
        base_size = int((pressure / self.MAX_PRESSURE) * 80) + 40

        # Add human variation
        major_variation = random.randint(*self._scale_variation((-10, 10)))
        minor_variation = random.randint(*self._scale_variation((-15, 15)))

        major = max(1, min(self.MAX_TOUCH_SIZE, base_size + major_variation))
        minor = max(1, min(self.MAX_TOUCH_SIZE, base_size + minor_variation))

        return major, minor

    def _generate_position_jitter(self, base_x: int, base_y: int, duration_ms: int) -> List[Tuple[int, int]]:
        """
        Generate natural position micro-movements during touch.

        Humans aren't perfectly still - there's always slight movement.
        """
        positions = []
        steps = max(1, duration_ms // 20)  # Position updates every 20ms

        for i in range(steps):
            # Jitter increases with duration (tremor)
            jitter_factor = min(1.0, duration_ms / 1000.0)  # Max jitter after 1 second
            jitter_range = self._scale_variation(self.POSITION_JITTER)
            max_jitter = jitter_range[1] * jitter_factor * self.variation_level

            jitter_x = random.uniform(-max_jitter, max_jitter)
            jitter_y = random.uniform(-max_jitter, max_jitter)

            x = int(base_x + jitter_x)
            y = int(base_y + jitter_y)

            positions.append((x, y))

        return positions

    def _generate_orientation_variation(self, duration_ms: int) -> List[float]:
        """
        Generate natural finger orientation changes during touch.
        """
        orientations = []
        steps = max(1, duration_ms // 30)  # Orientation changes less frequently

        base_orientation = random.uniform(-self.MAX_ORIENTATION/2, self.MAX_ORIENTATION/2)

        for i in range(steps):
            # Small random variations around base orientation
            variation = random.uniform(-0.1, 0.1) * self.variation_level
            orientation = base_orientation + variation
            orientation = max(-self.MAX_ORIENTATION, min(self.MAX_ORIENTATION, orientation))
            orientations.append(orientation)

        return orientations

    def _create_input_events(self, touch_points: List[TouchPoint], tracking_id: int) -> List[InputEvent]:
        """
        Convert touch points to raw input events for sendevent.
        """
        events = []

        for point in touch_points:
            # ABS_MT_SLOT (select touch slot)
            events.append(InputEvent(self.device, 3, 47, 0))  # SLOT 0

            # ABS_MT_TRACKING_ID
            events.append(InputEvent(self.device, 3, 57, tracking_id))

            # Position
            events.append(InputEvent(self.device, 3, 53, point.x))    # ABS_MT_POSITION_X
            events.append(InputEvent(self.device, 3, 54, point.y))    # ABS_MT_POSITION_Y

            # Touch properties
            events.append(InputEvent(self.device, 3, 48, point.touch_major))   # ABS_MT_TOUCH_MAJOR
            events.append(InputEvent(self.device, 3, 49, point.touch_minor))   # ABS_MT_TOUCH_MINOR
            events.append(InputEvent(self.device, 3, 52, int(point.orientation * 4096 / math.pi)))  # ABS_MT_ORIENTATION
            events.append(InputEvent(self.device, 3, 58, point.pressure))      # ABS_MT_PRESSURE
            events.append(InputEvent(self.device, 3, 59, point.distance))      # ABS_MT_DISTANCE

            # BTN_TOUCH (touch down/up)
            btn_value = 1 if point.pressure > 0 else 0
            events.append(InputEvent(self.device, 1, 330, btn_value))

            # SYN_REPORT
            events.append(InputEvent(self.device, 0, 0, 0))

        # Touch release (final event)
        if touch_points and touch_points[-1].pressure == 0:
            events.append(InputEvent(self.device, 3, 57, -1))  # ABS_MT_TRACKING_ID -1
            events.append(InputEvent(self.device, 1, 330, 0))  # BTN_TOUCH up
            events.append(InputEvent(self.device, 0, 0, 0))    # SYN_REPORT

        return events

    def generate_realistic_tap(self, x: int, y: int, hold_duration_ms: int = 100) -> List[InputEvent]:
        """
        Generate a realistic tap event with human-like characteristics.

        Coordinates are automatically rotated to match current display orientation,
        just like ADB input commands do.

        Args:
            x, y: Touch coordinates (in current display orientation)
            hold_duration_ms: How long to hold the tap

        Returns:
            List of InputEvent objects for sendevent commands
        """
        # Add human reaction delay
        reaction_delay = random.randint(*self._scale_variation(self.HUMAN_REACTION_TIME))
        time.sleep(reaction_delay / 1000.0)

        # Rotate coordinates to match display orientation (like ADB input does)
        x, y = self._rotate_coordinates(x, y)

        # Generate pressure curve
        pressure_curve = self._generate_pressure_curve(hold_duration_ms)

        # Generate position jitter
        positions = self._generate_position_jitter(x, y, hold_duration_ms)

        # Generate orientation variation
        orientations = self._generate_orientation_variation(hold_duration_ms)

        # Create touch points
        touch_points = []
        tracking_id = random.randint(1, 65534)

        # Ensure we have enough data points
        num_points = max(len(pressure_curve), len(positions), len(orientations))

        for i in range(num_points):
            pressure = pressure_curve[min(i, len(pressure_curve)-1)]
            pos_x, pos_y = positions[min(i, len(positions)-1)]
            orientation = orientations[min(i, len(orientations)-1)]

            touch_major, touch_minor = self._generate_touch_size(pressure)

            point = TouchPoint(
                x=pos_x, y=pos_y,
                pressure=pressure,
                touch_major=touch_major,
                touch_minor=touch_minor,
                orientation=orientation,
                distance=max(0, self.MAX_DISTANCE - pressure),  # Closer when pressed harder
                tracking_id=tracking_id
            )
            touch_points.append(point)

        # Add release point with zero pressure
        touch_points.append(TouchPoint(
            x=touch_points[-1].x, y=touch_points[-1].y,
            pressure=0,
            touch_major=0, touch_minor=0,
            orientation=touch_points[-1].orientation,
            distance=self.MAX_DISTANCE,
            tracking_id=tracking_id
        ))

        return self._create_input_events(touch_points, tracking_id)

    # def generate_natural_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
    #                           duration_ms: int = 300) -> List[InputEvent]:
    #     """
    #     Generate a natural swipe gesture with human-like curves and acceleration.

    #     Args:
    #         start_x, start_y: Starting coordinates
    #         end_x, end_y: Ending coordinates
    #         duration_ms: Total swipe duration

    #     Returns:
    #         List of InputEvent objects
    #     """
    #     # Add human reaction delay
    #     reaction_delay = random.randint(*self._scale_variation(self.HUMAN_REACTION_TIME))
    #     time.sleep(reaction_delay / 1000.0)

    #     # Calculate base line
    #     dx = end_x - start_x
    #     dy = end_y - start_y
    #     distance = math.sqrt(dx*dx + dy*dy)

    #     # Add natural curve (parabolic deviation)
    #     curve_factor = random.uniform(*self._scale_variation(self.SWIPE_CURVE_FACTOR))
    #     mid_x = (start_x + end_x) / 2
    #     mid_y = (start_y + end_y) / 2

    #     # Perpendicular vector for curve
    #     perp_x = -dy / distance * curve_factor * distance * 0.1
    #     perp_y = dx / distance * curve_factor * distance * 0.1

    #     mid_x += perp_x
    #     mid_y += perp_y

    #     # Generate curved path using quadratic bezier
    #     steps = max(5, duration_ms // 20)  # Position updates every 20ms
    #     touch_points = []

    #     tracking_id = random.randint(1, 65534)

    #     for i in range(steps + 1):
    #         t = i / steps

    #         # Quadratic bezier curve
    #         x = (1-t)**2 * start_x + 2*(1-t)*t * mid_x + t**2 * end_x
    #         y = (1-t)**2 * start_y + 2*(1-t)*t * mid_y + t**2 * end_y

    #         # Add micro-jitter
    #         jitter = random.uniform(-1, 1) * self.variation_level
    #         x += jitter
    #         y += jitter

    #         # Pressure curve (higher at start and end, lower in middle for natural feel)
    #         pressure_progress = 1.0 - 4 * (t - 0.5)**2  # Parabolic pressure
    #         base_pressure = int(self.MAX_PRESSURE * pressure_progress * random.uniform(0.8, 1.0))

    #         touch_major, touch_minor = self._generate_touch_size(base_pressure)

    #         point = TouchPoint(
    #             x=int(x), y=int(y),
    #             pressure=base_pressure,
    #             touch_major=touch_major,
    #             touch_minor=touch_minor,
    #             orientation=random.uniform(-0.2, 0.2),  # Slight orientation change
    #             distance=max(0, self.MAX_DISTANCE - base_pressure),
    #             tracking_id=tracking_id
    #         )
    #         touch_points.append(point)

    #     # Add release point
    #     touch_points.append(TouchPoint(
    #         x=int(end_x), y=int(end_y),
    #         pressure=0,
    #         touch_major=0, touch_minor=0,
    #         orientation=0,
    #         distance=self.MAX_DISTANCE,
    #         tracking_id=tracking_id
    #     ))

    #     return self._create_input_events(touch_points, tracking_id)

# def execute_events_android_input(self, events: List[InputEvent], event_delay_ms: int = 10):
    #     """
    #     Execute events using Android's input command instead of raw sendevent.

    #     This is a fallback method when sendevent permissions are blocked.
    #     Uses 'input motionevent' commands which work but have less control.
    #     """
    #     # Group events into logical touch actions
    #     current_touch = None
    #     touch_start_time = None

    #     for event in events:
    #         # For Android input, we simplify to basic DOWN/MOVE/UP actions
    #         if event.event_type == 3:  # ABS events
    #             if event.event_code == 53:  # ABS_MT_POSITION_X
    #                 if current_touch is None:
    #                     current_touch = {'x': event.event_value, 'y': None}
    #                 else:
    #                     current_touch['x'] = event.event_value
    #             elif event.event_code == 54:  # ABS_MT_POSITION_Y
    #                 if current_touch is None:
    #                     current_touch = {'x': None, 'y': event.event_value}
    #                 else:
    #                     current_touch['y'] = event.event_value
    #             elif event.event_code == 58:  # ABS_MT_PRESSURE
    #                 if current_touch:
    #                     current_touch['pressure'] = event.event_value
    #         elif event.event_type == 1 and event.event_code == 330:  # BTN_TOUCH
    #             if event.event_value == 1 and current_touch and current_touch['x'] is not None and current_touch['y'] is not None:
    #                 # Touch down
    #                 cmd = f"adb shell input motionevent DOWN {current_touch['x']} {current_touch['y']}"
    #                 subprocess.run(cmd.split(), capture_output=True)
    #                 touch_start_time = time.time()
    #             elif event.event_value == 0:
    #                 # Touch up
    #                 if current_touch and current_touch['x'] is not None and current_touch['y'] is not None:
    #                     cmd = f"adb shell input motionevent UP {current_touch['x']} {current_touch['y']}"
    #                     subprocess.run(cmd.split(), capture_output=True)
    #                 current_touch = None
    #         elif event.event_type == 0 and event.event_code == 0:  # SYN_REPORT
    #             # Sync event - could add small delay here
    #             if event_delay_ms > 0:
    #                 time.sleep(event_delay_ms / 1000.0)

    def execute_events(self, events: List[InputEvent], event_delay_ms: int = 10):
        """
        Execute a sequence of input events using raw sendevent commands.

        Args:
            events: List of InputEvent objects
            event_delay_ms: Delay between events (simulates event timing)
        """
        # Use runcon with system_server context to bypass SELinux restrictions
        for event in events:
            cmd = f"adb shell su -c 'runcon u:r:system_server:s0 /system/bin/sendevent {event.device} {event.event_type} {event.event_code} {event.event_value}'"
            try:
                subprocess.run(cmd.split(), check=True, capture_output=True)
                if event_delay_ms > 0:
                    time.sleep(event_delay_ms / 1000.0)
            except subprocess.CalledProcessError as e:
                print(f"Failed to execute event: {cmd}")
                print(f"Error: {e}")
                # print("Try using use_android_input=True for Android input commands")

    def demo_realistic_tap(self, x: int = 500, y: int = 800):
        """
        Demo function showing a realistic tap.

        This generates and prints the events without executing them.
        """
        events = self.generate_realistic_tap(x, y)
        print(f"Generated {len(events)} events for realistic tap at ({x}, {y}):")
        for i, event in enumerate(events[:20]):  # Show first 20 events
            print(f"  {i}: sendevent {event.device} {event.event_type} {event.event_code} {event.event_value}")
        if len(events) > 20:
            print(f"  ... and {len(events) - 20} more events")

    # def demo_android_input_tap(self, x: int = 500, y: int = 800):
    #     """
    #     Demo using Android input commands instead of raw events.
    #     This works but has less control over touch properties.
    #     """
    #     events = self.generate_realistic_tap(x, y)
    #     print(f"Generated {len(events)} events, executing with Android input commands:")
    #     self.execute_events_android_input(events)
    #     print("Tap executed using Android input commands")

    # def demo_natural_swipe(self, start_x: int = 200, start_y: int = 800,
    #                       end_x: int = 800, end_y: int = 800):
    #     """
    #     Demo function showing a natural swipe.

    #     This generates and prints the events without executing them.
    #     """
    #     events = self.generate_natural_swipe(start_x, start_y, end_x, end_y)
    #     print(f"Generated {len(events)} events for natural swipe from ({start_x}, {start_y}) to ({end_x}, {end_y}):")
    #     for i, event in enumerate(events[:20]):  # Show first 20 events
    #     print(f"  {i}: sendevent {event.device} {event.event_type} {event.event_code} {event.event_value}")
    #     if len(events) > 20:
    #         print(f"  ... and {len(events) - 20} more events")


# Example usage and testing
if __name__ == "__main__":
    simulator = HumanInputSimulator(variation_level=1.5)  # Very human-like

    print("=== Realistic Tap Demo (Raw Events) ===")
    simulator.demo_realistic_tap()

    # print("\n=== Android Input Tap Demo (Working Method) ===")
    # simulator.demo_android_input_tap()

    # print("\n=== Natural Swipe Demo ===")
    # simulator.demo_natural_swipe()

    print("\n=== Usage Examples ===")
    print("# Create simulator with custom settings")
    print("simulator = HumanInputSimulator(device='/dev/input/event2', variation_level=1.2)")
    print("")
    print("# Generate realistic tap")
    print("events = simulator.generate_realistic_tap(500, 800, hold_duration_ms=150)")
    print("simulator.execute_events(events)  # Raw hardware-level events")
    print("")
    # print("# Generate natural swipe")
    # print("events = simulator.generate_natural_swipe(100, 500, 900, 500, duration_ms=400)")
    # print("simulator.execute_events(events, use_android_input=True)")