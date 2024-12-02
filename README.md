# AreaManager

A cross-platform demo application for viewing SAR data and managing Areas of Interest (AOIs) using Google Earth Engine.

## Features

- Simple, clean interface
- SAR data visualization
- AOI management (Create, Edit, Delete)
- Export capabilities (Google Drive, Direct Download)
- Cross-platform compatibility (Windows, MacOS)
- Persistent AOI storage

## Quick Start

### First Time Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/areamanager.git
cd areamanager
```

2. Create and activate a virtual environment:

Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

MacOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Authenticate with Google Earth Engine:
```bash
earthengine authenticate
```

### Running the App

Windows:
```bash
run_app.bat
```

MacOS/Linux:
```bash
chmod +x run_app.sh
./run_app.sh
```

The app will open in your default web browser at `http://localhost:8501`

## Project Structure

```
areamanager/
├── app/
│   └── main.py          # Main Streamlit application
├── src/
│   └── area_utils.py    # AOI management utilities
├── data/
│   └── areas.geojson    # Persistent AOI storage
├── run_app.bat          # Windows launcher
├── run_app.sh           # MacOS/Linux launcher
└── requirements.txt     # Project dependencies
```

## Data Persistence

AOIs are stored in `data/areas.geojson`, which:
- Persists across sessions
- Can be version controlled
- Is platform-independent
- Can be easily shared between machines

## Notes

- The app requires an active internet connection for Google Earth Engine access
- First-time setup requires Google Earth Engine authentication
- AOIs are stored locally and can be backed up or synced via git
