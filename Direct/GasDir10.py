import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(layout="wide")
st.title("Dyce Energy Gas Pricing Tool - Reactive Mode")

st.markdown("""
As you enter AQ and postcode, the supplier prices will automatically display.
Then you can enter uplifts, and the final prices and annual cost will recalculate instantly.
""")

# Load postcode lookup
postcode_df = pd.read_csv("Clean_PostCode.csv")

# Upload tariff pricing file
tariff_file = st.file_uploader("Upload Supplier Tariff File (Excel)", type=["xlsx"])

tariff_df = None
if tariff_file:
    tariff_df = pd.read_excel(tariff_file, sheet_name=0)
    st.success("Tariff file loaded successfully.")

# Customer details
st.header("Customer Details")
customer_name = st.text_input("Customer Name")
contract_start_date = st.date_input("Contract Start Date", value=date.today())
carbon_offset = st.selectbox("Carbon Offset", ["Standard", "Green"])
carbon_flag = True if carbon_offset == "Green" else False

# Site data reactive state
if "site_data" not in st.session_state:
    st.session_state.site_data = [{} for _ in range(10)]

st.header("Site Details (Reactive, up to 10 sites)")

for i in range(10):
    st.markdown(f"**Site {i+1}**")
    cols = st.columns(10)

    # data store
    data = st.session_state.site_data[i]

    # capture entries
    data["mprn"] = cols[0].text_input("MPRN", key=f"mprn_{i}")
    data["site_name"] = cols[1].text_input("Site Name", key=f"name_{i}")
    data["aq"] = cols[2].number_input("AQ (kWh)", min_value=0.0, value=data.get("aq", 0.0), key=f"aq_{i}")
    data["postcode"] = cols[3].text_input("Postcode", key=f"pc_{i}")

    # do postcode/LDZ matching if they type postcode and AQ
    supplier_unit = ""
    supplier_standing = ""
    final_unit = ""
    final_standing = ""
    annual_cost = ""

    if data["postcode"] != "" and data["aq"] > 0 and tariff_df is not None:
        cleaned = data["postcode"].replace(" ", "").upper()
        outcode = cleaned[:-3]

        ldz_lookup = postcode_df[postcode_df["Outcode"] == outcode]

        if not ldz_lookup.empty:
            ldz = ldz_lookup.iloc[0]["LDZ"]
            band = tariff_df[
                (tariff_df["Minimum_Annual_Consumption"] <= data["aq"]) &
                (tariff_df["Maximum_Annual_Consumption"] >= data["aq"]) &
                (tariff_df["Carbon_Offset"] == carbon_flag) &
                (tariff_df["LDZ"] == ldz)
            ]
            if not band.empty:
                match = band.iloc[0]
                supplier_standing = match["Standing_Charge"]
                supplier_unit = match["Unit_Rate"]
                
                data["supplier_standing"] = supplier_standing
                data["supplier_unit"] = supplier_unit
            else:
                data["supplier_standing"] = "No Match"
                data["supplier_unit"] = "No Match"
        else:
            data["supplier_standing"] = "No LDZ"
            data["supplier_unit"] = "No LDZ"

    # show supplier rates (readonly)
    data["supplier_standing"] = cols[4].text_input("Supplier Standing (p/day)", value=str(data.get("supplier_standing", "")), disabled=True)
    data["supplier_unit"] = cols[5].text_input("Supplier Unit (p/kWh)", value=str(data.get("supplier_unit", "")), disabled=True)

    # uplifts
    data["stand_uplift"] = cols[6].number_input("Standing Uplift (p/day)", min_value=0.0, value=data.get("stand_uplift", 0.0), step=0.1, key=f"su_{i}")
    data["unit_uplift"] = cols[7].number_input("Unit Uplift (p/kWh)", min_value=0.0, value=data.get("unit_uplift", 0.0), step=0.1, key=f"uu_{i}")
    data["cost_per_metre"] = cols[8].number_input("Cost/metre (p/metre)", min_value=0.0, value=data.get("cost_per_metre", 0.0), key=f"cpm_{i}")

    # calculate final if supplier data exists
    if isinstance(data.get("supplier_standing"), (float, int)) and isinstance(data.get("supplier_unit"), (float, int)):
        final_standing = data["supplier_standing"] + data["stand_uplift"]
        final_unit = data["supplier_unit"] + data["unit_uplift"]
        annual_cost = (data["aq"] * final_unit / 100) + (365 * final_standing / 100)
    
    data["final_standing"] = cols[9].text_input("Final Standing (p/day)", value=str(round(final_standing, 4)) if final_standing else "", disabled=True)
    data["final_unit"] = cols[9].text_input("Final Unit (p/kWh)", value=str(round(final_unit, 4)) if final_unit else "", disabled=True)

    # final cost summary
    if annual_cost != "":
        st.write(f"Estimated Annual Cost for Site {i+1}: £{round(annual_cost,2)}")

st.success("Reactive pricing is live. As soon as you enter AQ + postcode, supplier costs will appear, ready for uplift.")
