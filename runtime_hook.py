# Runtime hook for executable-specific fixes
import os
import sys

def fix_executable_paths():
    """Fix paths when running in executable mode"""
    if getattr(sys, 'frozen', False):
        # Running in executable mode
        base_path = os.path.dirname(sys.executable)
        
        # Add base path to sys.path
        if base_path not in sys.path:
            sys.path.insert(0, base_path)
        
        # Set working directory to executable directory
        os.chdir(base_path)
        
        # Create necessary directories if they don't exist
        dirs_to_create = ['CookiesDir', 'VideosDirPath']
        for dir_name in dirs_to_create:
            dir_path = os.path.join(base_path, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

def fix_chrome_automation():
    """Fix Chrome automation issues in executable mode"""
    if getattr(sys, 'frozen', False):
        # Set environment variables for Chrome
        os.environ['CHROME_NO_SANDBOX'] = '1'
        os.environ['CHROME_DISABLE_DEV_SHM_USAGE'] = '1'
        
        # Add Chrome to PATH if not found
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                chrome_dir = os.path.dirname(chrome_path)
                if chrome_dir not in os.environ.get('PATH', ''):
                    current_path = os.environ.get('PATH', '')
                    os.environ['PATH'] = f"{chrome_dir};{current_path}"
                break

# Apply fixes
fix_executable_paths()
fix_chrome_automation()
