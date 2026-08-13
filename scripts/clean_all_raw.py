"""
Master Cleaning Script for FRP Raw Datasets
Cleans all raw dataset CSV files in data/raw and exports them to data/cleaned/
Generates a detailed cleaning report in reports/raw_cleaning_summary.csv
"""

import os
import glob
import pandas as pd
import numpy as np

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"
REPORTS_DIR = r"c:\Users\Lenovo\Desktop\FRP\reports"

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

csv_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
csv_files.sort()

print("=" * 90)
print("MASTER DATA CLEANING PROCESS STARTED")
print(f"Total CSV files found in raw folder: {len(csv_files)}")
print("=" * 90)

cleaning_report = []

# District median coordinates fallback
DISTRICT_COORDS = {
    'CHAMPAWAT': (28.9958, 80.1055),
    'SRIKAKULAM': (18.4100, 83.4000),
    'ELURU': (17.2458, 81.6597),
    'JALPAIGURI': (26.5167, 89.8000),
    'AGRA': (27.2038, 78.0350),
    'CHENNAI': (13.0827, 80.2707),
    'HYDERABAD': (17.3850, 78.4867),
    'DELHI': (28.6625, 77.2488),
    'PASHCHIMI SINGHBHUM': (22.7913, 86.1736)
}

for filepath in csv_files:
    fname = os.path.basename(filepath)
    
    # Skip duplicate copy file if present
    if "(1)" in fname:
        print(f"\nSkipping duplicate copy file: {fname}")
        continue

    file_size = os.path.getsize(filepath)
    print(f"\nProcessing: {fname} ({file_size / 1024:.2f} KB)")
    print("-" * 75)

    if file_size < 300:
        print(f"  WARNING: File too small / empty ({file_size} bytes). Skipping.")
        cleaning_report.append({
            'Raw_File': fname,
            'Clean_File': 'N/A',
            'Metric': 'N/A',
            'Rows_Before': 0,
            'Rows_After': 0,
            'Duplicates_Removed': 0,
            'Missing_Coords_Fixed': 0,
            'Missing_Metric_Fixed': 0,
            'Status': 'Skipped (Empty/Corrupted Raw File)'
        })
        continue

    try:
        df_raw = pd.read_csv(filepath, low_memory=False)
    except Exception as e:
        print(f"  ERROR reading {fname}: {e}")
        cleaning_report.append({
            'Raw_File': fname,
            'Clean_File': 'N/A',
            'Metric': 'N/A',
            'Rows_Before': 0,
            'Rows_After': 0,
            'Duplicates_Removed': 0,
            'Missing_Coords_Fixed': 0,
            'Missing_Metric_Fixed': 0,
            'Status': f'Failed Read ({e})'
        })
        continue

    rows_before = len(df_raw)
    if rows_before == 0:
        print("  File contains 0 rows. Skipping.")
        cleaning_report.append({
            'Raw_File': fname,
            'Clean_File': 'N/A',
            'Metric': 'N/A',
            'Rows_Before': 0,
            'Rows_After': 0,
            'Duplicates_Removed': 0,
            'Missing_Coords_Fixed': 0,
            'Missing_Metric_Fixed': 0,
            'Status': 'Skipped (0 Rows)'
        })
        continue

    df = df_raw.copy()
    df.columns = df.columns.str.strip()

    # 1. Standardize text columns
    state_col = 'State' if 'State' in df else [c for c in df.columns if 'state' in c.lower()][0]
    district_col = 'District' if 'District' in df else [c for c in df.columns if 'district' in c.lower()][0]
    station_col = 'Station' if 'Station' in df else [c for c in df.columns if 'station' in c.lower()][0]
    time_col = 'Data Acquisition Time' if 'Data Acquisition Time' in df else [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()][0]
    lat_col = 'Latitude' if 'Latitude' in df else [c for c in df.columns if 'lat' in c.lower()][0]
    lon_col = 'Longitude' if 'Longitude' in df else [c for c in df.columns if 'lon' in c.lower()][0]

    df[station_col] = df[station_col].astype(str).str.strip().str.rstrip('.')
    df[district_col] = df[district_col].astype(str).str.strip().str.upper()
    df[state_col] = df[state_col].astype(str).str.strip()

    # Optional metadata columns
    tehsil_col = 'Tehsil' if 'Tehsil' in df else None
    block_col = 'Block' if 'Block' in df else None
    river_col = 'River' if 'River' in df else None
    basin_col = 'Basin' if 'Basin' in df else None

    # 2. Datetime conversion
    df['Acquisition_Time'] = pd.to_datetime(df[time_col], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['Acquisition_Time'])

    # 3. Duplicate removal
    dups_before = df.duplicated(subset=[station_col, 'Acquisition_Time']).sum()
    df = df.drop_duplicates(subset=[station_col, 'Acquisition_Time'], keep='first')

    # 4. Lat / Lon cleaning & Imputation
    df['Latitude_Clean'] = pd.to_numeric(df[lat_col], errors='coerce')
    df['Longitude_Clean'] = pd.to_numeric(df[lon_col], errors='coerce')
    missing_coords_before = df['Latitude_Clean'].isnull().sum()

    if missing_coords_before > 0:
        for dist, coords in DISTRICT_COORDS.items():
            mask = df[district_col] == dist
            df.loc[mask & df['Latitude_Clean'].isnull(), 'Latitude_Clean'] = coords[0]
            df.loc[mask & df['Longitude_Clean'].isnull(), 'Longitude_Clean'] = coords[1]
        df['Latitude_Clean'] = df['Latitude_Clean'].fillna(df['Latitude_Clean'].median() if df['Latitude_Clean'].notnull().any() else 20.0)
        df['Longitude_Clean'] = df['Longitude_Clean'].fillna(df['Longitude_Clean'].median() if df['Longitude_Clean'].notnull().any() else 78.0)

    # 5. Detect and clean target metric
    target_orig_col = None
    target_clean_name = "Metric_Value"

    for c in df.columns:
        c_lower = c.lower()
        if 'rainfall' in c_lower:
            target_orig_col = c
            target_clean_name = "Hourly_Rainfall_mm"
            break
        elif 'water level' in c_lower or 'rwl' in c_lower:
            target_orig_col = c
            target_clean_name = "Water_Level_m"
            break
        elif 'discharge' in c_lower:
            target_orig_col = c
            target_clean_name = "River_Discharge_m3sec"
            break
        elif 'storage' in c_lower:
            target_orig_col = c
            target_clean_name = "Reservoir_Storage_mcm"
            break

    if not target_orig_col:
        # Fallback to last column
        target_orig_col = df.columns[-1]

    df[target_clean_name] = pd.to_numeric(df[target_orig_col], errors='coerce')
    nulls_before = df[target_clean_name].isnull().sum()

    # Outlier / NaN handling based on metric type
    if target_clean_name == "Hourly_Rainfall_mm":
        # Clip negative rainfall to 0.0 and extreme anomalies (>400 mm/hr) to 400.0
        df[target_clean_name] = df[target_clean_name].clip(lower=0.0, upper=400.0).fillna(0.0)
    else:
        # For water level / discharge: forward fill then back fill per station
        df[target_clean_name] = df.groupby(station_col)[target_clean_name].ffill().bfill()
        df[target_clean_name] = df[target_clean_name].fillna(df[target_clean_name].median() if df[target_clean_name].notnull().any() else 0.0)

    nulls_after = df[target_clean_name].isnull().sum()
    rows_after = len(df)

    # 6. Build Cleaned DataFrame Output
    df_export = pd.DataFrame({
        'Station': df[station_col],
        'State': df[state_col],
        'District': df[district_col],
        'Tehsil': df[tehsil_col] if tehsil_col else '-',
        'Block': df[block_col] if block_col else '-',
        'River': df[river_col] if river_col else '-',
        'Basin': df[basin_col] if basin_col else '-',
        'Latitude': df['Latitude_Clean'].round(6),
        'Longitude': df['Longitude_Clean'].round(6),
        'Acquisition_Time': df['Acquisition_Time'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        target_clean_name: df[target_clean_name].round(3)
    })

    clean_fname = f"cleaned_{fname}"
    clean_path = os.path.join(CLEANED_DIR, clean_fname)
    df_export.to_csv(clean_path, index=False)

    print(f"  Rows                  : {rows_before:,} -> {rows_after:,}")
    print(f"  Duplicates Removed    : {dups_before:,}")
    print(f"  Missing Coords Fixed  : {missing_coords_before:,}")
    print(f"  Missing Metric Fixed  : {nulls_before:,} -> {nulls_after:,}")
    print(f"  Saved to              : data/cleaned/{clean_fname}")

    cleaning_report.append({
        'Raw_File': fname,
        'Clean_File': clean_fname,
        'Metric': target_clean_name,
        'Rows_Before': rows_before,
        'Rows_After': rows_after,
        'Duplicates_Removed': dups_before,
        'Missing_Coords_Fixed': missing_coords_before,
        'Missing_Metric_Fixed': nulls_before,
        'Status': 'Successfully Cleaned'
    })

report_df = pd.DataFrame(cleaning_report)
summary_path = os.path.join(REPORTS_DIR, "raw_cleaning_summary.csv")
report_df.to_csv(summary_path, index=False)

print("\n" + "=" * 90)
print(f"MASTER DATA CLEANING COMPLETED SUCCESSFULLY!")
print(f"Summary Report saved to: {summary_path}")
print("=" * 90)
