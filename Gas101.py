import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Gas Pricing Uplift Tool", layout="wide")
st.title("🔹 Gas Pricing Uplift Tool")

uploaded_file = st.file_uploader("Upload your pricing XLSX file:", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]

    st.success("✅ File loaded successfully")

    # Show preview
    st.subheader("Flat File Preview")
    st.dataframe(df.head())

    st.markdown("---")
    st.subheader("Step 1 – Enter Uplifts (p / kWh and p / day)")

    default_bands = [
        {"Min": 0, "Max": 999},
        {"Min": 1000, "Max": 24999},
        {"Min": 25000, "Max": 49999},
        {"Min": 50000, "Max": 73199},
        {"Min": 73200, "Max": 124999},
        {"Min": 125000, "Max": 292999},
        {"Min": 293000, "Max": 731999},
    ]

    band_inputs = []
    with st.expander("Click to edit bands", expanded=True):
        for i, band in enumerate(default_bands):
            st.markdown(f"**Band {i+1}: {band['Min']} - {band['Max']} kWh**")
            cols = st.columns(6)
            entry = {
                "Min": band["Min"],
                "Max": band["Max"],
                "1yr_unit_noncarbon": cols[0].number_input(f"1yr Unit (NC)", value=1.0, key=f"1u_nc_{i}"),
                "1yr_standing_noncarbon": cols[1].number_input(f"1yr Stand (NC)", value=1.0, key=f"1s_nc_{i}"),
                "2yr_unit_noncarbon": cols[2].number_input(f"2yr Unit (NC)", value=1.0, key=f"2u_nc_{i}"),
                "2yr_standing_noncarbon": cols[3].number_input(f"2yr Stand (NC)", value=1.0, key=f"2s_nc_{i}"),
                "3yr_unit_noncarbon": cols[4].number_input(f"3yr Unit (NC)", value=1.0, key=f"3u_nc_{i}"),
                "3yr_standing_noncarbon": cols[5].number_input(f"3yr Stand (NC)", value=1.0, key=f"3s_nc_{i}")
            }
            entry["1yr_unit_carbon"] = cols[0].number_input(f"1yr Unit (C)", value=1.5, key=f"1u_c_{i}")
            entry["1yr_standing_carbon"] = cols[1].number_input(f"1yr Stand (C)", value=1.5, key=f"1s_c_{i}")
            entry["2yr_unit_carbon"] = cols[2].number_input(f"2yr Unit (C)", value=1.5, key=f"2u_c_{i}")
            entry["2yr_standing_carbon"] = cols[3].number_input(f"2yr Stand (C)", value=1.5, key=f"2s_c_{i}")
            entry["3yr_unit_carbon"] = cols[4].number_input(f"3yr Unit (C)", value=1.5, key=f"3u_c_{i}")
            entry["3yr_standing_carbon"] = cols[5].number_input(f"3yr Stand (C)", value=1.5, key=f"3s_c_{i}")

            band_inputs.append(entry)

    annual_consumption = st.number_input("Annual Consumption (kWh)", min_value=1, value=20000)

    def get_band_uplift(row):
        consumption = row.get("minimum_annual_consumption", 0)
        band = next((b for b in band_inputs if b["Min"] <= consumption <= b["Max"]), band_inputs[-1])

        try:
            contract_length = int(row.get("contract_duration", 1))
        except:
            contract_length = 1
        if contract_length not in [1, 2, 3]:
            contract_length = 1

        carbon_raw = str(row.get("carbon_offset", "")).strip().lower()
        carbon = carbon_raw in ["yes", "y", "true", "1"]

        if carbon:
            unit = band[f"{contract_length}yr_unit_carbon"]
            standing = band[f"{contract_length}yr_standing_carbon"]
        else:
            unit = band[f"{contract_length}yr_unit_noncarbon"]
            standing = band[f"{contract_length}yr_standing_noncarbon"]

        return pd.Series({
            "uplift_unit": unit,
            "uplift_standing": standing
        })

    uplift_df = df.apply(get_band_uplift, axis=1)
    df_final = pd.concat([df, uplift_df], axis=1)

    # Calculate uplifted rates (note: standing charge stays in pence)
    df_final["Unit_Rate_Uplifted"] = (df_final["unit_rate"] + df_final["uplift_unit"]).round(3)
    df_final["Standing_Charge_Uplifted"] = (df_final["standing_charge"] + df_final["uplift_standing"])

    df_final["Total_Annual_Cost"] = (
        (df_final["Standing_Charge_Uplifted"] * 365) +
        (df_final["Unit_Rate_Uplifted"] * annual_consumption)
    ) / 100

    output_df = df_final.drop(columns=[
        "unit_rate", "standing_charge", "uplift_unit", "uplift_standing"
    ], errors="ignore")

    output_df = output_df.rename(columns={
        "Unit_Rate_Uplifted": "Unit Rate (p/kWh)",
        "Standing_Charge_Uplifted": "Standing Charge (p/day)",
        "Total_Annual_Cost": "Total Annual Cost (£)"
    })

    if len(output_df.columns) > 18:
        output_df = output_df.iloc[:, :18].copy()

    st.subheader("✅ Price List Preview")
    st.dataframe(output_df.head())

    # Prepare Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        output_df.to_excel(writer, index=False, sheet_name="PriceList")

    st.download_button(
        "⬇️ Download Broker Price List",
        data=output.getvalue(),
        file_name="broker_pricelist.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
