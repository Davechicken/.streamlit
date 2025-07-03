import streamlit as st
import pandas as pd

st.set_page_config(page_title="Half Hourly Electricity Pricing Uplift Tool", layout="wide")
st.title("⚡ Half Hourly Electricity Pricing Uplift Tool")

# Upload Excel file
uploaded_file = st.file_uploader("Upload your Half Hourly Excel pricing file (.xlsx)", type=["xlsx"])

if uploaded_file:
    # Load Excel
df = pd.read_excel(uploaded_file)

# Inspect unique values
st.write("Unique Profile_Class values:", df["Profile_Class"].unique())

# Normalize Profile_Class column
df["Profile_Class"] = df["Profile_Class"].astype(str).str.strip().str.zfill(2)

# Confirm normalization
st.write("Normalized Profile_Class values:", df["Profile_Class"].unique())

# Filter for Half Hourly
hh_df = df[df["Profile_Class"] == "00"].copy()# Load Excel
    df = pd.read_excel(uploaded_file)

    # Filter for Half Hourly Profile Class
    hh_df = df[df["Profile_Class"] == "00"].copy()

    if hh_df.empty:
        st.error("No Half Hourly records found (Profile_Class == '00'). Please check your file.")
        st.stop()

    # Parse and validate date columns
    hh_df["Minimum_Contract_Start_Date"] = pd.to_datetime(
        hh_df["Minimum_Contract_Start_Date"], errors="coerce"
    )
    hh_df["Maximum_Contract_Start_Date"] = pd.to_datetime(
        hh_df["Maximum_Contract_Start_Date"], errors="coerce"
    )

    if hh_df["Minimum_Contract_Start_Date"].isnull().any() or hh_df["Maximum_Contract_Start_Date"].isnull().any():
        st.error("One or more contract start dates could not be parsed. Please fix the data.")
        st.stop()

    # Determine the earliest and latest dates for filtering
    min_start_date = hh_df["Minimum_Contract_Start_Date"].min().date()
    max_start_date = hh_df["Maximum_Contract_Start_Date"].max().date()

    # Sidebar filters
    st.sidebar.header("🔍 Filters")

    # Contract duration selection
    contract_durations = st.sidebar.multiselect(
        "Contract Durations (months):",
        options=sorted(hh_df["Contract_Duration"].unique()),
        default=[12, 24, 36],
    )

    # Contract start date range
    contract_start_range = st.sidebar.date_input(
        "Contract Start Date Range:",
        value=(min_start_date, max_start_date),
    )

    # Green energy selection
    green_option = st.sidebar.selectbox(
        "Green Energy Preference:",
        options=["All", "Standard", "Green"]
    )

    # Consumption band selection
    consumption_bands = {
        "0 - 99,999": (0, 99999),
        "100,000 - 299,999": (100000, 299999),
        "300,000 - 499,999": (300000, 499999),
        "500,000 - 799,999": (500000, 799999),
        "800,000 - 1,000,000": (800000, 1000000),
    }
    band_label = st.sidebar.selectbox(
        "Consumption Band:",
        options=list(consumption_bands.keys())
    )
    min_cons, max_cons = consumption_bands[band_label]

    # Uplift grid
    st.subheader("🔧 Uplift Values (Fixed pence, up to 3 decimals)")

    col1, col2, col3, col4 = st.columns(4)
    uplift_standing = col1.number_input("Standing Charge Uplift (pence)", value=0.000, format="%.3f")
    uplift_day = col2.number_input("Day Rate Uplift (pence)", value=0.000, format="%.3f")
    uplift_night = col3.number_input("Night Rate Uplift (pence)", value=0.000, format="%.3f")
    uplift_duos = col4.number_input("KVA (DUoS) Uplift (pence)", value=0.000, format="%.3f")

    # Apply filters
    filtered = hh_df[
        (hh_df["Contract_Duration"].isin(contract_durations))
        & (hh_df["Minimum_Annual_Consumption"] >= min_cons)
        & (hh_df["Maximum_Annual_Consumption"] <= max_cons)
        & (hh_df["Minimum_Contract_Start_Date"].dt.date >= contract_start_range[0])
        & (hh_df["Maximum_Contract_Start_Date"].dt.date <= contract_start_range[1])
    ]

    if green_option != "All":
        green_flag = green_option == "Green"
        filtered = filtered[filtered["Green_Energy"] == green_flag]

    if filtered.empty:
        st.warning("No records matched your filters.")
    else:
        # Apply uplifts
        for col, uplift in [
            ("Standing_Charge", uplift_standing),
            ("Day_Rate", uplift_day),
            ("Night_Rate", uplift_night),
            ("Capacity_Rate", uplift_duos),
        ]:
            if col in filtered.columns:
                filtered[col] = filtered[col] + uplift

        # Display results
        st.success(f"✅ {len(filtered)} records after filtering and uplift.")
        st.dataframe(
            filtered[
                [
                    "Contract_Duration",
                    "Minimum_Annual_Consumption",
                    "Maximum_Annual_Consumption",
                    "Minimum_Contract_Start_Date",
                    "Maximum_Contract_Start_Date",
                    "Green_Energy",
                    "Standing_Charge",
                    "Day_Rate",
                    "Night_Rate",
                    "Capacity_Rate",
                ]
            ]
        )

        # Download option
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Uplifted Data as CSV",
            data=csv,
            file_name="uplifted_half_hourly.csv",
            mime="text/csv"
        )
else:
    st.info("👈 Please upload an Excel file to begin.")
