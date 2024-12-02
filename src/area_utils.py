import json
import os
import ee
from datetime import datetime
from typing import Dict, List, Optional

class AOIManager:
    def __init__(self, geojson_path: str = "data/areas.geojson"):
        self.geojson_path = geojson_path
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.geojson_path), exist_ok=True)
        if not os.path.exists(self.geojson_path):
            self._save_geojson({"type": "FeatureCollection", "features": []})
    
    def _load_geojson(self) -> dict:
        """Load the GeoJSON file"""
        try:
            with open(self.geojson_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"type": "FeatureCollection", "features": []}
    
    def _save_geojson(self, data: dict):
        """Save the GeoJSON file"""
        with open(self.geojson_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def list_areas(self) -> List[str]:
        """Get list of all area names"""
        data = self._load_geojson()
        return [f["properties"]["name"] for f in data["features"]]
    
    def add_area(self, name: str, coordinates: List[List[float]], description: str = ""):
        """Add a new area"""
        data = self._load_geojson()
        
        # Check if name already exists
        if name in self.list_areas():
            raise ValueError(f"Area named '{name}' already exists")
        
        # Create new feature
        feature = {
            "type": "Feature",
            "properties": {
                "name": name,
                "description": description,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates]
            }
        }
        
        data["features"].append(feature)
        self._save_geojson(data)
    
    def delete_area(self, name: str):
        """Delete an area by name"""
        data = self._load_geojson()
        data["features"] = [f for f in data["features"] if f["properties"]["name"] != name]
        self._save_geojson(data)
    
    def get_area(self, name: str) -> Optional[dict]:
        """Get area details by name"""
        data = self._load_geojson()
        for feature in data["features"]:
            if feature["properties"]["name"] == name:
                return feature
        return None
    
    def update_area(self, name: str, coordinates: Optional[List[List[float]]] = None, 
                   description: Optional[str] = None):
        """Update an existing area"""
        data = self._load_geojson()
        for feature in data["features"]:
            if feature["properties"]["name"] == name:
                if coordinates:
                    feature["geometry"]["coordinates"] = [coordinates]
                if description is not None:
                    feature["properties"]["description"] = description
                feature["properties"]["modified"] = datetime.now().isoformat()
                break
        self._save_geojson(data)
    
    def export_to_ee(self, name: str) -> ee.Feature:
        """Convert area to Earth Engine Feature"""
        area = self.get_area(name)
        if not area:
            raise ValueError(f"Area '{name}' not found")
        
        return ee.Feature(
            ee.Geometry.Polygon(area["geometry"]["coordinates"]),
            area["properties"]
        )
    
    def export_to_drive(self, names: List[str], folder: str = "AreaManager_Exports"):
        """Export selected areas to Google Drive"""
        features = []
        for name in names:
            area = self.get_area(name)
            if area:
                features.append(area)
        
        if not features:
            return None
        
        fc = {"type": "FeatureCollection", "features": features}
        task = ee.batch.Export.table.toDrive(
            collection=ee.FeatureCollection(features),
            description=f'AOI_Export_{datetime.now().strftime("%Y%m%d")}',
            folder=folder,
            fileFormat='GeoJSON'
        )
        task.start()
        return task
    
    def get_download_url(self, names: List[str]) -> str:
        """Generate download URL for selected areas"""
        features = []
        for name in names:
            area = self.get_area(name)
            if area:
                features.append(area)
        
        if not features:
            return None
            
        fc = ee.FeatureCollection(features)
        url = fc.getDownloadURL(
            filetype='GeoJSON',
            selectors=['system:index', 'name', 'description', 'created', 'modified'],
            filename='areas_export'
        )
        return url
