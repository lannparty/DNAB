#!/usr/bin/env python3
"""
Hardware Touch Script - rotated view
- Enter coordinates in your rotated view
- Automatically translates to hardware coordinates
"""

import sys
import subprocess
import random

TOUCH_DEVICE = "/dev/input/event2"  # fixed

# Hardware resolution
HW_W, HW_H = 1080, 2340

# Your view resolution (rotated)
VIEW_W, VIEW_H = 2340, 1080  # swap if needed

# Rotation: "cw" = clockwise, "ccw" = counterclockwise
ROTATION = "cw"  # 90° clockwise

def transform_coords(x_view, y_view):
    """Convert view coordinates to hardware coordinates based on rotation."""
    if ROTATION == "cw":  # 90° clockwise
        x_hw = HW_W - int(y_view * HW_W / VIEW_H)
        y_hw = int(x_view * HW_H / VIEW_W)
    elif ROTATION == "ccw":  # 90° counter-clockwise
        x_hw = int(y_view * HW_W / VIEW_H)
        y_hw = HW_H - int(x_view * HW_H / VIEW_W)
    elif ROTATION == "180":
        x_hw = HW_W - int(x_view * HW_W / VIEW_W)
        y_hw = HW_H - int(y_view * HW_H / VIEW_H)
    else:  # no rotation
        x_hw = int(x_view * HW_W / VIEW_W)
        y_hw = int(y_view * HW_H / VIEW_H)
    return x_hw, y_hw

def send_touch_adb_shell(x, y, hold_ms=100,
                         pressure_max=100, touch_major=80,
                         touch_minor=75, orientation=0,
                         distance=27, tracking_id=None):

    if tracking_id is None:
        tracking_id = random.randint(1, 65534)

    cmds = [
        f"sendevent {TOUCH_DEVICE} 3 47 0",
        f"sendevent {TOUCH_DEVICE} 3 57 {tracking_id}",
        f"sendevent {TOUCH_DEVICE} 3 53 {x}",
        f"sendevent {TOUCH_DEVICE} 3 54 {y}",
        f"sendevent {TOUCH_DEVICE} 3 58 {pressure_max}",
        f"sendevent {TOUCH_DEVICE} 3 48 {touch_major}",
        f"sendevent {TOUCH_DEVICE} 3 49 {touch_minor}",
        f"sendevent {TOUCH_DEVICE} 3 52 {orientation}",
        f"sendevent {TOUCH_DEVICE} 3 59 {distance}",
        f"sendevent {TOUCH_DEVICE} 1 330 1",
        f"sendevent {TOUCH_DEVICE} 0 0 0",
        f"sleep {hold_ms / 1000:.3f}",
        f"sendevent {TOUCH_DEVICE} 3 58 0",
        f"sendevent {TOUCH_DEVICE} 1 330 0",
        f"sendevent {TOUCH_DEVICE} 3 57 -1",
        f"sendevent {TOUCH_DEVICE} 0 0 0",
    ]

    full_cmd = " && ".join(cmds)
    subprocess.run(['adb', 'shell', 'su', '-c', full_cmd], check=True)
    print(f"Touch sent → ({x},{y})")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 hardware_touch.py <x> <y> [hold_ms]")
        return

    x_view = int(sys.argv[1])
    y_view = int(sys.argv[2])
    hold_ms = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    x_hw, y_hw = transform_coords(x_view, y_view)
    send_touch_adb_shell(x_hw, y_hw, hold_ms)

if __name__ == "__main__":
    main()
