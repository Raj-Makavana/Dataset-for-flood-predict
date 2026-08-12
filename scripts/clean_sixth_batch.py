import os
import glob
import re
import zipfile
import tempfile
import shapefile
import pandas as pd

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"
REPORTS_DIR = r"c:\Users\Lenovo\Desktop\FRP\reports"

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 100)
print("STAGE 6: DECOMPRESSING, CLEANING & CONVERTING 6TH BATCH DATASETS TO CSV & EXCEL (.xlsx)")
print("Processing Spatial Boundaries, Surface Water Quality (CPCB), CWPRS, NCA, DVC, NIH Datasets")
print("=" * 100)

report_rows = []

# Helper function to sanitize string columns
def clean_df(df):
    df = df.loc[:, ~df.columns.duplicated()].copy()
    for str_col in df.select_dtypes(include=['object', 'string']).columns:
        df[str_col] = df[str_col].astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
    return df.drop_duplicates()

# Helper function to export CSV and Excel
def export_dataset(df, base_name, source_desc=""):
    df = clean_df(df)
    csv_p = os.path.join(CLEANED_DIR, f"cleaned_{base_name}.csv")
    xlsx_p = os.path.join(CLEANED_DIR, f"cleaned_{base_name}.xlsx")
    
    df.to_csv(csv_p, index=False)
    csv_sz = os.path.getsize(csv_p) / (1024 * 1024)
    
    xlsx_sz = 0.0
    if len(df) <= 30000:
        try:
            df.to_excel(xlsx_p, index=False, engine='openpyxl')
            xlsx_sz = os.path.getsize(xlsx_p) / (1024 * 1024)
        except Exception as ex:
            print(f"  Warning exporting Excel for {base_name}: {ex}", flush=True)
            
    print(f"  -> Exported cleaned_{base_name}: {len(df)} records | CSV: {csv_sz:.2f} MB | Excel: {xlsx_sz:.2f} MB", flush=True)
    report_rows.append({
        'Dataset': base_name,
        'Source': source_desc,
        'Total_Records': len(df),
        'Clean_CSV': f"cleaned_{base_name}.csv",
        'CSV_Size_MB': round(csv_sz, 2),
        'Clean_Excel': f"cleaned_{base_name}.xlsx" if xlsx_sz > 0 else "N/A (>30k rows)",
        'Excel_Size_MB': round(xlsx_sz, 2)
    })
    return df

# ---------------------------------------------------------
# 1. PROCESS SPATIAL BOUNDARIES (Basin, District, State, Subdistrict, Inter-basin)
# ---------------------------------------------------------
print("\n[1/3] Processing Spatial & Administrative Boundary Datasets...")

spatial_zips = [
    ('basin_cwc_shp.zip', 'basin_cwc'),
    ('district_nwic_geojson.zip', 'district_nwic'),
    ('state_nwic_shp.zip', 'state_nwic'),
    ('subdistrict_nwic_shp.zip', 'subdistrict_nwic'),
    ('inter_basin_transfer_link_shp.zip', 'inter_basin_transfer_link')
]

import json

for zip_name, tag in spatial_zips:
    zip_path = os.path.join(RAW_DIR, zip_name)
    
    # Auto-combine split parts if zip does not exist directly
    if not os.path.exists(zip_path):
        part1 = os.path.join(RAW_DIR, f"{zip_name}.part1")
        part2 = os.path.join(RAW_DIR, f"{zip_name}.part2")
        if os.path.exists(part1) and os.path.exists(part2):
            print(f"  Combining split parts for {zip_name}...")
            with open(zip_path, 'wb') as out_f:
                p_idx = 1
                while True:
                    pf = os.path.join(RAW_DIR, f"{zip_name}.part{p_idx}")
                    if os.path.exists(pf):
                        with open(pf, 'rb') as in_f:
                            out_f.write(in_f.read())
                        p_idx += 1
                    else:
                        break
                        
    if not os.path.exists(zip_path):
        continue
        
    records = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            shp_files = [f for f in z.namelist() if f.lower().endswith('.shp')]
            geojson_files = [f for f in z.namelist() if f.lower().endswith('.geojson')]
            
            if shp_files:
                tmpdir = tempfile.mkdtemp()
                z.extractall(tmpdir)
                shp_p = os.path.join(tmpdir, shp_files[0])
                sf = shapefile.Reader(shp_p, encoding='latin1')
                fields = [f[0] for f in sf.fields[1:]]
                for r in sf.records():
                    records.append(dict(zip(fields, r)))
            elif geojson_files:
                with z.open(geojson_files[0]) as g_file:
                    g_data = json.load(g_file)
                    features = g_data.get('features', [])
                    for feat in features:
                        records.append(feat.get('properties', {}))
    except Exception as e:
        print(f"  Warning reading spatial zip {zip_name}: {e}")
        
    if records:
        df_sp = pd.DataFrame(records)
        export_dataset(df_sp, tag, source_desc=zip_name)

# ---------------------------------------------------------
# 2. PROCESS CPCB SURFACE WATER QUALITY (SWQ) DATASETS
# ---------------------------------------------------------
print("\n[2/3] Processing CPCB Surface Water Quality (SWQ) Datasets...")
swq_files = [f for f in glob.glob(os.path.join(RAW_DIR, "swq_*.csv")) if not os.path.basename(f).startswith('.')]

swq_dfs = []
for swq_file in sorted(swq_files):
    fname = os.path.basename(swq_file)
    try:
        df_swq = pd.read_csv(swq_file)
        if not df_swq.empty:
            df_swq = clean_df(df_swq)
            tag = fname.replace('.csv', '')
            export_dataset(df_swq, tag, source_desc=fname)
            swq_dfs.append(df_swq)
    except Exception as e:
        print(f"  Warning reading SWQ file {fname}: {e}")

if swq_dfs:
    master_swq = pd.concat(swq_dfs, ignore_index=True)
    export_dataset(master_swq, "swq_master_all_india_cpcb", source_desc="Combined CPCB SWQ Datasets")

# ---------------------------------------------------------
# 3. PROCESS HYDRO-TELEMETRY & CLIMATE DATASETS (CWPRS, NCA, DVC, NIH Roorkee)
# ---------------------------------------------------------
print("\n[3/3] Processing Hydro-Telemetry & Climate Datasets...")

other_csvs = [f for f in glob.glob(os.path.join(RAW_DIR, "*.csv")) 
              if not os.path.basename(f).startswith('.') 
              and not os.path.basename(f).startswith('swq_')]

for csv_f in sorted(other_csvs):
    fname = os.path.basename(csv_f)
    try:
        df = pd.read_csv(csv_f, low_memory=False)
        if df.empty:
            continue
        
        # Standardize date columns if present
        date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'dt'])]
        for dc in date_cols:
            df[dc] = pd.to_datetime(df[dc], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[dc].astype(str))
            
        tag = fname.replace('.csv', '')
        export_dataset(df, tag, source_desc=fname)
    except Exception as e:
        print(f"  Warning reading hydro-telemetry CSV {fname}: {e}")

# Export Report
report_df = pd.DataFrame(report_rows)
report_csv = os.path.join(REPORTS_DIR, "stage3_sixth_batch_report.csv")
report_df.to_csv(report_csv, index=False)

print("\n" + "=" * 100)
print(f"STAGE 6 CLEANING & EXCEL CONVERSION COMPLETE! Processed {len(report_rows)} datasets.")
print(f"Report saved to: {report_csv}")
print("=" * 100)
