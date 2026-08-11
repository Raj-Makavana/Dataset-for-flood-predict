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
print("STAGE 5: DECOMPRESSING, CLEANING & CONVERTING 5TH BATCH DATASETS TO CSV & EXCEL (.xlsx)")
print("Processing Dams Master Infrastructure & ISRO SAC / NWIC Waterbody & Wetland Datasets")
print("=" * 100)

def parse_shp_zip(zip_path):
    records = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            shp_files = [f for f in z.namelist() if f.lower().endswith('.shp')]
            if not shp_files:
                return records
            tmpdir = tempfile.mkdtemp()
            z.extractall(tmpdir)
            shp_p = os.path.join(tmpdir, shp_files[0])
            # Try utf-8 then latin1
            sf = None
            for enc in ['utf-8', 'latin1', 'cp1252']:
                try:
                    sf = shapefile.Reader(shp_p, encoding=enc)
                    recs = sf.records()
                    fields = [f[0] for f in sf.fields[1:]]
                    for r in recs:
                        records.append(dict(zip(fields, r)))
                    break
                except Exception:
                    continue
    except Exception as e:
        print(f"  Warning reading SHP ZIP {zip_path}: {e}")
    return records

def parse_kml_or_kmz(fpath):
    records = []
    try:
        content = ""
        if fpath.lower().endswith('.kmz'):
            with zipfile.ZipFile(fpath, 'r') as z:
                kml_files = [f for f in z.namelist() if f.lower().endswith('.kml')]
                if kml_files:
                    content = z.read(kml_files[0]).decode('utf-8', errors='ignore')
        else:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        if not content:
            return records

        for m in re.finditer(r'<Placemark.*?>.*?</Placemark>', content, re.DOTALL):
            pm_str = m.group(0)
            pm_name = re.search(r'<name>(.*?)</name>', pm_str)
            name_val = pm_name.group(1).strip() if pm_name else ''

            # 1. SimpleData tags
            sdata = dict(re.findall(r'<SimpleData name="([^"]+)">(.*?)</SimpleData>', pm_str))
            if name_val and 'Name' not in sdata and 'name' not in sdata:
                sdata['Name'] = name_val

            # 2. Description <td> HTML table tags
            desc = re.search(r'<description>(.*?)</description>', pm_str, re.DOTALL)
            if desc:
                pairs = dict(re.findall(r'<td>(.*?)</td>\s*<td>(.*?)</td>', desc.group(1), re.DOTALL))
                sdata.update(pairs)

            if sdata:
                records.append(sdata)
    except Exception as e:
        print(f"  Warning reading KML/KMZ {fpath}: {e}")
    return records

# ---------------------------------------------------------
# 1. PROCESS DAMS MASTER DATASET (dam.zip / dam.kml)
# ---------------------------------------------------------
print("\n[1/2] Processing Master Dams Infrastructure Dataset...")
dam_files = [f for f in glob.glob(os.path.join(RAW_DIR, "dam.*")) if not os.path.basename(f).startswith('.')]
dam_records = []
if any(f.endswith('.zip') for f in dam_files):
    zip_f = [f for f in dam_files if f.endswith('.zip')][0]
    dam_records = parse_shp_zip(zip_f)
elif any(f.endswith('.kml') for f in dam_files):
    kml_f = [f for f in dam_files if f.endswith('.kml')][0]
    dam_records = parse_kml_or_kmz(kml_f)

if dam_records:
    dam_df = pd.DataFrame(dam_records)
    dam_df = dam_df.loc[:, ~dam_df.columns.duplicated()].copy()
    
    # Strip newlines from string columns
    for str_col in dam_df.select_dtypes(include=['object', 'string']).columns:
        dam_df[str_col] = dam_df[str_col].astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
    
    # Standardize Column Names for Dams
    DAM_COL_MAP = {
        'PIC': 'Dam_PIC_ID',
        'dm_name': 'Dam_Name',
        'state': 'State_Name',
        'district': 'District',
        'river': 'River',
        'incharge': 'Managing_Agency',
        'ht_found': 'Dam_Height_m',
        'cmp_year': 'Completion_Year',
        'basin': 'River_Basin',
        'mx_wt_lel': 'Max_Water_Level_m',
        'frl': 'Full_Reservoir_Level_m',
        'gs_st_cap': 'Gross_Storage_Capacity_mcm',
        'ds_sp_cap': 'Design_Spillway_Capacity',
        'dm_length': 'Dam_Length_m',
        'dm_type': 'Dam_Structure_Type',
        'purpose': 'Primary_Purpose',
        'latitude': 'Latitude',
        'longitude': 'Longitude'
    }
    dam_df = dam_df.rename(columns={k: v for k, v in DAM_COL_MAP.items() if k in dam_df.columns})
    dam_df = dam_df.drop_duplicates()
    
    # Export Dam Master CSV & Excel
    dam_csv = os.path.join(CLEANED_DIR, "cleaned_dam_master_india.csv")
    dam_xlsx = os.path.join(CLEANED_DIR, "cleaned_dam_master_india.xlsx")
    dam_df.to_csv(dam_csv, index=False)
    try:
        dam_df.to_excel(dam_xlsx, index=False, engine='openpyxl')
    except Exception as ex:
        print(f"  Warning exporting Dam Excel: {ex}")
    
    print(f"  -> Dam Master Dataset Cleaned: {len(dam_df)} dams | CSV: {os.path.getsize(dam_csv)/(1024*1024):.2f} MB | Excel: {os.path.getsize(dam_xlsx)/(1024*1024):.2f} MB")

# ---------------------------------------------------------
# 2. PROCESS WATERBODY & WETLAND ATLAS DATASETS (wb_*)
# ---------------------------------------------------------
print("\n[2/2] Processing Waterbody & Wetland Atlas Datasets (wb_*)...")
wb_files = [f for f in glob.glob(os.path.join(RAW_DIR, "wb_*.*")) if not os.path.basename(f).startswith('.')]

# Group wb files by State/UT tag
wb_groups = {}
for f in wb_files:
    fname = os.path.basename(f)
    m = re.match(r'(wb_[a-z0-9_]+?)(?:_shp)?\.(zip|kmz|kml)', fname, re.IGNORECASE)
    if m:
        grp_key = m.group(1).lower().replace('_shp', '')
        if grp_key not in wb_groups:
            wb_groups[grp_key] = []
        wb_groups[grp_key].append(f)

print(f"Found {len(wb_groups)} Waterbody State/UT groups across 5th Batch raw files.")

WB_COL_MAPPING = {
    'uuid': 'UUID',
    'wetcode': 'Wetland_Code',
    'wetname': 'Wetland_Name',
    'waterbody_name': 'Waterbody_Name',
    'Name': 'Waterbody_Name',
    'name': 'Waterbody_Name',
    'state': 'State_Code',
    'state_name': 'State_Name',
    'district': 'District',
    'subdistric': 'Subdistrict',
    'subdistrict': 'Subdistrict',
    'village': 'Village',
    'lat': 'Latitude',
    'latitude': 'Latitude',
    'long': 'Longitude',
    'longitude': 'Longitude',
    'river': 'River',
    'basin_name': 'River_Basin',
    'sub_basin': 'Sub_Basin',
    'level_i': 'Level_I_Category',
    'level_ii': 'Level_II_Category',
    'wb_type': 'Waterbody_Type',
    'l4type': 'Waterbody_Type',
    'waterbody_type': 'Waterbody_Type',
    'aqveg': 'Aquatic_Vegetation',
    'turbidity': 'Turbidity',
    'area_ha': 'Area_ha',
    'gis_area': 'Area_ha',
    'water_spread_area': 'Area_ha',
    'shape_leng': 'Perimeter_Length_m',
    'shape_length': 'Perimeter_Length_m',
    'shape_area': 'Shape_Area_sqm',
    'ds_name': 'Dataset_Name',
    'src_agency': 'Source_Agency'
}

report_rows = []
all_master_records = []

for grp_key in sorted(wb_groups.keys()):
    grp_files = wb_groups[grp_key]
    
    # Priority: _shp.zip > .kmz > .kml
    shp_zips = [f for f in grp_files if f.endswith('_shp.zip')]
    kmz_files = [f for f in grp_files if f.endswith('.kmz')]
    kml_files = [f for f in grp_files if f.endswith('.kml')]
    
    records = []
    source_used = ""
    if shp_zips:
        source_used = os.path.basename(shp_zips[0])
        records = parse_shp_zip(shp_zips[0])
    elif kmz_files:
        source_used = os.path.basename(kmz_files[0])
        records = parse_kml_or_kmz(kmz_files[0])
    elif kml_files:
        source_used = os.path.basename(kml_files[0])
        records = parse_kml_or_kmz(kml_files[0])
        
    if not records:
        print(f"  -> Warning: No records extracted for {grp_key}")
        continue
    
    df = pd.DataFrame(records)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Clean string column newlines
    for str_col in df.select_dtypes(include=['object', 'string']).columns:
        df[str_col] = df[str_col].astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
        
    # Column mapping
    col_map = {}
    for c in df.columns:
        c_low = c.strip().lower()
        for k_src, k_tgt in WB_COL_MAPPING.items():
            if c_low == k_src.lower():
                col_map[c] = k_tgt
                break
    df = df.rename(columns=col_map)
    df = df.drop_duplicates()
    
    # Convert numeric columns
    for num_col in ['Latitude', 'Longitude', 'Area_ha', 'Shape_Area_sqm', 'Perimeter_Length_m']:
        if num_col in df.columns:
            col_data = df[num_col]
            if isinstance(col_data, pd.DataFrame):
                col_data = col_data.iloc[:, 0]
            df[num_col] = pd.to_numeric(col_data, errors='coerce')
            
    # Export State/UT Cleaned CSV & Excel
    csv_name = f"cleaned_{grp_key}.csv"
    xlsx_name = f"cleaned_{grp_key}.xlsx"
    csv_p = os.path.join(CLEANED_DIR, csv_name)
    xlsx_p = os.path.join(CLEANED_DIR, xlsx_name)
    
    df.to_csv(csv_p, index=False)
    xlsx_sz_mb = 0.0
    try:
        df.to_excel(xlsx_p, index=False, engine='openpyxl')
        xlsx_sz_mb = os.path.getsize(xlsx_p) / (1024 * 1024)
    except Exception as ex:
        print(f"  Warning exporting Excel for {grp_key}: {ex}")
        
    csv_sz_mb = os.path.getsize(csv_p) / (1024 * 1024)
    print(f"  -> Cleaned {grp_key}: {len(df)} records ({source_used}) | CSV: {csv_sz_mb:.2f} MB | Excel: {xlsx_sz_mb:.2f} MB")
    
    report_rows.append({
        'Group_Key': grp_key,
        'Source_File': source_used,
        'Total_Records': len(df),
        'Clean_CSV': csv_name,
        'CSV_Size_MB': round(csv_sz_mb, 2),
        'Clean_Excel': xlsx_name,
        'Excel_Size_MB': round(xlsx_sz_mb, 2)
    })
    
    all_master_records.append(df)

# Export Master All-India 5th Batch Waterbodies CSV & Excel
if all_master_records:
    print("\n" + "=" * 100)
    print("CREATING MASTER ALL-INDIA 5TH BATCH WATERBODY ATLAS (CSV & EXCEL)...")
    print("=" * 100)
    master_wb = pd.concat(all_master_records, ignore_index=True).drop_duplicates()
    master_csv = os.path.join(CLEANED_DIR, "cleaned_wb_master_all_india_waterbodies.csv")
    master_xlsx = os.path.join(CLEANED_DIR, "cleaned_wb_master_all_india_waterbodies.xlsx")
    
    master_wb.to_csv(master_csv, index=False)
    print(f"  -> Master Waterbodies CSV Saved: {os.path.basename(master_csv)} ({len(master_wb)} records, {os.path.getsize(master_csv)/(1024*1024):.2f} MB)")
    
    if len(master_wb) <= 1000000:
        try:
            master_wb.to_excel(master_xlsx, index=False, engine='openpyxl')
            print(f"  -> Master Waterbodies Excel Saved: {os.path.basename(master_xlsx)} ({os.path.getsize(master_xlsx)/(1024*1024):.2f} MB)")
        except Exception as ex:
            print(f"  Warning exporting Master Excel: {ex}")

# Save Cleaning Report
report_df = pd.DataFrame(report_rows)
report_csv = os.path.join(REPORTS_DIR, "stage3_fifth_batch_report.csv")
report_df.to_csv(report_csv, index=False)
print(f"\nStage 5 Cleaning Report saved to: {report_csv}")

print("\n" + "=" * 100)
print("STAGE 5 CLEANING & EXCEL CONVERSION COMPLETE!")
print("=" * 100)
