from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd


today = date.today()
one_week_ago = today - timedelta(days = 7)
# cleaning data
sublet = pd.read_csv("data/postings.csv")
sublet["negotiable"] = sublet["negotiable"].fillna("No")
sublet["negotiable"] = sublet["negotiable"].replace("Negotiable", "Yes")
sublet["gender"] = sublet["gender"].fillna("Any")
sublet["gender"] = sublet["gender"].replace("Any / mixed", "Any")
sublet["date"] = pd.to_datetime(sublet["date"])

min_rent = sublet["rent_cad"].min()
max_rent = sublet["rent_cad"].max()

st.set_page_config(layout="wide")
left, right = st.columns([1,2])

with left: 
    st.markdown("## find your ubc sublet today!")
    st.markdown("##### browse through hundreds of whatsapp sublet postings with filters for rent, residence, unit type, gender etc.")

    min_price, max_price = st.slider(
        "**RENT:**", min_rent, max_rent, (min_rent, max_rent), 50)

    residences = st.multiselect("**RESIDENCE:**", ["Marine Drive", "Exchange Residence", "Ponderosa Commons",
    "Brock Commons", "Acadia Park", "Thunderbird Residence", "KWTQ", "Iona House"])

    gender = st.selectbox("**GENDER:**", ("Any", "Male", "Female"))

    unit = st.selectbox("**UNIT TYPE:**", 
    ("Any", "Studio", "1-bedroom", "2-bedroom", "3-bedroom", "4-bedroom", "5-bedroom", "6-bedroom"))

    date_after = st.date_input("**LISTING POSTED AFTER:**", value=one_week_ago)

    negotiable = st.checkbox("**Negotiable?**")

    st.markdown("double click to expand the message column to look for contact info")
    st.markdown("alternatively, join the WhatsApp chat to inquire directly:")
    st.link_button("WhatsApp", "https://chat.whatsapp.com/CYiCreQCkjM02gn6EWWS7M")
sublet = sublet[(sublet["rent_cad"] >= min_price) & (sublet["rent_cad"] <= max_price)]
sublet = sublet[sublet["residence"].isin(residences)]
if gender == "Male":
    sublet = sublet[sublet["gender"] != "Female"]
elif gender == "Female":
    sublet = sublet[sublet["gender"] != "Male"]
if unit != "Any":
    sublet = sublet[sublet["unit_type"] == unit]
sublet = sublet[sublet["date"] >= pd.Timestamp(date_after)]
if negotiable:
    sublet = sublet[sublet["negotiable"] == "Yes"]
sublet = sublet[["date", "sender", "residence", "unit_type", "rent_cad", "gender", "negotiable", "message"]]

with right:
    st.dataframe(sublet, width="stretch", height=700)
