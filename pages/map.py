import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import openrouteservice
import folium
from streamlit_folium import st_folium
import time

# --- Setup ---
st.set_page_config(page_title="Date Delivery Dashboard with Vehicle Routes", layout="wide")
st.title("📦 Date Delivery Dashboard with Vehicle Routes")
st.caption("Select region and vehicle to view optimized delivery route.")

# --- Load Data ---
@st.cache_data(ttl=60)
def load_demand_data():
    try:
        df = pd.read_csv("/Users/rand/Desktop/Nisreen/all_region_demands.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except FileNotFoundError:
        st.error("❌ Demand data file not found.")
        st.stop()

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    time.sleep(0.5)
    st.rerun()

df = load_demand_data()

# --- Validate demand column existence ---
if "demand (boxes)" not in df.columns:
    st.error("❌ 'demand (boxes)' column missing from data.")
    st.stop()

# --- Filter only stores with demand > 0 ---
df = df[df["demand (boxes)"] > 0]

# --- Regions list from demand data ---
valid_regions = sorted(df["region"].dropna().unique())
if not valid_regions:
    st.warning("⚠️ No stores with demand found in data.")
    st.stop()

selected_region = st.selectbox("📍 Select a Region:", valid_regions)

region_df = df[df["region"] == selected_region].copy()


if region_df.empty:
    st.warning(f"⚠️ No demand stores found in region '{selected_region}'.")
    st.stop()

# --- Parameters ---
vehicle_capacity = 400
num_vehicles = 4
warehouse_coords = (24.595356831188536, 46.74032442208924)  # Tamara warehouse

# --- Clustering function ---
def cluster_stores(stores, k=4):
    coords = stores[["lat", "lon"]].values
    if len(stores) < k:
        clusters = [stores.iloc[[i]] if i < len(stores) else stores.iloc[0:0] for i in range(k)]
        return clusters

    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(coords)
    stores["cluster"] = kmeans.labels_
    clusters = [stores[stores["cluster"] == i] for i in range(k)]
    return clusters

# --- Cluster stores ---
clusters = cluster_stores(region_df, k=num_vehicles)

# --- Vehicle selector ---
vehicle_options = [f"Vehicle {i+1} (stores: {len(c)}) — Total demand: {c['demand (boxes)'].sum()} boxes" for i, c in enumerate(clusters)]
selected_vehicle_idx = st.selectbox("🚐 Select Vehicle:", range(len(vehicle_options)), format_func=lambda x: vehicle_options[x])

vehicle_stores = clusters[selected_vehicle_idx]

if vehicle_stores.empty:
    st.warning("No stores assigned to this vehicle.")
    st.stop()

# --- OpenRouteService API key ---
API_KEY = "5b3ce3597851110001cf624815379242ee824897834dce29d0061855"

# --- Build coords for ORS (warehouse + stores) ---
coords = [(warehouse_coords[1], warehouse_coords[0])]  # ORS expects (lon, lat)
coords += list(zip(vehicle_stores["lon"], vehicle_stores["lat"]))

# --- Get route map ---
@st.cache_data(show_spinner=False)
def get_route_map(coords, api_key):
    if len(coords) < 2:
        return None, 0
    try:
        client = openrouteservice.Client(key=api_key)
        route = client.directions(
            coordinates=coords,
            profile='driving-car',
            format='geojson',
            optimize_waypoints=True
        )
        geometry = route['features'][0]['geometry']
        if not geometry:
            return None, 0
    except Exception as e:
        st.error(f"Routing error: {e}")
        return None, 0

    avg_lat = np.mean([lat for lon, lat in coords])
    avg_lon = np.mean([lon for lon, lat in coords])
    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

    folium.Marker(location=[warehouse_coords[0], warehouse_coords[1]], popup="Tamara Dates (Warehouse)", icon=folium.Icon(color="green")).add_to(fmap)
    for idx, (lon, lat) in enumerate(coords[1:], 1):
        folium.Marker(location=[lat, lon], popup=vehicle_stores.iloc[idx-1]["store"]).add_to(fmap)

    folium.GeoJson(route, name="route").add_to(fmap)

    distance_m = route["features"][0]["properties"]["summary"]["distance"]
    return fmap, distance_m / 1000  # meters to km

# --- Show route and info ---
route_map, distance_km = get_route_map(coords, API_KEY)

if route_map:
    st.markdown(f"### 🚚 Route for {vehicle_options[selected_vehicle_idx]} in {selected_region}")
    st_folium(route_map, width=700, height=500)

   
else:
    st.warning("Could not generate route map for selected vehicle.")
