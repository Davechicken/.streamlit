import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(layout="wide")
st.title("Dyce Energy Gas Pricing Tool")

st.markdown("""
Upload the weekly gas tariff pricing file, then enter up to 10 sites to calculate pricing with site-specific uplifts.
This version uses a static **Clean_PostCode.csv** for postcode-to-LDZ lookup.
""")

# Load postcode lookup from static CSV
postcode_df = pd.read_csv("Clean_PostCode.csv")

# Upload tariff pricing file
tariff_file = st.file_uploader("Upload Supplier Tariff File (Excel)", type=["xlsx"])

if tariff_file:
    tariff_df = pd.read_excel(tariff_file, sheet_name=0)
    st.success("Tariff file loaded successfully.")
    st.dataframe(tariff_df.head())
else:
    tariff_df = None

# Customer details
st.header("Customer Details")
customer_name = st.text_input("Customer Name")
contract_start_date = st.date_input("Contract Start Date", value=date.today())
carbon_offset = st.selectbox("Carbon Offset", ["Standard", "Green"])

st.header("Site Details (up to 10 sites)")

site_data = []
for i in range(10):
    st.markdown(f"**Site {i+1}**")
    cols = st.columns(7)
    mprn = cols[0].text_input("MPRN", key=f"mprn_{i}")
    site_name = cols[1].text_input("Site Name", key=f"name_{i}")
    aq = cols[2].number_input("AQ (kWh)", min_value=0.0, value=0.0, key=f"aq_{i}")
    postcode = cols[3].text_input("Postcode", key=f"pc_{i}")
    stand_uplift = cols[4].number_input("Standing Uplift (p/day)", min_value=0.0, value=0.0, step=0.1, key=f"su_{i}")
    unit_uplift = cols[5].number_input("Unit Uplift (p/kWh)", min_value=0.0, value=0.0, step=0.1, key=f"uu_{i}")
    cost_per_metre = cols[6].number_input("Cost per Metre (p/metre)", min_value=0.0, value=0.0, key=f"cpm_{i}")

    site_data.append({
        "mprn": mprn,
        "site_name": site_name,
        "aq": aq,
        "postcode": postcode,
        "stand_uplift": stand_uplift,
        "unit_uplift": unit_uplift,
        "cost_per_metre": cost_per_metre
    })

# Process button
if st.button("Calculate Pricing"):
    if tariff_df is not None:
        results = []
        for site in site_data:
            if site["mprn"] != "" and site["postcode"] != "":
                outcode = site["postcode"].split()[0].upper()
                ldz_lookup = postcode_df[postcode_df["Outcode"] == outcode]

                if not ldz_lookup.empty:
                    ldz = ldz_lookup.iloc[0]["LDZ"]

                    band = tariff_df[
                        (tariff_df["Minimum_Annual_Consumption"] <= site["aq"]) &
                        (tariff_df["Maximum_Annual_Consumption"] >= site["aq"]) &
                        (tariff_df["Carbon_Offset"] == (carbon_offset == "Green")) &
                        (tariff_df["LDZ"] == ldz)
                    ]

                    if not band.empty:
                        match = band.iloc[0]
                        supplier_standing = match["Standing_Charge"]
                        supplier_unit = match["Unit_Rate"]

                        final_unit = supplier_unit + site["unit_uplift"]
                        final_standing = supplier_standing + site["stand_uplift"]

                        annual_cost = (site["aq"] * final_unit / 100) + (365 * final_standing / 100)

                        results.append({
                            "MPRN": site["mprn"],
                            "Site Name": site["site_name"],
                            "AQ (kWh)": site["aq"],
                            "Postcode": site["postcode"],
                            "Supplier Standing (p/day)": round(supplier_standing, 4),
                            "Supplier Unit (p/kWh)": round(supplier_unit, 4),
                            "Final Standing (p/day)": round(final_standing, 4),
                            "Final Unit (p/kWh)": round(final_unit, 4),
                            "Annual Cost (£)": round(annual_cost, 2),
                            "Cost per Metre (p/metre)": site["cost_per_metre"]
                        })
                    else:
                        results.append({
                            "MPRN": site["mprn"],
                            "Site Name": site["site_name"],
                            "AQ (kWh)": site["aq"],
                            "Postcode": site["postcode"],
                            "Supplier Standing (p/day)": "No Match",
                            "Supplier Unit (p/kWh)": "No Match",
                            "Final Standing (p/day)": "No Match",
                            "Final Unit (p/kWh)": "No Match",
                            "Annual Cost (£)": "No Match",
                            "Cost per Metre (p/metre)": site["cost_per_metre"]
                        })
                else:
                    results.append({
                        "MPRN": site["mprn"],
                        "Site Name": site["site_name"],
                        "AQ (kWh)": site["aq"],
                        "Postcode": site["postcode"],
                        "Supplier Standing (p/day)": "No LDZ Found",
                        "Supplier Unit (p/kWh)": "No LDZ Found",
                        "Final Standing (p/day)": "No LDZ Found",
                        "Final Unit (p/kWh)": "No LDZ Found",
                        "Annual Cost (£)": "No LDZ Found",
                        "Cost per Metre (p/metre)": site["cost_per_metre"]
                    })
        results_df = pd.DataFrame(results)
        st.success("Pricing calculation complete.")
        st.dataframe(results_df)

        grand_total = results_df[results_df["Annual Cost (£)"] != "No Match"]["Annual Cost (£)"].sum()
        st.write(f"**Grand Total for all sites: £{round(grand_total,2)}**")
    else:
        st.error("Please upload the tariff file first.")
