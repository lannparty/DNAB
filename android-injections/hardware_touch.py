#!/usr/bin/env python3
"""
Hardware Touch Script Wrapper
Supports both script-based and direct ADB shell execution methods.
"""

import sys
import os
import subprocess
import random

def send_touch_adb_shell(x: int, y: int, hold_duration_ms: int = 100,
                        pressure_max: int = 100, touch_major: int = 80,
                        touch_minor: int = 75, orientation: int = 0,
                        distance: int = 27, tracking_id: int = None,
                        event_delay_ms: int = 10):
    """
    Send touch event directly through ADB shell (no script needed on device)
    """
    if tracking_id is None:
        tracking_id = random.randint(1, 65534)

    # Build the sendevent command sequence
    commands = []

    # Touch down sequence
    commands.extend([
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 47 0",  # ABS_MT_SLOT 0
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 57 {tracking_id}",  # ABS_MT_TRACKING_ID
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 53 {x}",  # ABS_MT_POSITION_X
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 54 {y}",  # ABS_MT_POSITION_Y
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 58 {pressure_max}",  # ABS_MT_PRESSURE
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 48 {touch_major}",  # ABS_MT_TOUCH_MAJOR
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 49 {touch_minor}",  # ABS_MT_TOUCH_MINOR
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 52 {orientation}",  # ABS_MT_ORIENTATION
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 59 {distance}",  # ABS_MT_DISTANCE
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 1 330 1",  # BTN_TOUCH DOWN
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 0 0 0",  # SYN_REPORT
    ])

    # Hold with pressure variation
    pressure_step = pressure_max // 5
    for i in range(1, 6):
        current_pressure = max(0, pressure_max - (i-1) * pressure_step // 2)
        commands.extend([
            f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 58 {current_pressure}",
            f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 0 0 0",
        ])

    # Hold for specified duration
    commands.append(f"sleep {hold_duration_ms / 1000:.3f}")

    # Touch up sequence
    commands.extend([
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 58 0",  # ABS_MT_PRESSURE 0
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 1 330 0",  # BTN_TOUCH UP
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 3 57 -1",  # ABS_MT_TRACKING_ID -1
        f"runcon u:r:system_server:s0 /system/bin/sendevent /dev/input/event2 0 0 0",  # SYN_REPORT
    ])

    # Join all commands with &&
    full_command = " && ".join(commands)

    # Execute via ADB
    try:
        result = subprocess.run(['adb', 'shell', 'su', '-c', full_command],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"Touch sent to ({x}, {y}) via ADB shell")
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return False
    except Exception as e:
        print(f"Error executing touch: {e}")
        return False


def send_touch(x: int, y: int, hold_duration_ms: int = 100,
               pressure_max: int = 100, touch_major: int = 80,
               touch_minor: int = 75, orientation: int = 0,
               distance: int = 27, tracking_id: int = None,
               event_delay_ms: int = 10, use_adb_shell: bool = False):
    """
    Send a touch event using either script method or direct ADB shell method.

    Args:
        x, y: Touch coordinates
        hold_duration_ms: Hold duration in milliseconds
        pressure_max: Maximum pressure (0-127)
        touch_major: Touch major axis size
        touch_minor: Touch minor axis size
        orientation: Touch orientation (radians * 4096)
        distance: Touch distance
        tracking_id: Touch tracking ID (auto-generated if None)
        event_delay_ms: Delay between events in milliseconds
        use_adb_shell: If True, use direct ADB shell instead of pushing script
    """

    if use_adb_shell:
        return send_touch_adb_shell(x, y, hold_duration_ms, pressure_max, touch_major,
                                   touch_minor, orientation, distance, tracking_id, event_delay_ms)
    else:
        # Use the script method (existing implementation)
        if tracking_id is None:
            tracking_id = random.randint(1, 65534)

        # Get script path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, 'hardware_touch.sh')

        # Ensure script exists
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Hardware touch script not found: {script_path}")

        try:
            # Push script to device
            push_cmd = ['adb', 'push', script_path, '/data/local/tmp/hardware_touch.sh']
            subprocess.run(push_cmd, check=True, capture_output=True)

            # Make script executable on device
            chmod_cmd = ['adb', 'shell', 'su', '-c', 'chmod +x /data/local/tmp/hardware_touch.sh']
            subprocess.run(chmod_cmd, check=True, capture_output=True)

            # Execute touch script with parameters
            cmd = [
                'adb', 'shell', 'su', '-c',
                f'sh /data/local/tmp/hardware_touch.sh {x} {y} {hold_duration_ms} {pressure_max} {touch_major} {touch_minor} {orientation} {distance} {tracking_id} {event_delay_ms}'
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Touch sent to ({x}, {y}) via script")

        except subprocess.CalledProcessError as e:
            print(f"Failed to execute touch: {e}")
            raise


def main():
    """Command line interface for sending touch events."""
    if len(sys.argv) < 3:
        print("Usage: python3 hardware_touch.py <x> <y> [hold_ms] [pressure] [major] [minor] [orientation] [distance] [tracking_id] [delay_ms] [--adb-shell]")
        print("Examples:")
        print("  python3 hardware_touch.py 1000 500")
        print("  python3 hardware_touch.py 1000 500 150 120 85 80 --adb-shell")
        sys.exit(1)

    try:
        # Parse arguments
        args = sys.argv[1:]
        use_adb_shell = '--adb-shell' in args
        if use_adb_shell:
            args.remove('--adb-shell')

        # Parse coordinates and optional parameters
        x = int(args[0])
        y = int(args[1])
        hold_duration_ms = int(args[2]) if len(args) > 2 else 100
        pressure_max = int(args[3]) if len(args) > 3 else 100
        touch_major = int(args[4]) if len(args) > 4 else 80
        touch_minor = int(args[5]) if len(args) > 5 else 75
        orientation = int(args[6]) if len(args) > 6 else 0
        distance = int(args[7]) if len(args) > 7 else 27
        tracking_id = int(args[8]) if len(args) > 8 else None
        event_delay_ms = int(args[9]) if len(args) > 9 else 10

        send_touch(x, y, hold_duration_ms, pressure_max, touch_major,
                  touch_minor, orientation, distance, tracking_id, event_delay_ms, use_adb_shell)

    except ValueError as e:
        print(f"Invalid argument: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()