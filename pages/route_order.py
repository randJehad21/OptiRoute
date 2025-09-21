import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import time
from sklearn.cluster import KMeans
import math
import plotly.express as px

# --- Setup ---
st.set_page_config(page_title="Store Visit Order - VRP", layout="wide")
st.title("🚚 Store Visit Sequence")
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
num_vehicles = 1
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
    expanded_stores = []
    for store in stores:
        demand = store["demand (boxes)"]
        if demand > capacity:
            # Split into multiple parts
            full_chunks = demand // capacity
            remainder = demand % capacity
            for _ in range(full_chunks):
                new_store = store.copy()
                new_store["demand (boxes)"] = capacity
                expanded_stores.append(new_store)
            if remainder > 0:
                new_store = store.copy()
                new_store["demand (boxes)"] = remainder
                expanded_stores.append(new_store)
        else:
            expanded_stores.append(store)

    # Now split as before
    sorted_stores = sorted(expanded_stores, key=lambda s: s["demand (boxes)"], reverse=True)
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
stores = region_df[["store", "code", "lat", "lon", "demand (boxes)"]].to_dict(orient="records")
clusters = cluster_stores(stores, k=num_vehicles)

region_total_distance = 0
region_total_cost = 0
trip_summary = []  # ✅ collect trip-level data
trip_details = []  # ✅ keep trip routes for later display

for i, cluster in enumerate(clusters):
    if not cluster:
        continue

    cluster_total_demand = sum(s["demand (boxes)"] for s in cluster)
    trips = split_by_capacity(cluster, vehicle_capacity)

    for trip_num, trip_stores in enumerate(trips, start=1):
        route_indices, solution, routing, manager = solve_vrp(trip_stores)
        if not route_indices:
            continue

        trip_distance = calculate_total_distance(solution, routing, manager)
        trip_cost = trip_distance * cost_per_km
        region_total_distance += trip_distance
        region_total_cost += trip_cost

        # ✅ Collect trip summary
        trip_summary.append({
            "Vehicle": f"Vehicle {i+1}",
            "Trip": f"Trip {trip_num}",
            "Stores": len(trip_stores),
            "Demand": sum(s["demand (boxes)"] for s in trip_stores),
            "Distance (km)": trip_distance,
            "Cost (SAR)": trip_cost
        })

        # ✅ Collect trip details for display later
        route_steps = []
        for j, idx in enumerate(route_indices):
            if idx == 0:
                route_steps.append(f"{j+1}. 🏢 *Warehouse*")
            else:
                store = trip_stores[idx - 1]
                route_steps.append(f"{j+1}. 🏬 {store['store']} — {store['demand (boxes)']} boxes")

        trip_details.append({
            "Vehicle": f"Vehicle {i+1}",
            "Trip": f"Trip {trip_num}",
            "Route": route_steps,
            "Distance": trip_distance,
            "Cost": trip_cost
        })


# --- Region Summary Cards ---
region_total_demand = region_df["demand (boxes)"].sum()
st.markdown("<h2 style='text-align:center'>📊 Region Summary</h2>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
card_style = "background-color:#f0f2f6;padding:20px;border-radius:12px;text-align:center;box-shadow: 2px 2px 12px rgba(0,0,0,0.1);"

with col1:
    st.markdown(f"<div style='{card_style}'>🚚<br><b>Total Distance</b><br><span style='font-size:24px;color:#1f77b4'>{region_total_distance:.2f} km</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div style='{card_style}'>💰<br><b>Total Cost</b><br><span style='font-size:24px;color:#ff7f0e'>{region_total_cost:.2f} SAR</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div style='{card_style}'>📦<br><b>Total Demand</b><br><span style='font-size:24px;color:#2ca02c'>{region_total_demand:.0f} boxes</span></div>", unsafe_allow_html=True)

st.markdown("---")



# --- Trip Details (BOTTOM) ---
st.markdown("---")
st.subheader("🧭 Trip Details")

if trip_details:
    for trip in trip_details:
        st.markdown(f"### 🚐 {trip['Trip']}")

        # 👉 Join route with arrows
        route_str = " → ".join(trip["Route"])

        # 👉 Layout: two columns (route | summary table)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(route_str)

        with col2:
            trip_summary_df = pd.DataFrame(
                {
                    "Metric": ["Distance (km)", "Cost (SAR)"],
                    "Value": [f"{trip['Distance']:.2f}", f"{trip['Cost']:.2f}"]
                }
            )
            st.table(trip_summary_df)



# --- Region Summary (TOP) ---
st.markdown("---")
st.subheader(f"📊 Region Summary for {selected_region}")

# Prepare data for bar chart
summary_df = pd.DataFrame(trip_summary)

# Add total row
total_distance = summary_df["Distance (km)"].sum()
total_cost = summary_df["Cost (SAR)"].sum()
summary_df_totals = pd.DataFrame({
    "Trip": ["Total"],
    "Distance (km)": [total_distance],
    "Cost (SAR)": [total_cost],
    "Vehicle": [""]
})

summary_df = pd.concat([summary_df, summary_df_totals], ignore_index=True)

# Melt for plotting
melted_df = summary_df.melt(
    id_vars=["Trip", "Vehicle"],
    value_vars=["Distance (km)", "Cost (SAR)"],
    var_name="Metric",
    value_name="Value"
)

# Assign custom colors: blue/red for trips, green/lightgreen for total
def color_mapper(row):
    if row["Trip"] == "Total":
        return "green" if row["Metric"] == "Cost (SAR)" else "lightgreen"
    else:
        return "red" if row["Metric"] == "Cost (SAR)" else "blue"

melted_df["Color"] = melted_df.apply(color_mapper, axis=1)

# Plot
fig = px.bar(
    melted_df,
    x="Trip",
    y="Value",
    color="Color",
    text="Value",
    barmode="group",
    title="📊 Distance and Cost per Trip"
)

fig.update_traces(texttemplate="%{y:.2f}", textposition="outside", showlegend=False)
st.plotly_chart(fig, use_container_width=True)