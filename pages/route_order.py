import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import time
from sklearn.cluster import KMeans
import math

# --- Setup ---
st.set_page_config(page_title="Store Visit Order - VRP", layout="wide")
st.title("🚚 Store Visit Sequence using VRP + Multi-Trip per Vehicle")
st.caption("Optimized store visit sequence per region with vehicle capacity and trip splitting.")

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

# --- Region Selection ---
regions_with_demand = sorted(df[df["demand (boxes)"] > 0]["region"].dropna().unique())
if not regions_with_demand:
    st.warning("⚠️ No stores with demand.")
    st.stop()

selected_region = st.selectbox("📍 Select a Region:", regions_with_demand)

region_df = df[(df["region"] == selected_region) & (df["demand (boxes)"] > 0)].copy()
if region_df.empty:
    st.warning(f"⚠️ No demand in region {selected_region}.")
    st.stop()

# --- Constants ---
warehouse = (24.595356831188536, 46.74032442208924)
vehicle_capacity = 400
num_vehicles = 4
cost_per_km = 1.50

# --- Helper: Cluster Stores ---
def cluster_stores(stores, k=4):
    coords = np.array([[s["lat"], s["lon"]] for s in stores])
    if len(stores) < k:
        clusters = [[] for _ in range(k)]
        for i, store in enumerate(stores):
            clusters[i].append(store)
        return clusters

    kmeans = KMeans(n_clusters=k, random_state=42).fit(coords)
    clusters = [[] for _ in range(k)]
    for i, store in enumerate(stores):
        clusters[kmeans.labels_[i]].append(store)
    return clusters

# --- Helper: Split stores by capacity ---
def split_by_capacity(stores, capacity):
    sorted_stores = sorted(stores, key=lambda s: s["demand (boxes)"], reverse=True)
    trips = []
    trip = []
    load = 0
    for store in sorted_stores:
        demand = store["demand (boxes)"]
        if load + demand > capacity:
            if trip:
                trips.append(trip)
            trip = [store]
            load = demand
        else:
            trip.append(store)
            load += demand
    if trip:
        trips.append(trip)
    return trips

# --- Helper: Distance Matrix ---
def create_distance_matrix(locations):
    return [[int(geodesic(loc1, loc2).km * 1000) for loc2 in locations] for loc1 in locations]

# --- Helper: VRP Solver ---
def solve_vrp(stores):
    locations = [warehouse] + [(s["lat"], s["lon"]) for s in stores]
    dist_matrix = create_distance_matrix(locations)

    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(params)
    route = []
    if solution:
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            index = solution.Value(routing.NextVar(index))
        route.append(0)
        return route, solution, routing, manager
    else:
        return [], None, None, None

# --- Helper: Calculate total distance ---
def calculate_total_distance(solution, routing, manager):
    total_distance = 0
    index = routing.Start(0)
    while not routing.IsEnd(index):
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
    return total_distance / 1000  # km

# --- Main Logic ---
st.subheader(f"📦 Visit Sequences for Region: {selected_region}")
stores = region_df[["store", "code", "lat", "lon", "demand (boxes)"]].to_dict(orient="records")
clusters = cluster_stores(stores, k=num_vehicles)

region_total_distance = 0
region_total_cost = 0

for i, cluster in enumerate(clusters):
    if not cluster:
        st.write(f"Vehicle {i+1}: No stores assigned.")
        continue

    cluster_total_demand = sum(s["demand (boxes)"] for s in cluster)
    trips = split_by_capacity(cluster, vehicle_capacity)

    st.markdown(f"### 🚐 Vehicle {i+1} - Total demand: {cluster_total_demand} boxes - {len(trips)} trip(s)")

    for trip_num, trip_stores in enumerate(trips, start=1):
        st.markdown(f"#### 🧭 Trip {trip_num}")
        route_indices, solution, routing, manager = solve_vrp(trip_stores)
        if not route_indices:
            st.warning("No route solution found for this trip.")
            continue

        for j, idx in enumerate(route_indices):
            if idx == 0:
                st.write(f"{j+1}. 🏢 *Warehouse*")
            else:
                store = trip_stores[idx - 1]
                st.write(f"{j+1}. 🏬 *{store['store']}* ({store['code']}) — {store['demand (boxes)']} boxes")

        trip_distance = calculate_total_distance(solution, routing, manager)
        trip_cost = trip_distance * cost_per_km
        region_total_distance += trip_distance
        region_total_cost += trip_cost

        st.write(f"**Estimated Trip Distance:** {trip_distance:.2f} km")
        st.write(f"**Estimated Trip Cost:** {trip_cost:.2f} SAR")

# --- Region Summary ---
st.markdown("---")
st.subheader("📊 Region Summary")
st.write(f"**Estimated Total Distance:** {region_total_distance:.2f} km")
st.write(f"**Estimated Total Cost:** {region_total_cost:.2f} SAR")
