import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

@st.cache_data
def load_data(uploaded_file):
    return pd.read_excel(uploaded_file)

st.title("NHH Pricing Tool")

# Upload flat file
uploaded_file = st.file_uploader("Upload the NHH flat file (XLSX)", type="xlsx")
if uploaded_file is not None:
    df = load_data(uploaded_file)

    # User selects Standard or Green
    green_choice = st.radio("Select Energy Type:", ["Standard", "Green"])
    green_flag = "Y" if green_choice == "Green" else "N"

    # User inputs EAC
    eac = st.number_input("Enter Estimated Annual Consumption (kWh):", min_value=0)

    # Filter by Standard/Green
    df_filtered = df[df["Green_Energy"] == green_flag]

    # Show Contract Duration options
    contract_options = df_filtered["Contract_Duration"].dropna().unique()
    contract_duration = st.selectbox("Select Contract Duration (Months):", sorted(contract_options))

    # Further filter
    df_filtered = df_filtered[df_filtered["Contract_Duration"] == contract_duration]

    # Show bands and allow uplifts per band
    st.subheader("Set Uplifts (p/kWh or p/Day) Per Consumption Band")
    uplift_inputs = []
    for _, row in df_filtered.iterrows():
        min_consumption = row["Minimum_Annual_Consumption"]
        max_consumption = row["Maximum_Annual_Consumption"]

        st.markdown(f"**Consumption Band: {int(min_consumption)} – {int(max_consumption)} kWh**")

        uplift_standing = st.number_input(
            f"Standing Charge Uplift (p/day) for {int(min_consumption)}–{int(max_consumption)} kWh",
            value=0.0,
            key=f"sc_{min_consumption}_{max_consumption}"
        )
        uplift_unit = st.number_input(
            f"Unit Rate Uplift (p/kWh) for {int(min_consumption)}–{int(max_consumption)} kWh",
            value=0.0,
            key=f"ur_{min_consumption}_{max_consumption}"
        )
        uplift_inputs.append({
            "min": min_consumption,
            "max": max_consumption,
            "uplift_standing": uplift_standing,
            "uplift_unit": uplift_unit
        })

    # Process button
    if st.button("Generate Pricing"):
        # Prepare output DataFrame
        output_rows = []

        for _, row in df_filtered.iterrows():
            min_c = row["Minimum_Annual_Consumption"]
            max_c = row["Maximum_Annual_Consumption"]

            # Find the corresponding uplifts
            uplifts = next(u for u in uplift_inputs if u["min"] == min_c and u["max"] == max_c)

            # Calculate uplifted rates
            standing = row["Standing_Charge"] + uplifts["uplift_standing"]
            unit_rate = row["Standard_Rate"] + uplifts["uplift_unit"]

            # Calculate annual cost
            annual_unit_cost = eac * unit_rate / 100  # Convert pence to £
            annual_standing_cost = standing * 365 / 100
            total_annual_cost = annual_unit_cost + annual_standing_cost

            output_rows.append({
                "Consumption Band": f"{int(min_c)}–{int(max_c)}",
                "Standing Charge (p/day)": standing,
                "Unit Rate (p/kWh)": unit_rate,
                "Estimated Annual Consumption (kWh)": eac,
                "Annual Unit Cost (£)": round(annual_unit_cost, 2),
                "Annual Standing Cost (£)": round(annual_standing_cost, 2),
                "Total Annual Cost (£)": round(total_annual_cost, 2)
            })

        output_df = pd.DataFrame(output_rows)

        # Display results
        st.dataframe(output_df, use_container_width=True)

        # Allow download with custom filename
        filename = st.text_input("Enter output filename (without extension):", value="NHH_Pricing")
        if st.button("Download Excel"):
            output_df.to_excel(f"{filename}.xlsx", index=False)
            st.success(f"File '{filename}.xlsx' has been saved.")
