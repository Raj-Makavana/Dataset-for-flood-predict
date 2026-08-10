"""
Environment Verification Script for Flood Risk Prediction Project
Checks installed libraries and system setup.
"""
import sys
import importlib

packages = [
    ("pandas", "Data manipulation & tabular datasets"),
    ("numpy", "Numerical calculations & array operations"),
    ("scipy", "Scientific & statistical utilities"),
    ("sklearn", "Machine learning algorithms (Scikit-Learn)"),
    ("xgboost", "Extreme Gradient Boosting model"),
    ("joblib", "Model serialization & saving"),
    ("matplotlib", "2D Data plotting & charting"),
    ("seaborn", "Statistical data visualization"),
    ("shapely", "Geometric objects & spatial math"),
    ("geopandas", "Geospatial vector data processing"),
    ("folium", "Interactive web map generation"),
    ("fastapi", "Backend REST API framework"),
    ("uvicorn", "ASGI server for web backend"),
    ("requests", "HTTP library for live weather fetching"),
]

print("=" * 60)
print(f"Python Version : {sys.version.split()[0]}")
print(f"Executable     : {sys.executable}")
print("=" * 60)
print("Checking Installed Project Libraries:\n")

all_ok = True
for pkg, desc in packages:
    try:
        mod = importlib.import_module(pkg)
        version = getattr(mod, "__version__", "Available")
        print(f"  [OK] {pkg:<12} (v{version:<10}) - {desc}")
    except ImportError as e:
        print(f"  [FAIL] {pkg:<10} - NOT INSTALLED ({e})")
        all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("SUCCESS: All required libraries are installed and ready!")
else:
    print("WARNING: Some libraries are missing. Please run 'pip install -r requirements.txt'")
print("=" * 60)
