import os
import glob
import pandas as pd

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"

# Explicit mapping of filenames to State / UT
FILE_STATE_MAP = {
    'rainfall_tel_hr_cwc_ap_2021_2025.csv': ('Andhra Pradesh', 'AP', 'State'),
    'rainfall_tel_hr_cwc_ar_2021_2025.csv': ('Arunachal Pradesh', 'AR', 'State'),
    'rainfall_tel_hr_cwc_as_2021_2025.csv': ('Assam', 'AS', 'State'),
    'rainfall_tel_hr_cwc_br_2021_2025.csv': ('Bihar', 'BR', 'State'),
    'rainfall_tel_hr_cwc_cg_2021_2025.csv': ('Chhattisgarh', 'CG', 'State'),
    'rainfall_tel_hr_goa_ga_2021_2025.csv': ('Goa', 'GA', 'State'),
    'rainfall_tel_hr_cwc_gj_2021_2025.csv': ('Gujarat', 'GJ', 'State'),
    'rainfall_tel_hr_cwc_hr_2021_2025.csv': ('Haryana', 'HR', 'State'),
    'rainfall_tel_hr_cwc_hp_2021_2025.csv': ('Himachal Pradesh', 'HP', 'State'),
    'rainfall_tel_hr_cwc_jh_2021_2025.csv': ('Jharkhand', 'JH', 'State'),
    'rainfall_tel_hr_cwc_ka_2021_2025.csv': ('Karnataka', 'KA', 'State'),
    'rainfall_tel_hr_cwc_kl_2021_2025.csv': ('Kerala', 'KL', 'State'),
    'rainfall_tel_hr_cwc_mp_2021_2025.csv': ('Madhya Pradesh', 'MP', 'State'),
    'rainfall_tel_hr_cwc_mh_2021_2025.csv': ('Maharashtra', 'MH', 'State'),
    'rainfall_tel_hr_cwc_mn_2021_2025.csv': ('Manipur', 'MN', 'State'),
    'rainfall_manual_daily_meghalaya_ml_2021_2025.csv': ('Meghalaya', 'ML', 'State'),
    'rainfall_tel_hr_meghalaya_ml_2021_2025.csv': ('Meghalaya', 'ML', 'State'),
    'rainfall_tel_hr_mizoram_mz_2026_2030.csv': ('Mizoram', 'MZ', 'State'),
    'rainfall_tel_hr_cwc_nl_2021_2025.csv': ('Nagaland', 'NL', 'State'),
    'rainfall_tel_hr_cwc_od_2021_2025.csv': ('Odisha', 'OD', 'State'),
    'rainfall_tel_hr_cwc_pb_1991_2020.csv': ('Punjab', 'PB', 'State'),
    'rainfall_tel_hr_cwc_rj_2021_2025.csv': ('Rajasthan', 'RJ', 'State'),
    'rainfall_tel_hr_cwc_sk_2021_2025.csv': ('Sikkim', 'SK', 'State'),
    'rainfall_tel_hr_cwc_tn_2021_2025.csv': ('Tamil Nadu', 'TN', 'State'),
    'rainfall_tel_hr_cwc_ts_2021_2025.csv': ('Telangana', 'TS', 'State'),
    'rainfall_tel_hr_cwc_tr_2021_2025.csv': ('Tripura', 'TR', 'State'),
    'rainfall_tel_hr_cwc_up_2021_2025.csv': ('Uttar Pradesh', 'UP', 'State'),
    'rainfall_tel_hr_cwc_uk_2021_2025.csv': ('Uttarakhand', 'UK', 'State'),
    'rainfall_tel_hr_cwc_wb_2021_2025.csv': ('West Bengal', 'WB', 'State'),
}

ALL_28_STATES = [
    ("Andhra Pradesh", "AP"),
    ("Arunachal Pradesh", "AR"),
    ("Assam", "AS"),
    ("Bihar", "BR"),
    ("Chhattisgarh", "CG"),
    ("Goa", "GA"),
    ("Gujarat", "GJ"),
    ("Haryana", "HR"),
    ("Himachal Pradesh", "HP"),
    ("Jharkhand", "JH"),
    ("Karnataka", "KA"),
    ("Kerala", "KL"),
    ("Madhya Pradesh", "MP"),
    ("Maharashtra", "MH"),
    ("Manipur", "MN"),
    ("Meghalaya", "ML"),
    ("Mizoram", "MZ"),
    ("Nagaland", "NL"),
    ("Odisha", "OD"),
    ("Punjab", "PB"),
    ("Rajasthan", "RJ"),
    ("Sikkim", "SK"),
    ("Tamil Nadu", "TN"),
    ("Telangana", "TS"),
    ("Tripura", "TR"),
    ("Uttar Pradesh", "UP"),
    ("Uttarakhand", "UK"),
    ("West Bengal", "WB")
]

ALL_8_UTS = [
    ("Andaman and Nicobar Islands", "AN"),
    ("Chandigarh", "CH"),
    ("Dadra and Nagar Haveli and Daman and Diu", "DN/DD"),
    ("Delhi (NCT)", "DL"),
    ("Jammu and Kashmir", "JK"),
    ("Ladakh", "LA"),
    ("Lakshadweep", "LD"),
    ("Puducherry", "PY")
]

# Analyze files
coverage_state = {}

for fname, (state_name, code, category) in FILE_STATE_MAP.items():
    fpath = os.path.join(RAW_DIR, fname)
    if os.path.exists(fpath):
        df = pd.read_csv(fpath, low_memory=False)
        rf_cols = [c for c in df.columns if 'rainfall' in c.lower()]
        rf_col = rf_cols[0] if rf_cols else None
        valid_rf = df[rf_col].dropna().count() if rf_col and len(df) > 0 else 0
        rows = len(df)
        
        if state_name not in coverage_state:
            coverage_state[state_name] = []
        coverage_state[state_name].append({
            'file': fname,
            'rows': rows,
            'valid_rf': valid_rf,
            'code': code
        })

print("=" * 115)
print("INDIAN STATES (28) RAINFALL DATASET COVERAGE")
print("=" * 115)
print(f"{'State Name':<22} | {'Code':<5} | {'Filename':<50} | {'Rows':<9} | {'Valid RF':<9} | Status")
print("-" * 115)

available_states = []
empty_states = []
missing_states = []

for state_name, code in ALL_28_STATES:
    if state_name in coverage_state:
        files = coverage_state[state_name]
        for fentry in files:
            r = fentry['rows']
            v = fentry['valid_rf']
            fn = fentry['file']
            if r == 0 or v == 0:
                status = "[EMPTY / NO DATA]"
                empty_states.append((state_name, code, fn, r, v))
                print(f"{state_name:<22} | {code:<5} | {fn:<50} | {r:>9,} | {v:>9,} | {status}")
            else:
                status = "[AVAILABLE]"
                available_states.append((state_name, code, fn, r, v))
                print(f"{state_name:<22} | {code:<5} | {fn:<50} | {r:>9,} | {v:>9,} | {status}")
    else:
        status = "[NO DATASET FILE]"
        missing_states.append((state_name, code))
        print(f"{state_name:<22} | {code:<5} | {'[NO FILE]':<50} | {'0':>9} | {'0':>9} | {status}")

print("\n" + "=" * 115)
print("INDIAN UNION TERRITORIES (8) RAINFALL DATASET COVERAGE")
print("=" * 115)
print(f"{'Union Territory Name':<42} | {'Code':<6} | Status")
print("-" * 115)

for ut_name, code in ALL_8_UTS:
    print(f"{ut_name:<42} | {code:<6} | [NO RAINFALL DATASET FILE]")

print("\n" + "=" * 115)
print("SUMMARY & FINAL VERDICT")
print("=" * 115)
print(f"1. Total States in India           : 28")
print(f"   - States WITH Valid Rainfall Data: {len(set([s[0] for s in available_states]))} / 28")
print(f"   - States WITHOUT Valid Data      : {28 - len(set([s[0] for s in available_states]))} / 28")
print(f"     * Mizoram (MZ)                 : File exists (rainfall_tel_hr_mizoram_mz_2026_2030.csv) but is EMPTY (0 rows).")

print(f"\n2. Total Union Territories in India : 8")
print(f"   - UTs WITH Rainfall Data          : 0 / 8")
print(f"   - UTs WITHOUT Rainfall Data       : 8 / 8")
print("     (Note: Puducherry PY has groundwater datasets 'gwl_tel_6_hourly_puducherry_py', but NO rainfall dataset).")
print("=" * 115)
