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

print("=" * 100)
print("STAGE 3 (SECOND BATCH): CLEANING RIVER DISCHARGE & RESERVOIR STORAGE/WATER LEVEL DATASETS")
print("=" * 100)

cleaning_report = []

for filepath in csv_files:
    fname = os.path.basename(filepath)
    # Skip rainfall files (handled in main rainfall cleaning script)
    if 'rainfall' in fname.lower():
        continue
        
    df_raw = pd.read_csv(filepath, low_memory=False)
    rows_before = len(df_raw)
    
    if rows_before == 0:
        print(f"\nSkipping empty file: {fname}")
        continue
        
    print(f"\nProcessing Second Batch File: {fname}")
    print("-" * 80)
    
    df = df_raw.copy()
    df.columns = df.columns.str.strip()
    
    # Identify key columns
    state_col = 'State' if 'State' in df else [c for c in df.columns if 'state' in c.lower()][0]
    district_col = 'District' if 'District' in df else [c for c in df.columns if 'district' in c.lower()][0]
    station_col = 'Station' if 'Station' in df else [c for c in df.columns if 'station' in c.lower()][0]
    time_col = 'Data Acquisition Time' if 'Data Acquisition Time' in df else [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()][0]
    lat_col = 'Latitude' if 'Latitude' in df else [c for c in df.columns if 'lat' in c.lower()][0]
    lon_col = 'Longitude' if 'Longitude' in df else [c for c in df.columns if 'lon' in c.lower()][0]
    
    # Identify target metric column (Discharge, Storage, Water Level)
    target_col = None
    target_name = "Metric_Value"
    if any('discharge' in c.lower() for c in df.columns):
        target_col = [c for c in df.columns if 'discharge' in c.lower()][0]
        target_name = "River_Discharge_m3sec"
    elif any('storage' in c.lower() for c in df.columns):
        target_col = [c for c in df.columns if 'storage' in c.lower()][0]
        target_name = "Reservoir_Storage_mcm"
    elif any('water level' in c.lower() for c in df.columns):
        target_col = [c for c in df.columns if 'water level' in c.lower()][0]
        target_name = "Reservoir_Water_Level_m"
        
    if not target_col:
        print(f"Skipping {fname}: No discharge/storage/water level column found.")
        continue
        
    state_name = df[state_col].dropna().iloc[0] if len(df[state_col].dropna()) > 0 else fname
    
    # Clean text formatting
    df[station_col] = df[station_col].astype(str).str.strip().str.rstrip('.')
    df[district_col] = df[district_col].astype(str).str.strip().str.upper()
    df[state_col] = df[state_col].astype(str).str.strip()
    
    # Datetime conversion
    df['Datetime_Clean'] = pd.to_datetime(df[time_col], errors='coerce', dayfirst=True)
    invalid_dates_cnt = df['Datetime_Clean'].isnull().sum()
    df = df.dropna(subset=['Datetime_Clean'])
    
    # Duplicate removal
    dups_before = df.duplicated(subset=[station_col, 'Datetime_Clean']).sum()
    df = df.drop_duplicates(subset=[station_col, 'Datetime_Clean'], keep='first')
    
    # Lat/Lon numeric conversion
    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
    missing_latlon = df[lat_col].isnull().sum()
    df[lat_col] = df[lat_col].fillna(df[lat_col].median() if df[lat_col].notnull().any() else 18.0)
    df[lon_col] = df[lon_col].fillna(df[lon_col].median() if df[lon_col].notnull().any() else 79.0)
    
    # Numeric conversion for target value
    df[target_name] = pd.to_numeric(df[target_col], errors='coerce')
    nulls_before = df[target_name].isnull().sum()
    
    # Impute missing values with station forward-fill + median fallback
    df[target_name] = df.groupby(station_col)[target_name].ffill().bfill()
    df[target_name] = df[target_name].fillna(df[target_name].median() if df[target_name].notnull().any() else 0.0)
    nulls_after = df[target_name].isnull().sum()
    
    rows_after = len(df)
    cleaned_filename = f"cleaned_{fname}"
    output_path = os.path.join(CLEANED_DIR, cleaned_filename)
    
    # Export cleaned columns
    df_export = df[[
        station_col, state_col, district_col, 'Tehsil', 'Block', 'River', 'Basin',
        lat_col, lon_col, 'Datetime_Clean', target_name
    ]].copy()
    
    df_export.columns = [
        'Station', 'State', 'District', 'Tehsil', 'Block', 'River', 'Basin',
        'Latitude', 'Longitude', 'Acquisition_Time', target_name
    ]
    
    df_export.to_csv(output_path, index=False)
    
    print(f"  Summary for {fname}:")
    print(f"  - Rows                 : {rows_before:,} -> {rows_after:,}")
    print(f"  - Metric Name          : {target_name}")
    print(f"  - Missing Metric Fixed : {nulls_before:,} -> {nulls_after:,}")
    print(f"  - Clean File Saved To  : data/cleaned/{cleaned_filename}")
    
    cleaning_report.append({
        'State': state_name,
        'File': fname,
        'Metric': target_name,
        'Rows Before': rows_before,
        'Rows After': rows_after,
        'Duplicates Removed': dups_before,
        'Missing LatLon Fixed': missing_latlon,
        'Missing Target Before': nulls_before,
        'Missing Target After': nulls_after,
        'Clean Path': output_path
    })

if cleaning_report:
    rep_df = pd.DataFrame(cleaning_report)
    rep_df.to_csv(os.path.join(REPORTS_DIR, "stage3_second_batch_report.csv"), index=False)

print("\n" + "=" * 100)
print("SECOND BATCH DATASETS CLEANING COMPLETE")
print("Cleaned datasets saved in data/cleaned/")
print("Report saved to reports/stage3_second_batch_report.csv")
print("=" * 100)
