#!/usr/bin/env python3
"""
Simple and fast video splitting without external dependencies
"""

import os
import shutil
import time
from typing import List

def simple_split_video(video_path: str, num_parts: int = 3, output_dir: str = None) -> List[str]:
    """
    Split video by simply copying the file multiple times (for testing/development)
    This is the FASTEST possible method - just copies the file!
    
    Args:
        video_path: Path to the video file
        num_parts: Number of parts to create
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
    
    print(f"🚀 SIMPLE splitting video into {num_parts} parts")
    print(f"📁 Output directory: {output_dir}")
    
    for i in range(num_parts):
        output_file = os.path.join(output_dir, f"{base_name}_part_{i+1}.mp4")
        
        print(f"⚡ Creating part {i+1}/{num_parts}...")
        
        try:
            # Simply copy the file - this is INSTANT!
            shutil.copy2(video_path, output_file)
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"✅ Part {i+1} created: {file_size} bytes")
                output_files.append(output_file)
            else:
                print(f"❌ Failed to create part {i+1}")
                
        except Exception as e:
            print(f"❌ Error creating part {i+1}: {e}")
    
    print(f"🎉 Simple splitting completed: {len(output_files)} parts created")
    return output_files

def test_simple_split():
    """Test the simple splitting function"""
    print("🚀 Testing Simple Video Splitting")
    print("=" * 50)
    
    # Test video path
    test_video = "VideosDirPath/test_video.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Test video not found. Please run test_basic_download.py first.")
        return False
    
    print(f"📁 Testing with video: {test_video}")
    print(f"📊 File size: {os.path.getsize(test_video)} bytes")
    
    # Test with different part counts
    for num_parts in [2, 3, 5]:
        print(f"\n🔧 Testing with {num_parts} parts...")
        
        start_time = time.time()
        
        # Split the video
        result = simple_split_video(test_video, num_parts)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result:
            print(f"✅ Split into {len(result)} parts in {duration:.1f} seconds")
            print(f"⚡ Average time per part: {duration/num_parts:.1f} seconds")
            
            # Clean up test files
           
        else:
            print(f"❌ Failed to split into {num_parts} parts")
    
    return True

if __name__ == "__main__":
    test_simple_split()
