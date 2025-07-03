import streamlit as st
import pandas as pd
from io import StringIO

# ----------------------------------------
# Load file
# ----------------------------------------
st.title("Half Hourly Electricity Pricing Uplift Tool")

uploaded_file = st.file_uploader("Upload Flat File CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # ----------------------------------------
    # Split Half Hourly
    # ----------------------------------------
    hh_df = df[df["Profile_Class"] == "00"].copy()

    st.write("Half Hourly Data Loaded:", hh_df.shape[0], "rows")

    # ----------------------------------------
    # Filter Inputs
    # ----------------------------------------
    st.subheader("Filter Criteria")

    contract_duration = st.selectbox("Select Contract Duration (Months):", [12, 24, 36])

    min_start_date = pd.to_datetime(hh_df["Minimum_Contract_Start_Date"]).min()
    max_start_date = pd.to_datetime(hh_df["Maximum_Contract_Start_Date"]).max()

    contract_start = st.date_input("Contract Start Date:", [min_start_date, max_start_date])

    consumption_band = st.selectbox(
        "Select Consumption Band:",
        [
            "0-99999",
            "100000-299999",
            "300000-499999",
            "500000-799999",
            "800000-1000000"
        ]
    )

    green_option = st.radio("Energy Type:", ["Standard", "Green"])

    # ----------------------------------------
    # Apply Filters
    # ----------------------------------------
    filtered = hh_df[
        (hh_df["Contract_Duration"] == contract_duration) &
        (pd.to_datetime(hh_df["Minimum_Contract_Start_Date"]) >= pd.to_datetime(contract_start[0])) &
        (pd.to_datetime(hh_df["Maximum_Contract_Start_Date"]) <= pd.to_datetime(contract_start[1]))
    ]

    # Consumption Band Filtering
    min_c, max_c = map(int, consumption_band.split("-"))
    filtered = filtered[
        (filtered["Minimum_Annual_Consumption"] >= min_c) &
        (filtered["Maximum_Annual_Consumption"] <= max_c)
    ]

    # Green Filtering
    if green_option == "Green":
        filtered = filtered[filtered["Green_Energy"].str.upper() == "TRUE"]
    else:
        filtered = filtered[filtered["Green_Energy"].str.upper() == "FALSE"]

    st.write("Filtered Rows:", filtered.shape[0])

    # ----------------------------------------
    # Uplift Grid Inputs
    # ----------------------------------------
    st.subheader("Uplift Values (Fixed Pence)")

    # For each Contract Duration, allow input
    uplift_df = pd.DataFrame({
        "Contract Duration": [12, 24, 36],
        "Standing Charge Uplift (p)": [0.000, 0.000, 0.000],
        "Day Uplift (p)": [0.000, 0.000, 0.000],
        "Night Uplift (p)": [0.000, 0.000, 0.000],
        "Capacity Uplift (p)": [0.000, 0.000, 0.000]
    })

    edited_uplift_df = st.data_editor(
        uplift_df,
        num_rows="fixed",
        key="uplift_editor"
    )

    # Get selected uplift row
    uplift_row = edited_uplift_df[
        edited_uplift_df["Contract Duration"] == contract_duration
    ].iloc[0]

    # ----------------------------------------
    # Apply Uplifts
    # ----------------------------------------
    st.subheader("Final Pricing Table")

    def apply_uplift(row):
        row["Standing_Charge"] = round(row["Standing_Charge"] + uplift_row["Standing Charge Uplift (p)"], 3)
        row["Day_Rate"] = round(row["Day_Rate"] + uplift_row["Day Uplift (p)"], 3)
        row["Night_Rate"] = round(row["Night_Rate"] + uplift_row["Night Uplift (p)"], 3)
        row["Capacity_Rate"] = round(row["Capacity_Rate"] + uplift_row["Capacity Uplift (p)"], 3)
        return row

    final_df = filtered.apply(apply_uplift, axis=1)

    st.dataframe(final_df)

    # Optionally download
    csv = final_df.to_csv(index=False)
    st.download_button("Download Uplifted CSV", csv, "uplifted_prices.csv", "text/csv")
