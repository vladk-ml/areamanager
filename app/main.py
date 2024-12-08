import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from datetime import timedelta

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import streamlit as st

st.set_page_config(
    page_title="Area Manager",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for compact layout
st.markdown("""
    <style>
        .main .block-container {
            padding: 1rem !important;
            max-width: 100% !important;
        }
        
        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Control sections */
        .control-section {
            background: #f0f2f6;
            border-radius: 5px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        /* Make buttons more compact */
        .stButton > button {
            width: 100%;
            margin: 0.25rem 0;
        }
        
        /* Adjust date button container */
        .date-buttons {
            display: flex;
            gap: 0.5rem;
        }
        
        .date-buttons .stButton {
            flex: 1;
        }
        
        /* Hide empty elements */
        .css-1544g2n.e1f1d6gn3 {
            padding: 0 !important;
            margin: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

import folium
import ee
from streamlit_folium import st_folium
from src.area_utils import AOIManager
from src.sar_utils import SARManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Earth Engine
@st.cache_resource
def initialize_ee():
    try:
        ee.Initialize(project='ee-sergiyk1974')
        return True
    except Exception as e:
        st.error(f"Failed to initialize Earth Engine: {str(e)}")
        st.error("Please run 'python authenticate.py' first.")
        st.stop()
        return False

def calculate_area_size(coords):
    """Calculate approximate area size in km²"""
    if not coords or len(coords) < 3:
        return 0
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in km"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    # Calculate area using shoelace formula with approximate distances
    area = 0
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        # Get coordinates for current and next point
        lat1, lon1 = coords[i][1], coords[i][0]
        lat2, lon2 = coords[j][1], coords[j][0]
        # Calculate the cross product of coordinates
        area += lon1 * lat2 - lon2 * lat1
    
    # Convert to absolute value and scale
    area = abs(area) * 111 * 111 / 2  # rough conversion to km²
    return round(area, 2)

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    return timestamp.strftime("%Y-%m-%d %H:%M")

def main():
    # Initialize session state variables
    if 'start_date' not in st.session_state:
        st.session_state.start_date = datetime.now() - timedelta(days=30)
    if 'end_date' not in st.session_state:
        st.session_state.end_date = datetime.now()
    if 'map' not in st.session_state:
        st.session_state.map = folium.Map(
            location=[54.6872, 25.2797],
            zoom_start=6,
            tiles='CartoDB positron',
            width="100%",
            height="100%",
            prefer_canvas=True,
            control_scale=True
        )
    if 'drawn_areas' not in st.session_state:
        st.session_state.drawn_areas = {}
    
    st.title("🛰️ Area Manager")
    
    # Initialize managers
    if 'aoi_manager' not in st.session_state:
        st.session_state.aoi_manager = AOIManager()
    if 'sar_manager' not in st.session_state:
        st.session_state.sar_manager = SARManager()
    
    # Initialize map if not already done
    if 'draw' not in st.session_state:
        draw = folium.plugins.Draw(
            export=False,
            position='topleft',
            draw_options={
                'polyline': False,
                'rectangle': True,
                'polygon': True,
                'circle': False,
                'marker': False,
                'circlemarker': False
            }
        )
        st.session_state.map.add_child(draw)
        st.session_state.draw = draw
        
        # Add existing areas to the map
        areas = st.session_state.aoi_manager.list_areas()
        if areas:
            for area_name in areas:
                area = st.session_state.aoi_manager.get_area(area_name)
                if area:
                    coords = area['geometry']['coordinates'][0]
                    folium.Polygon(
                        locations=[[p[1], p[0]] for p in coords],
                        popup=area_name,
                        color='red',
                        fill=True,
                        fillOpacity=0.2
                    ).add_to(st.session_state.map)
    
    # Create two columns: controls and map
    col1, col2 = st.columns([1, 3])
    
    # Control Panel Column
    with col1:
        # Area Management Section
        with st.container():
            st.subheader("Area Management")
            new_area_name = st.text_input("Area Name", key="new_area_name", label_visibility="collapsed")
            if st.button("Save Area", key="save_area"):
                try:
                    if 'output' in st.session_state and st.session_state.output.get("all_drawings"):
                        feature = st.session_state.output["all_drawings"][-1]
                        if feature["geometry"]["type"] in ["Polygon", "Rectangle"]:
                            st.session_state.aoi_manager.add_area(new_area_name, feature["geometry"]["coordinates"][0])
                            st.success(f"✅ Area '{new_area_name}' saved!")
                            st.rerun()
                        else:
                            st.warning("Please draw a polygon or rectangle")
                    else:
                        st.warning("Please draw an area on the map first")
                except Exception as e:
                    logger.error("Error saving area", exc_info=True)
                    st.error(f"Error saving area: {str(e)}")
        
        # Area Selection Section
        with st.container():
            st.subheader("Area Selection")
            areas = st.session_state.aoi_manager.list_areas()
            if areas:
                area_info = []
                for area_name in areas:
                    area_data = st.session_state.aoi_manager.get_area(area_name)
                    if area_data:
                        coords = area_data['geometry']['coordinates'][0]
                        size = calculate_area_size(coords)
                        timestamp = area_data.get('timestamp', '2024-01-01T00:00:00')
                        area_info.append({
                            'name': area_name,
                            'size': size,
                            'timestamp': timestamp,
                            'display': f"{area_name} ({size:.0f} km²)"
                        })
                
                selected_area = st.selectbox(
                    "Select Area",
                    options=[area['name'] for area in area_info],
                    format_func=lambda x: next((area['display'] for area in area_info if area['name'] == x), x),
                    label_visibility="collapsed",
                    key="selected_area"
                )
                
                if st.button("Delete Area", key="delete_area"):
                    if selected_area:
                        st.session_state.aoi_manager.delete_area(selected_area)
                        st.rerun()
        
        # Date Range Section
        with st.container():
            st.subheader("Date Range")
            start_date = st.date_input("Start Date", value=st.session_state.start_date, key="start_date_input")
            if start_date != st.session_state.start_date:
                st.session_state.start_date = start_date
                st.rerun()
            
            end_date = st.date_input("End Date", value=st.session_state.end_date, key="end_date_input")
            if end_date != st.session_state.end_date:
                st.session_state.end_date = end_date
                st.rerun()
            
            cols = st.columns(3)
            with cols[0]:
                if st.button("7d"):
                    st.session_state.start_date = datetime.now() - timedelta(days=7)
                    st.session_state.end_date = datetime.now()
                    st.rerun()
            with cols[1]:
                if st.button("14d"):
                    st.session_state.start_date = datetime.now() - timedelta(days=14)
                    st.session_state.end_date = datetime.now()
                    st.rerun()
            with cols[2]:
                if st.button("30d"):
                    st.session_state.start_date = datetime.now() - timedelta(days=30)
                    st.session_state.end_date = datetime.now()
                    st.rerun()
        
        # Map Controls Section
        with st.container():
            st.subheader("Map Controls")
            if st.button("Reset Map"):
                st.session_state.map = folium.Map(
                    location=[54.6872, 25.2797],
                    zoom_start=6,
                    tiles='CartoDB positron',
                    width="100%",
                    height="100%",
                    prefer_canvas=True,
                    control_scale=True
                )
                st.session_state.map.add_child(st.session_state.draw)
                st.rerun()
            
            if st.button("Clear SAR"):
                if hasattr(st.session_state, 'sar_layer'):
                    st.session_state.sar_layer = None
                    st.rerun()
        
        # SAR Controls Section
        with st.container():
            st.subheader("SAR Controls")
            
            preview_button = st.button("Preview Query")
            if preview_button:
                if selected_area:
                    area_coords = st.session_state.aoi_manager.get_area(selected_area)
                    if area_coords:
                        start_date = st.session_state.start_date
                        end_date = st.session_state.end_date
                        geometry = ee.Geometry(area_coords['geometry'])
                        
                        preview = st.session_state.sar_manager.preview_query(
                            geometry, 
                            start_date.strftime('%Y-%m-%d'), 
                            end_date.strftime('%Y-%m-%d')
                        )
                        
                        st.session_state.query_preview = preview
                        st.session_state.query_geometry = geometry
                        st.rerun()
                    else:
                        st.error("Could not load area coordinates")
                else:
                    st.error("Please select an area first")
            
            execute_button = st.button("Execute Query", disabled='query_preview' not in st.session_state)
            if execute_button and 'query_preview' in st.session_state:
                if st.session_state.query_preview['results_preview']['image_count'] > 0:
                    geometry = st.session_state.query_geometry
                    start_date = st.session_state.start_date
                    end_date = st.session_state.end_date
                    
                    sar_data = st.session_state.sar_manager.process_area(
                        geometry,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    )
                    if sar_data:
                        vis_params = {
                            'min': 0,
                            'max': 255,
                            'palette': ['black', 'white']
                        }
                        map_id_dict = sar_data.composite.getMapId(vis_params)
                        st.session_state.sar_layer = folium.TileLayer(
                            tiles=map_id_dict['tile_fetcher'].url_format,
                            attr='Google Earth Engine',
                            overlay=True,
                            name='SAR Data',
                            opacity=0.7
                        )
                        st.session_state.map.add_child(st.session_state.sar_layer)
                        st.session_state.current_sar_data = sar_data
                        st.rerun()
                else:
                    st.warning("No images found for the selected parameters")
            
            export_button = st.button("Export to Drive", disabled='current_sar_data' not in st.session_state)
            if export_button and 'current_sar_data' in st.session_state:
                try:
                    task = ee.batch.Export.image.toDrive(
                        image=st.session_state.current_sar_data.composite,
                        description=f'SAR_Export_{selected_area}_{datetime.now().strftime("%Y%m%d")}',
                        folder='AreaManager_Exports',
                        scale=10,
                        maxPixels=1e9,
                        region=st.session_state.query_geometry.bounds().getInfo()['coordinates']
                    )
                    task.start()
                    st.success("✅ Export started! Check your Google Drive folder 'AreaManager_Exports'")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
            
            # Show preview information if available
            if 'query_preview' in st.session_state:
                preview = st.session_state.query_preview
                st.markdown("### Query Info")
                st.json({
                    "Area": f"{preview['area_info']['size_km2']} km²",
                    "Date Range": f"{preview['date_range']['start']} to {preview['date_range']['end']}",
                    "Images Found": preview['results_preview']['image_count'],
                    "Estimated Size": f"{preview['results_preview']['estimated_size_mb']} MB",
                    "Parameters": preview['query_params']
                })
    
    # Map Column
    with col2:
        output = st_folium(
            st.session_state.map,
            width="100%",
            height=800,
            returned_objects=["all_drawings"]
        )
        if output:
            st.session_state.output = output

if __name__ == "__main__":
    if initialize_ee():
        main()
    else:
        st.error("Failed to initialize Earth Engine")
        st.stop()
