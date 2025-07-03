# HH_electricity_pricing.py

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Half Hourly Electricity Pricing", layout="wide")

st.title("Half Hourly Electricity Pricing Uplift Tool")

# File upload
uploaded_file = st.file_uploader("Upload your pricing file (.xlsx)", type=["xlsx"])

if uploaded_file:
    # Load the Excel file
    df = pd.read_excel(uploaded_file)
    
    # Show columns to confirm structure
    st.write("Loaded columns:", df.columns.tolist())

    # Clean 'Rate_Structure' column
    df["Rate_Structure"] = df["Rate_Structure"].astype(str).str.strip()

    # Debug: show unique values for reassurance
    st.write("Unique Rate_Structure values:", df["Rate_Structure"].unique())

    # Filter for Half Hourly
    hh_df = df[df["Rate_Structure"] == "HH"].copy()

    if hh_df.empty:
        st.error("No Half Hourly records found (Rate_Structure == 'HH'). Please check your file.")
    else:
        st.success(f"Found {len(hh_df)} Half Hourly records.")
        st.dataframe(hh_df.head())

        # Contract duration filter
        durations = st.multiselect(
            "Select Contract Durations (months):",
            sorted(hh_df["Contract_Duration"].dropna().unique()),
            default=sorted(hh_df["Contract_Duration"].dropna().unique())
        )

        # Contract start date range filter
        min_start = pd.to_datetime(hh_df["Minimum_Contract_Start_Date"]).min()
        max_start = pd.to_datetime(hh_df["Maximum_Contract_Start_Date"]).max()
        start_range = st.date_input(
            "Contract Start Date Range:",
            value=(min_start, max_start),
            min_value=min_start,
            max_value=max_start
        )

        # Consumption band filter
        consumption_bands = {
            "0 - 99,999": (0, 99999),
            "100,000 - 299,999": (100000, 299999),
            "300,000 - 499,999": (300000, 499999),
            "500,000 - 799,999": (500000, 799999),
            "800,000 - 1,000,000": (800000, 1000000)
        }
        selected_band = st.selectbox(
            "Select Annual Consumption Band:",
            list(consumption_bands.keys())
        )
        band_min, band_max = consumption_bands[selected_band]

        # Green energy filter mapped to "Standard"/"Green"
        hh_df["Green_Label"] = hh_df["Green_Energy"].apply(
            lambda x: "Green" if str(x).strip().upper() == "TRUE" else "Standard"
        )
        green_options = st.multiselect(
            "Select Energy Type:",
            ["Standard", "Green"],
            default=["Standard", "Green"]
        )

        # Apply filters
        filtered_df = hh_df[
            (hh_df["Contract_Duration"].isin(durations)) &
            (pd.to_datetime(hh_df["Minimum_Contract_Start_Date"]) >= pd.Timestamp(start_range[0])) &
            (pd.to_datetime(hh_df["Maximum_Contract_Start_Date"]) <= pd.Timestamp(start_range[1])) &
            (hh_df["Minimum_Annual_Consumption"] <= band_max) &
            (hh_df["Maximum_Annual_Consumption"] >= band_min) &
            (hh_df["Green_Label"].isin(green_options))
        ]

        st.write(f"Filtered records: {len(filtered_df)}")
        st.dataframe(filtered_df)

        # Uplift inputs
        st.header("Apply Uplifts (pence)")

        uplift_sc = st.number_input("Standing Charge Uplift (pence):", value=0.000, format="%.3f")
        uplift_day = st.number_input("Day Rate Uplift (pence):", value=0.000, format="%.3f")
        uplift_night = st.number_input("Night Rate Uplift (pence):", value=0.000, format="%.3f")
        uplift_kva = st.number_input("Capacity Rate Uplift (pence):", value=0.000, format="%.3f")

        # Apply uplifts
        uplifted_df = filtered_df.copy()
        uplifted_df["Standing_Charge"] = uplifted_df["Standing_Charge"].astype(float) + uplift_sc
        uplifted_df["Day_Rate"] = uplifted_df["Day_Rate"].astype(float) + uplift_day
        uplifted_df["Night_Rate"] = uplifted_df["Night_Rate"].astype(float) + uplift_night
        uplifted_df["Capacity_Rate"] = uplifted_df["Capacity_Rate"].astype(float) + uplift_kva

        st.success("Uplifts applied.")
        st.dataframe(uplifted_df)

        # Download link
        def convert_df(df):
            return df.to_csv(index=False).encode("utf-8")

        csv = convert_df(uplifted_df)
        st.download_button(
            label="Download Uplifted Pricing CSV",
            data=csv,
            file_name="uplifted_half_hourly_pricing.csv",
            mime="text/csv"
        )
