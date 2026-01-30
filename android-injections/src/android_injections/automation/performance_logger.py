"""Performance logging for auto-touch operations to identify bottlenecks."""

import time
import os
from pathlib import Path
from datetime import datetime


class PerformanceLogger:
    """Logger for tracking timing of auto-touch operations."""
    
    def __init__(self, log_dir=None):
        """Initialize performance logger with log directory."""
        if log_dir is None:
            # Default to log directory at repo root
            repo_root = Path(__file__).parent.parent.parent.parent.parent
            log_dir = repo_root / "log"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"auto_performance_{timestamp}.log"
        
        # Write header
        with open(self.log_file, 'w') as f:
            f.write(f"Auto-Touch Performance Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
        
        self.timings = {}
        self.frame_start = None
    
    def start_frame(self):
        """Mark the start of a frame update."""
        self.frame_start = time.perf_counter()
        self.timings = {}
    
    def log_timing(self, operation, duration_ms):
        """Log timing for a specific operation."""
        self.timings[operation] = duration_ms
    
    def end_frame(self):
        """End frame and write all timings to log."""
        if self.frame_start is None:
            return
        
        total_frame_time = (time.perf_counter() - self.frame_start) * 1000
        
        with open(self.log_file, 'a') as f:
            f.write(f"Frame @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}\n")
            f.write(f"  Total frame time: {total_frame_time:.3f}ms\n")
            
            for operation, duration in self.timings.items():
                percentage = (duration / total_frame_time * 100) if total_frame_time > 0 else 0
                f.write(f"  {operation}: {duration:.3f}ms ({percentage:.1f}%)\n")
            
            f.write("\n")
        
        self.frame_start = None
        self.timings = {}


# Global logger instance
_logger = None


def get_logger():
    """Get or create the global performance logger."""
    global _logger
    if _logger is None:
        _logger = PerformanceLogger()
    return _logger


def log_operation(operation_name):
    """Decorator to log timing of an operation."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            
            logger = get_logger()
            logger.log_timing(operation_name, duration_ms)
            
            return result
        return wrapper
    return decorator
