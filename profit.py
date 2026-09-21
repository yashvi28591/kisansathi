"""Cost / yield / profit estimator ("Kheti ka Hisaab").

The maths is plain Python (no AI, so no Gemini quota used).
Default numbers come from crop_economics.csv. The numbers shipped in that file are
ROUGH SAMPLE values so the feature works; replace them with real figures for your
state (CACP cost-of-cultivation reports, MSP, Agmarknet mandi prices) before demoing.
"""
import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/profit", tags=["profit"])
CSV_PATH = Path(__file__).parent / "crop_economics.csv"

# (yield multiplier, price multiplier)
SCENARIOS = {
    "good": (1.15, 1.05),
    "normal": (1.00, 1.00),
    "bad": (0.70, 0.90),
}


def load_table() -> dict:
    if not CSV_PATH.exists():
        raise HTTPException(503, "crop_economics.csv not found next to main.py")
    table = {}
    # utf-8-sig also handles files that Excel saved with a BOM
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                table[row["crop"].strip().lower()] = {
                    "yield_qtl_per_acre": float(row["yield_qtl_per_acre"]),
                    "cost_per_acre": float(row["cost_per_acre"]),
                    "price_per_qtl": float(row["price_per_qtl"]),
                }
            except (KeyError, ValueError, AttributeError):
                raise HTTPException(503, f"Bad row in crop_economics.csv: {row}")
    return table


def estimate(area_acres: float, yield_per_acre: float, price: float, cost_per_acre: float) -> dict:
    total_cost = cost_per_acre * area_acres
    base_yield_total = yield_per_acre * area_acres
    scenarios = []
    for name, (ymul, pmul) in SCENARIOS.items():
        production = base_yield_total * ymul
        revenue = production * price * pmul
        profit = revenue - total_cost
        scenarios.append(
            {
                "name": name,
                "production_qtl": round(production, 1),
                "revenue": round(revenue),
                "profit": round(profit),
                "profit_per_acre": round(profit / area_acres),
                "roi_pct": round(profit / total_cost * 100, 1) if total_cost else 0.0,
            }
        )
    return {
        "area_acres": round(area_acres, 2),
        "total_cost": round(total_cost),
        # price at which the NORMAL scenario neither gains nor loses
        "break_even_price_per_qtl": round(total_cost / base_yield_total, 1),
        # yield per acre at which the NORMAL price neither gains nor loses
        "break_even_yield_per_acre": round(cost_per_acre / price, 1),
        "scenarios": scenarios,
        "note": "Estimate only. Real results depend on weather, pests, prices and your actual costs.",
    }


class ProfitInput(BaseModel):
    area_acres: float = Field(gt=0, le=10000)
    yield_qtl_per_acre: float = Field(gt=0, le=500)
    price_per_qtl: float = Field(gt=0, le=1_000_000)
    cost_per_acre: float = Field(ge=0, le=10_000_000)


@router.get("/crops")
def crops():
    """Default yield, cost and price per acre for each crop in the CSV."""
    return load_table()


@router.post("/estimate")
def profit_estimate(body: ProfitInput):
    return estimate(
        body.area_acres, body.yield_qtl_per_acre, body.price_per_qtl, body.cost_per_acre
    )
