import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
import folium
import folium.plugins

if TYPE_CHECKING:
    from folium.plugins import Draw

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import streamlit as st
from src.area_utils import AOIManager
from src.sar_utils import SARManager
from src.time_range_manager import TimeRangeManager

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

import ee
from streamlit_folium import st_folium

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
    if 'aoi_manager' not in st.session_state:
        st.session_state.aoi_manager = AOIManager()
    if 'sar_manager' not in st.session_state:
        st.session_state.sar_manager = SARManager()
    if 'time_range_manager' not in st.session_state:
        st.session_state.time_range_manager = TimeRangeManager()
    if 'show_aois' not in st.session_state:
        st.session_state.show_aois = False
    if 'current_query' not in st.session_state:
        st.session_state.current_query = {
            'aoi': None,
            'start_date': None,
            'end_date': None
        }
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
    if 'draw' not in st.session_state:
        st.session_state.draw = folium.plugins.Draw(  # type: ignore[attr-defined]
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
        st.session_state.map.add_child(st.session_state.draw)

    st.title("🛰️ Area Manager")

    # Create sidebar for controls instead of column
    with st.sidebar:
        st.subheader("Controls")
        
        # Basic Controls
        with st.container():
            st.subheader("Basic Controls")
            if st.button('Reset Map', help='Reset the entire map to its initial state, clearing all drawings and layers'):
                st.session_state.aoi_manager.clear_all()
                st.session_state.sar_manager.clear()
                st.session_state.show_aois = False
                if 'map' in st.session_state:
                    del st.session_state.map
                if 'draw' in st.session_state:
                    del st.session_state.draw
                st.rerun()

            if st.button('Clear SAR', help='Remove the SAR data overlay, keeping drawn areas intact'):
                st.session_state.sar_manager.clear()
                st.rerun()

            # AOI Visibility Toggle
            show_aois = st.checkbox('Show AOIs', value=st.session_state.show_aois)
            if show_aois != st.session_state.show_aois:
                st.session_state.show_aois = show_aois
                if 'map' in st.session_state:
                    del st.session_state.map
                if 'draw' in st.session_state:
                    del st.session_state.draw
                st.rerun()

        # Area Management Section
        with st.container():
            st.subheader("Area Management")
            
            # Area drawing and saving
            new_area_name = st.text_input("Area Name", key="new_area_name")
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
                    st.error(f"Error saving area: {str(e)}")
            
            # Area selection
            areas = st.session_state.aoi_manager.list_areas()
            if areas:
                selected_area = st.selectbox("Select Area", areas)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Delete Area", key="delete_area"):
                        st.session_state.aoi_manager.delete_area(selected_area)
                        st.rerun()
                with col2:
                    if st.button("Load to Query", key="load_aoi"):
                        st.session_state.current_query['aoi'] = selected_area
                        st.rerun()

        # Time Range Management Section
        with st.container():
            st.subheader("Time Range Management")
            
            # Quick date options
            st.markdown("**Quick Date Selection:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Last 7 days"):
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    st.session_state.current_query['start_date'] = start_date.strftime('%Y-%m-%d')
                    st.session_state.current_query['end_date'] = end_date.strftime('%Y-%m-%d')
                    st.rerun()
            with col2:
                if st.button("Last 14 days"):
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=14)
                    st.session_state.current_query['start_date'] = start_date.strftime('%Y-%m-%d')
                    st.session_state.current_query['end_date'] = end_date.strftime('%Y-%m-%d')
                    st.rerun()
            with col3:
                if st.button("Last 30 days"):
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    st.session_state.current_query['start_date'] = start_date.strftime('%Y-%m-%d')
                    st.session_state.current_query['end_date'] = end_date.strftime('%Y-%m-%d')
                    st.rerun()
            
            st.markdown("**Custom Date Range:**")
            # Date input
            start_date = st.date_input("Start Date", 
                value=datetime.strptime(st.session_state.current_query['start_date'], '%Y-%m-%d') if st.session_state.current_query['start_date'] else None)
            end_date = st.date_input("End Date", 
                value=datetime.strptime(st.session_state.current_query['end_date'], '%Y-%m-%d') if st.session_state.current_query['end_date'] else None)
            
            # Save time range
            col1, col2 = st.columns(2)
            with col1:
                time_range_name = st.text_input("Time Range Name")
            with col2:
                if st.button("Save Range") and time_range_name and start_date and end_date:
                    if st.session_state.time_range_manager.save_timerange(
                        time_range_name,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d")
                    ):
                        st.success(f"Saved time range: {time_range_name}")
                        st.rerun()
            
            # Load saved time ranges
            saved_ranges = st.session_state.time_range_manager.list_timeranges()
            if saved_ranges:
                st.markdown("**Saved Ranges:**")
                selected_range = st.selectbox("Select Range", saved_ranges)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Delete Range", key="delete_range"):
                        st.session_state.time_range_manager.delete_timerange(selected_range)
                        st.rerun()
                with col2:
                    if st.button("Load to Query", key="load_timerange"):
                        timerange = st.session_state.time_range_manager.get_timerange(selected_range)
                        if timerange:
                            st.session_state.current_query['start_date'] = timerange['start_date']
                            st.session_state.current_query['end_date'] = timerange['end_date']
                            st.rerun()

        # Query Section
        with st.container():
            st.subheader("Query Builder")
            
            # Show current query parameters
            st.markdown("**Current Query Parameters:**")
            aoi_status = st.session_state.current_query['aoi'] or "Not selected"
            st.markdown(f"- **Area of Interest:** {aoi_status}")
            
            date_status = "Not selected"
            if st.session_state.current_query['start_date'] and st.session_state.current_query['end_date']:
                date_status = f"{st.session_state.current_query['start_date']} to {st.session_state.current_query['end_date']}"
            st.markdown(f"- **Time Range:** {date_status}")
            
            # Preview and Execute buttons
            if st.session_state.current_query['aoi'] and st.session_state.current_query['start_date']:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Preview Query"):
                        area = st.session_state.aoi_manager.get_area(st.session_state.current_query['aoi'])
                        preview = st.session_state.sar_manager.preview_query(
                            area['geometry'],
                            st.session_state.current_query['start_date'],
                            st.session_state.current_query['end_date']
                        )
                        st.write(preview)
                
                with col2:
                    if st.button("Execute Query"):
                        area = st.session_state.aoi_manager.get_area(st.session_state.current_query['aoi'])
                        sar_data = st.session_state.sar_manager.process_area(
                            area['geometry'],
                            st.session_state.current_query['start_date'],
                            st.session_state.current_query['end_date']
                        )
                        if sar_data:
                            vis_params = {
                                'bands': ['VH_ascending', 'VH_descending', 'VV_combined'],
                                'min': [-25, -20, -25],
                                'max': [0, 10, 0],
                                'gamma': 1.0,
                                'opacity': 1.0
                            }
                            map_id_dict = sar_data.composite.getMapId(vis_params)
                            st.session_state.sar_layer = folium.TileLayer(
                                tiles=map_id_dict['tile_fetcher'].url_format,
                                attr='Google Earth Engine',
                                overlay=True,
                                name='SAR Data',
                                opacity=1.0
                            )
                            st.session_state.map.add_child(st.session_state.sar_layer)
                            st.session_state.current_sar_data = sar_data
                            st.rerun()

    # Main content area for map
    st.markdown("""
        <style>
        .stMapContainer {
            height: 800px;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize map
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
    if 'draw' not in st.session_state:
        st.session_state.draw = folium.plugins.Draw(  # type: ignore[attr-defined]
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
        st.session_state.map.add_child(st.session_state.draw)

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
