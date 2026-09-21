"""KisanSaathi backend: the single place where all pieces connect."""
import io
import json
import os
import re
from pathlib import Path
from typing import Optional
from profit import router as profit_router

import joblib
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
import time


load_dotenv()

HERE = Path(__file__).parent
MODEL_PATH = HERE / "crop_model.joblib"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(title="KisanSaathi API", version="0.1.0")
app.include_router(profit_router)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ---------------------------------------------------------------- helpers
_crop_bundle = None


def get_crop_bundle():
    global _crop_bundle
    if _crop_bundle is None:
        if not MODEL_PATH.exists():
            raise HTTPException(
                503,
                "Crop model not trained yet. Run: python train_crop_model.py (inside backend/)",
            )
        _crop_bundle = joblib.load(MODEL_PATH)
    return _crop_bundle
def call_ai(
    prompt: str,
    system: str,
    image_bytes: Optional[bytes] = None,
    max_tokens: int = 2000,
    json_mode: bool = False,
) -> str:
    """The ONLY function that talks to Gemini. Retries when Google is busy."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(503, "GEMINI_API_KEY is not set. Put it in .env")
    from google import genai
    from google.genai import types

    contents = []
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
    contents.append(prompt)
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        response_mime_type="application/json" if json_mode else None,
    )

    client = genai.Client(api_key=key)
    models = [GEMINI_MODEL] + ([FALLBACK_MODEL] if FALLBACK_MODEL else [])
    last_error = None
    for model_name in models:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model_name, contents=contents, config=config
                )
                if resp.text:
                    return resp.text
                raise HTTPException(502, "The AI returned an empty answer. Try another photo.")
            except HTTPException:
                raise
            except Exception as e:
                last_error = e
                if getattr(e, "code", None) in (500, 503, 504):
                    time.sleep(2 * (attempt + 1))  # wait 2s, 4s, 6s then retry
                    continue
                break  # a non-temporary error: move on to the fallback model
    raise HTTPException(502, f"AI service error: {last_error}")


def parse_json_loose(text: str) -> Optional[dict]:
    """Extract a JSON object from model output, tolerating ```json fences."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------- routes
@app.get("/health")
def health():
    return {
        "status": "ok",
        "crop_model_ready": MODEL_PATH.exists(),
        "ai_key_set": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/weather")
def weather(lat: float, lon: float):
    """7-day forecast from Open-Meteo (free, no API key)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        raise HTTPException(502, f"Weather service error: {e}")

    d = data["daily"]
    days = []
    for i, date in enumerate(d["time"]):
        days.append(
            {
                "date": date,
                "temp_max": d["temperature_2m_max"][i],
                "temp_min": d["temperature_2m_min"][i],
                "rain_mm": d["precipitation_sum"][i] or 0,
                "rain_prob": d["precipitation_probability_max"][i] or 0,
            }
        )
    return {
        "current": data.get("current", {}),
        "days": days,
        "total_rain_7d_mm": round(sum(x["rain_mm"] for x in days), 1),
    }


class CropInput(BaseModel):
    N: float = Field(ge=0, le=200)
    P: float = Field(ge=0, le=200)
    K: float = Field(ge=0, le=300)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    ph: float = Field(ge=0, le=14)
    rainfall: float = Field(ge=0, le=5000)


@app.post("/recommend")
def recommend(body: CropInput):
    bundle = get_crop_bundle()
    model, features = bundle["model"], bundle["features"]
    values = body.model_dump()
    row = [[values[f] for f in features]]  # same order as training
    probs = model.predict_proba(row)[0]
    ranked = sorted(zip(model.classes_, probs), key=lambda t: t[1], reverse=True)[:3]
    return {"recommendations": [{"crop": c, "probability": round(float(p), 3)} for c, p in ranked]}


DIAGNOSE_SYSTEM = """You are an expert plant pathologist helping small farmers in India.
Look at the photo and respond with ONLY a JSON object (no markdown) with these keys:
{
  "is_plant": true/false,
  "crop": "crop name or 'unknown'",
  "condition": "disease/pest/deficiency name, or 'healthy'",
  "confidence": "low" | "medium" | "high",
  "symptoms_seen": "what you can actually see in the image",
  "treatment": ["practical, affordable steps"],
  "prevention": ["short tips"],
  "urgency": "low" | "medium" | "high",
  "note": "advice to retake the photo if unclear, else empty"
}
Be honest: if the image is blurry, not a plant, or you are unsure, say so and lower the confidence.
Prefer low-cost and organic options first; mention chemicals only as a last resort with a caution to follow label instructions."""


@app.post("/diagnose")
async def diagnose(
    file: UploadFile = File(...),
    crop: str = Form(""),
    language: str = Form("English"),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large (max 10 MB).")

    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # fix phone-rotated photos
        img = img.convert("RGB")  # handles PNG/RGBA
        img.thumbnail((1024, 1024))
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "That file is not a valid image.")

    hint = f"The farmer says the crop is: {crop}." if crop.strip() else "The crop is not specified."
    prompt = f"{hint} Write all text values in {language}. Return only the JSON object."
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    text = call_ai(prompt, DIAGNOSE_SYSTEM, image_bytes=buf.getvalue(), json_mode=True)
    parsed = parse_json_loose(text)
    if parsed is None:
        return {"parse_failed": True, "raw": text}
    return parsed


class AdvisoryRequest(BaseModel):
    crop: str
    location: str = "the farmer's location"
    language: str = "English"
    weather: Optional[dict] = None
    diagnosis: Optional[dict] = None
    recommended_crops: Optional[list] = None


ADVISORY_SYSTEM = """You write short, practical agro-advisories for small and marginal farmers in India.
Use simple words, short sentences and concrete actions with timing (e.g. 'irrigate on Tuesday morning').
Only use the data provided; do not invent numbers. If data is missing, say what would help.
Structure: 1) This week's weather in one line, 2) 3-5 action points, 3) one warning if any.
Keep it under 180 words."""


@app.post("/advisory")
def advisory(body: AdvisoryRequest):
    parts = [f"Crop: {body.crop}", f"Location: {body.location}"]
    if body.weather:
        days = body.weather.get("days", [])[:7]
        parts.append("7-day forecast: " + json.dumps(days))
    if body.diagnosis:
        parts.append("Latest disease diagnosis: " + json.dumps(body.diagnosis))
    if body.recommended_crops:
        parts.append("Crops suggested for the soil: " + json.dumps(body.recommended_crops))
    parts.append(f"Write the advisory in {body.language}.")
    text = call_ai("\n".join(parts), ADVISORY_SYSTEM, max_tokens=1500)
    return {"advisory": text.strip()}
