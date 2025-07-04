import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Dyce Energy Gas Pricing Tool - v1")

st.markdown("""
This tool allows you to upload the weekly gas tariff pricing file, enter up to 10 sites, and apply your margin to calculate pricing.
""")

# Upload tariff pricing file
tariff_file = st.file_uploader("Upload Supplier Tariff File (Excel)", type=["xlsx"])

tariff_df = None
if tariff_file:
    tariff_df = pd.read_excel(tariff_file, sheet_name=0)
    st.success("Tariff file loaded successfully.")
    st.dataframe(tariff_df.head())

# Customer details
st.header("Customer Details")
customer_name = st.text_input("Customer Name")
contract_start_month = st.selectbox("Contract Start Month", options=["July 2025", "August 2025", "September 2025"])
margin = st.number_input("Margin to add (p/kWh)", min_value=0.0, value=0.5, step=0.1)

st.header("Site Details (up to 10 sites)")

# Create table for 10 sites
site_data = []
for i in range(10):
    st.markdown(f"**Site {i+1}**")
    cols = st.columns(6)
    mprn = cols[0].text_input(f"MPRN", key=f"mprn_{i}")
    site_name = cols[1].text_input(f"Site Name", key=f"name_{i}")
    aq = cols[2].number_input(f"AQ (kWh)", min_value=0.0, value=0.0, key=f"aq_{i}")
    postcode = cols[3].text_input(f"Postcode", key=f"pc_{i}")
    carbon = cols[4].selectbox(f"Carbon Offset", ["Standard", "Green"], key=f"carbon_{i}")
    cost_per_metre = cols[5].number_input(f"Cost per Metre (p/metre)", min_value=0.0, value=0.0, key=f"cpm_{i}")

    site_data.append({
        "mprn": mprn,
        "site_name": site_name,
        "aq": aq,
        "postcode": postcode,
        "carbon": carbon,
        "cost_per_metre": cost_per_metre
    })

# Process button
if st.button("Calculate Pricing"):
    if tariff_df is not None:
        results = []
        for site in site_data:
            if site["mprn"] != "":
                band = tariff_df[
                    (tariff_df['Minimum_Annual_Consumption'] <= site['aq']) &
                    (tariff_df['Maximum_Annual_Consumption'] >= site['aq']) &
                    (tariff_df['Carbon_Offset'] == (site['carbon'] == "Green"))
                ]
                if not band.empty:
                    match = band.iloc[0]
                    standing_charge = match['Standing_Charge']
                    unit_rate = match['Unit_Rate'] + margin
                    annual_cost = (site['aq'] * unit_rate / 100) + (365 * standing_charge / 100)

                    results.append({
                        "MPRN": site['mprn'],
                        "Site Name": site['site_name'],
                        "Unit Rate (p/kWh)": round(unit_rate, 4),
                        "Standing Charge (p/day)": round(standing_charge, 4),
                        "Annual Cost (£)": round(annual_cost, 2),
                        "Cost per Metre (p/metre)": site['cost_per_metre']
                    })
                else:
                    results.append({
                        "MPRN": site['mprn'],
                        "Site Name": site['site_name'],
                        "Unit Rate (p/kWh)": "No Match",
                        "Standing Charge (p/day)": "No Match",
                        "Annual Cost (£)": "No Match",
                        "Cost per Metre (p/metre)": site['cost_per_metre']
                    })

        results_df = pd.DataFrame(results)
        st.success("Pricing calculation complete.")
        st.dataframe(results_df)

        grand_total = results_df[results_df['Annual Cost (£)'] != "No Match"]["Annual Cost (£)"].sum()
        st.write(f"**Grand Total for all sites: £{round(grand_total,2)}**")
    else:
        st.error("Please upload the tariff file first.")
