# ✅ Optimized Streamlit App with Cached Routing and Delayed Heavy Tasks

import streamlit as st
import pandas as pd
import openrouteservice
import folium
from streamlit_folium import st_folium

# --- Setup ---
st.set_page_config(page_title="Date Delivery Dashboard", layout="wide")
st.title("📦 Date Delivery Dashboard")
st.caption("Enter store demands and visualize van delivery routes.")

# --- REGIONS DEFINITION (you should move this to a separate file or API if it's too long) ---
regions = {
    "Region 1": [
        {"store": "Al Jazera Rabie", "code": "A1-J-RI", "lat": 24.77327743, "lon": 46.65507078},
    {"store": "Al Jazera Yasmeen", "code": "A1-J-YN", "lat": 24.82200725, "lon": 46.63035005},
    {"store": "Carrefour Tala Mall", "code": "A1-C-NL", "lat": 24.77191384, "lon": 46.66890489},
    {"store": "Danube Al-Ghadeer", "code": "A1-D-GR", "lat": 24.77010894, "lon": 46.66511644},
    {"store": "Danube alyasamin", "code": "A1-D-YN", "lat": 24.82360708, "lon": 46.65527799},
    {"store": "Panda 05", "code": "A1-P-SA", "lat": 24.79816323, "lon": 46.64220638},
    {"store": "Panda 10003 Alia", "code": "A1-P-RI", "lat": 24.80750705, "lon": 46.66907814},
    {"store": "Panda 101", "code": "A1-P-NA", "lat": 24.80675473, "lon": 46.69284581},
    {"store": "Panda 155", "code": "A1-P-NS", "lat": 24.81460881, "lon": 46.72534301},
    {"store": "Panda 101", "code": "A1-P-NA", "lat": 24.80675473, "lon": 46.69285654},
    {"store": "Panda 177", "code": "A1-P-MH", "lat": 24.81469646, "lon": 46.72534301},
    {"store": "Spar Yasmeen", "code": "A1-SYN-YN", "lat": 24.82268059, "lon": 46.65027672},
    {"store": "Tamimi 150", "code": "A1-T-YN", "lat": 24.82055699, "lon": 46.64246374},
    {"store": "Tamimi 155", "code": "A1-T-NS", "lat": 24.85843413, "lon": 46.64687467},
    {"store": "Tamimi 160", "code": "A1-T-RI", "lat": 24.7910008, "lon": 46.64908309},
    {"store": "Tamimi 155", "code": "A1-T-NS", "lat": 24.8192612, "lon": 46.68674659},
    {"store": "Al Jazeera Sulemania", "code": "A1-J-MT", "lat": 24.7559616, "lon": 46.6837359},
    {"store": "Al Sadhaan Marouj", "code": "A1-SN-MJ", "lat": 24.7537898, "lon": 46.6640234},
    {"store": "Carrefour Garnada", "code": "A1-C-GH", "lat": 24.7809357, "lon": 46.7291759},
    {"store": "Danube Al Maghriqat", "code": "A1-D-MG", "lat": 24.761595, "lon": 46.7231027},
    {"store": "Manuel", "code": "A1-ML-NZ", "lat": 24.7588202, "lon": 46.7158892},
    {"store": "Panda 01", "code": "A1-P-SH", "lat": 24.7194598, "lon": 46.6909462},
    {"store": "Panda 104", "code": "A1-P-IZ", "lat": 24.778361, "lon": 46.7100689},
    {"store": "Spar Nuzha", "code": "A1-SNZ-NZ", "lat": 24.764191, "lon": 46.7143295},
    {"store": "Tamimi 134", "code": "A1-T-NZ", "lat": 24.7574589, "lon": 46.712862},
    {"store": "Panda 121", "code": "A1-P-YK", "lat": 24.7984362, "lon": 46.6420482},
    {"store": "Panda 156", "code": "A1-P-HM", "lat": 24.8369625, "lon": 46.7430598},
    {"store": "Tamimi 159", "code": "A1-T-SN", "lat": 24.7283786, "lon": 46.6909123},
    {"store": "Tamimi 165", "code": "A1-T-NDA", "lat": 24.80129, "lon": 46.6740985},
    {"store": "Al Sadhan King abdullah", "code": "A1-SN-WD", "lat": 24.731641, "lon": 46.674702},
    {"store": "Al Sadhan olya", "code": "A1-SN-OY", "lat": 24.73181901, "lon": 46.67471245},
    {"store": "Danube alhayaa", "code": "A1-D-KF", "lat": 24.74379309, "lon": 46.67942164},
    {"store": "Panda 114", "code": "A1-P-MF", "lat": 24.770748, "lon": 46.688954},
    {"store": "Panda 13", "code": "A1-P-MF(2)", "lat": 24.760752, "lon": 46.674567}
    ],

    "Region 2": [
        {"store": "Danube Al Nakhlah", "code": "A2-D-NH", "lat": 24.74076727, "lon": 46.64475332},
    {"store": "Danube Hittin", "code": "A2-D-HN", "lat": 24.75339879, "lon": 46.60989062},
    {"store": "Danube tilal", "code": "A2-D-MA", "lat": 24.8085767, "lon": 46.61644289},
    {"store": "HP Panda 10004", "code": "A2-HP-HN", "lat": 24.75343512, "lon": 46.58588005},
    {"store": "Panda 125", "code": "A2-P-Nk", "lat": 24.74435609, "lon": 46.62116199},
    {"store": "Spar Nakheel", "code": "A2-SNK-Nk", "lat": 24.74329357, "lon": 46.65120285},
    {"store": "Tamimi 152", "code": "A2-T-MA", "lat": 24.80169832, "lon": 46.60325121},
    {"store": "Al Jazeera Aqiq", "code": "A2-J-AQ", "lat": 24.7668505, "lon": 46.6226404},
    {"store": "Carrefour Park", "code": "A2-C-AQ", "lat": 24.7585705, "lon": 46.6298084},
    {"store": "Danube aleaqiq", "code": "A2-D-AQ", "lat": 24.7628259, "lon": 46.6256822},
    {"store": "spar aqeq", "code": "A2-SAQ-AQ", "lat": 24.7855021, "lon": 46.6340227},
    {"store": "Spar Rahmania", "code": "A2-SR-R", "lat": 24.7115515, "lon": 46.6623195},
    {"store": "Tamimi 148", "code": "A2-T-NHD", "lat": 24.7419941, "lon": 46.6032341},
    {"store": "Al Sadhan Sahafa", "code": "A2-SN-SHF", "lat": 24.810072, "lon": 46.624147},
    {"store": "Carrefour Sados", "code": "A2-C-IQ", "lat": 24.685599, "lon": 46.582742},
    {"store": "Danube earqa", "code": "A2-D-IQ", "lat": 24.694253, "lon": 46.605778},
    {"store": "Panda 10022 Galary", "code": "A2-P-KF", "lat": 24.741813, "lon": 46.658356},
    {"store": "Tamimi 142", "code": "A2-T-IQ", "lat": 24.694086, "lon": 46.607353}
    ],

    "Region 3": [
        {"store": "Carrefour Qasar", "code": "A3-C-Q", "lat": 24.72392483, "lon": 46.77511304},
    {"store": "Danube Al Waha", "code": "A3-D-W", "lat": 24.7855432, "lon": 46.7994933},
    {"store": "Al Sadhaan Manar Khuraish", "code": "A3-SN-MN", "lat": 24.7280214, "lon": 46.7841065},
    {"store": "Al Sadhaan Rawdha", "code": "A3-SN-RW", "lat": 24.7537953, "lon": 46.7698137},
    {"store": "Carrefour quods", "code": "A3-C-QS", "lat": 24.7564006, "lon": 46.7603304},
    {"store": "Carrefoure Khuraish", "code": "A3-C-RW", "lat": 24.7235466, "lon": 46.7751711},
    {"store": "Danube Andalusia", "code": "A3-D-AS", "lat": 24.7352131, "lon": 46.7836774},
    {"store": "Danube Rawabi", "code": "A3-D-RWI", "lat": 24.6854953, "lon": 46.7941638},
    {"store": "Danube Yarmouk", "code": "A3-D-YK", "lat": 24.812373, "lon": 46.770157},
    {"store": "HP Panda 10008 Ryan", "code": "A3-HP-RN", "lat": 24.7024288, "lon": 46.7705606},
    {"store": "HP Panda 10013 Sheikh Jaber", "code": "A3-HP-YK", "lat": 24.7983409, "lon": 46.8145969},
    {"store": "Panda 110", "code": "A3-P-H", "lat": 24.7681581, "lon": 46.7571312},
    {"store": "Panda 116", "code": "A3-P-QD", "lat": 24.7551094, "lon": 46.7915755},
    {"store": "Panda 124", "code": "A3-P-NHD", "lat": 24.6810412, "lon": 46.7830672},
    {"store": "Panda 121", "code": "A3-P-YK", "lat": 24.8176386, "lon": 46.781834},
    {"store": "Panda 140", "code": "A3-P-ND", "lat": 24.811306, "lon": 46.9000236},
    {"store": "Panda 146", "code": "A3-P-NM", "lat": 24.7255769, "lon": 46.8160959},
    {"store": "Panda 146", "code": "A3-P-NM", "lat": 24.8278211, "lon": 46.7818354},
    {"store": "Panda 146", "code": "A3-P-NM", "lat": 24.7016751, "lon": 46.8334267},
    {"store": "Spar Hamra", "code": "A3-SH-H", "lat": 24.7628677, "lon": 46.7455837},
    {"store": "Tamimi 180", "code": "A3-T-IH", "lat": 24.779418, "lon": 46.788618},
    {"store": "Panda 26", "code": "A3-P-OL", "lat": 24.742204, "lon": 46.807839},
    {"store": "Panda 10014", "code": "A3-P-SW", "lat": 24.789925, "lon": 46.764848},
    {"store": "Panda 117", "code": "A3-P-MTH", "lat": 24.811385, "lon": 46.87663},
    {"store": "Panda 119", "code": "A3-P-RB", "lat": 24.807755, "lon": 46.806916},
    {"store": "Panda 04", "code": "A3-P-MU", "lat": 24.71171, "lon": 46.845049}
    ],
    "Region 4": [
    {"store": "Al Jazerah Takasusi", "code": "A4-J-Nk", "lat": 24.67923569, "lon": 46.7553215},
    {"store": "Al Jazeera Sulemania", "code": "A4-J-SH", "lat": 24.7055562, "lon": 46.6886577},
    {"store": "Al Sadhan Sulemania", "code": "A4-SN-SH", "lat": 24.7070377, "lon": 46.68916},
    {"store": "Danube altakhasusiu", "code": "A4-D-MM", "lat": 24.6659221, "lon": 46.6831204},
    {"store": "Panda 01", "code": "A4-P-SH", "lat": 24.6651906, "lon": 46.7111002},
    {"store": "Panda 158", "code": "A4-P-MR", "lat": 24.6153925, "lon": 46.7464658},
    {"store": "Tamimi 136", "code": "A4-T-SH", "lat": 24.698075, "lon": 46.7016967},
    {"store": "Farm 51", "code": "A4-FM-SF", "lat": 24.6544575, "lon": 46.6693714},
    {"store": "HP Panda Salam mall", "code": "A4-HP-SM", "lat": 24.5571512, "lon": 46.6373092},
    {"store": "Panda 121", "code": "A4-P-YK", "lat": 24.5702212, "lon": 46.8357108},
    {"store": "Panda 131", "code": "A4-P-RW", "lat": 24.5695707, "lon": 46.7882154},
    {"store": "Al Sadhan Rabwa", "code": "A4-SN-RB", "lat": 24.68876136, "lon": 46.75250942},
    {"store": "Al Sadhan Rabwa", "code": "A4-SN-RB", "lat": 24.688664, "lon": 46.752489},
    {"store": "Al Sadhan shafa", "code": "A4-SN-SHFA", "lat": 24.545833, "lon": 46.712127},
    {"store": "Carrefoure Flamingo", "code": "A4-C-SW", "lat": 24.600748, "lon": 46.69908},
    {"store": "Danube albadiea", "code": "A4-D-BD", "lat": 24.592456, "lon": 46.621979},
    {"store": "Danube panorama", "code": "A4-D-MZ", "lat": 24.693625, "lon": 46.668143},
    {"store": "HP Panda 100", "code": "A4-HP-MZ", "lat": 24.676289, "lon": 46.677194},
    {"store": "HP Panda 10006 Uraijah", "code": "A4-HP-AZ", "lat": 24.578825, "lon": 46.584268},
    {"store": "HP Panda 10007", "code": "A4-HP-HZM", "lat": 24.537192, "lon": 46.656921},
    {"store": "HP Panda 10010", "code": "A4-HP-UM", "lat": 24.679862, "lon": 46.653596},
    {"store": "HP Panda 100", "code": "A4-HP-MZ", "lat": 24.664741, "lon": 46.682404},
    {"store": "HP Panda 10010", "code": "A4-HP-UM", "lat": 24.68010222, "lon": 46.65346829},
    {"store": "Hp Panda Badia", "code": "A4-HP-BD", "lat": 24.604124, "lon": 46.650225},
    {"store": "Panda 04", "code": "A4-P-MU", "lat": 24.665572, "lon": 46.711122},
    {"store": "Panda 08", "code": "A4-P-JR", "lat": 24.677211, "lon": 46.744174},
    {"store": "Panda 102", "code": "A4-P-MZ", "lat": 24.649948, "lon": 46.726401},
    {"store": "Panda 118", "code": "A4-P-AZ", "lat": 24.586328, "lon": 46.759865},
    {"store": "Panda 10014", "code": "A4-P-SW", "lat": 24.63969914, "lon": 46.69319368},
    {"store": "Panda 144", "code": "A4-P-B", "lat": 24.5866367, "lon": 46.75987175},
    {"store": "Panda 6", "code": "A4-P-OL", "lat": 24.639445, "lon": 46.693209},
    {"store": "Panda 07", "code": "A4-P-OL", "lat": 24.627727, "lon": 46.681699},
    {"store": "Tamimi 129", "code": "A4-T-SW", "lat": 24.589983, "lon": 46.622998},
    {"store": "Tamimi 131", "code": "A4-T-OY", "lat": 24.690919, "lon": 46.682013},
    {"store": "Tamimi 140", "code": "A4-T-RB", "lat": 24.68632, "lon": 46.746638},
    {"store": "Tamimi 144", "code": "A4-T-MZ", "lat": 24.67434, "lon": 46.668434},
    {"store": "Tamimi 144", "code": "A4-T-MZ", "lat": 24.662049, "lon": 46.729971},
    {"store": "Tamimi 140", "code": "A4-T-RB", "lat": 24.68999871, "lon": 46.73342591},
    {"store": "Tamimi 163", "code": "A4-T-ZH", "lat": 24.689819, "lon": 46.733099}

    ]
}
# --- COMBINE ALL STORES ---
all_stores = []
for region_name, stores in regions.items():
    for s in stores:
        s["region"] = region_name
        s["Demand (Boxes)"] = 0
        all_stores.append(s)

df_all = pd.DataFrame(all_stores)
df_all.columns = df_all.columns.str.strip().str.lower()
edited_df = df_all.copy()

# --- SEARCH ---
search_query = st.text_input("🔍 Search for a store (by name or code):", key="store_search").lower()
if search_query:
    filtered_df = edited_df[edited_df.apply(
        lambda row: search_query in row["store"].lower() or search_query in row["code"].lower(), axis=1)]
else:
    filtered_df = edited_df

# --- DATA EDITOR ---
st.subheader("📋 Enter Demand for Stores")
edited_part = st.data_editor(filtered_df, use_container_width=True, num_rows="dynamic", key="editor")
edited_df.update(edited_part)

# --- SAVE BUTTON ---
if st.button("💾 Save All Store Demands"):
    desktop_path = "/Users/rand/Desktop/Nisreen/all_region_demands.csv"
    edited_df.to_csv(desktop_path, index=False)
    st.success(f"All demands saved to: {desktop_path}")
    st.dataframe(edited_df)

    csv_data = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Demand CSV",
        data=csv_data,
        file_name="all_region_demands.csv",
        mime="text/csv",
        key="download_csv"
    )

