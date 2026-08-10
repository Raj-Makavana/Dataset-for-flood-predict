"""
Stage 2: Comprehensive Raw Data Inspection Script
Inspects all downloaded CSV datasets in data/raw without modifying them.
Checks state coverage for India and generates a detailed report.
"""
import os
import glob
import pandas as pd
import numpy as np

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"

# All 28 States and 8 Union Territories of India
ALL_INDIA_STATES = {
    'Andhra Pradesh': 'AP',
    'Arunachal Pradesh': 'AR',
    'Assam': 'AS',
    'Bihar': 'BR',
    'Chhattisgarh': 'CG',
    'Goa': 'GA',
    'Gujarat': 'GJ',
    'Haryana': 'HR',
    'Himachal Pradesh': 'HP',
    'Jharkhand': 'JH',
    'Karnataka': 'KA',
    'Kerala': 'KL',
    'Madhya Pradesh': 'MP',
    'Maharashtra': 'MH',
    'Manipur': 'MN',
    'Meghalaya': 'ML',
    'Mizoram': 'MZ',
    'Nagaland': 'NL',
    'Odisha': 'OD',
    'Punjab': 'PB',
    'Rajasthan': 'RJ',
    'Sikkim': 'SK',
    'Tamil Nadu': 'TN',
    'Telangana': 'TS',
    'Tripura': 'TR',
    'Uttar Pradesh': 'UP',
    'Uttarakhand': 'UK',
    'West Bengal': 'WB',
    # UTs
    'Andaman & Nicobar Islands': 'AN',
    'Chandigarh': 'CH',
    'Dadra & Nagar Haveli and Daman & Diu': 'DN',
    'Delhi': 'DL',
    'Jammu & Kashmir': 'JK',
    'Ladakh': 'LA',
    'Lakshadweep': 'LD',
    'Puducherry': 'PY'
}

csv_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
csv_files.sort()

print("=" * 80)
print(f"STAGE 2: RAW DATASET INSPECTION REPORT")
print(f"Total CSV Files Found in data/raw/: {len(csv_files)}")
print("=" * 80)

found_states_dict = {}
summary_table = []

for filepath in csv_files:
    fname = os.path.basename(filepath)
    size_bytes = os.path.getsize(filepath)
    size_str = f"{size_bytes / (1024*1024):.2f} MB" if size_bytes >= 1024*1024 else f"{size_bytes / 1024:.2f} KB"

    print(f"\n--------------------------------------------------------------------------------")
    print(f"File: {fname}")
    print(f"File Size: {size_str} ({size_bytes:,} bytes)")
    
    if size_bytes < 100:
        print("  WARNING: File appears to be empty or corrupted (<100 bytes)")
        summary_table.append({
            'filename': fname,
            'state_code': 'N/A',
            'state_name': 'Corrupted/Empty',
            'file_size': size_str,
            'size_bytes': size_bytes,
            'rows': 0,
            'cols': 0,
            'stations': 0,
            'min_date': 'N/A',
            'max_date': 'N/A',
            'dup_rows': 0,
            'missing_pct': '100%'
        })
        continue

    try:
        # Read dataset
        df = pd.read_csv(filepath, low_memory=False)
        num_rows, num_cols = df.shape
        cols = list(df.columns)
        
        # Get State from dataframe column if present
        state_name_in_df = df['State'].dropna().iloc[0] if 'State' in df and len(df['State'].dropna()) > 0 else "Unknown"
        
        state_code = ALL_INDIA_STATES.get(state_name_in_df, "N/A")
        found_states_dict[state_name_in_df] = state_code
        
        dup_rows = df.duplicated().sum()
        missing_cells = df.isnull().sum().sum()
        total_cells = df.size
        missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0
        
        # Date column search
        date_cols = [c for c in cols if 'date' in c.lower() or 'time' in c.lower() or 'timestamp' in c.lower()]
        min_date, max_date = "N/A", "N/A"
        if date_cols:
            dcol = date_cols[0]
            try:
                dt_series = pd.to_datetime(df[dcol], errors='coerce', dayfirst=True)
                min_date = str(dt_series.min())
                max_date = str(dt_series.max())
            except Exception:
                pass

        # Lat/Lon search
        lat_cols = [c for c in cols if 'lat' in c.lower()]
        lon_cols = [c for c in cols if 'lon' in c.lower() or 'lng' in c.lower()]
        lat_range = f"{df[lat_cols[0]].min():.4f} to {df[lat_cols[0]].max():.4f}" if lat_cols else "N/A"
        lon_range = f"{df[lon_cols[0]].min():.4f} to {df[lon_cols[0]].max():.4f}" if lon_cols else "N/A"
        
        # Station IDs search
        stn_cols = [c for c in cols if 'station' in c.lower() or 'stn' in c.lower() or 'site' in c.lower() or 'code' in c.lower()]
        num_stations = df[stn_cols[0]].nunique() if stn_cols else 0

        # Target Rainfall values missing count
        rainfall_col = [c for c in cols if 'rainfall' in c.lower()]
        rf_null_cnt = df[rainfall_col[0]].isnull().sum() if rainfall_col else 0
        rf_null_pct = (rf_null_cnt / num_rows * 100) if num_rows > 0 else 0

        print(f"State Name in File: {state_name_in_df}")
        print(f"Dimensions        : {num_rows:,} rows x {num_cols} columns")
        print(f"Date Range        : {min_date} to {max_date}")
        print(f"Unique Stations   : {num_stations}")
        print(f"Lat Range         : {lat_range}")
        print(f"Lon Range         : {lon_range}")
        print(f"Duplicate Rows    : {dup_rows:,}")
        print(f"Missing Cells     : {missing_cells:,} ({missing_pct:.2f}% of all cells)")
        print(f"Rainfall Nulls    : {rf_null_cnt:,} ({rf_null_pct:.1f}% missing rainfall records)")
        
        summary_table.append({
            'filename': fname,
            'state_code': state_code,
            'state_name': state_name_in_df,
            'file_size': size_str,
            'size_bytes': size_bytes,
            'rows': num_rows,
            'cols': num_cols,
            'stations': num_stations,
            'min_date': min_date,
            'max_date': max_date,
            'dup_rows': dup_rows,
            'missing_pct': f"{missing_pct:.2f}%",
            'rainfall_null_pct': f"{rf_null_pct:.1f}%"
        })

    except Exception as e:
        print(f"  ERROR Reading File {fname}: {e}")

print("\n" + "=" * 80)
print("INDIAN STATES & UNION TERRITORIES COVERAGE CHECK")
print("=" * 80)

all_official_states = set(ALL_INDIA_STATES.keys())
found_official_states = set([s for s in found_states_dict.keys() if s in all_official_states])
missing_official_states = all_official_states - found_official_states

print(f"\nTotal Indian States & UTs Tracked  : {len(ALL_INDIA_STATES)}")
print(f"States & UTs Covered in data/raw/  : {len(found_official_states)}")
print(f"States & UTs MISSING               : {len(missing_official_states)}")

print("\n--------------------------------------------------------------------------------")
print("FOUND STATES IN DATASET:")
for s in sorted(found_official_states):
    code = ALL_INDIA_STATES[s]
    print(f"  [PRESENT] {s:<30} ({code})")

print("\n--------------------------------------------------------------------------------")
print("MISSING STATES & UNION TERRITORIES:")
missing_states = []
missing_uts = []
for s in sorted(missing_official_states):
    code = ALL_INDIA_STATES[s]
    if code in ['AN', 'CH', 'DN', 'DL', 'JK', 'LA', 'LD', 'PY']:
        missing_uts.append((s, code))
    else:
        missing_states.append((s, code))

print("\nMissing States:")
for s, code in missing_states:
    print(f"  [MISSING] {s:<30} ({code})")

print("\nMissing Union Territories:")
for u, code in missing_uts:
    print(f"  [MISSING] {u:<30} ({code})")

# Save detailed summary json/csv for reports
summary_df = pd.DataFrame(summary_table)
os.makedirs(r"c:\Users\Lenovo\Desktop\FRP\reports", exist_ok=True)
summary_df.to_csv(r"c:\Users\Lenovo\Desktop\FRP\reports\stage2_raw_data_summary.csv", index=False)
print(f"\nSaved detailed dataset summary to: reports/stage2_raw_data_summary.csv")
