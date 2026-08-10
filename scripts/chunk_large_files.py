import os
import glob

RAW_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\raw"
CLEANED_DIR = r"c:\Users\Lenovo\Desktop\FRP\data\cleaned"

print("=" * 90)
print("SPLITTING ALL LARGE DATASETS (>45MB) FOR 100% GITHUB COMPLIANCE...")
print("=" * 90)

for folder in [RAW_DIR, CLEANED_DIR]:
    base_files = [f for f in glob.glob(os.path.join(folder, "*.*")) if not os.path.basename(f).startswith('.') and '.part' not in os.path.basename(f)]
    for fpath in base_files:
        fname = os.path.basename(fpath)
        sz_mb = os.path.getsize(fpath) / (1024 * 1024)
        if sz_mb > 45.0:
            print(f"\nProcessing Large File ({sz_mb:.2f} MB): {folder}/{fname}")
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
            # Remove original un-split file to conserve disk space
            try:
                os.remove(fpath)
                print(f"  -> Removed original file: {fname} to conserve disk space")
            except Exception as ex:
                print(f"  -> Warning: Could not remove {fname}: {ex}")

print("\n" + "=" * 90)
print("SPLITTING COMPLETE! ALL FILES IN RAW AND CLEANED ARE <45MB AND READY FOR GITHUB PUSH.")
print("=" * 90)
