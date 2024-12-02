import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import streamlit as st
import ee
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta
from src.area_utils import AOIManager
from src.sar_utils import SARManager

# Page configuration
st.set_page_config(
    page_title="Area Manager",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Initialize managers
@st.cache_resource
def get_managers():
    return AOIManager(), SARManager()

# Main title
st.title("🛰️ Area Manager")

# Initialize Earth Engine and managers
if initialize_ee():
    st.success("Earth Engine initialized successfully!")
else:
    st.error("Failed to initialize Earth Engine")
    st.stop()

aoi_manager, sar_manager = get_managers()

# Sidebar for date selection
with st.sidebar:
    st.header("Date Range")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_date = st.date_input("Start Date", value=start_date)
    end_date = st.date_input("End Date", value=end_date)
    
    if start_date > end_date:
        st.error("Start date must be before end date")
        st.stop()

# Create columns for layout
col1, col2 = st.columns([2, 1])

# Map column
with col1:
    st.subheader("Map")
    try:
        # Initialize map
        m = folium.Map(
            location=[20, 0],
            zoom_start=3,
            control_scale=True
        )
        
        # Add drawing controls
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
        draw.add_to(m)
        
        # Add existing areas to the map
        areas = aoi_manager.list_areas()
        if areas:
            for area_name in areas:
                area = aoi_manager.get_area(area_name)
                if area:
                    coords = area['geometry']['coordinates'][0]
                    folium.Polygon(
                        locations=[[p[1], p[0]] for p in coords],
                        popup=area_name,
                        color='red',
                        fill=True
                    ).add_to(m)
        
        # Display the map
        folium_static(m, height=600)
        
    except Exception as e:
        st.error(f"Error displaying map: {str(e)}")

# Controls column
with col2:
    st.subheader("Area Management")
    
    # List existing areas
    areas = aoi_manager.list_areas()
    if areas:
        selected_areas = st.multiselect("Select Areas", areas)
        
        if selected_areas:
            if st.button("Delete Selected"):
                for area in selected_areas:
                    aoi_manager.delete_area(area)
                st.experimental_rerun()
            
            # SAR Data Visualization
            if st.button("Show SAR Data"):
                try:
                    for area_name in selected_areas:
                        area = aoi_manager.get_area(area_name)
                        if area:
                            geometry = ee.Geometry.Polygon(area['geometry']['coordinates'])
                            collection = sar_manager.get_sar_collection(
                                geometry,
                                start_date.strftime('%Y-%m-%d'),
                                end_date.strftime('%Y-%m-%d')
                            )
                            composite = sar_manager.create_composite(collection)
                            sar_manager.add_to_map(m, composite)
                            
                            # Get statistics
                            stats = sar_manager.get_statistics(composite, geometry)
                            if stats:
                                st.write(f"### Statistics for {area_name}")
                                st.write(f"Mean VV: {stats.get('VV_mean', 'N/A'):.2f} dB")
                                st.write(f"Std Dev VV: {stats.get('VV_stdDev', 'N/A'):.2f} dB")
                                st.write(f"Min VV: {stats.get('VV_min', 'N/A'):.2f} dB")
                                st.write(f"Max VV: {stats.get('VV_max', 'N/A'):.2f} dB")
                    
                    st.success("SAR data loaded successfully!")
                    
                except Exception as e:
                    st.error(f"Error loading SAR data: {str(e)}")
            
            # Export options
            st.subheader("Export Options")
            
            if st.button("Export to Drive"):
                try:
                    for area_name in selected_areas:
                        area = aoi_manager.get_area(area_name)
                        if area:
                            geometry = ee.Geometry.Polygon(area['geometry']['coordinates'])
                            collection = sar_manager.get_sar_collection(
                                geometry,
                                start_date.strftime('%Y-%m-%d'),
                                end_date.strftime('%Y-%m-%d')
                            )
                            composite = sar_manager.create_composite(collection)
                            task = sar_manager.export_to_drive(
                                composite,
                                geometry,
                                f"SAR_Export_{area_name}_{start_date.strftime('%Y%m%d')}"
                            )
                            st.success(f"Export task started for {area_name}! Check your Google Drive in a few minutes.")
                except Exception as e:
                    st.error(f"Error exporting SAR data: {str(e)}")
            
            if st.button("Download GeoJSON"):
                with st.spinner("Generating download URL..."):
                    url = aoi_manager.get_download_url(selected_areas)
                    if url:
                        st.markdown(f"[Download GeoJSON]({url})")
    
    st.markdown("---")
    
    # Add new area
    st.subheader("Add New Area")
    new_name = st.text_input("Area Name")
    new_description = st.text_area("Description")
    
    if st.button("Add Area from Map"):
        try:
            # Get drawn features from the map
            drawn_features = m.last_active_drawing
            if drawn_features and drawn_features['geometry']['type'] in ['Polygon', 'Rectangle']:
                coords = drawn_features['geometry']['coordinates'][0]
                aoi_manager.add_area(new_name, coords, new_description)
                st.success(f"Added area: {new_name}")
                st.experimental_rerun()
            else:
                st.warning("Please draw a polygon or rectangle on the map first.")
        except Exception as e:
            st.error(f"Error adding area: {str(e)}")

# Status bar at the bottom
status_container = st.container()
with status_container:
    st.markdown("---")
    st.markdown("Ready")
