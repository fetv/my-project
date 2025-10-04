#!/usr/bin/env python3
"""
Video splitting using ffmpeg bundled with moviepy
"""

import os
import time
import subprocess
from typing import List
from moviepy.config import get_setting

def get_ffmpeg_path():
    """Get the path to ffmpeg bundled with moviepy"""
    try:
        # Try to get ffmpeg from moviepy's bundled version
        ffmpeg_path = get_setting("FFMPEG_BINARY")
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            return ffmpeg_path
        
        # Fallback to system ffmpeg
        return "ffmpeg"
    except:
        return "ffmpeg"

def ffmpeg_split_video(video_path: str, num_parts: int = 3, output_dir: str = None, max_duration: int = 113) -> List[str]:
    """
    Split video into actual time segments using ffmpeg (bundled with moviepy)
    
    Args:
        video_path: Path to the video file
        num_parts: Number of parts to split into
        output_dir: Output directory
        max_duration: Maximum duration per part in seconds (default: 113 seconds = 1:53 minutes)
    
    Returns:
        List of output file paths
    """
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return []
    
    if output_dir is None:
        output_dir = os.path.dirname(video_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_files = []
    
    print(f"🎬 FFMPEG splitting video into {num_parts} parts")
    print(f"📁 Output directory: {output_dir}")
    
    try:
        # Get ffmpeg path
        ffmpeg_path = get_ffmpeg_path()
        print(f"🔧 Using ffmpeg: {ffmpeg_path}")
        
        # Get video duration using moviepy (more reliable)
        print("📹 Getting video duration...")
        
        try:
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            duration = video.duration
            video.close()
            print(f"✅ Got duration via moviepy: {duration:.1f} seconds")
        except Exception as e:
            print(f"❌ Failed to get duration: {e}")
            return []
        
        # Calculate parts based on maximum duration limit
        max_duration_seconds = max_duration
        part_duration = max_duration_seconds  # Each part is exactly 113 seconds
        
        # Calculate how many full parts we can create
        max_possible_parts = int(duration // part_duration)
        actual_num_parts = min(num_parts, max_possible_parts)
        
        # Ensure we have at least one part if video is long enough
        if duration >= 3.0:  # Minimum 3 seconds for TikTok
            actual_num_parts = max(1, actual_num_parts)
        
        print(f"📊 Video duration: {duration:.1f}s, Max part duration: {max_duration_seconds}s")
        print(f"📊 Creating {actual_num_parts} parts (each {part_duration}s)")
        print(f"📊 Max possible parts: {max_possible_parts}")
        
        for i in range(actual_num_parts):
            start_time = i * part_duration
            
            # Check if we have enough video content for this part
            if start_time >= duration:
                print(f"⚠️ Part {i+1}: Not enough video content (start time {start_time:.1f}s >= duration {duration:.1f}s)")
                break
                
            end_time = min((i + 1) * part_duration, duration)
            
            # Check if part duration is too short (TikTok minimum is ~3 seconds)
            part_actual_duration = end_time - start_time
            if part_actual_duration < 3.0:
                print(f"⚠️ Part {i+1}: Duration too short ({part_actual_duration:.1f}s < 3s), skipping")
                continue
            
            output_file = os.path.join(output_dir, f"{base_name}_part_{i+1}.mp4")
            
            print(f"✂️ Creating part {i+1}/{actual_num_parts}: {start_time:.1f}s - {end_time:.1f}s")
            
            # Use ffmpeg to extract segment without re-encoding (FASTEST)
            cmd = [
                ffmpeg_path, '-i', video_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-c', 'copy',  # Copy streams without re-encoding
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Overwrite output files
                output_file
            ]
            
            try:
                # Run ffmpeg command with hidden console window (Windows)
                if hasattr(subprocess, 'STARTUPINFO'):  # Windows only
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ Part {i+1} created: {file_size} bytes")
                    output_files.append(output_file)
                else:
                    print(f"❌ Failed to create part {i+1}")
                    if result.stderr:
                        print(f"Error: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ Error creating part {i+1}: {e}")
        
    except Exception as e:
        print(f"❌ Error processing video: {e}")
        return []
    
    print(f"🎉 FFMPEG splitting completed: {len(output_files)} parts created")
    return output_files

def test_ffmpeg_split():
    """Test the ffmpeg splitting function"""
    print("🎬 Testing FFMPEG Video Splitting")
    print("=" * 50)
    
    # Test video path
    test_video = "VideosDirPath/test_video.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Test video not found. Please run test_basic_download.py first.")
        return False
    
    print(f"📁 Testing with video: {test_video}")
    print(f"📊 File size: {os.path.getsize(test_video)} bytes")
    
    # Test with different part counts
    for num_parts in [2, 3]:
        print(f"\n🔧 Testing with {num_parts} parts...")
        
        start_time = time.time()
        
        # Split the video
        result = ffmpeg_split_video(test_video, num_parts)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result:
            print(f"✅ Split into {len(result)} parts in {duration:.1f} seconds")
            print(f"⚡ Average time per part: {duration/num_parts:.1f} seconds")
        
        else:
            print(f"❌ Failed to split into {num_parts} parts")
    
    return True

if __name__ == "__main__":
    test_ffmpeg_split()
