"""Catálogo de culturas e modelos de rotação (arquivos JSON versionados)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Crop:
    slug: str
    name: str
    family: str
    category: str
    raw: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    @property
    def kc_mean(self) -> float:
        kc = self.raw["kc"]
        # média ponderada simples das fases (inicial, média ×2, final)
        return (kc["ini"] + 2 * kc["mid"] + kc["end"]) / 4

    def pest_role(self, pest: str) -> str:
        return self.raw.get("pests", {}).get(pest, "unknown")


@dataclass(frozen=True)
class Catalog:
    crops: dict[str, Crop]
    pests: dict[str, dict[str, str]]
    equipment: dict[str, str]
    templates: list[dict[str, Any]]
    region_bbox: dict[str, float]
    version: str
    disclaimer: str

    def crop(self, slug: str) -> Crop:
        if slug not in self.crops:
            raise KeyError(f"Cultura desconhecida no catálogo: {slug}")
        return self.crops[slug]

    def public(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "disclaimer": self.disclaimer,
            "pests": self.pests,
            "equipment": self.equipment,
            "crops": [c.raw for c in self.crops.values()],
            "templates": self.templates,
        }


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    crops_doc = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
    tpl_doc = json.loads((DATA_DIR / "templates.json").read_text(encoding="utf-8"))
    crops = {
        c["slug"]: Crop(slug=c["slug"], name=c["name_pt"], family=c["family"], category=c["category"], raw=c)
        for c in crops_doc["crops"]
    }
    for t in tpl_doc["templates"]:
        for s in t["steps"]:
            for slug in s["crops"]:
                if slug not in crops:
                    raise ValueError(f"Modelo {t['key']} usa cultura inexistente: {slug}")
    return Catalog(
        crops=crops,
        pests=crops_doc["pests"],
        equipment=crops_doc["equipment"],
        templates=tpl_doc["templates"],
        region_bbox=tpl_doc["region_bbox"],
        version=crops_doc["version"],
        disclaimer=crops_doc["disclaimer"],
    )
