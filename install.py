import os
import sys
import subprocess
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    # Ensure we're in the areamanager directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    Path("data").mkdir(exist_ok=True)
    if not Path("data/areas.geojson").exists():
        with open("data/areas.geojson", "w") as f:
            f.write('{"type": "FeatureCollection", "features": []}')

def setup_venv():
    """Create and activate virtual environment"""
    if not Path("venv").exists():
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

def install_dependencies():
    """Install required packages"""
    python_cmd = str(Path("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python"))
    
    # Upgrade pip
    subprocess.run([python_cmd, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Install requirements
    subprocess.run([python_cmd, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def main():
    """Main installation process"""
    try:
        # Ensure we're in the areamanager directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        print(f"Working directory: {os.getcwd()}")
        print("Starting AreaManager installation...")
        print("1. Creating directories...")
        create_directories()
        
        print("2. Setting up virtual environment...")
        setup_venv()
        
        print("3. Installing dependencies...")
        install_dependencies()
        
        print("\nInstallation completed successfully!")
        print("To authenticate with Google Earth Engine, run: python authenticate.py")
        print("After authentication, you can run the app using: python run.py")
        
    except Exception as e:
        print(f"\nError during installation: {str(e)}")
        try:
            input("\nPress Enter to exit...")
        except EOFError:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
