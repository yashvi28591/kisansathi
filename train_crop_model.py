"""
Train the crop recommendation model.

1. Download the Kaggle dataset "Crop Recommendation Dataset" (Atharva Ingle)
   and save the CSV as backend/Crop_recommendation.csv
   Columns needed: N, P, K, temperature, humidity, ph, rainfall, label
2. Run:  python train_crop_model.py
3. It creates backend/crop_model.joblib which main.py loads.
"""
from pathlib import Path
import sys

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

HERE = Path(__file__).parent
CSV = HERE / "Crop_recommendation.csv"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

if not CSV.exists():
    sys.exit(f"Dataset not found at {CSV}. Download it from Kaggle first (see top of this file).")

df = pd.read_csv(CSV)
missing = [c for c in FEATURES + ["label"] if c not in df.columns]
if missing:
    sys.exit(f"CSV is missing columns: {missing}. Found: {list(df.columns)}")

X, y = df[FEATURES], df["label"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
acc = accuracy_score(y_test, model.predict(X_test))
print(f"Test accuracy: {acc:.3f}")

joblib.dump({"model": model, "features": FEATURES}, HERE / "crop_model.joblib")
print("Saved crop_model.joblib")
