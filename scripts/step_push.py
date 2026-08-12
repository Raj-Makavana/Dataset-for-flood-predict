import os
import glob
import subprocess

print("=" * 90)
print("INCREMENTAL STEP PUSH TO GITHUB TO PREVENT TIMEOUTS...")
print("=" * 90)

# Step 1: Add scripts & reports
print("\nStep 1: Pushing scripts & reports...")
subprocess.run("git add scripts/ reports/", shell=True)
subprocess.run('git commit -m "Add Seventh Batch processing scripts and report"', shell=True)
subprocess.run("git push origin main", shell=True)

# Step 2: Push data/cleaned in chunks
print("\nStep 2: Pushing data/cleaned/ in chunks...")
cleaned_files = sorted(glob.glob("data/cleaned/*.*"))
chunk = []
chunk_size = 0
chunk_idx = 1

for f in cleaned_files:
    sz = os.path.getsize(f)
    chunk.append(f)
    chunk_size += sz
    # If chunk >= 40 MB, commit and push
    if chunk_size >= 40 * 1024 * 1024:
        print(f"\nCommitting cleaned batch {chunk_idx} ({chunk_size/(1024*1024):.2f} MB)...")
        cmd_add = "git add " + " ".join([f'"{c}"' for c in chunk])
        subprocess.run(cmd_add, shell=True)
        subprocess.run(f'git commit -m "Add Seventh Batch cleaned datasets part {chunk_idx}"', shell=True)
        subprocess.run("git push origin main", shell=True)
        chunk = []
        chunk_size = 0
        chunk_idx += 1

if chunk:
    print(f"\nCommitting final cleaned batch {chunk_idx} ({chunk_size/(1024*1024):.2f} MB)...")
    cmd_add = "git add " + " ".join([f'"{c}"' for c in chunk])
    subprocess.run(cmd_add, shell=True)
    subprocess.run(f'git commit -m "Add Seventh Batch cleaned datasets part {chunk_idx}"', shell=True)
    subprocess.run("git push origin main", shell=True)

# Step 3: Push data/raw in chunks
print("\nStep 3: Pushing data/raw/ in chunks...")
raw_files = sorted(glob.glob("data/raw/*.*"))
chunk = []
chunk_size = 0
chunk_idx = 1

for f in raw_files:
    sz = os.path.getsize(f)
    chunk.append(f)
    chunk_size += sz
    if chunk_size >= 40 * 1024 * 1024:
        print(f"\nCommitting raw batch {chunk_idx} ({chunk_size/(1024*1024):.2f} MB)...")
        cmd_add = "git add " + " ".join([f'"{c}"' for c in chunk])
        subprocess.run(cmd_add, shell=True)
        subprocess.run(f'git commit -m "Add Seventh Batch raw datasets part {chunk_idx}"', shell=True)
        subprocess.run("git push origin main", shell=True)
        chunk = []
        chunk_size = 0
        chunk_idx += 1

if chunk:
    print(f"\nCommitting final raw batch {chunk_idx} ({chunk_size/(1024*1024):.2f} MB)...")
    cmd_add = "git add " + " ".join([f'"{c}"' for c in chunk])
    subprocess.run(cmd_add, shell=True)
    subprocess.run(f'git commit -m "Add Seventh Batch raw datasets part {chunk_idx}"', shell=True)
    subprocess.run("git push origin main", shell=True)

print("\n" + "=" * 90)
print("ALL SEVENTH BATCH DATASETS SUCCESSFULLY PUSHED TO GITHUB REPOSITORY!")
print("=" * 90)
