import streamlit as st
import pandas as pd

st.title("Half Hourly Electricity Pricing Uplift Tool")

# File uploader for Excel
uploaded_file = st.file_uploader("Upload Supplier Pricing File (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # Validate that Rate_Structure exists
    if "Rate_Structure" not in df.columns:
        st.error("The uploaded file does not contain a 'Rate_Structure' column.")
    else:
        # Filter for Half Hourly
        hh_df = df[df["Rate_Structure"] == "HH"].copy()

        if hh_df.empty:
            st.warning("No Half Hourly records found (Rate_Structure == 'HH').")
        else:
            # Map Green_Energy to Standard/Green
            hh_df["Energy_Type"] = hh_df["Green_Energy"].map({True: "Green", False: "Standard"})

            # UI selections
            contract_duration = st.selectbox(
                "Select Contract Duration (Months):",
                options=[12, 24, 36],
                index=0
            )

            energy_type = st.selectbox(
                "Select Energy Type:",
                options=["Standard", "Green"],
                index=0
            )

            # Filtered DataFrame
            filtered_df = hh_df[
                (hh_df["Contract_Duration"] == contract_duration) &
                (hh_df["Energy_Type"] == energy_type)
            ].copy()

            if filtered_df.empty:
                st.warning("No records match the selected Contract Duration and Energy Type.")
            else:
                # Define consumption bands
                bands = [
                    (0, 99999),
                    (100000, 299999),
                    (300000, 499999),
                    (500000, 799999),
                    (800000, 1000000)
                ]

                # Show bands for reference
                st.subheader("Consumption Bands")
                for bmin, bmax in bands:
                    st.write(f"{bmin} - {bmax} kWh")

                # Uplift grid
                st.subheader("Apply Uplifts (in pence)")

                uplift_data = []
                for bmin, bmax in bands:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        standing = st.number_input(
                            f"Standing Charge uplift ({bmin}-{bmax})",
                            value=0.000, step=0.001, format="%.3f", key=f"standing_{bmin}"
                        )
                    with col2:
                        day = st.number_input(
                            f"Day Rate uplift ({bmin}-{bmax})",
                            value=0.000, step=0.001, format="%.3f", key=f"day_{bmin}"
                        )
                    with col3:
                        night = st.number_input(
                            f"Night Rate uplift ({bmin}-{bmax})",
                            value=0.000, step=0.001, format="%.3f", key=f"night_{bmin}"
                        )
                    with col4:
                        capacity = st.number_input(
                            f"Capacity Rate uplift ({bmin}-{bmax})",
                            value=0.000, step=0.001, format="%.3f", key=f"capacity_{bmin}"
                        )
                    uplift_data.append({
                        "band_min": bmin,
                        "band_max": bmax,
                        "Standing_Charge": standing,
                        "Day_Rate": day,
                        "Night_Rate": night,
                        "Capacity_Rate": capacity
                    })

                # Process uplifts
                output_rows = []

                for _, row in filtered_df.iterrows():
                    cons = row["Minimum_Annual_Consumption"]
                    uplift_row = None
                    for band in uplift_data:
                        if band["band_min"] <= cons <= band["band_max"]:
                            uplift_row = band
                            break
                    if uplift_row is None:
                        # Skip if not in any band
                        continue

                    # Create output row
                    new_row = row.copy()
                    new_row["Standing_Charge"] = row.get("Standing_Charge", 0) + uplift_row["Standing_Charge"]
                    new_row["Day_Rate"] = row.get("Day_Rate", 0) + uplift_row["Day_Rate"]
                    new_row["Night_Rate"] = row.get("Night_Rate", 0) + uplift_row["Night_Rate"]
                    new_row["Capacity_Rate"] = row.get("Capacity_Rate", 0) + uplift_row["Capacity_Rate"]
                    new_row["Consumption_Band"] = f"{uplift_row['band_min']}-{uplift_row['band_max']}"

                    output_rows.append(new_row)

                if not output_rows:
                    st.warning("No rows fell within the defined consumption bands.")
                else:
                    result_df = pd.DataFrame(output_rows)

                    st.subheader("Uplifted Pricing Data")
                    st.dataframe(result_df)

                    # Download
                    st.download_button(
                        label="Download Uplifted Data as Excel",
                        data=result_df.to_excel(index=False, engine="openpyxl"),
                        file_name="uplifted_pricing.xlsx"
                    )
