import os
import glob
import pandas as pd

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"
REPORTS_DIR = r"c:\Users\Lenovo\Desktop\FRP\reports"

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 100, flush=True)
print("STAGE 7: CLEANING & CONVERTING 7TH BATCH DATASETS TO CSV & EXCEL (.xlsx)", flush=True)
print("Processing CWC River Velocity & Discharge, Telemetry River Water Level, and Biological SWQ Datasets", flush=True)
print("=" * 100, flush=True)

report_rows = []

def clean_df(df):
    df = df.loc[:, ~df.columns.duplicated()].copy()
    for str_col in df.select_dtypes(include=['object', 'string']).columns:
        df[str_col] = df[str_col].astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
    return df.drop_duplicates()

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

# 1. Biological SWQ Datasets
print("\n[1/3] Processing CWC Biological Surface Water Quality Datasets...", flush=True)
bio_files = sorted(glob.glob(os.path.join(RAW_DIR, "swq_*.csv")))
bio_dfs = []

for bf in bio_files:
    fname = os.path.basename(bf)
    try:
        df = pd.read_csv(bf, low_memory=False)
        if df.empty:
            continue
        date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'dt'])]
        for dc in date_cols:
            df[dc] = pd.to_datetime(df[dc], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[dc].astype(str))
        tag = fname.replace('.csv', '')
        export_dataset(df, tag, source_desc=fname)
        bio_dfs.append(df)
    except Exception as e:
        print(f"  Warning reading bio SWQ file {fname}: {e}", flush=True)

if bio_dfs:
    master_bio = pd.concat(bio_dfs, ignore_index=True)
    export_dataset(master_bio, "swq_master_cwc_biological", source_desc="Combined CWC Biological SWQ Datasets")

# 2. River Velocity & Discharge Datasets
print("\n[2/3] Processing CWC River Velocity & Discharge Datasets...", flush=True)
vel_files = sorted(glob.glob(os.path.join(RAW_DIR, "river_velocity_discharge_*.csv")))

for vf in vel_files:
    fname = os.path.basename(vf)
    try:
        df = pd.read_csv(vf, low_memory=False)
        if df.empty:
            continue
        date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'dt'])]
        for dc in date_cols:
            df[dc] = pd.to_datetime(df[dc], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[dc].astype(str))
        tag = fname.replace('.csv', '')
        export_dataset(df, tag, source_desc=fname)
    except Exception as e:
        print(f"  Warning reading river velocity file {fname}: {e}", flush=True)

# 3. Telemetry River Water Level (RWL) Datasets
print("\n[3/3] Processing CWC Telemetry River Water Level Datasets...", flush=True)
rwl_files = sorted([f for f in glob.glob(os.path.join(RAW_DIR, "rwl_*.csv")) if os.path.basename(f) not in [os.path.basename(x) for x in bio_files + vel_files]])

for rf in rwl_files:
    fname = os.path.basename(rf)
    try:
        df = pd.read_csv(rf, low_memory=False)
        if df.empty:
            continue
        date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'dt'])]
        for dc in date_cols:
            df[dc] = pd.to_datetime(df[dc], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[dc].astype(str))
        tag = fname.replace('.csv', '')
        export_dataset(df, tag, source_desc=fname)
    except Exception as e:
        print(f"  Warning reading RWL telemetry file {fname}: {e}", flush=True)

# Export Report
report_df = pd.DataFrame(report_rows)
report_csv = os.path.join(REPORTS_DIR, "stage3_seventh_batch_report.csv")
report_df.to_csv(report_csv, index=False)

print("\n" + "=" * 100, flush=True)
print(f"STAGE 7 CLEANING & CONVERSION COMPLETE! Processed {len(report_rows)} datasets.", flush=True)
print(f"Report saved to: {report_csv}", flush=True)
print("=" * 100, flush=True)
