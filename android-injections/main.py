#!/usr/bin/env python3
"""
Main entry point for Android Injections application.
This script enables running the app from the root directory.
"""

import sys
import os

# Add src/ to Python path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from android_injections.main import main

if __name__ == '__main__':
    main()
