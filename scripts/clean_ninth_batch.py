import os
import glob
import pandas as pd

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"
REPORTS_DIR = r"c:\Users\Lenovo\Desktop\FRP\reports"

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 100, flush=True)
print("STAGE 9: CLEANING 9TH BATCH RAW RIVER WATER LEVEL (RWL) DATASETS", flush=True)
print("Processing newly uploaded 8 raw RWL datasets for Assam, Bihar, & CWC Basins", flush=True)
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

raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))
print(f"Found {len(raw_files)} raw CSV files in {RAW_DIR}", flush=True)

for rf in raw_files:
    fname = os.path.basename(rf)
    base_tag = fname.replace('.csv', '')
    try:
        df = pd.read_csv(rf, low_memory=False)
        if df.empty:
            print(f"  Skipping empty file: {fname}", flush=True)
            continue
        
        # Datetime column formatting
        date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'dt'])]
        for dc in date_cols:
            df[dc] = pd.to_datetime(df[dc], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[dc].astype(str))
            
        export_dataset(df, base_tag, source_desc=fname)
    except Exception as e:
        print(f"  Error processing raw file {fname}: {e}", flush=True)

# Export Summary Report
report_df = pd.DataFrame(report_rows)
report_csv = os.path.join(REPORTS_DIR, "stage3_ninth_batch_report.csv")
report_df.to_csv(report_csv, index=False)

print("\n" + "=" * 100, flush=True)
print(f"STAGE 9 CLEANING COMPLETE! Processed {len(report_rows)} datasets.", flush=True)
print(f"Report saved to: {report_csv}", flush=True)
print("=" * 100, flush=True)
