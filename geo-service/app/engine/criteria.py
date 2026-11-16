"""Filtros duros e critérios de pontuação (0–100) — tarefa B5.

Cada função devolve número, confiança e uma explicação curta rastreável até dado + regra.
As regras estão em ``docs/motor.md``.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from app.i18n import is_english, tr as translate
from app.catalog.loader import Catalog, Crop
from app.climate.indicators import MONTH_NAMES, RAINY_SEASON, percentile
from app.engine.rotation import CASH, Rotation, Step
from app.schemas import Constraints, FieldInfo, SoilInfo

CRITERIA_LABELS = {
    "save_water": "Uso de água",
    "soil_structure": "Estrutura e infiltração",
    "n_fixation": "Nitrogênio",
    "erosion_control": "Controle de erosão",
    "organic_matter": "Matéria orgânica (palhada)",
    "pest_break": "Quebra de pragas e doenças",
    "forage": "Forragem",
    "extra_income": "Renda complementar",
    "market_fit": "Adequação ao mercado",
    "climate_risk": "Segurança climática",
}
CLIMATE_RISK_WEIGHT = 3  # sempre conta; não é ajustável pelo produtor
AWC_BY_TEXTURE = {"arenosa": 40.0, "media": 70.0, "argilosa": 100.0, "muito_argilosa": 110.0}
DROUGHT_FACTOR = {"low": 1.0, "medium": 0.8, "high": 0.6}
FROST_SENS = {"none": 1.0, "low": 0.7, "medium": 0.3, "high": 0.0}
ROLE_BREAK = {"suppressor": 1.0, "non_host": 0.7, "poor_host": 0.5, "unknown": 0.2, "host": 0.0}
WATER_FILTER_DEFICIT = 0.5  # elimina se a cultura recebe < 50% da água em ≥ 50% dos anos


@dataclass
class Ctx:
    profile: dict[str, Any]
    catalog: Catalog
    field: FieldInfo
    soil: SoilInfo | None
    constraints: Constraints
    current: Rotation | None
    terrain: dict[str, Any] | None = None
    vegetation: dict[str, Any] | None = None
    stress: dict[str, Any] | None = None
    earthdata: dict[str, Any] | None = None
    monthly: dict[int, dict[str, Any]] = field(init=False)
    years: list[str] = field(init=False)
    climate_conf: float = field(init=False)

    def __post_init__(self) -> None:
        self.monthly = {m["month"]: m for m in self.profile["monthly"]}
        self.years = [str(y) for y in self.profile["yearly"]["years"]]
        self.climate_conf = float(self.profile["confidence"]["value"])

    @property
    def awc(self) -> float:
        if self.soil and self.soil.texture:
            return AWC_BY_TEXTURE[self.soil.texture]
        return 70.0

    @property
    def period(self) -> str:
        p = self.profile["source"]["period"]
        return f"{p['start'][:4]}–{p['end'][:4]}"


@dataclass
class Criterion:
    key: str
    score: float
    confidence: float
    explanation: str
    details: dict[str, Any] = field(default_factory=dict)


def br(x: float, nd: int = 1) -> str:
    """Format a number for the current analysis language."""
    value = f"{x:.{nd}f}"
    return value if is_english() else value.replace(".", ",")


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def months_join(items: list[str]) -> str:
    return ", ".join(items[:-1]) + (translate(" e ") if len(items) > 1 else "") + items[-1] if items else ""


def months_txt(months: list[int]) -> str:
    if not months:
        return translate("nenhum mês")
    return months_join([translate(MONTH_NAMES[m - 1]) for m in months])


# ------------------------------------------------------------------ água
def _kc_for(crops: list[Crop], pos: int, n: int) -> float:
    phase = "ini" if pos == 0 else "end" if (pos == n - 1 and n >= 3) else "mid"
    return max(c["kc"][phase] for c in crops)


def step_water(ctx: Ctx, step: Step) -> dict[str, Any]:
    """Balanço mensal com balde de água no solo, ano a ano. Retorna fração de déficit por ano."""
    crops = [ctx.catalog.crop(c) for c in step.crops]
    main = crops[0]
    tol = DROUGHT_FACTOR[main["drought_tolerance"]]
    months = step.months
    n = len(months)
    irr = (ctx.field.irrigation_mm_day or 0.0) if ctx.field.irrigated else 0.0
    per_year: dict[str, float] = {}
    etc_total: list[float] = []
    deficit_total: list[float] = []
    for y in ctx.years:
        prev = (months[0] - 2) % 12 + 1
        pm = ctx.monthly[prev]
        prev_rain, prev_eto = pm["rain_by_year"].get(y), pm["eto_by_year"].get(y)
        storage = ctx.awc if (prev_rain or 0) >= (prev_eto or 1e9) else ctx.awc / 2
        etc_sum = deficit = 0.0
        ok = True
        for pos, m in enumerate(months):
            mo = ctx.monthly[m]
            rain, eto = mo["rain_by_year"].get(y), mo["eto_by_year"].get(y)
            if rain is None or eto is None:
                ok = False
                break
            frac = 0.5 if (n > 1 and pos in (0, n - 1)) else 1.0
            etc = eto * _kc_for(crops, pos, n) * frac
            supply = 0.8 * rain * frac + irr * 30 * frac + storage
            d = max(0.0, etc - supply)
            storage = min(ctx.awc, max(0.0, supply - etc))
            etc_sum += etc
            deficit += d * tol
        if ok and etc_sum > 0:
            per_year[y] = deficit / etc_sum
            etc_total.append(etc_sum)
            deficit_total.append(deficit)
    vals = list(per_year.values())
    return {
        "per_year": per_year,
        "deficit_p50": percentile(vals, 0.5) or 0.0,
        "deficit_p10": percentile(vals, 0.1) or 0.0,
        "deficit_p90": percentile(vals, 0.9) or 0.0,
        "share_years_over_filter": (sum(v > WATER_FILTER_DEFICIT for v in vals) / len(vals)) if vals else 0.0,
        "etc_mm": statistics.fmean(etc_total) if etc_total else 0.0,
        "deficit_mm": statistics.fmean(deficit_total) if deficit_total else 0.0,
    }


def crit_water(ctx: Ctx, rot: Rotation) -> Criterion:
    steps = [s for s in rot.steps if s.water_check]
    if not steps:
        return Criterion("save_water", 50, 0.3, translate("Sem etapas avaliáveis."))
    waters = [step_water(ctx, s) for s in steps]
    etc = sum(w["etc_mm"] for w in waters)
    years = ctx.years
    yearly_frac = []
    for y in years:
        e = d = 0.0
        for w, s in zip(waters, steps):
            if y in w["per_year"]:
                e_y = w["etc_mm"]
                e += e_y
                d += w["per_year"][y] * e_y
        if e > 0:
            yearly_frac.append(d / e)
    p50 = percentile(yearly_frac, 0.5) or 0.0
    # bônus: cultura tolerante à seca ocupando meses de veranico na estação chuvosa
    spell = ctx.profile["season"]["pct_seasons_dry_spell_ge_10"] or 0
    bonus = 0.0
    for s in steps:
        crop = ctx.catalog.crop(s.crops[0])
        if crop["drought_tolerance"] == "high" and any(m in RAINY_SEASON for m in s.months) and spell >= 30:
            bonus = 8.0
    score = clamp(100 * (1 - 1.6 * p50) + bonus)
    conf = ctx.climate_conf * (1.0 if ctx.soil and ctx.soil.texture else 0.85)
    return Criterion(
        "save_water", score, conf,
        translate(
            "Em um ano típico falta cerca de {0}% da água que as culturas usariam (ETc ≈ {1} mm no ano, balanço mensal com {2} mm de água no solo).",
            round(100 * p50),
            round(etc),
            round(ctx.awc),
        ),
        {"deficit_frac_p50": round(p50, 3), "deficit_frac_p10": round(percentile(yearly_frac, 0.1) or 0, 3),
         "deficit_frac_p90": round(percentile(yearly_frac, 0.9) or 0, 3), "etc_mm": round(etc),
         "yearly_scores": [clamp(100 * (1 - 1.6 * f) + bonus) for f in yearly_frac], "steps": waters},
    )


# ------------------------------------------------------------------ clima
def interp_threshold(table: dict[str, float | None], thr: float) -> float:
    pts = sorted((float(k), v) for k, v in table.items() if v is not None)
    if not pts:
        return 0.0
    if thr <= pts[0][0]:
        return pts[0][1]
    if thr >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= thr <= x1:
            return y0 + (y1 - y0) * (thr - x0) / (x1 - x0)
    return 0.0


def step_climate_loss(ctx: Ctx, step: Step) -> dict[str, Any]:
    crop = ctx.catalog.crop(step.crops[0])
    months = step.months
    sensitive = months[1:-1] if len(months) >= 3 else months
    p_frost = max((ctx.monthly[m]["frost_prob"].get("2.0") or 0) for m in months) * FROST_SENS[crop["frost_tolerance"]]
    heat_days = max(interp_threshold(ctx.monthly[m]["heat_days"], crop["t_heat_stress_c"]) for m in sensitive)
    p_heat = min(0.6, heat_days / 15)
    p_dry = 0.0
    if any(m in RAINY_SEASON for m in sensitive):
        pct = (ctx.profile["season"]["pct_seasons_dry_spell_ge_10"] or 0) / 100
        p_dry = pct * {"low": 0.6, "medium": 0.4, "high": 0.15}[crop["drought_tolerance"]]
    loss = 1 - (1 - p_frost) * (1 - p_heat) * (1 - p_dry)
    reasons = []
    if p_frost >= 0.05:
        reasons.append(translate("geada em {0}% dos anos", round(100 * p_frost)))
    if heat_days >= 1:
        reasons.append(translate("~{0} dia(s)/mês acima de {1} °C na fase sensível", format(heat_days, '.0f'), format(crop['t_heat_stress_c'], '.0f')))
    if p_dry >= 0.05:
        reasons.append(translate("veranico ≥ 10 dias em {0}% das safras", round(pct * 100)))
    return {"crop": crop.slug, "loss": loss, "reasons": reasons, "p_frost": p_frost, "heat_days": heat_days, "p_dry": p_dry}


def crit_climate(ctx: Ctx, rot: Rotation) -> Criterion:
    risks = [(step_climate_loss(ctx, s), 1.0 if s.purpose in CASH else 0.5) for s in rot.steps]
    if not risks:
        return Criterion("climate_risk", 50, 0.3, translate("Sem culturas para avaliar."))
    loss = sum(r["loss"] * w for r, w in risks) / sum(w for _, w in risks)
    worst = max(risks, key=lambda rw: rw[0]["loss"])[0]
    expl = (translate("Maior risco: {0} — ", ctx.catalog.crop(worst['crop']).name) + "; ".join(worst["reasons"])) if worst["reasons"] else translate("Sem riscos climáticos relevantes nas fases sensíveis.")
    return Criterion("climate_risk", clamp(100 * (1 - loss)), ctx.climate_conf, expl, {"steps": [r for r, _ in risks]})


# ------------------------------------------------------------------ solo
def crit_erosion(ctx: Ctx, rot: Rotation) -> Criterion:
    cover = rot.cover_by_month(ctx.catalog)
    # índice de Fournier modificado: chuva² / chuva anual → peso da erosividade de cada mês
    rains = {m: (ctx.monthly[m]["rain_mm"]["mean"] or 0.0) for m in range(1, 13)}
    total = sum(rains.values()) or 1.0
    weights = {m: rains[m] ** 2 / total for m in rains}
    wsum = sum(weights.values()) or 1.0
    protected = sum(weights[m] * cover[m][0] for m in range(1, 13)) / wsum
    exposed = [m for m in range(1, 13) if cover[m][0] < 0.5 and weights[m] / wsum > 0.05]
    # Fator topográfico (LS da RUSLE) relativo a um relevo suave de 3 %: amplia ou reduz o efeito da exposição.
    ls_rel = 1.0
    if ctx.terrain and ctx.terrain.get("ls_relative") is not None:
        ls_rel = clamp(float(ctx.terrain["ls_relative"]), 0.4, 2.5)
    score = clamp(100 * (1 - (1 - protected) * ls_rel))
    expl = translate("Protege {0}% da chuva erosiva do ano", round(100 * protected))
    expl += translate("; fica exposto em {0}", months_txt(exposed)) if exposed else translate("; sem meses chuvosos de solo exposto")
    if ctx.terrain:
        t = ctx.terrain
        expl += (translate(
            ". Relevo {0} (declividade média {1}% no SRTM, fator LS {2}): {3} o risco.",
            translate(t['relief_class']),
            br(t['slope_pct']['mean']),
            br(t['ls_factor'], 2),
            translate('aumenta' if ls_rel > 1.05 else 'reduz' if ls_rel < 0.95 else 'mantém'),
        ))
    else:
        expl += "."
    conf = ctx.climate_conf * (0.95 if ctx.terrain else 0.85)
    return Criterion("erosion_control", score, conf, expl,
                     {"cover": {m: cover[m] for m in cover}, "exposed_rainy_months": exposed, "ls_relative": ls_rel,
                      "protected_frac": round(protected, 3)})


def crit_structure(ctx: Ctx, rot: Rotation) -> Criterion:
    pts = 0.0
    kinds = set()
    for s in rot.steps:
        for slug in s.crops:
            c = ctx.catalog.crop(slug)
            kinds.add(c["root_system"])
            pts += {"deep": 25, "medium": 12, "shallow": 5}[c["root_depth"]]
    pts += 10 if len(kinds) > 1 else 0
    bare = rot.bare_months(ctx.catalog)
    pts -= 5 * len(bare)
    expl = translate("Raízes: {0}; {1} mês(es) de solo descoberto.", ', '.join(translate(kind) for kind in sorted(kinds)) or translate('nenhuma'), len(bare))
    return Criterion("soil_structure", clamp(pts), 0.55, expl, {"bare_months": bare})


def crit_nitrogen(ctx: Ctx, rot: Rotation) -> Criterion:
    n = sum(ctx.catalog.crop(c)["n_credit_kg_ha"] for s in rot.steps for c in s.crops)
    return Criterion("n_fixation", clamp(n / 120 * 100), 0.55,
                     translate("Crédito estimado de ~{0} kg N/ha para a cultura seguinte (estimativa do catálogo).", n), {"n_kg_ha": n})


def crit_organic(ctx: Ctx, rot: Rotation) -> Criterion:
    total = 0.0
    for s in rot.steps:
        for slug in s.crops:
            c = ctx.catalog.crop(slug)
            factor = 1.2 if c["cn_ratio"] >= 40 else 1.0 if c["cn_ratio"] >= 25 else 0.7
            share = 0.6 if len(s.crops) > 1 else 1.0  # consórcio: cada cultura produz menos
            total += c["residue_t_ha"] * factor * share
    return Criterion("organic_matter", clamp(total / 16 * 100), 0.55,
                     translate("Aporte equivalente de ~{0} t/ha/ano de palhada (ponderado pela relação C:N).", br(total)), {"residue_index": round(total, 1)})


# ------------------------------------------------------------------ pragas
def key_pests(ctx: Ctx, rot: Rotation) -> list[str]:
    ref = ctx.current if ctx.current and ctx.current.steps else rot
    cash = [c for s in ref.steps if s.purpose in CASH for c in s.crops] or ref.crop_slugs()
    return [p for p in ctx.catalog.pests if any(ctx.catalog.crop(c).pest_role(p) == "host" for c in cash)]


def crit_pests(ctx: Ctx, rot: Rotation) -> Criterion:
    pests = key_pests(ctx, rot)
    if not pests:
        return Criterion("pest_break", 50, 0.3, translate("Sem pragas-chave identificadas no catálogo."))
    best = {}
    for p in pests:
        best[p] = max(ROLE_BREAK[ctx.catalog.crop(c).pest_role(p)] for c in rot.crop_slugs())
    part = statistics.fmean(best.values()) * 75
    families = {ctx.catalog.crop(c).family for c in rot.crop_slugs()}
    part += {1: 0, 2: 15}.get(len(families), 25)
    seq = [tuple(s.crops) for s in rot.steps]
    if any(a == b for a, b in zip(seq, seq[1:])):
        part -= 10
    broken = [ctx.catalog.pests[p]["name"].split(" (")[0] for p, v in best.items() if v >= 0.5]
    open_ = [ctx.catalog.pests[p]["name"].split(" (")[0] for p, v in best.items() if v < 0.5]
    expl = (translate("Interrompe: {0}. ", ', '.join(broken)) if broken else "") + (translate("Não interrompe: {0}. ", ', '.join(open_)) if open_ else "")
    expl += translate("{0} família(s) botânica(s).", len(families))
    return Criterion("pest_break", clamp(part), 0.45, expl, {"pests": best, "families": sorted(families)})


# ------------------------------------------------------------------ renda e forragem
def crit_forage(ctx: Ctx, rot: Rotation) -> Criterion:
    val = {"high": 1.0, "medium": 0.6, "low": 0.3, "none": 0.0}
    dry = [5, 6, 7, 8, 9]
    act = rot.active_months()
    pts = sum(max((val[ctx.catalog.crop(c)["forage_value"]] for s in act.get(m, []) for c in s.crops), default=0) for m in dry)
    expl = translate("Oferta de forragem em ~{0} dos 5 meses de entressafra (mai–set).", br(pts))
    if not ctx.constraints.has_livestock:
        expl += translate(" Sem gado informado: só vale se houver comprador de forragem/feno.")
    return Criterion("forage", clamp(pts / 4 * 100), 0.55, expl, {"forage_months": round(pts, 1)})


def crit_income(ctx: Ctx, rot: Rotation) -> Criterion:
    cash_steps = [s for s in rot.steps if s.purpose in CASH]
    extra = cash_steps[1:]
    v = sum(max(ctx.catalog.crop(c)["market_index"] for c in s.crops) for s in extra)
    forage_sale = 0.2 if ctx.constraints.has_livestock and any(s.purpose == "forage" for s in rot.steps) else 0.0
    score = clamp((v + forage_sale) * 100)
    names = [ctx.catalog.crop(s.crops[0]).name for s in extra]
    expl = translate("Segunda fonte de renda: {0}.", ', '.join(names)) if names else translate("Sem segunda safra comercial.")
    if forage_sale:
        expl += translate(" Pastejo na entressafra conta como renda indireta.")
    return Criterion("extra_income", score, 0.4, expl + translate(" (índice de mercado é hipótese a validar)"))


def crit_market(ctx: Ctx, rot: Rotation) -> Criterion:
    cash = sorted({c for s in rot.steps if s.purpose in CASH for c in s.crops})
    if not cash:
        return Criterion("market_fit", 60, 0.3, translate("Sem culturas comerciais."))
    vals, unknown, nobuyer = [], [], []
    for c in cash:
        if c in ctx.constraints.buyer_crops:
            vals.append(1.0)
        elif c in ctx.constraints.no_buyer_crops:
            vals.append(0.0)
            nobuyer.append(ctx.catalog.crop(c).name)
        else:
            vals.append(0.5)
            unknown.append(ctx.catalog.crop(c).name)
    expl = []
    if nobuyer:
        expl.append(translate("Sem comprador informado para {0}.", ', '.join(nobuyer)))
    if unknown:
        expl.append(translate("Mercado não informado para {0}.", ', '.join(unknown)))
    if not expl:
        expl.append(translate("Há comprador conhecido para todas as culturas comerciais."))
    return Criterion("market_fit", clamp(statistics.fmean(vals) * 100), 0.8 if not unknown else 0.3, " ".join(expl),
                     {"unknown": unknown, "no_buyer": nobuyer})


CRITERIA_FUNCS = {
    "save_water": crit_water,
    "soil_structure": crit_structure,
    "n_fixation": crit_nitrogen,
    "erosion_control": crit_erosion,
    "organic_matter": crit_organic,
    "pest_break": crit_pests,
    "forage": crit_forage,
    "extra_income": crit_income,
    "market_fit": crit_market,
    "climate_risk": crit_climate,
}


# ------------------------------------------------------------------ filtros duros
def hard_filters(ctx: Ctx, rot: Rotation) -> list[str]:
    reasons: list[str] = []
    cat = ctx.catalog
    for s in rot.steps:
        for slug in s.crops:
            c = cat.crop(slug)
            if slug in ctx.constraints.excluded_crops:
                reasons.append(translate("{0} foi excluída por você.", c.name))
            missing = [e for e in c["equipment"] if e in ctx.constraints.missing_equipment]
            if missing:
                reasons.append(translate("{0} exige {1}, que você informou não ter.", c.name, cat.equipment[missing[0]].lower()))
            tmeans = [ctx.monthly[m]["tmean_c"] for m in s.months if ctx.monthly[m]["tmean_c"] is not None]
            if tmeans and min(tmeans) < c["t_base_c"]:
                reasons.append(translate("{0}: temperatura média abaixo da base ({1} °C) durante o ciclo.", c.name, c['t_base_c']))
            pf = max((ctx.monthly[m]["frost_prob"].get("2.0") or 0) for m in s.months)
            if (c["frost_tolerance"] == "none" and pf >= 0.3) or (c["frost_tolerance"] == "low" and pf >= 0.5):
                reasons.append(translate("{0}: geada em {1}% dos anos na janela de cultivo.", c.name, round(100 * pf)))
            if ctx.soil and ctx.soil.ph_water is not None:
                lo, hi = c["ph_range"]
                if ctx.soil.ph_water < lo - 1.0 or ctx.soil.ph_water > hi + 0.5:
                    reasons.append(translate("{0}: pH {1} fora da faixa tolerada ({2}–{3}) sem correção viável.", c.name, ctx.soil.ph_water, lo, hi))
        if s.water_check:
            w = step_water(ctx, s)
            if w["share_years_over_filter"] >= 0.5:
                reasons.append(
                    translate(
                        "{0} ({1}): falta mais da metade da água necessária em {2}% dos anos.",
                        cat.crop(s.crops[0]).name,
                        months_txt([s.sow_month]),
                        round(100 * w['share_years_over_filter']),
                    )
                )
    # mesma família em sequência com praga/doença compartilhada (inclui a volta para o próximo ano)
    seq = rot.steps + rot.steps[:1] if len(rot.steps) > 1 else []
    for a, b in zip(seq, seq[1:]):
        for ca in a.crops:
            for cb in b.crops:
                if cb in a.crops:  # mesma planta continuando (ex.: braquiária do consórcio)
                    continue
                A, B = cat.crop(ca), cat.crop(cb)
                if A.family != B.family:
                    continue
                shared = [p for p, info in cat.pests.items()
                          if info.get("sequence_filter") and A.pest_role(p) == "host" and B.pest_role(p) == "host"]
                if shared:
                    names = [cat.pests[p]["name"].split(" (")[0].lower() for p in shared]
                    reasons.append(translate(
                        "{0} seguida de {1}: mesma família ({2}) e ambas hospedam {3}.",
                        A.name,
                        B.name,
                        A.family,
                        months_join(names),
                    ))
    return list(dict.fromkeys(reasons))
