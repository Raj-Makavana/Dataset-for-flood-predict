"""
Master Cleaning Script for FRP Raw Datasets (Memory-Efficient Chunked Cleaning)
Cleans all raw CSV datasets, groundwater level, reservoir data, and shapefile ZIPs in data/raw
Exports cleaned versions to data/cleaned/
Generates a detailed cleaning report in reports/raw_cleaning_summary.csv
"""

import os
import glob
import zipfile
import tempfile
import shapefile
import pandas as pd
import numpy as np

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"
REPORTS_DIR = r"c:\Users\Lenovo\Desktop\FRP\reports"

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 90)
print("MASTER DATA CLEANING PROCESS STARTED (MEMORY-EFFICIENT CHUNKED MODE)")
print("=" * 90)

cleaning_report = []

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

# 1. PROCESS ZIP SHAPEFILES (e.g. dam.zip)
zip_files = glob.glob(os.path.join(RAW_DIR, "*.zip"))
for zpath in zip_files:
    zname = os.path.basename(zpath)
    print(f"\nProcessing ZIP Dataset: {zname}")
    print("-" * 75)
    try:
        with zipfile.ZipFile(zpath, 'r') as z:
            shp_files = [f for f in z.namelist() if f.lower().endswith('.shp')]
            if shp_files:
                tmpdir = tempfile.mkdtemp()
                z.extractall(tmpdir)
                shp_p = os.path.join(tmpdir, shp_files[0])
                for enc in ['utf-8', 'latin1', 'cp1252']:
                    try:
                        sf = shapefile.Reader(shp_p, encoding=enc)
                        recs = sf.records()
                        fields = [f[0] for f in sf.fields[1:]]
                        dam_records = []
                        shapes = sf.shapes()
                        for i, r in enumerate(recs):
                            d_dict = dict(zip(fields, r))
                            if i < len(shapes) and shapes[i].points:
                                d_dict['Longitude'] = shapes[i].points[0][0]
                                d_dict['Latitude'] = shapes[i].points[0][1]
                            dam_records.append(d_dict)
                        df_dam = pd.DataFrame(dam_records)
                        clean_fname = f"cleaned_{zname.replace('.zip', '')}_locations_india.csv"
                        clean_path = os.path.join(CLEANED_DIR, clean_fname)
                        df_dam.to_csv(clean_path, index=False)
                        print(f"  Exported Dam GIS Dataset: {len(df_dam)} records -> data/cleaned/{clean_fname}")
                        cleaning_report.append({
                            'Raw_File': zname,
                            'Clean_File': clean_fname,
                            'Metric': 'Dam_Locations_GIS',
                            'Rows_Before': len(df_dam),
                            'Rows_After': len(df_dam),
                            'Duplicates_Removed': 0,
                            'Missing_Coords_Fixed': 0,
                            'Missing_Metric_Fixed': 0,
                            'Status': 'Successfully Cleaned (GIS Shapefile)'
                        })
                        break
                    except Exception:
                        continue
    except Exception as e:
        print(f"  Error reading ZIP {zname}: {e}")

# 2. PROCESS ALL CSV DATASETS (CHUNKED TO PREVENT RAM OVERLOAD)
csv_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
csv_files.sort()

print(f"\nProcessing {len(csv_files)} CSV Raw Datasets...")

for filepath in csv_files:
    fname = os.path.basename(filepath)
    
    # Skip duplicate copy files if present
    if "(1)" in fname:
        print(f"\nSkipping duplicate copy file: {fname}")
        continue

    file_size = os.path.getsize(filepath)
    print(f"\nProcessing: {fname} ({file_size / (1024*1024):.2f} MB)")
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

    clean_fname = f"cleaned_{fname}"
    clean_path = os.path.join(CLEANED_DIR, clean_fname)

    # Remove pre-existing file if any
    if os.path.exists(clean_path):
        try:
            os.remove(clean_path)
        except Exception:
            pass

    total_rows_before = 0
    total_rows_after = 0
    total_dups = 0
    total_missing_coords = 0
    total_missing_metric = 0
    target_metric_name = "Metric_Value"

    # Use chunked processing for files > 30MB
    chunksize = 100000 if file_size > 30 * 1024 * 1024 else None

    try:
        reader = pd.read_csv(filepath, low_memory=False, chunksize=chunksize) if chunksize else [pd.read_csv(filepath, low_memory=False)]
        is_first_chunk = True

        for chunk_df in reader:
            df = chunk_df.copy()
            total_rows_before += len(df)

            df.columns = df.columns.str.replace(r'[\r\n]+', ' ', regex=True).str.strip()

            # Handle special state datasets like Karnataka Reservoir
            if 'karnataka_man_reservoir' in fname.lower():
                df['State'] = 'Karnataka'
                df['District'] = 'Karnataka'
                df['Station'] = df['Reservoir Name'] if 'Reservoir Name' in df else 'Reservoir'
                df['Acquisition_Time'] = pd.to_datetime(df['Monitoring Date'], errors='coerce', dayfirst=True)
                df['Water_Level_ft'] = pd.to_numeric(df['Reservoir Level (ft)'], errors='coerce')
                df['Latitude_Clean'] = 15.3173
                df['Longitude_Clean'] = 75.7139
                df = df.dropna(subset=['Acquisition_Time'])
                dups = df.duplicated(subset=['Station', 'Acquisition_Time']).sum()
                total_dups += dups
                df = df.drop_duplicates(subset=['Station', 'Acquisition_Time'], keep='first')
                df['Water_Level_ft'] = df.groupby('Station')['Water_Level_ft'].ffill().bfill().fillna(0.0)
                
                df_export = pd.DataFrame({
                    'Station': df['Station'],
                    'State': df['State'],
                    'District': df['District'],
                    'Tehsil': '-',
                    'Block': '-',
                    'River': df['River'] if 'River' in df else '-',
                    'Basin': df['Basin'] if 'Basin' in df else '-',
                    'Latitude': df['Latitude_Clean'],
                    'Longitude': df['Longitude_Clean'],
                    'Acquisition_Time': df['Acquisition_Time'].dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'Reservoir_Water_Level_ft': df['Water_Level_ft'].round(3)
                })
                total_rows_after += len(df_export)
                df_export.to_csv(clean_path, mode='a', header=is_first_chunk, index=False)
                is_first_chunk = False
                target_metric_name = "Reservoir_Water_Level_ft"
                continue

            # Standardize column mapping
            state_col = 'State' if 'State' in df else ([c for c in df.columns if 'state' in c.lower()][0] if any('state' in c.lower() for c in df.columns) else None)
            district_col = 'District' if 'District' in df else ([c for c in df.columns if 'district' in c.lower()][0] if any('district' in c.lower() for c in df.columns) else None)
            station_col = 'Station' if 'Station' in df else ([c for c in df.columns if 'station' in c.lower()][0] if any('station' in c.lower() for c in df.columns) else None)
            time_col = 'Data Acquisition Time' if 'Data Acquisition Time' in df else ([c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()][0] if any('time' in c.lower() or 'date' in c.lower() for c in df.columns) else None)
            lat_col = 'Latitude' if 'Latitude' in df else ([c for c in df.columns if 'lat' in c.lower()][0] if any('lat' in c.lower() for c in df.columns) else None)
            lon_col = 'Longitude' if 'Longitude' in df else ([c for c in df.columns if 'lon' in c.lower()][0] if any('lon' in c.lower() for c in df.columns) else None)

            if station_col:
                df[station_col] = df[station_col].astype(str).str.strip().str.rstrip('.')
            if district_col:
                df[district_col] = df[district_col].astype(str).str.strip().str.upper()
            if state_col:
                df[state_col] = df[state_col].astype(str).str.strip()

            tehsil_col = 'Tehsil' if 'Tehsil' in df else None
            block_col = 'Block' if 'Block' in df else None
            river_col = 'River' if 'River' in df else None
            basin_col = 'Basin' if 'Basin' in df else None

            # Datetime conversion
            if time_col:
                df['Acquisition_Time'] = pd.to_datetime(df[time_col], errors='coerce', dayfirst=True)
                df = df.dropna(subset=['Acquisition_Time'])
            else:
                df['Acquisition_Time'] = pd.Timestamp.now()

            # Duplicate removal
            if station_col and 'Acquisition_Time' in df:
                dups = df.duplicated(subset=[station_col, 'Acquisition_Time']).sum()
                total_dups += dups
                df = df.drop_duplicates(subset=[station_col, 'Acquisition_Time'], keep='first')

            # Lat / Lon cleaning & Imputation
            if lat_col and lon_col:
                df['Latitude_Clean'] = pd.to_numeric(df[lat_col], errors='coerce')
                df['Longitude_Clean'] = pd.to_numeric(df[lon_col], errors='coerce')
                missing = df['Latitude_Clean'].isnull().sum()
                total_missing_coords += missing

                if missing > 0 and district_col:
                    for dist, coords in DISTRICT_COORDS.items():
                        mask = df[district_col] == dist
                        df.loc[mask & df['Latitude_Clean'].isnull(), 'Latitude_Clean'] = coords[0]
                        df.loc[mask & df['Longitude_Clean'].isnull(), 'Longitude_Clean'] = coords[1]
                    df['Latitude_Clean'] = df['Latitude_Clean'].fillna(df['Latitude_Clean'].median() if df['Latitude_Clean'].notnull().any() else 20.0)
                    df['Longitude_Clean'] = df['Longitude_Clean'].fillna(df['Longitude_Clean'].median() if df['Longitude_Clean'].notnull().any() else 78.0)
            else:
                df['Latitude_Clean'] = 20.0
                df['Longitude_Clean'] = 78.0

            # Target Metric Detection
            target_orig_col = None
            target_clean_name = "Metric_Value"

            for c in df.columns:
                c_lower = c.lower()
                if 'groundwater' in c_lower or 'gwl' in c_lower:
                    target_orig_col = c
                    target_clean_name = "Groundwater_Level_m"
                    break
                elif 'rainfall' in c_lower:
                    target_orig_col = c
                    target_clean_name = "Hourly_Rainfall_mm"
                    break
                elif 'discharge' in c_lower:
                    target_orig_col = c
                    target_clean_name = "River_Discharge_m3sec"
                    break
                elif 'storage' in c_lower:
                    target_orig_col = c
                    target_clean_name = "Reservoir_Storage_mcm"
                    break
                elif 'water level' in c_lower or 'rwl' in c_lower:
                    target_orig_col = c
                    target_clean_name = "Water_Level_m"
                    break

            if not target_orig_col:
                target_orig_col = df.columns[-1]

            target_metric_name = target_clean_name

            df[target_clean_name] = pd.to_numeric(df[target_orig_col], errors='coerce')
            total_missing_metric += df[target_clean_name].isnull().sum()

            if target_clean_name == "Hourly_Rainfall_mm":
                df[target_clean_name] = df[target_clean_name].clip(lower=0.0, upper=400.0).fillna(0.0)
            elif station_col:
                df[target_clean_name] = df.groupby(station_col)[target_clean_name].ffill().bfill()
                df[target_clean_name] = df[target_clean_name].fillna(df[target_clean_name].median() if df[target_clean_name].notnull().any() else 0.0)
            else:
                df[target_clean_name] = df[target_clean_name].fillna(0.0)

            total_rows_after += len(df)

            # Export Cleaned Chunk
            df_export = pd.DataFrame({
                'Station': df[station_col] if station_col else 'General',
                'State': df[state_col] if state_col else '-',
                'District': df[district_col] if district_col else '-',
                'Tehsil': df[tehsil_col] if tehsil_col else '-',
                'Block': df[block_col] if block_col else '-',
                'River': df[river_col] if river_col else '-',
                'Basin': df[basin_col] if basin_col else '-',
                'Latitude': df['Latitude_Clean'].round(6),
                'Longitude': df['Longitude_Clean'].round(6),
                'Acquisition_Time': df['Acquisition_Time'].dt.strftime('%Y-%m-%d %H:%M:%S'),
                target_clean_name: df[target_clean_name].round(3)
            })

            df_export.to_csv(clean_path, mode='a', header=is_first_chunk, index=False)
            is_first_chunk = False

        print(f"  Rows                  : {total_rows_before:,} -> {total_rows_after:,}")
        print(f"  Duplicates Removed    : {total_dups:,}")
        print(f"  Saved to              : data/cleaned/{clean_fname}")

        cleaning_report.append({
            'Raw_File': fname,
            'Clean_File': clean_fname,
            'Metric': target_metric_name,
            'Rows_Before': total_rows_before,
            'Rows_After': total_rows_after,
            'Duplicates_Removed': total_dups,
            'Missing_Coords_Fixed': total_missing_coords,
            'Missing_Metric_Fixed': total_missing_metric,
            'Status': 'Successfully Cleaned'
        })

    except Exception as e:
        print(f"  ERROR processing {fname}: {e}")
        cleaning_report.append({
            'Raw_File': fname,
            'Clean_File': 'N/A',
            'Metric': 'N/A',
            'Rows_Before': total_rows_before,
            'Rows_After': 0,
            'Duplicates_Removed': 0,
            'Missing_Coords_Fixed': 0,
            'Missing_Metric_Fixed': 0,
            'Status': f'Failed Processing ({e})'
        })

report_df = pd.DataFrame(cleaning_report)
summary_path = os.path.join(REPORTS_DIR, "raw_cleaning_summary.csv")
report_df.to_csv(summary_path, index=False)

print("\n" + "=" * 90)
print(f"MASTER DATA CLEANING COMPLETED SUCCESSFULLY!")
print(f"Summary Report saved to: {summary_path}")
print("=" * 90)
