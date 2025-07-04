import streamlit as st
import pandas as pd
import io

# Set wide layout
st.set_page_config(
    page_title="NHH Pricing Calculator",
    layout="wide"
)

st.title("NHH Pricing Calculator")

# File uploader
uploaded_file = st.file_uploader("Upload the Flat File (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    st.write("✅ Flat file loaded successfully.")
    st.dataframe(df.head())

    # User Inputs
    eac = st.number_input(
        "Estimated Annual Consumption (kWh)",
        min_value=0,
        step=100
    )

    contract_duration = st.selectbox(
        "Contract Duration (months)",
        options=sorted(df["Contract_Duration"].dropna().unique())
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
        calculate_btn = st.button("Calculate")

        if calculate_btn:
            with st.spinner("Processing..."):
                @st.cache_data(show_spinner=False)
                def process_pricing(df, eac, contract_duration,
                                    uplift_standing, uplift_day, uplift_night, uplift_evw,
                                    day_pct, night_pct, evw_pct):
                    # Filter for matching row
                    filtered = df[
                        (df["Rate_Structure"].str.upper() == "NHH") &
                        (df["Contract_Duration"] == contract_duration) &
                        (df["Minimum_Annual_Consumption"] <= eac) &
                        (df["Maximum_Annual_Consumption"] >= eac)
                    ]
                    if filtered.empty:
                        return None, None
                    row = filtered.iloc[0]

                    # Base rates + uplifts
                    standing_p_day = row["Standing_Charge"] + uplift_standing
                    day_p_kwh = row["Day_Rate"] + uplift_day
                    night_p_kwh = row["Night_Rate"] + uplift_night
                    evw_p_kwh = row["Evening_And_Weekend_Rate"] + uplift_evw

                    # Consumption split
                    day_kwh = eac * (day_pct / 100)
                    night_kwh = eac * (night_pct / 100)
                    evw_kwh = eac * (evw_pct / 100)

                    # Costs
                    standing_cost = standing_p_day * 365 / 100
                    day_cost = (day_kwh * day_p_kwh) / 100
                    night_cost = (night_kwh * night_p_kwh) / 100
                    evw_cost = (evw_kwh * evw_p_kwh) / 100

                    total_cost = standing_cost + day_cost + night_cost + evw_cost

                    results_df = pd.DataFrame({
                        "Description": [
                            "Standing Charge (p/day)",
                            "Day Rate (p/kWh)",
                            "Night Rate (p/kWh)",
                            "Evening & Weekend Rate (p/kWh)",
                            "Annual Standing Charge (£)",
                            "Annual Day Consumption (£)",
                            "Annual Night Consumption (£)",
                            "Annual Evening & Weekend Consumption (£)",
                            "Estimated Annual Cost (£)"
                        ],
                        "Value": [
                            standing_p_day,
                            day_p_kwh,
                            night_p_kwh,
                            evw_p_kwh,
                            standing_cost,
                            day_cost,
                            night_cost,
                            evw_cost,
                            total_cost
                        ]
                    })

                    return row, results_df

                matched_row, results_df = process_pricing(
                    df, eac, contract_duration,
                    uplift_standing, uplift_day, uplift_night, uplift_evw,
                    day_pct, night_pct, evw_pct
                )

            if matched_row is None:
                st.error("No matching tariff found for this EAC and contract duration.")
            else:
                st.success("Calculation Complete")
                st.markdown(
                    f"**Matched Band:** {matched_row['Minimum_Annual_Consumption']} – {matched_row['Maximum_Annual_Consumption']} kWh"
                )
                st.table(results_df)

                # Custom output filename
                file_name = st.text_input(
                    "Custom Output Filename (without extension)",
                    value="nhh_quote"
                )

                # Prepare Excel download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    results_df.to_excel(writer, index=False, sheet_name="NHH Quote")
                    writer.save()
                processed_data = output.getvalue()

                st.download_button(
                    label="Download Excel Quote",
                    data=processed_data,
                    file_name=f"{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

else:
    st.warning("Please upload the flat file to start.")
