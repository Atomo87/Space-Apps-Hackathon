"""Contrato B1 — entradas da API do geo-service (Pydantic).

As saídas são dicionários JSON documentados em ``docs/contrato-b1.md`` e tipados em
``resources/js/types/contract.ts`` no Laravel.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

PRIORITY_KEYS = (
    "save_water", "soil_structure", "n_fixation", "erosion_control", "organic_matter",
    "pest_break", "forage", "extra_income", "market_fit",
)


class ClimateRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_year: int | None = Field(default=None, ge=1981)
    end_year: int | None = None


class TerrainRequest(BaseModel):
    latitude: float = Field(ge=-60, le=60)  # cobertura do SRTM
    longitude: float = Field(ge=-180, le=180)
    boundary: dict[str, Any] | None = None  # GeoJSON Polygon do talhão (opcional)


class VegetationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FieldInfo(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    area_ha: float | None = Field(default=None, ge=0)
    irrigated: bool = False
    irrigation_mm_day: float | None = Field(default=None, ge=0, le=20)


class SoilInfo(BaseModel):
    source: Literal["lab_analysis", "farmer_estimate", "unknown"] = "unknown"
    texture: Literal["arenosa", "media", "argilosa", "muito_argilosa"] | None = None
    clay_pct: float | None = Field(default=None, ge=0, le=100)
    ph_water: float | None = Field(default=None, ge=3, le=9)
    organic_matter_pct: float | None = Field(default=None, ge=0, le=20)
    v_pct: float | None = Field(default=None, ge=0, le=100)


class HistoryEntry(BaseModel):
    crop: str
    sown_at: date
    harvested_at: date

    @model_validator(mode="after")
    def _order(self) -> "HistoryEntry":
        if self.harvested_at <= self.sown_at:
            raise ValueError("A colheita deve ser depois do plantio.")
        return self


class Priorities(BaseModel):
    save_water: int = Field(default=3, ge=0, le=5)
    soil_structure: int = Field(default=3, ge=0, le=5)
    n_fixation: int = Field(default=3, ge=0, le=5)
    erosion_control: int = Field(default=3, ge=0, le=5)
    organic_matter: int = Field(default=3, ge=0, le=5)
    pest_break: int = Field(default=3, ge=0, le=5)
    forage: int = Field(default=3, ge=0, le=5)
    extra_income: int = Field(default=3, ge=0, le=5)
    market_fit: int = Field(default=3, ge=0, le=5)


class Constraints(BaseModel):
    excluded_crops: list[str] = []
    buyer_crops: list[str] = []
    no_buyer_crops: list[str] = []
    missing_equipment: list[str] = []
    has_livestock: bool = False


class Scenario(BaseModel):
    rain_delta_pct: float = Field(default=0, ge=-40, le=20)
    temp_delta_c: float = Field(default=0, ge=0, le=3)


class AnalysisRequest(BaseModel):
    climate: dict[str, Any]
    # Relevo (POST /v1/terrain). Opcional: sem ele, a erosão considera só chuva e cobertura.
    terrain: dict[str, Any] | None = None
    # NDVI MODIS (POST /v1/vegetation). Opcional: entra no diagnóstico e nas evidências, não na nota.
    vegetation: dict[str, Any] | None = None
    # Estresse observado (POST /v1/stress): MODIS LST e ET/PET. Opcional, diagnóstico e evidências.
    stress: dict[str, Any] | None = None
    # Conjuntos com login Earthdata (POST /v1/earthdata): SMAP, GPM IMERG, ECOSTRESS, GRACE-FO.
    earthdata: dict[str, Any] | None = None
    field: FieldInfo
    soil: SoilInfo | None = None
    history: list[HistoryEntry] = []
    priorities: Priorities = Priorities()
    constraints: Constraints = Constraints()
    scenario: Scenario = Scenario()
