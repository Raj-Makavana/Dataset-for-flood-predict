import os
import glob
import re
import zipfile
import tempfile
import pandas as pd
from dbfread import DBF

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"
REPORTS_DIR = r"c:\Users\Lenovo\Desktop\FRP\reports"

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 100)
print("STAGE 4: CLEANING DYNAMIC WATER BODY ATLAS (DWA PH1 & PH2) DATASETS")
print("Converting KMZ / Shapefiles to Cleaned tabular CSV and Excel (.xlsx) formats")
print("=" * 100)

def parse_dbf_zip(zip_path):
    records = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            dbf_files = [f for f in z.namelist() if f.lower().endswith('.dbf')]
            if not dbf_files:
                return records
            tmpdir = tempfile.mkdtemp()
            z.extractall(tmpdir)
            dbf_p = os.path.join(tmpdir, dbf_files[0])
            table = DBF(dbf_p, encoding='utf-8', char_decode_errors='ignore')
            for r in table:
                records.append(dict(r))
    except Exception as e:
        print(f"  Warning reading DBF {zip_path}: {e}")
    return records

def parse_kmz(kmz_path):
    records = []
    try:
        with zipfile.ZipFile(kmz_path, 'r') as z:
            kml_files = [f for f in z.namelist() if f.lower().endswith('.kml')]
            if not kml_files:
                return records
            content = z.read(kml_files[0]).decode('utf-8', errors='ignore')
            # Extract placemark descriptions containing HTML tables
            desc_blocks = re.findall(r'<description>(.*?)</description>', content, re.DOTALL)
            for desc in desc_blocks:
                pairs = dict(re.findall(r'<td>(.*?)</td>\s*<td>(.*?)</td>', desc, re.DOTALL))
                if pairs:
                    records.append(pairs)
    except Exception as e:
        print(f"  Warning reading KMZ {kmz_path}: {e}")
    return records

# Group files by (Phase, StateCode)
files = glob.glob(os.path.join(RAW_DIR, "dwa_*.*"))
groups = {}
for f in files:
    fname = os.path.basename(f)
    m = re.match(r'(dwa_ph[12]_[a-z0-9_]+?)(?:_shp|_geojson)?\.(zip|kmz)', fname, re.IGNORECASE)
    if m:
        grp_key = m.group(1).lower()
        if grp_key not in groups:
            groups[grp_key] = []
        groups[grp_key].append(f)

print(f"Found {len(groups)} distinct State/Phase groups across 4th Batch raw files.")

report_rows = []
all_master_records = []

COLUMN_MAPPING = {
    'uuid': 'UUID',
    'state': 'State_Code',
    'stcode': 'State_Census_Code',
    'state_name': 'State_Name',
    'district': 'District',
    'dtcode': 'District_Code',
    'subdistric': 'Subdistrict',
    'subdistrict': 'Subdistrict',
    'sdcode': 'Subdistrict_Code',
    'village': 'Village',
    'vlcode': 'Village_Code',
    'latitude': 'Latitude',
    'longitude': 'Longitude',
    'river': 'River',
    'basin': 'Basin_Code',
    'basin_name': 'River_Basin',
    'subbasin': 'Subbasin_Code',
    'sub_basin': 'Sub_Basin',
    'wshed': 'Watershed_Code',
    'wb_type': 'Waterbody_Type',
    'waterbody_type': 'Waterbody_Category_Code',
    'ownership': 'Ownership',
    'rural_urba': 'Rural_Urban',
    'rural_urban': 'Rural_Urban',
    'nearest_se': 'Nearest_Settlement',
    'nearest_settlement_name': 'Nearest_Settlement',
    'water_spre': 'Water_Spread_Area',
    'water_spread_area': 'Water_Spread_Area',
    'storage_ca': 'Storage_Capacity',
    'storage_capacity': 'Storage_Capacity',
    'gis_area': 'GIS_Area_ha',
    'apr_22': 'Water_Presence_Apr22',
    'nov_22': 'Water_Presence_Nov22',
    'apr_23': 'Water_Presence_Apr23',
    'nov_23': 'Water_Presence_Nov23',
    'shape_leng': 'Perimeter_Length_m',
    'shape_length': 'Perimeter_Length_m',
    'shape_area': 'Shape_Area_sqm',
    'ds_name': 'Dataset_Name',
    'src_agency': 'Source_Agency'
}

for grp_key in sorted(groups.keys()):
    grp_files = groups[grp_key]
    print(f"\nProcessing Group: {grp_key} ({len(grp_files)} files)")
    
    # Prefer _shp.zip, then _geojson.zip, then .kmz
    shp_zips = [f for f in grp_files if f.endswith('_shp.zip')]
    kmz_files = [f for f in grp_files if f.endswith('.kmz')]
    
    records = []
    source_used = ""
    if shp_zips:
        source_used = os.path.basename(shp_zips[0])
        records = parse_dbf_zip(shp_zips[0])
    elif kmz_files:
        source_used = os.path.basename(kmz_files[0])
        records = parse_kmz(kmz_files[0])
    
    if not records:
        print(f"  -> Warning: No tabular records extracted for {grp_key}")
        continue
    
    df = pd.DataFrame(records)
    rows_before = len(df)
    
    # Normalize column names
    col_map = {}
    for c in df.columns:
        c_low = c.lower().strip()
        if c_low in COLUMN_MAPPING:
            col_map[c] = COLUMN_MAPPING[c_low]
    
    df = df.rename(columns=col_map)
    
    # Standardize phase and key columns
    phase = "Phase 1" if "ph1" in grp_key else "Phase 2"
    df['Phase'] = phase
    
    # Remove duplicate columns if any
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Strip newlines and extra whitespace from string columns
    for str_col in df.select_dtypes(include=['object', 'string']).columns:
        df[str_col] = df[str_col].astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
    
    # Standardized state name
    if 'State_Name' in df.columns:
        df['State_Name'] = df['State_Name'].str.title()
    
    # Numeric conversions
    for num_col in ['Latitude', 'Longitude', 'GIS_Area_ha', 'Shape_Area_sqm', 'Perimeter_Length_m']:
        if num_col in df.columns:
            col_data = df[num_col]
            if isinstance(col_data, pd.DataFrame):
                col_data = col_data.iloc[:, 0]
            df[num_col] = pd.to_numeric(col_data, errors='coerce')
    
    # Remove exact duplicate rows
    df = df.drop_duplicates()
    rows_after = len(df)
    
    # Select clean column subset if available
    desired_order = ['Phase', 'State_Name', 'State_Code', 'District', 'Subdistrict', 'Village',
                     'UUID', 'Latitude', 'Longitude', 'River_Basin', 'Sub_Basin', 'River',
                     'Waterbody_Type', 'GIS_Area_ha', 'Shape_Area_sqm', 'Perimeter_Length_m',
                     'Water_Presence_Apr22', 'Water_Presence_Nov22', 'Water_Presence_Apr23', 'Water_Presence_Nov23',
                     'Nearest_Settlement', 'Source_Agency']
    
    final_cols = [c for c in desired_order if c in df.columns]
    # Add any remaining columns
    other_cols = [c for c in df.columns if c not in final_cols]
    df = df[final_cols + other_cols]
    
    # Save as CSV & Excel (.xlsx)
    csv_filename = f"cleaned_{grp_key}.csv"
    xlsx_filename = f"cleaned_{grp_key}.xlsx"
    
    csv_path = os.path.join(CLEANED_DIR, csv_filename)
    xlsx_path = os.path.join(CLEANED_DIR, xlsx_filename)
    
    df.to_csv(csv_path, index=False)
    
    # Export to Excel (up to 1,000,000 rows limit)
    try:
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        xlsx_size_mb = os.path.getsize(xlsx_path) / (1024 * 1024)
    except Exception as ex:
        print(f"  Warning exporting Excel for {grp_key}: {ex}")
        xlsx_size_mb = 0.0
    
    csv_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    print(f"  -> Extracted {rows_after} records ({source_used}) | CSV: {csv_size_mb:.2f} MB | Excel: {xlsx_size_mb:.2f} MB")
    
    report_rows.append({
        'Group_Key': grp_key,
        'Phase': phase,
        'Source_File': source_used,
        'Total_Waterbodies': rows_after,
        'Clean_CSV': csv_filename,
        'CSV_Size_MB': round(csv_size_mb, 2),
        'Clean_Excel': xlsx_filename,
        'Excel_Size_MB': round(xlsx_size_mb, 2)
    })
    
    all_master_records.append(df)

# Save Master All-India Waterbody Atlas Excel & CSV
if all_master_records:
    print("\n" + "=" * 100)
    print("CREATING MASTER ALL-INDIA WATERBODY ATLAS (EXCEL & CSV)...")
    print("=" * 100)
    master_df = pd.concat(all_master_records, ignore_index=True)
    master_df = master_df.drop_duplicates()
    
    master_csv = os.path.join(CLEANED_DIR, "cleaned_dwa_master_all_india_waterbodies.csv")
    master_df.to_csv(master_csv, index=False)
    print(f"  -> Master CSV Saved: {os.path.basename(master_csv)} ({len(master_df)} waterbodies, {os.path.getsize(master_csv)/(1024*1024):.2f} MB)")
    
    # If master_df <= 1,000,000 rows, export full Master Excel (.xlsx)
    if len(master_df) <= 1000000:
        master_xlsx = os.path.join(CLEANED_DIR, "cleaned_dwa_master_all_india_waterbodies.xlsx")
        try:
            master_df.to_excel(master_xlsx, index=False, engine='openpyxl')
            print(f"  -> Master Excel Saved: {os.path.basename(master_xlsx)} ({os.path.getsize(master_xlsx)/(1024*1024):.2f} MB)")
        except Exception as ex:
            print(f"  Warning exporting Master Excel: {ex}")

# Save Report
report_df = pd.DataFrame(report_rows)
report_csv = os.path.join(REPORTS_DIR, "stage3_fourth_batch_report.csv")
report_df.to_csv(report_csv, index=False)
print(f"\nStage 4 Cleaning Report saved to: {report_csv}")

print("\n" + "=" * 100)
print("STAGE 4 CLEANING AND EXCEL CONVERSION COMPLETE!")
print("=" * 100)
