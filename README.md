# KisanSaathi (starter)

FastAPI backend + Streamlit frontend. Weather, crop recommendation, disease photo check, and AI advisory (powered by Google Gemini).

## Setup (once)
```bash
python -m venv venv
# Windows: venv\Scripts\activate      Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env backend/.env     # then edit backend/.env and add your GEMINI_API_KEY (from aistudio.google.com)
```

## Train the crop model (once)
1. Download the Kaggle "Crop Recommendation Dataset" and save the CSV as `backend/Crop_recommendation.csv`
2. `cd backend && python train_crop_model.py`

## Run (two terminals)
```bash
# Terminal 1
cd backend
uvicorn main:app --reload --port 8000
# open http://localhost:8000/docs to test every endpoint

# Terminal 2
cd frontend
streamlit run app.py
```

## Test in this order
1. `/health` shows both flags true
2. `/weather?lat=28.61&lon=77.21`
3. `/recommend` with the sample values
4. `/diagnose` with 10 REAL phone photos (not only dataset images)
5. `/advisory`
6. The Streamlit page
