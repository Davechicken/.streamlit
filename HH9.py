import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Half Hourly Electricity Pricing Uplift Tool")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    hh_df = df[df["Rate_Structure"].str.upper() == "HH"]

    if hh_df.empty:
        st.error("No Half Hourly records found (Rate_Structure = 'HH'). Please check your file.")
    else:
        st.subheader("Raw Half Hourly Data")
        st.dataframe(hh_df, use_container_width=True)

        # Contract Duration Dropdown
        contract_options = sorted(hh_df["Contract_Duration"].dropna().unique())
        selected_duration = st.selectbox("Select Contract Duration (Months):", contract_options)

        # Energy Type Dropdown
        energy_options = ["Standard", "Green"]
        selected_energy = st.selectbox("Select Energy Type:", energy_options)
        energy_flag = True if selected_energy.lower() == "green" else False

        # Filter
        filtered_df = hh_df[
            (hh_df["Contract_Duration"] == selected_duration) &
            (hh_df["Green_Energy"] == energy_flag)
        ]

        if filtered_df.empty:
            st.warning("No data matches your filters.")
        else:
            st.subheader("Define Uplifts per Consumption Band (pence)")

            consumption_bands = [
                (0, 99999),
                (100000, 299999),
                (300000, 499999),
                (500000, 799999),
                (800000, 1000000)
            ]

            uplift_data = []
            for band in consumption_bands:
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.write(f"{band[0]:,}-{band[1]:,} kWh")
                with col2:
                    standing = st.number_input(f"Standing Charge ({band[0]}-{band[1]})", value=0.000, format="%.3f")
                with col3:
                    day = st.number_input(f"Day Rate ({band[0]}-{band[1]})", value=0.000, format="%.3f")
                with col4:
                    night = st.number_input(f"Night Rate ({band[0]}-{band[1]})", value=0.000, format="%.3f")
                with col5:
                    kva = st.number_input(f"kVA Rate ({band[0]}-{band[1]})", value=0.000, format="%.3f")
                uplift_data.append({
                    "band": band,
                    "standing": standing,
                    "day": day,
                    "night": night,
                    "kva": kva
                })

            # Spinner while calculating
            with st.spinner("Applying uplifts..."):
                def apply_uplifts(row):
                    annual = row["Maximum_Annual_Consumption"]
                    for uplift in uplift_data:
                        if uplift["band"][0] <= annual <= uplift["band"][1]:
                            row["Standing_Charge"] = round((row["Standing_Charge"] or 0) + uplift["standing"], 3)
                            row["Day_Rate"] = round((row["Day_Rate"] or 0) + uplift["day"], 3)
                            row["Night_Rate"] = round((row["Night_Rate"] or 0) + uplift["night"], 3)
                            row["Capacity_Rate"] = round((row["Capacity_Rate"] or 0) + uplift["kva"], 3)
                            row["Consumption_Band"] = f"{uplift['band'][0]:,}-{uplift['band'][1]:,}"
                            break
                    return row

                result_df = filtered_df.apply(apply_uplifts, axis=1)

                # Sort by band order
                band_order = [f"{b[0]:,}-{b[1]:,}" for b in consumption_bands]
                result_df["Consumption_Band"] = pd.Categorical(result_df["Consumption_Band"], categories=band_order, ordered=True)
                result_df = result_df.sort_values("Consumption_Band")

            # Display final table
            display_cols = [
                "Consumption_Band", "Contract_Duration", "Green_Energy",
                "Standing_Charge", "Day_Rate", "Night_Rate", "Capacity_Rate"
            ]
            st.subheader("Uplifted Pricing Data")
            st.dataframe(result_df[display_cols], use_container_width=True)

            # Excel download
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                result_df.to_excel(writer, index=False)
            output.seek(0)

            st.download_button(
                label="Download Uplifted Data as Excel",
                data=output,
                file_name="uplifted_pricing.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
