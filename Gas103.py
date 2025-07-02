import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Gas Pricing Uplift Tool", layout="wide")
st.title("🔹 Gas Pricing Uplift Tool")

# Upload XLSX
uploaded_file = st.file_uploader("Upload your pricing XLSX file:", type="xlsx")

if uploaded_file:
    # Read Excel
    df = pd.read_excel(uploaded_file)

    # Drop unwanted credit score columns if they exist
    df = df.drop(columns=[col for col in ["Minimum_Credit_Score", "Maximum_Credit_Score"] if col in df.columns])

    # Show preview
    st.subheader("File Preview")
    st.dataframe(df.head())

    st.markdown("---")
    st.subheader("Step 1 – Enter Uplifts (p/kWh and p/day)")

    # Consumption Bands
    bands = [
        {"Min": 1000, "Max": 24999},
        {"Min": 25000, "Max": 49999},
        {"Min": 50000, "Max": 73199},
        {"Min": 73200, "Max": 124999},
        {"Min": 125000, "Max": 292999},
        {"Min": 293000, "Max": 449999},
        {"Min": 450000, "Max": 731999},
    ]

    band_inputs = []
    with st.expander("Click to enter uplifts for each band", expanded=True):
        for i, band in enumerate(bands):
            st.markdown(f"**Band {i+1}: {band['Min']} - {band['Max']} kWh**")
            cols = st.columns(4)
            entry = {
                "Min": band["Min"],
                "Max": band["Max"],
                # Standard
                "Standard_Standing": cols[0].number_input(
                    "Standard Standing Charge (p/day)", min_value=0, value=0, step=1, key=f"std_standing_{i}"
                ),
                "Standard_Unit": cols[1].number_input(
                    "Standard Unit Rate (p/kWh)", min_value=0.000, value=0.000, step=0.001, format="%.3f", key=f"std_unit_{i}"
                ),
                # Carbon Neutral
                "Carbon_Standing": cols[2].number_input(
                    "Carbon Neutral Standing Charge (p/day)", min_value=0, value=0, step=1, key=f"carbon_standing_{i}"
                ),
                "Carbon_Unit": cols[3].number_input(
                    "Carbon Neutral Unit Rate (p/kWh)", min_value=0.000, value=0.000, step=0.001, format="%.3f", key=f"carbon_unit_{i}"
                )
            }
            band_inputs.append(entry)

    # Compute uplift logic
    def get_band_uplift(row):
        # Find matching band
        consumption = row.get("Minimum_Annual_Consumption", 0)
        band = next((b for b in band_inputs if b["Min"] <= consumption <= b["Max"]), band_inputs[-1])

        # Determine if Carbon Neutral
        carbon_raw = str(row.get("Carbon_Offset", "")).strip().lower()
        carbon = carbon_raw in ["y", "yes", "true", "1"]

        if carbon:
            unit_uplift = band["Carbon_Unit"]
            standing_uplift = band["Carbon_Standing"]
        else:
            unit_uplift = band["Standard_Unit"]
            standing_uplift = band["Standard_Standing"]

        return pd.Series({
            "Uplift_Unit": unit_uplift,
            "Uplift_Standing": standing_uplift
        })

    uplift_df = df.apply(get_band_uplift, axis=1)
    df_final = pd.concat([df, uplift_df], axis=1)

    # Compute uplifted rates
    df_final["Unit Rate"] = df_final["Unit_Rate"] + df_final["Uplift_Unit"]
    # Standing Charge in pence/day
    df_final["Standing Charge"] = (df_final["Standing_Charge"] * 100) + df_final["Uplift_Standing"]

    # Compute total annual cost
    df_final["Total Annual Cost (£)"] = (
        (df_final["Standing Charge"] * 365) +
        (df_final["Unit Rate"] * df_final["Minimum_Annual_Consumption"])
    ) / 100

    # Clean up columns for output
    columns_to_keep = [
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
        "Standing Charge",
        "Unit Rate",
        "Total Annual Cost (£)"
    ]

    st.markdown("---")
    st.subheader("✅ Price List Preview")
    st.dataframe(df_final[columns_to_keep].head())

    # Excel output
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_final[columns_to_keep].to_excel(writer, index=False, sheet_name="PriceList")

    st.download_button(
        "⬇️ Download Broker Price List",
        data=output.getvalue(),
        file_name="broker_pricelist.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
