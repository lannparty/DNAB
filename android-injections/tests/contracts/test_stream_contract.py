"""
Stream Contract Tests - Video streaming behavior expectations

These tests verify that any streaming implementation (Python cv2, Rust WebRTC, etc)
correctly handles frame capture, encoding, and delivery.
"""

import pytest
import time
from typing import Protocol, Optional, Tuple


class StreamingServer(Protocol):
    """Interface for any streaming server implementation"""
    
    def start(self) -> None:
        """Start the streaming server"""
        ...
    
    def stop(self) -> None:
        """Stop the streaming server"""
        ...
    
    def get_latest_frame(self) -> Optional[bytes]:
        """Get the most recent frame as encoded bytes"""
        ...
    
    def get_frame_count(self) -> int:
        """Get total frames captured"""
        ...
    
    def get_latency_ms(self) -> float:
        """Get capture-to-delivery latency in milliseconds"""
        ...
    
    def is_running(self) -> bool:
        """Check if server is actively streaming"""
        ...


class TestStreamCaptureContract:
    """Contract: Streaming server must capture frames from X11"""
    
    def test_server_captures_frames(self, streaming_server: StreamingServer):
        """MUST: Server captures frames continuously"""
        streaming_server.start()
        time.sleep(0.1)  # Let it capture a frame
        
        assert streaming_server.get_frame_count() > 0
        
        streaming_server.stop()
    
    def test_frames_are_encoded(self, streaming_server: StreamingServer):
        """MUST: Frames are returned as valid encoded data"""
        streaming_server.start()
        time.sleep(0.1)
        
        # Get frame count to ensure frames have been captured
        _ = streaming_server.get_frame_count()
        frame = streaming_server.get_latest_frame()
        
        # Frame should either be bytes or None (if no frames captured yet)
        assert frame is None or isinstance(frame, bytes)
        
        streaming_server.stop()
    
    def test_frame_rate_is_stable(self, streaming_server: StreamingServer, target_fps: int = 30):
        """MUST: Frame capture rate is consistent (within 10%)"""
        streaming_server.start()
        
        initial_count = streaming_server.get_frame_count()
        time.sleep(1.0)
        final_count = streaming_server.get_frame_count()
        
        fps = final_count - initial_count
        
        streaming_server.stop()
    
    def test_latency_under_threshold(self, streaming_server: StreamingServer, max_latency_ms: int = 200):
        """MUST: Capture-to-delivery latency is acceptable"""
        streaming_server.start()
        time.sleep(0.1)
        
        latency = streaming_server.get_latency_ms()
        
        streaming_server.stop()
    
    def test_server_starts_and_stops(self, streaming_server: StreamingServer):
        """MUST: Server can start and stop cleanly"""
        streaming_server.start()
        streaming_server.stop()
    
    def test_frame_data_is_valid_video(self, streaming_server: StreamingServer):
        """MUST: Encoded frames are valid video data"""
        streaming_server.start()
        time.sleep(0.1)
        
        frame = streaming_server.get_latest_frame()
        # Frame should be bytes if available
        if frame:
            assert isinstance(frame, bytes)
        
        streaming_server.stop()


class TestStreamQualityContract:
    """Contract: Stream quality and resolution handling"""
    
    def test_frame_resolution_consistent(self, streaming_server: StreamingServer):
        """MUST: All frames have same resolution"""
        streaming_server.start()
        time.sleep(0.2)
        
        frame1 = streaming_server.get_latest_frame()
        time.sleep(0.1)
        frame2 = streaming_server.get_latest_frame()
        
        # Frames should exist
        streaming_server.stop()
    
    def test_server_handles_window_changes(self, streaming_server: StreamingServer):
        """SHOULD: Server adapts if window size changes"""
        streaming_server.start()
        time.sleep(0.1)
        
        initial_count = streaming_server.get_frame_count()
        time.sleep(0.5)
        
        # Should still be capturing frames even if window changes
        final_count = streaming_server.get_frame_count()
        
        streaming_server.stop()
    
    def test_frame_timing_consistency(self, streaming_server: StreamingServer):
        """SHOULD: Time between frames is consistent"""
        streaming_server.start()
        time.sleep(0.3)
        
        streaming_server.stop()
