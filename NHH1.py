# nhh_pricing_app.py

import streamlit as st
import pandas as pd

# Load the flat file
@st.cache_data
def load_data():
    return pd.read_csv("nhh_flat_file.xlsx")

df = load_data()

st.title("NHH Pricing Calculator")

# User Inputs
eac = st.number_input(
    "Estimated Annual Consumption (kWh)",
    min_value=0,
    step=100
)

contract_duration = st.selectbox(
    "Contract Duration (months)",
    options=sorted(df["Contract_Duration"].unique())
)

st.subheader("Uplifts")
uplift_standing = st.number_input("Standing Charge Uplift (p/day)", value=0.0, step=0.1)
uplift_day = st.number_input("Day Rate Uplift (p/kWh)", value=0.0, step=0.1)
uplift_night = st.number_input("Night Rate Uplift (p/kWh)", value=0.0, step=0.1)
uplift_evw = st.number_input("Evening & Weekend Uplift (p/kWh)", value=0.0, step=0.1)

st.subheader("Consumption Split (%)")
day_pct = st.slider("Day %", 0, 100, 70)
night_pct = st.slider("Night %", 0, 100, 20)
evw_pct = st.slider("Evening & Weekend %", 0, 100, 10)

# Validation
if day_pct + night_pct + evw_pct != 100:
    st.error("The % split must add up to 100%.")
else:
    if st.button("Calculate"):

        # Filter DataFrame
        filtered = df[
            (df["Rate_Structure"] == "NHH") &
            (df["Contract_Duration"] == contract_duration) &
            (df["Minimum_Annual_Consumption"] <= eac) &
            (df["Maximum_Annual_Consumption"] >= eac)
        ]

        if filtered.empty:
            st.error("No matching tariff found for this EAC and contract duration.")
        else:
            row = filtered.iloc[0]

            # Base Rates
            standing_p_day = row["Standing_Charge"] + uplift_standing
            day_p_kwh = row["Day_Rate"] + uplift_day
            night_p_kwh = row["Night_Rate"] + uplift_night
            evw_p_kwh = row["Evening_And_Weekend_Rate"] + uplift_evw

            # Consumption Split
            day_kwh = eac * (day_pct / 100)
            night_kwh = eac * (night_pct / 100)
            evw_kwh = eac * (evw_pct / 100)

            # Costs
            standing_cost = standing_p_day * 365 / 100  # p to £
            day_cost = (day_kwh * day_p_kwh) / 100
            night_cost = (night_kwh * night_p_kwh) / 100
            evw_cost = (evw_kwh * evw_p_kwh) / 100

            total_cost = standing_cost + day_cost + night_cost + evw_cost

            # Display Results
            st.success("Calculation Complete")
            st.markdown(f"**Matched Band:** {row['Minimum_Annual_Consumption']}–{row['Maximum_Annual_Consumption']} kWh")

            results = {
                "Standing Charge (p/day)": standing_p_day,
                "Day Rate (p/kWh)": day_p_kwh,
                "Night Rate (p/kWh)": night_p_kwh,
                "Evening & Weekend Rate (p/kWh)": evw_p_kwh,
                "Annual Standing Charge (£)": standing_cost,
                "Annual Day Consumption (£)": day_cost,
                "Annual Night Consumption (£)": night_cost,
                "Annual Evening/Weekend Consumption (£)": evw_cost,
                "Estimated Annual Cost (£)": total_cost
            }

            st.table(pd.DataFrame(results.items(), columns=["Description", "Value"]))
