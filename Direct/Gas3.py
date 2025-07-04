import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Dyce Energy Gas Pricing Tool - v2")

st.markdown("""
Upload the weekly gas tariff pricing file and postcode reference, then enter up to 10 sites to calculate pricing with margin. This version includes postcode-to-LDZ mapping.
""")

# Upload tariff pricing file
tariff_file = st.file_uploader("Upload Supplier Tariff File (Excel)", type=["xlsx"])
# Upload postcode reference
postcode_file = st.file_uploader("Upload Postcode Lookup File (Excel)", type=["xlsx"])

tariff_df = None
postcode_df = None
if tariff_file:
    tariff_df = pd.read_excel(tariff_file, sheet_name=0)
    st.success("Tariff file loaded successfully.")
    st.dataframe(tariff_df.head())

if postcode_file:
    postcode_df = pd.read_excel(postcode_file, sheet_name=0)
    st.success("Postcode lookup loaded successfully.")
    st.dataframe(postcode_df.head())

# Customer details
st.header("Customer Details")
customer_name = st.text_input("Customer Name")
contract_start_month = st.selectbox("Contract Start Month", options=["July 2025", "August 2025", "September 2025"])
margin = st.number_input("Margin to add (p/kWh)", min_value=0.0, value=0.5, step=0.1)
standing_uplift = st.number_input("Uplift to add to Standing Charge (p/day)", min_value=0.0, value=0.0, step=0.1)

st.header("Site Details (up to 10 sites)")

site_data = []
for i in range(10):
    st.markdown(f"**Site {i+1}**")
    cols = st.columns(6)
    mprn = cols[0].text_input("MPRN", key=f"mprn_{i}")
    site_name = cols[1].text_input("Site Name", key=f"name_{i}")
    aq = cols[2].number_input("AQ (kWh)", min_value=0.0, value=0.0, key=f"aq_{i}")
    postcode = cols[3].text_input("Postcode", key=f"pc_{i}")
    carbon = cols[4].selectbox("Carbon Offset", ["Standard", "Green"], key=f"carbon_{i}")
    cost_per_metre = cols[5].number_input("Cost per Metre (p/metre)", min_value=0.0, value=0.0, key=f"cpm_{i}")
    
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
    if tariff_df is not None and postcode_df is not None:
        results = []
        for site in site_data:
            if site["mprn"] != "" and site["postcode"] != "":
                # extract outcode from postcode
                outcode = site['postcode'].split()[0].upper()
                
                ldz_lookup = postcode_df[postcode_df['Outcode'] == outcode]
                if not ldz_lookup.empty:
                    ldz = ldz_lookup.iloc[0]['LDZ']

                    # match tariff
                    band = tariff_df[
                        (tariff_df['Minimum_Annual_Consumption'] <= site['aq']) &
                        (tariff_df['Maximum_Annual_Consumption'] >= site['aq']) &
                        (tariff_df['Carbon_Offset'] == (site['carbon'] == "Green")) &
                        (tariff_df['LDZ'] == ldz)
                    ]
                    
                    if not band.empty:
                        match = band.iloc[0]
                        supplier_standing = match['Standing_Charge']
                        supplier_unit = match['Unit_Rate']
                        
                        # apply uplifts
                        final_unit = supplier_unit + margin
                        final_standing = supplier_standing + standing_uplift

                        annual_cost = (site['aq'] * final_unit / 100) + (365 * final_standing / 100)

                        results.append({
                            "MPRN": site['mprn'],
                            "Site Name": site['site_name'],
                            "Supplier Standing (p/day)": round(supplier_standing,4),
                            "Supplier Unit (p/kWh)": round(supplier_unit,4),
                            "Final Standing (p/day)": round(final_standing,4),
                            "Final Unit (p/kWh)": round(final_unit,4),
                            "Annual Cost (£)": round(annual_cost, 2),
                            "Cost per Metre (p/metre)": site['cost_per_metre']
                        })
                    else:
                        results.append({
                            "MPRN": site['mprn'],
                            "Site Name": site['site_name'],
                            "Supplier Standing (p/day)": "No Match",
                            "Supplier Unit (p/kWh)": "No Match",
                            "Final Standing (p/day)": "No Match",
                            "Final Unit (p/kWh)": "No Match",
                            "Annual Cost (£)": "No Match",
                            "Cost per Metre (p/metre)": site['cost_per_metre']
                        })
                else:
                    results.append({
                        "MPRN": site['mprn'],
                        "Site Name": site['site_name'],
                        "Supplier Standing (p/day)": "No LDZ Found",
                        "Supplier Unit (p/kWh)": "No LDZ Found",
                        "Final Standing (p/day)": "No LDZ Found",
                        "Final Unit (p/kWh)": "No LDZ Found",
                        "Annual Cost (£)": "No LDZ Found",
                        "Cost per Metre (p/metre)": site['cost_per_metre']
                    })
        
        results_df = pd.DataFrame(results)
        st.success("Pricing calculation complete.")
        st.dataframe(results_df)

        grand_total = results_df[results_df['Annual Cost (£)'] != "No Match"]["Annual Cost (£)"].sum()
        st.write(f"**Grand Total for all sites: £{round(grand_total,2)}**")
    else:
        st.error("Please upload both the tariff and postcode files.")
