from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class RFQRequest(BaseModel):
    pair: str
    notional: float = Field(gt=0)
    tier: str

    @validator("pair")
    def validate_pair(cls, v):
        if v not in ["EUR/USD", "GBP/USD", "USD/INR"]:
            raise ValueError(f"Invalid pair: {v}")
        return v

    @validator("tier")
    def validate_tier(cls, v):
        if v.lower() not in ["retail", "corporate", "institutional"]:
            raise ValueError(f"Invalid tier: {v}")
        return v.lower()


class RFQResponse(BaseModel):
    rfq_id: str
    pair: str
    mid_price: float
    spread_bps: float
    bid: float
    ask: float
    model: str
    volatility: float
    timestamp: str


class RFQOutcome(BaseModel):
    rfq_id: str
    accepted: bool
