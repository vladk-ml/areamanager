import os
import sys
import signal
import psutil
import shutil
from pathlib import Path

def kill_streamlit_processes():
    """Kill all running Streamlit processes"""
    killed = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if it's a Streamlit process
            if proc.info['cmdline'] and 'streamlit' in ' '.join(proc.info['cmdline']):
                print(f"Killing Streamlit process: {proc.info['pid']}")
                psutil.Process(proc.info['pid']).kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed

def clear_cache():
    """Clear Streamlit cache"""
    cache_dir = Path.home() / ".streamlit"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print("Cleared Streamlit cache")

def remove_venv():
    """Remove virtual environment"""
    venv_path = Path("venv")
    if venv_path.exists():
        shutil.rmtree(venv_path)
        print("Removed virtual environment")

def main():
    """Main cleanup process"""
    try:
        # Ensure we're in the project directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        print("Starting cleanup...")
        
        # Kill Streamlit processes
        if kill_streamlit_processes():
            print("Killed running Streamlit processes")
        else:
            print("No running Streamlit processes found")
        
        # Clear cache
        clear_cache()
        
        # Remove virtual environment
        remove_venv()
        
        print("\nCleanup completed successfully!")
        print("You can reinstall the app using: python install.py")
        
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
