import ee
import folium
from datetime import datetime, timedelta

class SARManager:
    def __init__(self):
        self.collection = 'COPERNICUS/S1_GRD'
        
    def get_sar_collection(self, geometry, start_date, end_date):
        """Get Sentinel-1 SAR collection for the given area and time range"""
        return (ee.ImageCollection(self.collection)
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                .filter(ee.Filter.eq('instrumentMode', 'IW')))
    
    def create_composite(self, collection):
        """Create a composite image from the collection"""
        return collection.select('VV').mean()
    
    def add_to_map(self, m, image, vis_params=None):
        """Add SAR data to the map"""
        if vis_params is None:
            vis_params = {
                'min': -25,
                'max': 0,
                'palette': ['black', 'white']
            }
        
        map_id_dict = image.getMapId(vis_params)
        folium.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            overlay=True,
            name='SAR Data'
        ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
    
    def export_to_drive(self, image, geometry, description, folder='SAR_Exports'):
        """Export SAR data to Google Drive"""
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=folder,
            scale=10,
            region=geometry,
            maxPixels=1e9
        )
        task.start()
        return task
    
    def get_statistics(self, image, geometry):
        """Get basic statistics for the SAR data in the area"""
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.stdDev(), '', True
            ).combine(
                ee.Reducer.minMax(), '', True
            ),
            geometry=geometry,
            scale=30,
            maxPixels=1e9
        )
        return stats.getInfo()
