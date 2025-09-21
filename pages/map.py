import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sklearn.cluster import KMeans
import openrouteservice
import folium
from streamlit_folium import st_folium
import time

# --- Setup ---
st.set_page_config(page_title="Store Visit Order - VRP with Map", layout="wide")
st.title("🚚 Store Visit Sequence with Map")
st.caption("Optimized store visit sequence per region with vehicle capacity and trip routes.")

# # --- Load Data ---
# @st.cache_data(ttl=60)
# def load_demand_data():
#     try:
#         df = pd.read_csv("/Users/rand/Desktop/Nisreen/all_region_demands.csv")
#         df.columns = df.columns.str.strip().str.lower()
#         return df
#     except FileNotFoundError:
#         st.error("❌ Demand data file not found.")
#         st.stop()

# if st.button("🔄 Refresh Data"):
#     st.cache_data.clear()
#     time.sleep(0.5)
#     st.rerun()

# df = load_demand_data()
# df = df[df["demand (boxes)"] > 0]

# --- Load Data from Session State ---
if 'demand_data' in st.session_state:
    df = st.session_state['demand_data']
    df = df[df["demand (boxes)"] > 0]
else:
    st.warning("❌ No demand data found. Please enter the demand first on the main page.")
    st.stop()


# --- Sidebar: Region Selection ---
regions_with_demand = sorted(df["region"].dropna().unique())
selected_region = st.sidebar.selectbox("📍 Select a Region:", regions_with_demand)
region_df = df[df["region"] == selected_region].copy()
if region_df.empty:
    st.warning(f"⚠️ No demand in region {selected_region}.")
    st.stop()

# --- Constants ---
warehouse_coords = (24.595356831188536, 46.74032442208924)
vehicle_capacity = 400
num_vehicles = 1
API_KEY = "5b3ce3597851110001cf624815379242ee824897834dce29d0061855"  

# --- VRP & Clustering Helpers ---
def cluster_stores(stores, k=4):
    coords = stores[["lat","lon"]].values
    if len(stores) < k:
        clusters = [stores.iloc[[i]] if i < len(stores) else stores.iloc[0:0] for i in range(k)]
        return clusters
    kmeans = KMeans(n_clusters=k, random_state=42).fit(coords)
    stores["cluster"] = kmeans.labels_
    return [stores[stores["cluster"]==i] for i in range(k)]

def split_by_capacity(stores, capacity):
    expanded_stores=[]
    for _, s in stores.iterrows():
        demand = s["demand (boxes)"]
        if demand>capacity:
            full_chunks=demand//capacity
            remainder=demand%capacity
            for _ in range(full_chunks):
                new_s=s.copy(); new_s["demand (boxes)"]=capacity; expanded_stores.append(new_s)
            if remainder>0:
                new_s=s.copy(); new_s["demand (boxes)"]=remainder; expanded_stores.append(new_s)
        else:
            expanded_stores.append(s)
    sorted_stores=sorted(expanded_stores,key=lambda s: s["demand (boxes)"],reverse=True)
    trips=[]
    trip=[]
    load=0
    for s in sorted_stores:
        demand=s["demand (boxes)"]
        if load+demand>capacity:
            if trip: trips.append(trip)
            trip=[s]; load=demand
        else: trip.append(s); load+=demand
    if trip: trips.append(trip)
    return trips

# --- Build Trips ---
stores = region_df[["store","lat","lon","demand (boxes)"]].to_dict("records")
clusters = cluster_stores(region_df, k=num_vehicles)
trips=[]
for cluster in clusters:
    if not cluster.empty: trips.extend(split_by_capacity(cluster, vehicle_capacity))

# --- Trip Selection ---
trip_labels = [
    f"**Trip {i+1}** — Stores: {len(t)} — Demand: {sum(s['demand (boxes)'] for s in t)} boxes"
    for i, t in enumerate(trips)
]
selected_trip_idx = st.radio("🚐 Select Trip:", options=range(len(trip_labels)), format_func=lambda x: trip_labels[x])
selected_trip = trips[selected_trip_idx]

# # --- Trip Summary Metrics ---
# total_stores = len(selected_trip)
# total_demand = sum(s["demand (boxes)"] for s in selected_trip)

# col1, col2, col3 = st.columns(3)
# col1.metric("🏬 Total Stores", total_stores)
# col2.metric("📦 Total Demand (boxes)", total_demand)
# # Distance will be updated after routing
# distance_placeholder = col3.empty()

# --- Collapsible Store List ---
with st.expander("📋 View Stores in this Trip", expanded=False):
    trip_table = pd.DataFrame(selected_trip)[["store","demand (boxes)"]]
    st.table(trip_table)

# --- Get ORS Map ---
coords = [(warehouse_coords[1], warehouse_coords[0])] + [(s["lon"], s["lat"]) for s in selected_trip]

@st.cache_data(show_spinner=False)
def get_route_map(coords, api_key, trip_stores):
    try:
        client = openrouteservice.Client(key=api_key)
        route = client.directions(coordinates=coords, profile='driving-car', format='geojson', optimize_waypoints=True)
        fmap = folium.Map(location=[warehouse_coords[0], warehouse_coords[1]], zoom_start=12)
        folium.Marker(location=warehouse_coords, popup="Warehouse", icon=folium.Icon(color="green")).add_to(fmap)
        for idx,(lon,lat) in enumerate(coords[1:]):
            demand = trip_stores[idx]["demand (boxes)"]
            color = "red" if demand > vehicle_capacity/2 else "blue"
            folium.Marker(location=[lat,lon], popup=f"{trip_stores[idx]['store']} ({demand} boxes)",
                          icon=folium.Icon(color=color)).add_to(fmap)
        folium.GeoJson(route, name="route").add_to(fmap)
        distance_km = route["features"][0]["properties"]["summary"]["distance"]/1000
        return fmap, distance_km
    except Exception as e: 
        st.error(f"Routing error: {e}")
        return None, 0

with st.spinner("🗺️ Generating route map..."):
    route_map, distance_km = get_route_map(coords, API_KEY, selected_trip)

if route_map:
    # distance_placeholder.metric("🛣️ Estimated Distance (km)", f"{distance_km:.2f}")
    st.markdown("---")
    st.markdown("### 🚚 Route Map")
    st_folium(route_map, width=700, height=500)
else:
    st.warning("Could not generate route map for this trip.")
