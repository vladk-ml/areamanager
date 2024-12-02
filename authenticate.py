import os
import sys
import subprocess
from pathlib import Path

def authenticate_gee():
    """Authenticate Google Earth Engine with specific project ID"""
    # Ensure we're in the areamanager directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    python_cmd = str(Path("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python"))
    
    print("\nAuthenticating with Google Earth Engine...")
    print("Make sure you're logged into your Google account in your default browser.")
    
    try:
        subprocess.run([python_cmd, "-c", """
import ee
try:
    ee.Authenticate()
    ee.Initialize(project='ee-sergiyk1974')
    print('\\n✓ Google Earth Engine authentication completed successfully!')
except Exception as e:
    print(f'\\n❌ Authentication failed: {str(e)}')
"""], check=True)
    except subprocess.CalledProcessError:
        print("\n❌ Authentication process failed.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        authenticate_gee()
    except KeyboardInterrupt:
        print("\n\nAuthentication cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
