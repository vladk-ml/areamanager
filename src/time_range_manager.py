import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class TimeRangeManager:
    def __init__(self, json_path: str = "data/timeranges.json"):
        self.json_path = json_path
        self._ensure_data_dir()
        self._load_timeranges()

    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)

    def _load_timeranges(self):
        """Load time ranges from storage"""
        if os.path.exists(self.json_path):
            with open(self.json_path, 'r') as f:
                self.timeranges = json.load(f)
        else:
            self.timeranges = {}
            self._save_timeranges()

    def _save_timeranges(self):
        """Save time ranges to storage"""
        with open(self.json_path, 'w') as f:
            json.dump(self.timeranges, f, indent=2)

    def save_timerange(self, name: str, start_date: str, end_date: str) -> bool:
        """Save a new time range"""
        try:
            # Validate dates
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
            
            self.timeranges[name] = {
                "start_date": start_date,
                "end_date": end_date,
                "timestamp": datetime.now().isoformat()
            }
            self._save_timeranges()
            return True
        except ValueError:
            return False

    def get_timerange(self, name: str) -> Optional[Dict[str, str]]:
        """Get a time range by name"""
        return self.timeranges.get(name)

    def list_timeranges(self) -> List[str]:
        """List all saved time ranges"""
        return list(self.timeranges.keys())

    def delete_timerange(self, name: str) -> bool:
        """Delete a time range"""
        if name in self.timeranges:
            del self.timeranges[name]
            self._save_timeranges()
            return True
        return False

    def clear_all(self):
        """Clear all time ranges"""
        self.timeranges = {}
        self._save_timeranges()
