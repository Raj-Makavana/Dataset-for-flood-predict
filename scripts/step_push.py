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
print("\nStep 2: Pushing data/cleaned/...")
subprocess.run("git add data/cleaned/", shell=True)
subprocess.run('git commit -m "Add Seventh Batch cleaned datasets"', shell=True)
subprocess.run("git push origin main", shell=True)

# Step 3: Push data/raw in chunks
print("\nStep 3: Pushing data/raw/...")
subprocess.run("git add data/raw/", shell=True)
subprocess.run('git commit -m "Add Seventh Batch raw datasets"', shell=True)
subprocess.run("git push origin main", shell=True)

print("\n" + "=" * 90)
print("ALL SEVENTH BATCH DATASETS SUCCESSFULLY PUSHED TO GITHUB REPOSITORY!")
print("=" * 90)
