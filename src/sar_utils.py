import ee
import folium
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class SARData:
    """Container for SAR data and its metadata"""
    composite: ee.Image
    collection_size: int
    bounds: Dict[str, Any]
    timestamp: str

class SARManager:
    def __init__(self):
        self.collection = 'COPERNICUS/S1_GRD'
    
    def process_area(self, geometry: ee.Geometry, start_date: str, end_date: str) -> Optional[SARData]:
        """Process an area to get SAR data. Returns None if no data available."""
        try:
            # Validate geometry
            if not isinstance(geometry, ee.Geometry):
                raise ValueError("Invalid geometry type. Expected ee.Geometry")
            
            # Get the collection
            collection = (ee.ImageCollection(self.collection)
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')))
            
            # Check collection size
            size = collection.size().getInfo()
            if size == 0:
                logger.warning(f"No SAR data found for date range {start_date} to {end_date}")
                return None
            
            # Create composite
            composite = self._create_composite(collection)
            
            # Get bounds for export
            bounds = geometry.bounds().getInfo()
            
            return SARData(
                composite=composite,
                collection_size=size,
                bounds=bounds,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error processing SAR data: {str(e)}", exc_info=True)
            raise
    
    def _create_composite(self, collection: ee.ImageCollection) -> ee.Image:
        """Create a composite image from the collection"""
        return collection.map(lambda img: img.select('VV')
                        .clip(img.geometry())
                        .focal_median(50, 'circle', 'meters')
                        .unitScale(-30, 5)
                        .multiply(255)
                        ).mean()
    
    def add_to_map(self, m: folium.Map, sar_data: SARData) -> None:
        """Add SAR data to the map"""
        try:
            vis_params = {
                'min': 0,
                'max': 255,
                'palette': ['black', 'white']
            }
            
            map_id_dict = sar_data.composite.getMapId(vis_params)
            
            # Create layer
            layer = folium.TileLayer(
                tiles=map_id_dict['tile_fetcher'].url_format,
                attr='Google Earth Engine',
                name=f'SAR Data ({sar_data.timestamp})',
                overlay=True,
                opacity=0.7
            )
            
            # Add layer
            layer.add_to(m)
            
            # Ensure layer control exists
            if not hasattr(m, '_children') or not any(isinstance(child, folium.LayerControl) for child in m._children.values()):
                folium.LayerControl().add_to(m)
                
        except Exception as e:
            logger.error(f"Error adding SAR data to map: {str(e)}", exc_info=True)
            raise
    
    def start_export(self, sar_data: SARData, geometry: ee.Geometry, description: str) -> ee.batch.Task:
        """Start export task for SAR data"""
        try:
            # Scale back to dB values for export
            export_image = sar_data.composite.multiply(35).add(-30)
            
            # Start export task
            task = ee.batch.Export.image.toDrive(
                image=export_image,
                description=description,
                folder='SAR_Exports',
                scale=10,
                region=geometry,
                maxPixels=1e10,
                fileFormat='GeoTIFF',
                formatOptions={'cloudOptimized': True}
            )
            
            task.start()
            logger.info(f"Export task started: {description}")
            return task
            
        except Exception as e:
            logger.error(f"Error starting export: {str(e)}", exc_info=True)
            raise
    
    def get_statistics(self, sar_data: SARData, geometry: ee.Geometry) -> Dict[str, Any]:
        """Get basic statistics for the SAR data in the area"""
        stats = sar_data.composite.reduceRegion(
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
    
    def preview_query(self, geometry: ee.Geometry, start_date: str, end_date: str) -> Dict[str, Any]:
        """Preview the query without processing data"""
        try:
            # Get the collection
            collection = (ee.ImageCollection(self.collection)
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')))
            
            # Get collection size
            size = collection.size().getInfo()
            
            # Calculate area size
            area_size = geometry.area().divide(1e6).getInfo()  # Convert to km²
            
            # Get bounds
            bounds = geometry.bounds().getInfo()
            
            # Estimate data size (rough estimate: 2MB per image)
            estimated_size = size * 2  # MB
            
            return {
                'query_params': {
                    'collection': self.collection,
                    'polarization': 'VV',
                    'instrument_mode': 'IW',
                    'orbit': 'DESCENDING'
                },
                'area_info': {
                    'size_km2': round(area_size, 2),
                    'bounds': bounds
                },
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'results_preview': {
                    'image_count': size,
                    'estimated_size_mb': estimated_size
                }
            }
            
        except Exception as e:
            logger.error(f"Error previewing query: {str(e)}", exc_info=True)
            raise
