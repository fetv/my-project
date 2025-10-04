#!/usr/bin/env python3
"""
Smart Video Downloader - Adapts to Internet Speed
Automatically chooses the best quality and download method based on connection speed
"""

import os
import time
import speedtest
import requests
from datetime import datetime
from pytube import YouTube
import yt_dlp

def log(message, level="info"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def test_internet_speed():
    """Test internet speed and return Mbps"""
    try:
        log("🌐 Testing internet speed...", "info")
        st = speedtest.Speedtest()
        st.get_best_server()
        
        # Test download speed
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        log(f"📥 Download Speed: {download_speed:.1f} Mbps", "success")
        
        return download_speed
    except Exception as e:
        log(f"⚠️ Speed test failed: {e}", "warning")
        log("🔄 Using default speed (10 Mbps)", "info")
        return 10.0  # Default fallback

def get_optimal_quality(speed_mbps):
    """Determine optimal video quality based on internet speed"""
    if speed_mbps >= 100:  # Ultra-fast connection
        return "1080p", "best[height<=1080][filesize<100M]/best[height<=1080]"
    elif speed_mbps >= 50:
        return "720p", "best[height<=720][filesize<50M]/best[height<=720]"
    elif speed_mbps >= 25:
        return "720p", "best[height<=720][filesize<30M]/best[height<=720]"
    elif speed_mbps >= 10:
        return "480p", "best[height<=480][filesize<20M]/best[height<=480]"
    elif speed_mbps >= 5:
        return "360p", "best[height<=360][filesize<15M]/best[height<=360]"
    else:
        return "240p", "best[height<=240][filesize<10M]/best[height<=240]"

def get_optimal_downloader(speed_mbps):
    """Choose the best downloader based on speed"""
    if speed_mbps >= 20:
        return "yt-dlp"  # Better for high speeds
    else:
        return "pytube"  # More reliable for slower speeds

def download_with_pytube(video_url, output_path, quality="720p"):
    """Download using pytube with quality selection"""
    try:
        log("🚀 Using pytube downloader...", "info")
        start_time = time.time()
        
        # Create YouTube object with better error handling
        try:
            yt = YouTube(video_url)
            log(f"📹 Video: {yt.title}", "info")
            log(f"⏱️ Duration: {yt.length} seconds", "info")
        except Exception as e:
            log(f"❌ Failed to get video info: {str(e)}", "error")
            return False
        
        # Select stream based on quality
        try:
            if quality == "1080p":
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            elif quality == "720p":
                stream = yt.streams.filter(progressive=True, file_extension='mp4', resolution='720p').first()
            elif quality == "480p":
                stream = yt.streams.filter(progressive=True, file_extension='mp4', resolution='480p').first()
            elif quality == "360p":
                stream = yt.streams.filter(progressive=True, file_extension='mp4', resolution='360p').first()
            else:
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').first()
            
            if not stream:
                log("⚠️ Quality not available, using best available", "warning")
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                log("❌ No suitable stream found", "error")
                return False
                
            log(f"✅ Selected: {stream.resolution} ({stream.filesize_mb:.1f} MB)", "success")
        except Exception as e:
            log(f"❌ Failed to select stream: {str(e)}", "error")
            return False
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Download
        log("📥 Downloading...", "info")
        download_start = time.time()
        
        try:
            stream.download(output_path=output_dir, filename=os.path.basename(output_path))
        except Exception as e:
            log(f"❌ Download failed: {str(e)}", "error")
            return False
        
        download_time = time.time() - download_start
        total_time = time.time() - start_time
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            speed = file_size / download_time  # MB/s
            
            log(f"✅ Download completed!", "success")
            log(f"📏 Size: {file_size:.1f} MB", "info")
            log(f"⏱️ Time: {download_time:.1f}s", "info")
            log(f"🚀 Speed: {speed:.1f} MB/s", "success")
            
            return True
        else:
            log("❌ Download failed - file not found or empty", "error")
            return False
            
    except Exception as e:
        log(f"❌ pytube error: {str(e)}", "error")
        return False

def download_with_ytdlp(video_url, output_path, quality_filter):
    """Download using yt-dlp with quality selection"""
    try:
        log("🚀 Using yt-dlp downloader...", "info")
        start_time = time.time()
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # yt-dlp options optimized for maximum speed
        ydl_opts = {
            'format': quality_filter,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10,  # Reduced for faster connections
            'retries': 1,  # Minimal retries
            'fragment_retries': 2,  # Minimal fragment retries
            'concurrent_fragment_downloads': 32,  # Maximum parallel downloads
            'buffersize': 8192,  # Larger buffer for speed
            'nocheckcertificate': True,
            'no_check_certificate': True,
            'max_sleep_interval': 2,  # Maximum sleep interval
            'sleep_interval': 0.5,  # Minimal sleep interval
            'external_downloader': 'aria2c',  # Use aria2c if available
            'external_downloader_args': ['--max-connection-per-server=16', '--min-split-size=1M', '--split=16'],
        }
        
        # Download
        log("📥 Downloading...", "info")
        download_start = time.time()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        download_time = time.time() - download_start
        total_time = time.time() - start_time
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            speed = file_size / download_time  # MB/s
            
            log(f"✅ Download completed!", "success")
            log(f"📏 Size: {file_size:.1f} MB", "info")
            log(f"⏱️ Time: {download_time:.1f}s", "info")
            log(f"🚀 Speed: {speed:.1f} MB/s", "success")
            
            return True
        else:
            log("❌ Download failed", "error")
            return False
            
    except Exception as e:
        log(f"❌ yt-dlp error: {str(e)}", "error")
        return False

def smart_download(video_url, output_path):
    """Smart download that adapts to internet speed"""
    try:
        log("🧠 Starting smart download...", "info")
        
        # Test internet speed
        speed_mbps = test_internet_speed()
        
        # Determine optimal quality and downloader
        quality, quality_filter = get_optimal_quality(speed_mbps)
        downloader = get_optimal_downloader(speed_mbps)
        
        log(f"📊 Speed: {speed_mbps:.1f} Mbps", "info")
        log(f"🎯 Optimal Quality: {quality}", "success")
        log(f"🔧 Optimal Downloader: {downloader}", "success")
        
        # Download with selected method
        if downloader == "pytube":
            success = download_with_pytube(video_url, output_path, quality)
        else:
            success = download_with_ytdlp(video_url, output_path, quality_filter)
        
        # Fallback if primary method fails
        if not success:
            log("🔄 Primary method failed, trying fallback...", "warning")
            if downloader == "pytube":
                success = download_with_ytdlp(video_url, output_path, "best")
            else:
                success = download_with_pytube(video_url, output_path, "480p")
        
        return success
        
    except Exception as e:
        log(f"❌ Smart download error: {str(e)}", "error")
        return False

def main():
    """Main function"""
    log("🎬 Smart Video Downloader", "info")
    log("="*50, "info")
    
    # Get video URL from user
    video_url = input("Enter YouTube URL: ").strip()
    
    if not video_url:
        log("❌ No URL provided", "error")
        return
    
    # Generate output filename
    try:
        yt = YouTube(video_url)
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_path = f"smart_download_{safe_title}.mp4"
    except:
        output_path = "smart_download_video.mp4"
    
    # Start smart download
    log(f"🎯 Target: {output_path}", "info")
    
    success = smart_download(video_url, output_path)
    
    if success:
        log("🎉 Download completed successfully!", "success")
        log(f"📁 File saved as: {output_path}", "info")
    else:
        log("❌ Download failed", "error")

if __name__ == "__main__":
    main()
