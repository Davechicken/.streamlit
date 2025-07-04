import streamlit as st
import pandas as pd
import io

# Make app full-width
st.set_page_config(layout="wide")

st.title("NHH Pricing Tool")

# Upload file each time
uploaded_file = st.file_uploader("Upload the Flat File (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    st.write("Flat file loaded successfully. Preview:")
    st.dataframe(df.head())

    # Standard or Green selection
    green_option = st.selectbox(
        "Select Tariff Type:",
        options=["Standard", "Green"]
    )

    # Contract duration selection
    contract_duration = st.selectbox(
        "Select Contract Duration (Months):",
        options=[12, 24, 36]
    )

    st.subheader("Uplifts per Consumption Band")

    # Define bandings
    bands = [
        (1000, 3000),
        (3001, 12500),
        (12501, 26000),
        (26001, 100000),
        (100001, 175000),
        (175001, 225000),
        (225001, 300000)
    ]

    # Prepare storage for uplifts
    uplift_inputs = []

    # Dynamic grid inputs
    for idx, (min_val, max_val) in enumerate(bands):
        st.markdown(f"**Band {idx+1}: {min_val:,} – {max_val:,} kWh**")
        cols = st.columns(4)
        uplift_standing = cols[0].number_input(
            f"Standing Charge Uplift (p/day) - Band {idx+1}", value=0.0, step=0.1, key=f"sc_{idx}"
        )
        uplift_day = cols[1].number_input(
            f"Day Rate Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"day_{idx}"
        )
        uplift_night = cols[2].number_input(
            f"Night Rate Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"night_{idx}"
        )
        uplift_evw = cols[3].number_input(
            f"Evening & Weekend Uplift (p/kWh) - Band {idx+1}", value=0.0, step=0.1, key=f"evw_{idx}"
        )
        uplift_inputs.append({
            "min": min_val,
            "max": max_val,
            "uplift_standing": uplift_standing,
            "uplift_day": uplift_day,
            "uplift_night": uplift_night,
            "uplift_evw": uplift_evw
        })

    # Custom report title
    report_title = st.text_input("Enter Report Filename (without .xlsx):", value="nhh_price_book")

    if st.button("Generate Excel Price Book"):
        output_rows = []

        for band in uplift_inputs:
            # Filter matching rows
            filtered = df[
                (df["Minimum_Annual_Consumption"] <= band["max"]) &
                (df["Maximum_Annual_Consumption"] >= band["min"]) &
                (df["Contract_Duration"] == contract_duration) &
                (
                    (df["Green_Energy"].str.upper() == "YES") if green_option == "Green" else
                    (df["Green_Energy"].str.upper() == "NO")
                )
            ]

            if filtered.empty:
                output_rows.append({
                    "Band": f"{band['min']:,} – {band['max']:,}",
                    "Standing Charge (p/day)": "N/A",
                    "Day Rate (p/kWh)": "N/A",
                    "Night Rate (p/kWh)": "N/A",
                    "Evening & Weekend Rate (p/kWh)": "N/A"
                })
            else:
                row = filtered.iloc[0]
                output_rows.append({
                    "Band": f"{band['min']:,} – {band['max']:,}",
                    "Standing Charge (p/day)": row["Standing_Charge"] + band["uplift_standing"],
                    "Day Rate (p/kWh)": row["Day_Rate"] + band["uplift_day"],
                    "Night Rate (p/kWh)": row["Night_Rate"] + band["uplift_night"],
                    "Evening & Weekend Rate (p/kWh)": row["Evening_And_Weekend_Rate"] + band["uplift_evw"]
                })

        # Prepare DataFrame
        result_df = pd.DataFrame(output_rows)

        st.success("Excel file prepared. Preview:")
        st.dataframe(result_df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False, sheet_name="Price Book")

        processed_data = output.getvalue()

        st.download_button(
            label="Download Excel Price Book",
            data=processed_data,
            file_name=f"{report_title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.warning("Please upload the flat file to start.")
