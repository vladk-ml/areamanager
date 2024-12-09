import ee
import folium
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

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
    
    def _validate_dates(self, start_date: str, end_date: str) -> Tuple[ee.Date, ee.Date]:
        """Validate and convert date strings to ee.Date objects"""
        try:
            ee_start_date = ee.Date(start_date)
            ee_end_date = ee.Date(end_date)
            
            # Ensure end date is after start date
            if ee_end_date.difference(ee_start_date, 'day').getInfo() <= 0:
                raise ValueError("End date must be after start date")
                
            return ee_start_date, ee_end_date
        except Exception as e:
            raise ValueError(f"Invalid date format. Dates should be in YYYY-MM-DD format. Error: {str(e)}")

    def process_area(self, geometry: Dict[str, Any], start_date: str, end_date: str) -> Optional[SARData]:
        """Process an area to get SAR data. Returns None if no data available."""
        try:
            # Convert geometry to Earth Engine format
            ee_geometry = ee.Geometry(geometry)
            
            # Validate dates
            ee_start_date, ee_end_date = self._validate_dates(start_date, end_date)
            
            # Get Sentinel-1 collection
            collection = ee.ImageCollection(self.collection) \
                .filterDate(ee_start_date, ee_end_date) \
                .filterBounds(ee_geometry)
            
            # Check collection size
            size = collection.size().getInfo()
            if size == 0:
                logger.warning(f"No SAR data found for date range {start_date} to {end_date}")
                return None
            
            # Create composite
            composite = self._create_composite(collection)
            
            # Get bounds for export
            bounds = ee_geometry.bounds().getInfo()
            
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
        """Create a composite image optimized for interference pattern detection"""
        # Filter to get images with VV and VH dual polarization
        filtered = collection.filter(
            ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')
        ).filter(
            ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')
        ).filter(
            ee.Filter.eq('instrumentMode', 'IW')  # Interferometric Wide Swath mode
        )
        
        # Separate ascending and descending passes
        ascending = filtered.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))
        descending = filtered.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
        
        # Create composite using the three bands as in JavaScript
        vh_ascending = ascending.select('VH').max()
        vh_descending = descending.select('VH').max()
        vv_combined = ee.ImageCollection(
            ascending.select('VV').merge(descending.select('VV'))
        ).max()
        
        # Combine all three bands and apply median filter
        composite = ee.Image.cat([
            vh_ascending.rename('VH_ascending'),
            vh_descending.rename('VH_descending'),
            vv_combined.rename('VV_combined')
        ]).focal_median()
        
        return composite
    
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
    
    def preview_query(self, geometry: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
        """Preview the query parameters and expected results"""
        try:
            # Convert geometry to Earth Engine format
            ee_geometry = ee.Geometry(geometry)
            
            # Validate dates
            ee_start_date, ee_end_date = self._validate_dates(start_date, end_date)
            
            # Get Sentinel-1 collection
            collection = ee.ImageCollection(self.collection) \
                .filterDate(ee_start_date, ee_end_date) \
                .filterBounds(ee_geometry)
            
            size = collection.size().getInfo()
            
            # Calculate area size in km²
            area_size = ee_geometry.area().divide(1e6).getInfo()  # Convert to km²
            
            # Estimate data size (rough estimate)
            estimated_size_mb = size * 0.5  # Rough estimate of MB per image
            
            return {
                'area_info': {
                    'size_km2': area_size
                },
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'results_preview': {
                    'image_count': size,
                    'estimated_size_mb': estimated_size_mb
                },
                'query_params': {
                    'collection': self.collection,
                    'polarisation': 'VH',
                    'mode': 'IW',
                    'orbit': 'DESCENDING'
                }
            }
            
        except ValueError as e:
            return {
                'error': str(e),
                'area_info': {
                    'size_km2': 0
                },
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'results_preview': {
                    'image_count': 0,
                    'estimated_size_mb': 0
                },
                'query_params': {
                    'collection': self.collection,
                    'polarisation': 'VH',
                    'mode': 'IW',
                    'orbit': 'DESCENDING'
                }
            }
        except Exception as e:
            logger.error(f"Error previewing query: {str(e)}", exc_info=True)
            raise
