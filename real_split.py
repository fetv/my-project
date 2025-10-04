#!/usr/bin/env python3
"""
Real video splitting that actually crops videos into time segments
"""

import os
import time
from typing import List
from moviepy.editor import VideoFileClip

def real_split_video(video_path: str, num_parts: int = 3, output_dir: str = None) -> List[str]:
    """
    Split video into actual time segments (crops the video)
    
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
    
    print(f"🎬 REAL splitting video into {num_parts} parts")
    print(f"📁 Output directory: {output_dir}")
    
    try:
        # Load video once
        print("📹 Loading video...")
        video = VideoFileClip(video_path)
        duration = video.duration
        
        print(f"⏱️ Video duration: {duration:.1f} seconds")
        part_duration = duration / num_parts
        
        for i in range(num_parts):
            start_time = i * part_duration
            end_time = min((i + 1) * part_duration, duration)
            
            output_file = os.path.join(output_dir, f"{base_name}_part_{i+1}.mp4")
            
            print(f"✂️ Creating part {i+1}/{num_parts}: {start_time:.1f}s - {end_time:.1f}s")
            
            try:
                # Extract the time segment
                part_video = video.subclip(start_time, end_time)
                
                # Write with optimized settings for speed
                part_video.write_videofile(
                    output_file,
                    verbose=False,
                    logger=None,
                    codec='libx264',
                    audio_codec='aac',
                    preset='ultrafast',  # Fastest encoding
                    threads=4,
                    audio=True,
                    temp_audiofile=None,
                    remove_temp=True,
                    audio_fps=22050,  # Lower audio quality for speed
                    audio_nbytes=2,
                    audio_bufsize=1000,
                    ffmpeg_params=[
                        '-strict', 'experimental',
                        '-movflags', '+faststart',
                        '-tune', 'fastdecode',
                        '-crf', '28'  # Higher compression (faster)
                    ]
                )
                
                # Close the part video to free memory
                part_video.close()
                
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ Part {i+1} created: {file_size} bytes")
                    output_files.append(output_file)
                else:
                    print(f"❌ Failed to create part {i+1}")
                    
            except Exception as e:
                print(f"❌ Error creating part {i+1}: {e}")
        
        # Close the main video
        video.close()
        
    except Exception as e:
        print(f"❌ Error loading video: {e}")
        return []
    
    print(f"🎉 Real splitting completed: {len(output_files)} parts created")
    return output_files

def test_real_split():
    """Test the real splitting function"""
    print("🎬 Testing Real Video Splitting")
    print("=" * 50)
    
    # Test video path
    test_video = "VideosDirPath/test_video.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Test video not found. Please run test_basic_download.py first.")
        return False
    
    print(f"📁 Testing with video: {test_video}")
    print(f"📊 File size: {os.path.getsize(test_video)} bytes")
    
    # Test with different part counts
    for num_parts in [5]:
        print(f"\n🔧 Testing with {num_parts} parts...")
        
        start_time = time.time()
        
        # Split the video
        result = real_split_video(test_video, num_parts)
        
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
    test_real_split()
