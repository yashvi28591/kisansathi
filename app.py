"""Bilingual (English / Hindi) Streamlit UI. Talks ONLY to the FastAPI backend.

All fixed text (buttons, labels, tabs, table headers, crop names) comes from the
TEXT dictionary below, so switching language costs ZERO AI requests.
Only the diagnosis and advisory text written by Gemini uses the AI, and it is
asked to reply in the selected language.
"""
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="KisanSaathi", page_icon="🌾", layout="wide")

# ------------------------------------------------------------------ text
TEXT = {
    "en": {
        "title": "🌾 KisanSaathi: AI farming assistant",
        "backend_url": "Backend URL",
        "location": "Location",
        "lat": "Latitude",
        "lon": "Longitude",
        "places": {
            "Delhi": "Delhi", "Lucknow": "Lucknow", "Ludhiana": "Ludhiana",
            "Pune": "Pune", "Hyderabad": "Hyderabad", "Custom": "Custom (enter yourself)",
        },
        "tabs": ["1. Weather", "2. Crop recommendation", "3. Disease check", "4. Advisory"],
        # weather
        "get_forecast": "Get 7-day forecast",
        "temp_now": "Temperature now (°C)",
        "hum_now": "Humidity now (%)",
        "rain_7d": "Rain next 7 days (mm)",
        "cols": {
            "date": "Date", "temp_max": "Max temp (°C)", "temp_min": "Min temp (°C)",
            "rain_mm": "Rain (mm)", "rain_prob": "Rain chance (%)",
        },
        # crop
        "crop_caption": "Enter soil test values (from a Soil Health Card) and local conditions.",
        "N": "Nitrogen (N)", "P": "Phosphorus (P)", "K": "Potassium (K)",
        "temp": "Temperature (°C)", "hum": "Humidity (%)", "ph": "Soil pH", "rain": "Rainfall (mm)",
        "recommend": "Recommend crops",
        "best_match": "Best match",
        "probability": "Probability",
        # disease
        "crop_optional": "Crop (optional)",
        "upload": "Upload a clear photo of the affected leaf",
        "diagnose": "Diagnose",
        "analysing": "Analysing...",
        "parse_failed": "Could not read the answer; raw text is shown below.",
        "not_plant": "This doesn't look like a plant photo. Please retake it.",
        "confidence": "Confidence",
        "urgency": "Urgency",
        "seen": "What we see:",
        "treatment": "Treatment",
        "prevention": "Prevention",
        "levels": {"low": "low", "medium": "medium", "high": "high"},
        # advisory
        "adv_crop": "Crop for the advisory",
        "adv_caption": "Uses your forecast, crop suggestions and diagnosis if you have run them.",
        "gen_adv": "Generate advisory",
        "writing": "Writing advisory...",
        # errors
        "no_backend": "Cannot reach the backend at {api}. Is it running?",
        "err": "Error {code}",
        "crops": {},
    },
    "hi": {
        "title": "🌾 किसानसाथी: AI खेती सहायक",
        "backend_url": "बैकएंड URL",
        "location": "स्थान",
        "lat": "अक्षांश",
        "lon": "देशांतर",
        "places": {
            "Delhi": "दिल्ली", "Lucknow": "लखनऊ", "Ludhiana": "लुधियाना",
            "Pune": "पुणे", "Hyderabad": "हैदराबाद", "Custom": "अन्य (स्वयं दर्ज करें)",
        },
        "tabs": ["1. मौसम", "2. फसल सुझाव", "3. रोग जाँच", "4. सलाह"],
        "get_forecast": "7 दिन का पूर्वानुमान देखें",
        "temp_now": "अभी का तापमान (°C)",
        "hum_now": "अभी की नमी (%)",
        "rain_7d": "अगले 7 दिन की बारिश (मिमी)",
        "cols": {
            "date": "तारीख", "temp_max": "अधिकतम तापमान (°C)", "temp_min": "न्यूनतम तापमान (°C)",
            "rain_mm": "बारिश (मिमी)", "rain_prob": "बारिश की संभावना (%)",
        },
        "crop_caption": "मृदा स्वास्थ्य कार्ड के मिट्टी परीक्षण मान और स्थानीय परिस्थितियाँ दर्ज करें।",
        "N": "नाइट्रोजन (N)", "P": "फॉस्फोरस (P)", "K": "पोटैशियम (K)",
        "temp": "तापमान (°C)", "hum": "नमी (%)", "ph": "मिट्टी का pH", "rain": "बारिश (मिमी)",
        "recommend": "फसल सुझाएँ",
        "best_match": "सबसे उपयुक्त फसल",
        "probability": "संभावना",
        "crop_optional": "फसल (वैकल्पिक)",
        "upload": "प्रभावित पत्ती की साफ़ फोटो अपलोड करें",
        "diagnose": "जाँच करें",
        "analysing": "जाँच हो रही है...",
        "parse_failed": "जवाब पढ़ा नहीं जा सका; नीचे मूल पाठ दिखाया गया है।",
        "not_plant": "यह पौधे की फोटो नहीं लगती। कृपया दोबारा फोटो लें।",
        "confidence": "विश्वास स्तर",
        "urgency": "तात्कालिकता",
        "seen": "हमें क्या दिखा:",
        "treatment": "उपचार",
        "prevention": "रोकथाम",
        "levels": {"low": "कम", "medium": "मध्यम", "high": "अधिक"},
        "adv_crop": "सलाह के लिए फसल",
        "adv_caption": "अगर आपने मौसम, फसल सुझाव और रोग जाँच चलाई है तो सलाह में उनका उपयोग होता है।",
        "gen_adv": "सलाह बनाएँ",
        "writing": "सलाह तैयार हो रही है...",
        "no_backend": "{api} पर बैकएंड से संपर्क नहीं हो पा रहा। क्या वह चालू है?",
        "err": "त्रुटि {code}",
        "crops": {
            "rice": "चावल", "maize": "मक्का", "chickpea": "चना", "kidneybeans": "राजमा",
            "pigeonpeas": "अरहर", "mothbeans": "मोठ", "mungbean": "मूँग", "blackgram": "उड़द",
            "lentil": "मसूर", "pomegranate": "अनार", "banana": "केला", "mango": "आम",
            "grapes": "अंगूर", "watermelon": "तरबूज", "muskmelon": "खरबूजा", "apple": "सेब",
            "orange": "संतरा", "papaya": "पपीता", "coconut": "नारियल", "cotton": "कपास",
            "jute": "जूट", "coffee": "कॉफ़ी",
        },
    },
}

# ------------------------------------------------------------------ language
choice = st.sidebar.selectbox("Language / भाषा", ["English", "हिन्दी"], key="ui_lang")
L = "hi" if choice == "हिन्दी" else "en"
AI_LANGUAGE = "Hindi" if L == "hi" else "English"  # sent to the backend for AI text
TR = TEXT[L]


def crop_label(name: str) -> str:
    """Show crop names in the chosen language (falls back to the original)."""
    return TR["crops"].get(str(name).lower(), name)


def level_label(value) -> str:
    return TR["levels"].get(str(value).lower(), value)


st.title(TR["title"])
API = st.sidebar.text_input(TR["backend_url"], "http://localhost:8000", key="api_url")

PLACES = {
    "Delhi": (28.61, 77.21),
    "Lucknow": (26.85, 80.95),
    "Ludhiana": (30.90, 75.85),
    "Pune": (18.52, 73.86),
    "Hyderabad": (17.39, 78.49),
    "Custom": None,
}
place = st.sidebar.selectbox(
    TR["location"], list(PLACES), format_func=lambda p: TR["places"][p], key="place"
)
if PLACES[place] is None:
    lat = st.sidebar.number_input(TR["lat"], value=26.0, format="%.4f", key="lat")
    lon = st.sidebar.number_input(TR["lon"], value=80.0, format="%.4f", key="lon")
else:
    lat, lon = PLACES[place]

ss = st.session_state
for k in ("weather", "recs", "diagnosis"):
    ss.setdefault(k, None)


def call(method, path, **kwargs):
    """Call the backend; show a clear error instead of crashing."""
    try:
        r = requests.request(method, f"{API}{path}", timeout=120, **kwargs)
    except requests.RequestException:
        st.error(TR["no_backend"].format(api=API))
        return None
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        st.error(f"{TR['err'].format(code=r.status_code)}: {detail}")
        return None
    return r.json()


tab_w, tab_c, tab_d, tab_a = st.tabs(TR["tabs"])

# ------------------------------------------------------------------ weather
with tab_w:
    if st.button(TR["get_forecast"], key="btn_weather"):
        ss.weather = call("GET", "/weather", params={"lat": lat, "lon": lon})
    if ss.weather:
        cur = ss.weather.get("current", {})
        c1, c2, c3 = st.columns(3)
        c1.metric(TR["temp_now"], cur.get("temperature_2m", "n/a"))
        c2.metric(TR["hum_now"], cur.get("relative_humidity_2m", "n/a"))
        c3.metric(TR["rain_7d"], ss.weather["total_rain_7d_mm"])
        table = pd.DataFrame(ss.weather["days"]).rename(columns=TR["cols"])
        st.dataframe(table)

# ------------------------------------------------------------------ crops
with tab_c:
    st.caption(TR["crop_caption"])
    a, b, c = st.columns(3)
    N = a.number_input(TR["N"], 0.0, 200.0, 90.0, key="in_N")
    P = b.number_input(TR["P"], 0.0, 200.0, 42.0, key="in_P")
    K = c.number_input(TR["K"], 0.0, 300.0, 43.0, key="in_K")
    temp = a.number_input(TR["temp"], -10.0, 60.0, 25.0, key="in_temp")
    hum = b.number_input(TR["hum"], 0.0, 100.0, 80.0, key="in_hum")
    ph = c.number_input(TR["ph"], 0.0, 14.0, 6.5, key="in_ph")
    rain = a.number_input(TR["rain"], 0.0, 5000.0, 200.0, key="in_rain")
    if st.button(TR["recommend"], key="btn_recommend"):
        ss.recs = call(
            "POST",
            "/recommend",
            json={"N": N, "P": P, "K": K, "temperature": temp,
                  "humidity": hum, "ph": ph, "rainfall": rain},
        )
    if ss.recs:
        recs = ss.recs["recommendations"]
        st.success(f"{TR['best_match']}: **{crop_label(recs[0]['crop'])}**")
        chart = pd.DataFrame(
            {TR["probability"]: [r["probability"] for r in recs]},
            index=[crop_label(r["crop"]) for r in recs],
        )
        st.bar_chart(chart)

# ------------------------------------------------------------------ disease
with tab_d:
    crop_hint = st.text_input(TR["crop_optional"], "", key="crop_hint")
    up = st.file_uploader(TR["upload"], type=["jpg", "jpeg", "png", "webp"], key="leaf")
    if up is not None:
        st.image(up, width=320)
        if st.button(TR["diagnose"], key="btn_diagnose"):
            with st.spinner(TR["analysing"]):
                ss.diagnosis = call(
                    "POST",
                    "/diagnose",
                    files={"file": (up.name, up.getvalue(), up.type or "image/jpeg")},
                    data={"crop": crop_hint, "language": AI_LANGUAGE},
                )
    d = ss.diagnosis
    if d:
        if d.get("parse_failed"):
            st.warning(TR["parse_failed"])
            st.write(d.get("raw"))
        elif not d.get("is_plant", True):
            st.warning(TR["not_plant"])
        else:
            st.subheader(f"{d.get('crop', '?')}: {d.get('condition', '?')}")
            st.write(
                f"{TR['confidence']}: **{level_label(d.get('confidence'))}** | "
                f"{TR['urgency']}: **{level_label(d.get('urgency'))}**"
            )
            st.write(f"**{TR['seen']}**", d.get("symptoms_seen"))
            st.write(f"**{TR['treatment']}**")
            for t in d.get("treatment", []):
                st.write(f"- {t}")
            st.write(f"**{TR['prevention']}**")
            for t in d.get("prevention", []):
                st.write(f"- {t}")
            if d.get("note"):
                st.info(d["note"])

# ------------------------------------------------------------------ advisory
with tab_a:
    default_crop = crop_label(ss.recs["recommendations"][0]["crop"]) if ss.recs else ""
    adv_crop = st.text_input(TR["adv_crop"], default_crop, key="adv_crop")
    st.caption(TR["adv_caption"])
    if st.button(TR["gen_adv"], key="btn_advisory") and adv_crop:
        with st.spinner(TR["writing"]):
            res = call(
                "POST",
                "/advisory",
                json={
                    "crop": adv_crop,
                    "location": TR["places"][place],
                    "language": AI_LANGUAGE,
                    "weather": ss.weather,
                    "diagnosis": ss.diagnosis
                    if ss.diagnosis and not ss.diagnosis.get("parse_failed")
                    else None,
                    "recommended_crops": ss.recs["recommendations"] if ss.recs else None,
                },
            )
        if res:
            st.markdown(res["advisory"])