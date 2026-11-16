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
    sampled_at: date | None = Field(default=None, description='Data de coleta declarada pelo produtor; nao comprova autenticidade do laudo.')
    analysis_provider: str | None = Field(default=None, min_length=2, max_length=180, description='Laboratorio ou responsavel informado.')
    report_reference: str | None = Field(default=None, min_length=3, max_length=180, description='Referencia declarada do laudo; nao enviar documento sensivel neste campo.')
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

    @model_validator(mode="after")
    def validate_environment(self):
        """Falhar antes do ranking: ausencia de evidencia nunca vira risco zero."""
        import math
        def finite(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        try:
            if self.climate.get('source', {}).get('demo'):
                raise ValueError('Perfis demonstrativos nao sao aceitos na aplicacao.')
            monthly = self.climate["monthly"]
            if not isinstance(monthly, list) or len(monthly) != 12:
                raise ValueError("O perfil deve conter os doze meses.")
            if {m["month"] for m in monthly} != set(range(1, 13)):
                raise ValueError("Meses duplicados ou ausentes.")
            common = set(str(y) for y in self.climate["yearly"]["years"])
            for month in monthly:
                for name in ("rain_by_year", "eto_by_year"):
                    values = month[name]
                    common &= {str(y) for y, v in values.items() if finite(v) and v >= 0}
                for name in ("frost_prob", "heat_days"):
                    if not month[name] or any(not finite(v) for v in month[name].values()):
                        raise ValueError("Indicadores de frio/calor incompletos.")
            if len(common) < 2:
                raise ValueError("Exigidos pelo menos dois anos completos de chuva e ETo para comparar ciclos entre anos.")
            if not finite(self.climate["season"]["pct_seasons_dry_spell_ge_10"]):
                raise ValueError("Historico de veranicos insuficiente.")
            if not finite(self.climate["confidence"]["value"]):
                raise ValueError("Confianca invalida.")
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("ClimateProfile malformado; utilize a resposta de /v1/climate-profile.") from exc
        return self
