import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Retail Sales Intelligence", page_icon="📊", layout="wide")

# Palette
NAVY = "#17365D"
BLUE = "#3D78B2"
TEAL = "#3A9D9A"
GOLD = "#E5B85C"
BG = "#F4F7FB"


st.markdown(f"""
<style>
.stApp {{
    background: {BG};
    color: #000000;
}}

.block-container {{
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    color: #000000;
}}

h1, h2, h3, h4, p, label, span, li {{
    color: #000000;
}}

div[data-testid="stMetric"] {{
    background: white;
    border: 1px solid #DCE5EF;
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(23,54,93,.05);
    color: #000000;
}}

div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
    color: #000000 !important;
}}

[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {{
    color: #000000 !important;
}}
</style>
""", unsafe_allow_html=True)


st.title("Retail Sales Intelligence Dashboard")
st.caption("Interactive overview of sales, profitability, orders, product categories and regional performance.")

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file, parse_dates=["Order Date"])
    else:
        data = pd.read_csv(Path(__file__).with_name("retail_sales_dashboard_data.csv"), parse_dates=["Order Date"])
    return data

uploaded = st.sidebar.file_uploader("Upload a retail sales CSV (optional)", type=["csv"])
data = load_data(uploaded)

# Filters / slicers
st.sidebar.header("Filters")
regions = sorted(data["Region"].dropna().unique().tolist())
categories = sorted(data["Category"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("Region", regions, default=regions)
selected_categories = st.sidebar.multiselect("Category", categories, default=categories)
min_date, max_date = data["Order Date"].min().date(), data["Order Date"].max().date()
date_range = st.sidebar.date_input("Order date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

filtered = data[data["Region"].isin(selected_regions) & data["Category"].isin(selected_categories)].copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[filtered["Order Date"].dt.date.between(start_date, end_date)]

if filtered.empty:
    st.warning("No rows match the selected filters. Change the filters to view results.")
    st.stop()

total_sales = filtered["Sales"].sum()
total_profit = filtered["Profit"].sum()
orders = filtered["Order ID"].nunique()
aov = total_sales / orders if orders else 0

# KPI cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sales", f"₹{total_sales:,.0f}")
c2.metric("Total Profit", f"₹{total_profit:,.0f}")
c3.metric("Number of Orders", f"{orders:,}")
c4.metric("Average Order Value", f"₹{aov:,.0f}")

st.divider()
left, right = st.columns(2)
monthly = filtered.assign(Month=filtered["Order Date"].dt.to_period("M").dt.to_timestamp()).groupby("Month", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
fig_line = px.line(monthly, x="Month", y="Sales", markers=True, title="Monthly Sales Trend", template="plotly_white")
fig_line.update_traces(line_color=BLUE, marker_color=TEAL)
fig_line.update_layout(margin=dict(l=10,r=10,t=55,b=10), xaxis_title="Month", yaxis_title="Sales (₹)")
left.plotly_chart(fig_line, use_container_width=True)

by_category = filtered.groupby("Category", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).sort_values("Sales", ascending=True)
fig_bar = px.bar(by_category, x="Sales", y="Category", orientation="h", color="Sales", title="Sales by Category", template="plotly_white", color_continuous_scale=["#B7D9E8", NAVY])
fig_bar.update_layout(margin=dict(l=10,r=10,t=55,b=10), xaxis_title="Sales (₹)", yaxis_title="")
right.plotly_chart(fig_bar, use_container_width=True)

left2, right2 = st.columns(2)
by_region = filtered.groupby("Region", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique"))
fig_tree = px.treemap(by_region, path=["Region"], values="Sales", color="Profit", color_continuous_scale="RdYlGn", title="Regional Sales Treemap", hover_data={"Orders": True, "Profit": ":,.2f"})
fig_tree.update_layout(margin=dict(l=10,r=10,t=55,b=10))
left2.plotly_chart(fig_tree, use_container_width=True)

city = filtered.groupby("City", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique"))
# Geographic bubble map
fig_map = px.scatter_geo(city, locations="City", locationmode="country names", size="Sales", color="Profit",
                         hover_name="City", hover_data={"Sales": ":,.0f", "Profit": ":,.0f", "Orders": True},
                         scope="asia", title="City Sales Map (bubble size = sales)", template="plotly_white",
                         color_continuous_scale="RdYlGn")
# scatter_geo country-name mode won't geocode Indian cities reliably; use lat/lon for accurate plotting.
coords = {
    "Delhi": (28.6139,77.2090), "Chandigarh": (30.7333,76.7794), "Amritsar": (31.6340,74.8723), "Jaipur": (26.9124,75.7873),
    "Bengaluru": (12.9716,77.5946), "Chennai": (13.0827,80.2707), "Hyderabad": (17.3850,78.4867), "Kochi": (9.9312,76.2673),
    "Kolkata": (22.5726,88.3639), "Patna": (25.5941,85.1376), "Bhubaneswar": (20.2961,85.8245), "Guwahati": (26.1445,91.7362),
    "Mumbai": (19.0760,72.8777), "Pune": (18.5204,73.8567), "Ahmedabad": (23.0225,72.5714), "Surat": (21.1702,72.8311),
    "Bhopal": (23.2599,77.4126), "Indore": (22.7196,75.8577), "Nagpur": (21.1458,79.0882), "Raipur": (21.2514,81.6296)
}
city["Latitude"] = city["City"].map(lambda x: coords[x][0])
city["Longitude"] = city["City"].map(lambda x: coords[x][1])
fig_map = px.scatter_geo(city, lat="Latitude", lon="Longitude", size="Sales", color="Profit", hover_name="City",
                         hover_data={"Sales": ":,.0f", "Profit": ":,.0f", "Orders": True, "Latitude": False, "Longitude": False},
                         scope="asia", projection="natural earth", title="Sales by City (bubble size = sales)", template="plotly_white",
                         color_continuous_scale="RdYlGn")
fig_map.update_geos(lataxis_range=[5,36], lonaxis_range=[67,98], showcountries=True, showland=True, landcolor="#EEF2F6")
fig_map.update_layout(margin=dict(l=0,r=0,t=55,b=0))
right2.plotly_chart(fig_map, use_container_width=True)

st.subheader("Filtered order data")
st.dataframe(filtered, use_container_width=True, hide_index=True)
csv_download = filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered data as CSV", csv_download, "filtered_retail_sales.csv", "text/csv")

st.subheader("Key insights from the current selection")
best_category = filtered.groupby("Category")["Sales"].sum().idxmax()
best_region = filtered.groupby("Region")["Sales"].sum().idxmax()
best_city = filtered.groupby("City")["Sales"].sum().idxmax()
margin = (total_profit / total_sales * 100) if total_sales else 0
ins1, ins2, ins3 = st.columns(3)
ins1.info(f"Top category by sales: **{best_category}**")
ins2.info(f"Top region by sales: **{best_region}**")
ins3.info(f"Top city by sales: **{best_city}**")
st.caption(f"Profit margin for the current selection: {margin:.1f}%. Insights update automatically when filters change.")
