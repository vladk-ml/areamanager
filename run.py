import os
import sys
import subprocess
from pathlib import Path

def run_app():
    """Run the Streamlit app"""
    try:
        # Ensure we're in the project directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Get the streamlit executable path
        streamlit_path = str(Path("venv/Scripts/streamlit.exe" if os.name == "nt" else "venv/bin/streamlit"))
        
        if not os.path.exists(streamlit_path):
            print("Error: Virtual environment not found. Please run install.py first.")
            sys.exit(1)
        
        # Run the app
        print("Starting AreaManager app...")
        subprocess.run([streamlit_path, "run", "app/main.py"])
        
    except Exception as e:
        print(f"Error running app: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    run_app()
