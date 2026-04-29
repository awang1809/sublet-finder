import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
left, right = st.columns([1,1])

st.markdown("## view the price history of the sublet that you're interested in:")

sublet = pd.read_csv("data/postings.csv")
sublet["date"] = pd.to_datetime(sublet["date"])

unit = st.selectbox("**UNIT TYPE:**", 
    ("Any", "Studio", "1-bedroom", "2-bedroom", "4-bedroom"))

residences = st.multiselect("**RESIDENCE:**", ["Marine Drive", "Exchange Residence", "Ponderosa Commons",
    "Brock Commons", "Acadia Park", "Thunderbird Residence", "KWTQ", "Iona House"], default=
    ["Marine Drive", "Exchange Residence", "Ponderosa Commons",
    "Brock Commons", "Acadia Park", "Thunderbird Residence", "KWTQ", "Iona House"])

sublet = sublet[["date", "residence", "unit_type", "rent_cad"]]
sublet = sublet[sublet['residence'].isin(residences)]
if unit != "Any":
    sublet = sublet[sublet['unit_type'] == unit]

sublet_line = sublet.groupby("date")["rent_cad"].mean().reset_index()

if residences:
    date_range = pd.date_range(start=sublet_line["date"].min(), end=sublet_line["date"].max(), freq="D")
    sublet_line = (sublet_line.set_index("date").reindex(date_range, fill_value=None).reset_index().rename(columns={"index": "date"}))
    sublet_line["rent_cad"] = sublet_line["rent_cad"].interpolate(method="linear")

sublet_bar = sublet.groupby("date")["residence"].count()
with left:
    st.line_chart(sublet_line.set_index("date")["rent_cad"], x_label="Date", y_label="Rent", width="stretch", height=400)
with right:
    st.bar_chart(sublet_bar, x_label="Date", y_label="Amount of postings", width="stretch", height=400)