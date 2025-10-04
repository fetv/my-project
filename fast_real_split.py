#!/usr/bin/env python3
"""
Fast video splitting using ffmpeg directly (much faster than moviepy)
"""

import os
import subprocess
import time
from typing import List

def fast_real_split_video(video_path: str, num_parts: int = 3, output_dir: str = None) -> List[str]:
    """
    Split video into actual time segments using ffmpeg directly (MUCH FASTER)
    
    Args:
        video_path: Path to the video file
        num_parts: Number of parts to split into
        output_dir: Output directory
    
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
    
    print(f"⚡ FAST REAL splitting video into {num_parts} parts")
    print(f"📁 Output directory: {output_dir}")
    
    try:
        # Get video duration using ffprobe
        print("📹 Getting video duration...")
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ]
        # Run ffprobe command with hidden console window (Windows)
        if hasattr(subprocess, 'STARTUPINFO'):  # Windows only
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to get video duration: {result.stderr}")
            return []
        
        duration = float(result.stdout.strip())
        print(f"⏱️ Video duration: {duration:.1f} seconds")
        
        part_duration = duration / num_parts
        
        for i in range(num_parts):
            start_time = i * part_duration
            end_time = min((i + 1) * part_duration, duration)
            
            output_file = os.path.join(output_dir, f"{base_name}_part_{i+1}.mp4")
            
            print(f"✂️ Creating part {i+1}/{num_parts}: {start_time:.1f}s - {end_time:.1f}s")
            
            # Use ffmpeg to extract segment without re-encoding (FASTEST)
            cmd = [
                'ffmpeg', '-i', video_path,
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
    
    print(f"🎉 Fast real splitting completed: {len(output_files)} parts created")
    return output_files

def test_fast_real_split():
    """Test the fast real splitting function"""
    print("⚡ Testing Fast Real Video Splitting")
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
        result = fast_real_split_video(test_video, num_parts)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result:
            print(f"✅ Split into {len(result)} parts in {duration:.1f} seconds")
            print(f"⚡ Average time per part: {duration/num_parts:.1f} seconds")
            
            # Clean up test files
            for part_file in result:
                try:
                    os.remove(part_file)
                    print(f"🧹 Cleaned up: {os.path.basename(part_file)}")
                except:
                    pass
        else:
            print(f"❌ Failed to split into {num_parts} parts")
    
    return True

if __name__ == "__main__":
    test_fast_real_split()
