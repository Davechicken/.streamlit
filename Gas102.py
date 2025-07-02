import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gas Pricing Uplift Tool", layout="wide")

st.title("📈 Gas Pricing Uplift Tool")

# 1. Upload the Excel file
uploaded_file = st.file_uploader("Upload your pricing Excel file (.xlsx):", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Exclude unwanted credit score columns
    df = df.drop(columns=["Minimum_Credit_Score", "Maximum_Credit_Score"], errors="ignore")

    # Show preview
    st.subheader("📋 File Preview")
    st.dataframe(df.head())

    # Define new consumption bands
    bands = [
        ("1,000 - 24,999", 1000, 24999),
        ("25,000 - 49,999", 25000, 49999),
        ("50,000 - 73,199", 50000, 73199),
        ("73,200 - 124,999", 73200, 124999),
        ("125,000 - 292,999", 125000, 292999),
        ("293,000 - 449,999", 293000, 449999),
        ("450,000 - 731,999", 450000, 731999)
    ]

    st.subheader("⚙️ Enter Uplifts (in pence)")
    uplifts = {}
    cols = st.columns(len(bands))
    for idx, (label, min_c, max_c) in enumerate(bands):
        with cols[idx]:
            uplifts[label] = st.number_input(
                f"{label}", min_value=0.0, step=0.01, format="%.2f", key=label
            )

    if st.button("✅ Apply Uplifts and Generate Output"):
        # Function to determine uplift per row
        def get_uplift(consumption):
            for label, min_c, max_c in bands:
                if min_c <= consumption <= max_c:
                    return uplifts[label]
            return 0.0  # Default if no band matched

        df["Uplift_pence_per_kWh"] = df["Minimum_Annual_Consumption"].apply(get_uplift)
        df["Unit_Rate_Uplifted"] = df["Unit_Rate"] + (df["Uplift_pence_per_kWh"] / 100)

        # Convert Standing Charge to pence per day
        df["Standing_Charge_pence_per_day"] = df["Standing_Charge"] * 100

        # Map Carbon Offset labels
        df["Carbon_Offset"] = df["Carbon_Offset"].map({
            "Y": "Carbon Neutral",
            "N": "Standard"
        })

        # Build final output dataframe
        output_df = df[
            [
                "Broker_ID",
                "Production_Date",
                "Utility",
                "LDZ",
                "Exit_Zone",
                "Sale_Type",
                "Contract_Duration",
                "Minimum_Annual_Consumption",
                "Maximum_Annual_Consumption",
                "Minimum_Contract_Start_Date",
                "Maximum_Contract_Start_Date",
                "Minimum_Valid_Quote_Date",
                "Maximum_Valid_Quote_Date",
                "Product_Name",
                "Carbon_Offset",
                "Standing_Charge_pence_per_day",
                "Unit_Rate_Uplifted"
            ]
        ].copy()

        # Rename columns for clarity
        output_df.rename(columns={
            "Standing_Charge_pence_per_day": "Standing Charge (pence/day)",
            "Unit_Rate_Uplifted": "Unit Rate (p/kWh)"
        }, inplace=True)

        st.subheader("📋 Price List Preview")
        st.dataframe(output_df)

        # Download link
        @st.cache_data
        def convert_df_to_excel(df):
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Price List")
            return output.getvalue()

        excel_data = convert_df_to_excel(output_df)
        st.download_button(
            label="⬇️ Download Price List as Excel",
            data=excel_data,
            file_name="uplifted_price_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
