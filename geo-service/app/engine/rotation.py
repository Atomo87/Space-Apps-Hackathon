"""Representação das rotações (em meses do ano) e leitura da rotação atual pelo histórico."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.catalog.loader import Catalog
from app.climate.indicators import MONTH_NAMES
from app.schemas import HistoryEntry

PURPOSE_BY_CATEGORY = {"grain": "cash", "legume": "cash", "fiber": "cash", "cover": "cover", "forage": "forage", "vegetable": "cash", "tuber": "cash"}
CASH = {"cash"}


def month_span(start: int, end: int) -> list[int]:
    out, m = [start], start
    while m != end:
        m = m % 12 + 1
        out.append(m)
        if len(out) > 12:
            break
    return out


@dataclass
class Step:
    crops: list[str]
    sow_month: int
    end_month: int
    purpose: str
    water_check: bool = True
    note: str | None = None

    @property
    def months(self) -> list[int]:
        return month_span(self.sow_month, self.end_month)

    def as_dict(self, catalog: Catalog) -> dict[str, Any]:
        return {
            "crops": self.crops,
            "crop_names": [catalog.crop(c).name for c in self.crops],
            "sow_month": self.sow_month,
            "end_month": self.end_month,
            "months": self.months,
            "label": f"{MONTH_NAMES[self.sow_month - 1]}–{MONTH_NAMES[self.end_month - 1]}",
            "purpose": self.purpose,
            "note": self.note,
        }


@dataclass
class Rotation:
    key: str
    title: str
    focus: str
    steps: list[Step]
    is_current: bool = False
    notes: list[str] = field(default_factory=list)

    def crop_slugs(self) -> list[str]:
        return [c for s in self.steps for c in s.crops]

    def active_months(self) -> dict[int, list[Step]]:
        act: dict[int, list[Step]] = defaultdict(list)
        for s in self.steps:
            for m in s.months:
                act[m].append(s)
        return act

    def cover_by_month(self, catalog: Catalog) -> dict[int, tuple[float, str]]:
        """Fator de cobertura (0–1) por mês: cultura viva, palhada (plantio direto) ou solo descoberto.

        - mês de semeadura: cobertura parcial (0,5) ou a palhada anterior, se maior;
        - palhada após a colheita: 3 meses (C:N ≥ 40, fator 0,7), 2 meses (25–40, 0,6) ou 1 mês (< 25, 0,4).
        """
        residue: dict[int, float] = {}
        for s in self.steps:
            cn = max(catalog.crop(c)["cn_ratio"] for c in s.crops)
            months, factor = (3, 0.7) if cn >= 40 else (2, 0.6) if cn >= 25 else (1, 0.4)
            m = s.end_month
            for _ in range(months):
                m = m % 12 + 1
                residue[m] = max(residue.get(m, 0.0), factor)
        act = self.active_months()
        cover: dict[int, tuple[float, str]] = {}
        for m in range(1, 13):
            steps = act.get(m, [])
            established = [s for s in steps if s.sow_month != m]
            if established:
                dormant = all(not s.water_check for s in established)
                cover[m] = (0.8, "cobertura viva (dormente na seca)") if dormant else (1.0, "cultura em campo")
            elif steps:
                r = residue.get(m, 0.0)
                cover[m] = (max(0.5, r), "semeadura sobre palhada" if r > 0.5 else "semeadura")
            elif residue.get(m):
                cover[m] = (residue[m], "palhada")
            else:
                cover[m] = (0.0, "solo descoberto")
        return cover

    def bare_months(self, catalog: Catalog) -> list[int]:
        """Meses sem planta viva (pode haver palhada) — o "campo descoberto" do desafio."""
        act = self.active_months()
        return [m for m in range(1, 13) if m not in act]

    def signature(self) -> tuple:
        return tuple((tuple(sorted(s.crops)), s.sow_month) for s in self.steps)


def rotation_from_template(tpl: dict[str, Any]) -> Rotation:
    return Rotation(
        key=tpl["key"],
        title=tpl["title"],
        focus=tpl["focus"],
        steps=[Step(crops=list(s["crops"]), sow_month=s["sow_month"], end_month=s["end_month"], purpose=s["purpose"],
                    water_check=s.get("water_check", True), note=s.get("note")) for s in tpl["steps"]],
    )


def current_rotation(history: list[HistoryEntry], catalog: Catalog) -> tuple[Rotation | None, dict[str, Any]]:
    """Lê a rotação atual: janela de 12 meses que termina na colheita mais recente."""
    if not history:
        return None, {"window": None, "bare_days": None, "bare_months": [], "entries": 0}

    end = max(h.harvested_at for h in history)
    start = end - timedelta(days=364)
    in_window = [h for h in sorted(history, key=lambda h: h.sown_at) if h.harvested_at >= start and h.sown_at <= end]

    covered: set[date] = set()
    steps: list[Step] = []
    for h in in_window:
        if h.crop not in catalog.crops:
            continue
        a, b = max(h.sown_at, start), min(h.harvested_at, end)
        d = a
        while d <= b:
            covered.add(d)
            d += timedelta(days=1)
        crop = catalog.crop(h.crop)
        steps.append(Step(crops=[h.crop], sow_month=h.sown_at.month, end_month=h.harvested_at.month,
                          purpose=PURPOSE_BY_CATEGORY.get(crop.category, "cash")))

    # dias descobertos por mês dentro da janela
    bare_by_month: dict[int, int] = defaultdict(int)
    d = start
    while d <= end:
        if d not in covered:
            bare_by_month[d.month] += 1
        d += timedelta(days=1)
    bare_months = sorted(m for m, n in bare_by_month.items() if n >= 15)

    names = " → ".join(catalog.crop(s.crops[0]).name for s in steps) or "Sem cultura registrada"
    if bare_months:
        names += " → pousio"
    rot = Rotation(key="atual", title=f"Atual: {names}", focus="Referência (o que você já faz)", steps=steps, is_current=True)
    return rot, {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "bare_days": sum(bare_by_month.values()),
        "bare_months": bare_months,
        "entries": len(in_window),
    }
