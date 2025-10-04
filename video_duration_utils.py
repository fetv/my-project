#!/usr/bin/env python3
"""
Video Duration Utilities for TikTok Auto-Uploader
Handles video duration requirements and extensions
"""

import os
import subprocess
import tempfile
from typing import Tuple, Optional
from moviepy.editor import VideoFileClip, concatenate_videoclips, ColorClip

def get_ffmpeg_path() -> str:
    """Get the path to ffmpeg executable"""
    # Try to find ffmpeg in the current directory first (bundled version)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_paths = [
        os.path.join(current_dir, "ffmpeg.exe"),  # Windows
        os.path.join(current_dir, "ffmpeg"),      # Linux/Mac
        "ffmpeg"  # System PATH
    ]
    
    for path in ffmpeg_paths:
        if os.path.exists(path) or path == "ffmpeg":
            return path
    
    return "ffmpeg"  # Fallback to system PATH

def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds using moviepy
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds
    """
    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        video.close()
        return duration
    except Exception as e:
        print(f"❌ Failed to get video duration: {e}")
        return 0.0

def check_video_duration_requirements(video_path: str) -> Tuple[bool, str, float]:
    """
    Check if video meets TikTok duration requirements
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Tuple of (is_valid, message, duration)
    """
    duration = get_video_duration(video_path)
    
    if duration == 0:
        return False, "Failed to get video duration", 0.0
    
    # TikTok requirements:
    # - Minimum: ~3 seconds
    # - Maximum: 10 minutes (600 seconds)
    # - Our custom requirement: Only upload videos less than 2 minutes (120 seconds)
    
    if duration < 3.0:
        return False, f"Video too short ({duration:.1f}s < 3s minimum)", duration
    elif duration > 120.0:
        return False, f"Video too long ({duration:.1f}s > 120s limit)", duration
    else:
        return True, f"Video duration OK ({duration:.1f}s)", duration

def extend_video_to_minimum_duration(video_path: str, target_duration: float = 63.0) -> Optional[str]:
    """
    Extend video to minimum duration by looping from the beginning
    
    Args:
        video_path: Path to the input video
        target_duration: Target duration in seconds (default 63s = 1.03 minutes)
        
    Returns:
        Path to the extended video file, or None if failed
    """
    try:
        print(f"🔄 Extending video to {target_duration:.1f} seconds by looping...")
        
        # Load the original video
        video = VideoFileClip(video_path)
        original_duration = video.duration
        
        if original_duration >= target_duration:
            print(f"✅ Video already meets minimum duration ({original_duration:.1f}s >= {target_duration:.1f}s)")
            video.close()
            return video_path
        
        print(f"📏 Original duration: {original_duration:.1f}s")
        print(f"📏 Target duration: {target_duration:.1f}s")
        
        # Calculate how many times we need to loop the video
        # We'll play the full video, then loop from beginning to fill the remaining time
        remaining_time = target_duration - original_duration
        print(f"📏 Remaining time to fill: {remaining_time:.1f}s")
        
        # Create clips list: [original_video, looped_portion]
        clips = [video]
        
        # Add looped portion from the beginning
        if remaining_time > 0:
            # Create a subclip from the beginning of the video
            # We'll take the minimum of the remaining time or the full video duration
            loop_duration = min(remaining_time, original_duration)
            loop_clip = video.subclip(0, loop_duration)
            clips.append(loop_clip)
            
            print(f"🔄 Adding {loop_duration:.1f}s loop from beginning")
        
        # Concatenate all clips
        extended_video = concatenate_videoclips(clips)
        
        # Create output path
        base_name = os.path.splitext(video_path)[0]
        output_path = f"{base_name}_extended.mp4"
        
        print(f"💾 Saving extended video to: {output_path}")
        
        # Write the extended video
        extended_video.write_videofile(
            output_path,
            verbose=False,
            logger=None,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            threads=4,
            audio=True,
            temp_audiofile=None,
            remove_temp=True,
            audio_fps=22050,
            audio_nbytes=2,
            audio_bufsize=1000,
            ffmpeg_params=[
                '-strict', 'experimental',
                '-movflags', '+faststart',
                '-tune', 'fastdecode',
                '-crf', '28'
            ]
        )
        
        # Clean up
        video.close()
        extended_video.close()
        if len(clips) > 1:
            clips[1].close()  # Close the loop clip
        
        # Verify the extended video
        final_duration = get_video_duration(output_path)
        print(f"✅ Video extended successfully: {final_duration:.1f}s")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Failed to extend video: {e}")
        return None

def process_video_for_upload(video_path: str, log_callback=None) -> Tuple[bool, str, Optional[str]]:
    """
    Process video according to duration requirements
    
    Args:
        video_path: Path to the video file
        log_callback: Optional callback function for logging
        
    Returns:
        Tuple of (should_upload, message, processed_video_path)
    """
    def log(message, level="info"):
        if log_callback:
            log_callback(message, level)
        else:
            print(f"[{level.upper()}] {message}")
    
    try:
        # Check duration requirements
        is_valid, message, duration = check_video_duration_requirements(video_path)
        
        if not is_valid:
            log(f"❌ Video rejected: {message}", "error")
            return False, message, None
        
        log(f"✅ Duration check passed: {message}", "success")
        
        # If video is less than 1 minute (60 seconds), extend it to 1.03 minutes (63 seconds)
        if duration < 60.0:
            log(f"🔄 Video duration ({duration:.1f}s) is less than 1 minute, extending to 1.03 minutes...", "info")
            
            extended_path = extend_video_to_minimum_duration(video_path, 63.0)
            if extended_path:
                log(f"✅ Video extended successfully to 1.03 minutes", "success")
                return True, "Video extended to 1.03 minutes", extended_path
            else:
                log(f"❌ Failed to extend video", "error")
                return False, "Failed to extend video", None
        else:
            # Video is between 1-2 minutes, upload as-is
            log(f"✅ Video duration ({duration:.1f}s) is acceptable for upload", "success")
            return True, "Video ready for upload", video_path
            
    except Exception as e:
        error_msg = f"Error processing video: {e}"
        log(error_msg, "error")
        return False, error_msg, None

def cleanup_extended_video(video_path: str):
    """
    Clean up extended video file if it's different from the original
    
    Args:
        video_path: Path to the video file to clean up
    """
    try:
        if video_path and os.path.exists(video_path) and "_extended" in video_path:
            os.remove(video_path)
            print(f"🧹 Cleaned up extended video: {video_path}")
    except Exception as e:
        print(f"⚠️ Failed to clean up extended video {video_path}: {e}")
