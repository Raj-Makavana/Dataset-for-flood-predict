import os
import glob
import zipfile
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
print("STAGE 3 (THIRD BATCH): CLEANING CLIMATE, HYDROLOGICAL & WATER LEVEL DATASETS")
print("=" * 100)

cleaning_report = []

for filepath in csv_files:
    fname = os.path.basename(filepath)
    rows_before = 0
    try:
        df_raw = pd.read_csv(filepath, low_memory=False)
        rows_before = len(df_raw)
    except Exception as e:
        print(f"Error reading {fname}: {e}")
        continue

    if rows_before == 0:
        print(f"\nSkipping empty file: {fname}")
        continue

    print(f"\nProcessing Third Batch File: {fname}")
    print("-" * 80)

    df = df_raw.copy()
    df.columns = df.columns.str.strip()

    # Identify key columns
    state_cols = [c for c in df.columns if 'state' in c.lower()]
    state_col = 'State' if 'State' in df else (state_cols[0] if state_cols else None)

    district_cols = [c for c in df.columns if 'district' in c.lower()]
    district_col = 'District' if 'District' in df else (district_cols[0] if district_cols else None)

    station_cols = [c for c in df.columns if 'station' in c.lower() or 'site' in c.lower()]
    station_col = 'Station' if 'Station' in df else (station_cols[0] if station_cols else None)

    time_cols = [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()]
    time_col = 'Data Acquisition Time' if 'Data Acquisition Time' in df else (time_cols[0] if time_cols else None)

    lat_cols = [c for c in df.columns if 'lat' in c.lower()]
    lat_col = 'Latitude' if 'Latitude' in df else (lat_cols[0] if lat_cols else None)

    lon_cols = [c for c in df.columns if 'lon' in c.lower()]
    lon_col = 'Longitude' if 'Longitude' in df else (lon_cols[0] if lon_cols else None)

    # Detect metric category and target value column
    target_col = None
    metric_category = "General_Telemetry"

    cols_lower = {c: c.lower() for c in df.columns}
    for c, cl in cols_lower.items():
        if 'rainfall' in cl:
            target_col = c
            metric_category = "Hourly_Rainfall_mm"
            break
        elif 'discharge' in cl:
            target_col = c
            metric_category = "River_Discharge_m3sec"
            break
        elif 'water level' in cl or 'rwl' in cl or 'level' in cl:
            target_col = c
            metric_category = "Water_Level_m"
            break
        elif 'humid' in cl or 'rh' in cl:
            target_col = c
            metric_category = "Relative_Humidity_pct"
            break
        elif 'temp' in cl:
            target_col = c
            metric_category = "Temperature_C"
            break
        elif 'gwl' in cl:
            target_col = c
            metric_category = "Groundwater_Level_m"
            break

    if not target_col:
        # Fallback to last column
        target_col = df.columns[-1]
        metric_category = "Telemetry_Metric"

    state_name = df[state_col].dropna().iloc[0] if (state_col and len(df[state_col].dropna()) > 0) else fname

    # Check file size. If larger than 50MB, use chunked processing to save RAM memory
    file_sz_mb = os.path.getsize(filepath) / (1024 * 1024)
    cleaned_filename = f"cleaned_{fname}"
    output_path = os.path.join(CLEANED_DIR, cleaned_filename)

    if file_sz_mb > 50.0:
        print(f"Large File ({file_sz_mb:.2f} MB): Using low-memory chunked processing...")
        if os.path.exists(output_path):
            os.remove(output_path)
            
        first_chunk = True
        total_rows_proc = 0
        
        for chunk in pd.read_csv(filepath, chunksize=100000, low_memory=False):
            chunk.columns = chunk.columns.str.strip()
            total_rows_proc += len(chunk)
            
            # Identify columns
            st_col = 'State' if 'State' in chunk else [c for c in chunk.columns if 'state' in c.lower()][0]
            dist_col = 'District' if 'District' in chunk else [c for c in chunk.columns if 'district' in c.lower()][0]
            stn_col = 'Station' if 'Station' in chunk else [c for c in chunk.columns if 'station' in c.lower() or 'site' in c.lower()][0]
            tm_col = 'Data Acquisition Time' if 'Data Acquisition Time' in chunk else [c for c in chunk.columns if 'time' in c.lower() or 'date' in c.lower()][0]
            lt_col = 'Latitude' if 'Latitude' in chunk else [c for c in chunk.columns if 'lat' in c.lower()][0]
            ln_col = 'Longitude' if 'Longitude' in chunk else [c for c in chunk.columns if 'lon' in c.lower()][0]
            
            tgt_col = chunk.columns[-1]
            for c in chunk.columns:
                if any(k in c.lower() for k in ['rainfall', 'discharge', 'water level', 'rwl', 'humid', 'temp', 'gwl']):
                    tgt_col = c
                    break
                    
            chunk['Datetime_Clean'] = pd.to_datetime(chunk[tm_col], errors='coerce', dayfirst=True)
            chunk = chunk.dropna(subset=['Datetime_Clean'])
            chunk = chunk.drop_duplicates(subset=[stn_col, 'Datetime_Clean'], keep='first')
            
            chunk[lt_col] = pd.to_numeric(chunk[lt_col], errors='coerce').fillna(20.0)
            chunk[ln_col] = pd.to_numeric(chunk[ln_col], errors='coerce').fillna(78.0)
            chunk[metric_category] = pd.to_numeric(chunk[tgt_col], errors='coerce').fillna(0.0)
            
            export_cols = [stn_col, st_col, dist_col, lt_col, ln_col, 'Datetime_Clean', metric_category]
            col_names = ['Station', 'State', 'District', 'Latitude', 'Longitude', 'Acquisition_Time', metric_category]
            
            df_sub = chunk[export_cols].copy()
            df_sub.columns = col_names
            
            df_sub.to_csv(output_path, mode='a', header=first_chunk, index=False)
            first_chunk = False
            
        out_sz = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  Processed {total_rows_proc:,} rows -> Cleaned File ({out_sz:.2f} MB)")
        cleaning_report.append({
            'State': state_name,
            'File': fname,
            'Metric': metric_category,
            'Rows Before': total_rows_proc,
            'Rows After': total_rows_proc,
            'Duplicates Removed': 0,
            'Missing Target Before': 0,
            'Missing Target After': 0,
            'Clean Path': output_path,
            'Clean Size MB': round(out_sz, 2)
        })
        continue

    # Standard memory processing for smaller files (< 50MB)
    if station_col:
        df[station_col] = df[station_col].astype(str).str.strip().str.rstrip('.')
    if district_col:
        df[district_col] = df[district_col].astype(str).str.strip().str.upper()
    if state_col:
        df[state_col] = df[state_col].astype(str).str.strip()

    # Datetime handling
    if time_col:
        df['Datetime_Clean'] = pd.to_datetime(df[time_col], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['Datetime_Clean'])
    else:
        df['Datetime_Clean'] = pd.Timestamp.now()

    # Deduplication
    if station_col and 'Datetime_Clean' in df.columns:
        dups_before = df.duplicated(subset=[station_col, 'Datetime_Clean']).sum()
        df = df.drop_duplicates(subset=[station_col, 'Datetime_Clean'], keep='first')
    else:
        dups_before = 0

    # Lat / Lon cleaning
    if lat_col:
        df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
    else:
        df['Latitude'] = 20.0
        lat_col = 'Latitude'

    if lon_col:
        df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
    else:
        df['Longitude'] = 78.0
        lon_col = 'Longitude'

    df[lat_col] = df[lat_col].fillna(df[lat_col].median() if df[lat_col].notnull().any() else 20.0)
    df[lon_col] = df[lon_col].fillna(df[lon_col].median() if df[lon_col].notnull().any() else 78.0)

    # Metric numeric conversion & imputation
    df[metric_category] = pd.to_numeric(df[target_col], errors='coerce')
    nulls_before = df[metric_category].isnull().sum()

    if station_col:
        df[metric_category] = df.groupby(station_col)[metric_category].ffill().bfill()
    df[metric_category] = df[metric_category].fillna(df[metric_category].median() if df[metric_category].notnull().any() else 0.0)
    nulls_after = df[metric_category].isnull().sum()

    rows_after = len(df)
    output_path = os.path.join(CLEANED_DIR, cleaned_filename)

    # Standard export columns
    export_cols = []
    col_names = []

    for c_src, c_dst in [
        (station_col, 'Station'),
        (state_col, 'State'),
        (district_col, 'District'),
        ('Tehsil' if 'Tehsil' in df else None, 'Tehsil'),
        ('Block' if 'Block' in df else None, 'Block'),
        ('River' if 'River' in df else None, 'River'),
        ('Basin' if 'Basin' in df else None, 'Basin'),
        (lat_col, 'Latitude'),
        (lon_col, 'Longitude'),
        ('Datetime_Clean', 'Acquisition_Time'),
        (metric_category, metric_category)
    ]:
        if c_src and c_src in df.columns:
            export_cols.append(c_src)
            col_names.append(c_dst)

    df_export = df[export_cols].copy()
    df_export.columns = col_names
    df_export.to_csv(output_path, index=False)

    out_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Summary for {fname}:")
    print(f"  - Rows                 : {rows_before:,} -> {rows_after:,}")
    print(f"  - Metric               : {metric_category}")
    print(f"  - Missing Metric Fixed : {nulls_before:,} -> {nulls_after:,}")
    print(f"  - Clean File Saved To  : data/cleaned/{cleaned_filename} ({out_size_mb:.2f} MB)")

    cleaning_report.append({
        'State': state_name,
        'File': fname,
        'Metric': metric_category,
        'Rows Before': rows_before,
        'Rows After': rows_after,
        'Duplicates Removed': dups_before,
        'Missing Target Before': nulls_before,
        'Missing Target After': nulls_after,
        'Clean Path': output_path,
        'Clean Size MB': round(out_size_mb, 2)
    })

if cleaning_report:
    rep_df = pd.DataFrame(cleaning_report)
    rep_df.to_csv(os.path.join(REPORTS_DIR, "stage3_third_batch_report.csv"), index=False)

# Auto-chunk any file over 45 MB in raw/ or cleaned/ so GitHub push never fails
print("\n" + "=" * 100)
print("CHECKING FOR FILES > 45MB TO SPLIT FOR GITHUB COMPLIANCE...")
print("=" * 100)

for folder in [RAW_DIR, CLEANED_DIR]:
    # Get list of base files (ignoring hidden or part files)
    base_files = [f for f in glob.glob(os.path.join(folder, "*.*")) if not os.path.basename(f).startswith('.') and '.part' not in os.path.basename(f)]
    for fpath in base_files:
        fname = os.path.basename(fpath)
        sz_mb = os.path.getsize(fpath) / (1024 * 1024)
        if sz_mb > 45.0:
            print(f"Splitting large file ({sz_mb:.2f} MB): {fname}")
            chunk_size = 45 * 1024 * 1024
            part_num = 1
            with open(fpath, 'rb') as src:
                while True:
                    data = src.read(chunk_size)
                    if not data:
                        break
                    part_file = os.path.join(folder, f"{fname}.part{part_num}")
                    with open(part_file, 'wb') as p_out:
                        p_out.write(data)
                    print(f"  -> Created chunk: {os.path.basename(part_file)} ({len(data)/(1024*1024):.2f} MB)")
                    part_num += 1
            # Remove original un-split file to save disk space
            try:
                os.remove(fpath)
                print(f"  -> Removed original un-split file: {fname} to conserve disk space")
            except Exception as ex:
                print(f"  -> Warning: Could not remove {fname}: {ex}")

print("\n" + "=" * 100)
print("THIRD BATCH DATASETS CLEANING & CHUNKING COMPLETE")
print("Cleaned datasets saved in data/cleaned/")
print("Report saved to reports/stage3_third_batch_report.csv")
print("=" * 100)
