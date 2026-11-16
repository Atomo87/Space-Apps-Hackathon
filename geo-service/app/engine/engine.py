"""Motor de rotação explicável — orquestra diagnóstico, filtros, pontuação, seleção e explicação."""

from __future__ import annotations

import statistics
from typing import Any

from app.i18n import tr as translate
from app.catalog.loader import Catalog, load_catalog
from app.climate.indicators import MONTH_NAMES, RAINY_SEASON
from app.config import DISCLAIMER, ENGINE_VERSION
from app.engine.criteria import (
    CLIMATE_RISK_WEIGHT, br, CRITERIA_FUNCS, CRITERIA_LABELS, Criterion, Ctx, hard_filters, interp_threshold, months_txt,
)
from app.engine.rotation import CASH, Rotation, current_rotation, rotation_from_template
from app.engine.scenario import apply_scenario
from app.schemas import AnalysisRequest

LABELS = "ABCD"
HUMAN_JUDGMENT = [
    "Pressão local de pragas e doenças e resistência a defensivos.",
    "Mercado real, logística e contratos.",
    "Disponibilidade de sementes, máquinas e mão de obra.",
    "Microclima (baixadas de geada, encharcamento) menor que o pixel do satélite.",
    "Tradição, preferências e segurança alimentar da família.",
]


def level(conf: float) -> str:
    return "alta" if conf >= 0.7 else "media" if conf >= 0.5 else "baixa"


def dataset_ref(ctx: Ctx) -> dict[str, Any]:
    return {"datasets": ["POWER"], "period": ctx.period}


# ======================================================================= diagnóstico
def build_diagnosis(ctx: Ctx, history_meta: dict[str, Any]) -> dict[str, Any]:
    prof = ctx.profile
    cal = [dict(c) for c in prof["calendar"]]
    cur = ctx.current
    cur_active = cur.active_months() if cur else {}
    bare = set(history_meta.get("bare_months") or [])
    vulnerable = []
    veg = ctx.vegetation
    prim, _ = veg_primary(veg) if veg else (None, None)
    prim_month = {vm["month"]: vm for vm in prim["monthly"]} if prim else {}
    modis_month = {vm["month"]: vm for vm in veg["monthly"]} if veg else {}
    lst = (ctx.stress or {}).get("lst")
    lst_month = {lm["month"]: lm for lm in lst["monthly"]} if lst else {}
    smap = (ctx.earthdata or {}).get("smap")
    smap_month = {sm["month"]: sm for sm in smap["monthly"]} if smap else {}
    for c in cal:
        m = c["month"]
        c["bare_soil"] = (2 if m in RAINY_SEASON else 1) if m in bare else 0
        if veg:
            # 30 m (HLS) onde houver mediana do mês; senão a série longa de 250 m (MODIS).
            vm = prim_month[m] if prim_month[m]["p50"] is not None else modis_month[m]
            c["low_green"] = vm["level"]
            c["ndvi_p50"] = vm["p50"]
        if lst:
            c["hot_surface"] = lst_month[m]["level"]
            c["lst_p50"] = lst_month[m]["p50"]
        if smap:
            c["soil_dry"] = smap_month[m]["level"]
            c["sm_p50"] = smap_month[m]["p50"]
        c["current_crops"] = sorted({ctx.catalog.crop(s).name for st in cur_active.get(m, []) for s in st.crops})
        risks = []
        for st in cur_active.get(m, []):
            crop = ctx.catalog.crop(st.crops[0])
            hd = interp_threshold(ctx.monthly[m]["heat_days"], crop["t_heat_stress_c"])
            if hd >= 2:
                risks.append(translate("calor acima de {0} °C (~{1} dias)", format(crop['t_heat_stress_c'], '.0f'), format(hd, '.0f')))
            fp = ctx.monthly[m]["frost_prob"].get("2.0") or 0
            if fp >= 0.1 and crop["frost_tolerance"] in ("none", "low"):
                risks.append(translate("geada em {0}% dos anos", round(100 * fp)))
            if c["drought"] == 2:
                risks.append(translate("falta de água / veranico"))
            if c["heavy_rain"] == 2:
                risks.append(translate("chuva extrema"))
        if risks:
            vulnerable.append({"month": m, "name": c["name"], "crops": c["current_crops"], "risks": list(dict.fromkeys(risks))})

    hl: list[dict[str, Any]] = []
    s = prof["season"]
    if s.get("pct_seasons_dry_spell_ge_10") is not None:
        hl.append({"key": "dry_spell", "text": translate("Veranico de 10 dias ou mais em {0}% das safras (média do maior veranico: {1} dias).", format(s['pct_seasons_dry_spell_ge_10'], '.0f'), format(s['dry_spell_mean_max_days'], '.0f')), **dataset_ref(ctx)})
    neg = [m["month"] for m in prof["monthly"] if (m["water_balance_mm"] or 0) < -20]
    if neg:
        worst = min(prof["monthly"], key=lambda m: m["water_balance_mm"] or 0)
        hl.append({"key": "water_deficit", "text": translate("Chuva abaixo da evapotranspiração em {0}; pior mês: {1} ({2} mm).", months_txt(neg), translate(worst['name']), format(worst['water_balance_mm'], '.0f')), **dataset_ref(ctx)})
    if bare:
        hl.append({"key": "bare_soil", "text": translate("Pelo seu histórico, o solo fica descoberto em {0} (~{1} dias no último ano).", months_txt(sorted(bare)), history_meta['bare_days']), "datasets": [translate("Histórico informado")], "period": translate("últimos 12 meses")})
    heavy = [c["month"] for c in cal if c["heavy_rain"] == 2]
    if heavy:
        hl.append({"key": "heavy_rain", "text": translate("Chuvas fortes (acima de {0} mm/dia) concentradas em {1}.", format(prof['extremes']['p95_wet_day_mm'], '.0f'), months_txt(heavy)), **dataset_ref(ctx)})
    hot = [c["month"] for c in cal if c["heat"] == 2]
    if hot:
        hl.append({"key": "heat", "text": translate("Dias acima de 34 °C frequentes em {0}.", months_txt(hot)), **dataset_ref(ctx)})
    frost = [c["month"] for c in cal if c["frost"] >= 1]
    if frost:
        hl.append({"key": "frost", "text": translate("Risco de geada (mínima ≤ 2 °C na grade) em {0} — baixadas podem ter mais risco.", months_txt(frost)), **dataset_ref(ctx)})
    t = ctx.terrain
    if t:
        hl.append({"key": "slope", "text": translate(
            "Relevo {0}: declividade média de {1}% (10% do talhão acima de {2}%), {3}–{4} m de altitude.",
            translate(t['relief_class']),
            br(t['slope_pct']['mean']),
            br(t['slope_pct']['p90']),
            t['elevation_m']['min'],
            t['elevation_m']['max'],
        ),
                   "datasets": ["SRTM"], "period": "2000"})
    if veg:
        hl.extend(vegetation_highlights(veg, bare))
    rain_year = sum((m["rain_mm"]["mean"] or 0) for m in prof["monthly"]) or None
    if ctx.stress:
        hl.extend(stress_highlights(ctx.stress, ctx.monthly, rain_year))
    if ctx.earthdata:
        hl.extend(earthdata_highlights(ctx.earthdata, rain_year))
    tr = prof["trends"]["tmax_c"]
    if tr.get("per_decade") is not None and tr.get("p_value") is not None and tr["p_value"] < 0.1:
        hl.append({"key": "trend_tmax", "text": translate("Temperatura máxima com tendência de {0}{1} °C por década (Mann-Kendall p = {2}).", '+' if tr['per_decade'] > 0 else '', br(tr['per_decade']), br(tr['p_value'], 2)), **dataset_ref(ctx)})
    trr = prof["trends"]["rain_mm"]
    if trr.get("per_decade") is not None and trr.get("p_value") is not None and trr["p_value"] < 0.1:
        hl.append({"key": "trend_rain", "text": translate("Chuva anual com tendência de {0}{1} mm por década (Mann-Kendall p = {2}).", '+' if trr['per_decade'] > 0 else '', br(trr['per_decade'], 0), br(trr['p_value'], 2)), **dataset_ref(ctx)})

    return {
        "calendar": cal,
        "current": {
            "title": cur.title,
            "steps": [st.as_dict(ctx.catalog) for st in cur.steps],
            **history_meta,
        } if cur else None,
        "current_crop_vulnerable": vulnerable,
        "highlights": hl,
        "monthly": [
            {k: m[k] for k in ("month", "name", "rain_mm", "eto_mm", "water_balance_mm", "tmax_c", "tmin_c", "tmean_c",
                               "dry_spell_max_days", "extreme_rain_days", "soil_moisture_root", "frost_days_mean")}
            | {"heat_days_34": m["heat_days"].get("34"), "frost_prob": m["frost_prob"].get("2.0")}
            for m in prof["monthly"]
        ],
        "season": prof["season"],
        "extremes": prof["extremes"],
        "trends": prof["trends"],
        "recent": prof["recent"],
        "yearly": prof["yearly"],
        "source": prof["source"],
        "confidence": {"value": ctx.climate_conf, "level": level(ctx.climate_conf), "notes": prof["confidence"]["notes"]},
        "scenario": prof.get("scenario_applied"),
        "terrain": t,
        "vegetation": veg,
        "stress": ctx.stress,
        "earthdata": earthdata_for_view(ctx.earthdata, rain_year),
    }


def earthdata_for_view(ed: dict[str, Any] | None, power_rain_year: float | None) -> dict[str, Any] | None:
    """Acrescenta ao GPM a comparação com a chuva da NASA POWER (o motor tem as duas séries)."""
    if not ed:
        return None
    out = dict(ed)
    gpm = ed.get("gpm")
    if gpm and power_rain_year:
        out["gpm"] = {**gpm, "power_annual_mm": round(power_rain_year), "vs_power_pct": round(100 * (gpm["annual_mm"] / power_rain_year - 1))}
    return out


def earthdata_highlights(ed: dict[str, Any], power_rain_year: float | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    smap = ed.get("smap")
    if smap:
        dry = [translate(MONTH_NAMES[m - 1]) for m in smap["dry_months"]]
        rec = smap["recent"]
        text = (translate("Umidade do solo medida pelo satélite SMAP: mais seco em {0} e mais úmido em {1}", translate(smap['driest']), translate(smap['wettest']))
                + (translate("; meses mais secos para este solo: {0}", ', '.join(dry)) if dry else "") + ".")
        if rec.get("sm") is not None and rec.get("anomaly") is not None:
            text += (translate(
                " Último mês: {0} m³/m³, {1} do normal ({2}{3}).",
                br(rec['sm'], 2),
                translate('acima' if rec['anomaly'] >= 0 else 'abaixo'),
                '+' if rec['anomaly'] >= 0 else '',
                br(rec['anomaly'], 2),
            ))
        out.append({"key": "smap", "text": text, "datasets": ["SMAP"], "period": f"{smap['coverage']['start'][:4]}–{smap['coverage']['end'][:4]}"})
    gpm = ed.get("gpm")
    if gpm:
        text = translate("Chuva medida por satélite (GPM IMERG): ~{0} mm/ano.", gpm['annual_mm'])
        if power_rain_year:
            diff = round(100 * (gpm["annual_mm"] / power_rain_year - 1))
            agree = translate("as duas fontes concordam") if abs(diff) <= 15 else translate("diferença relevante; confira com o pluviômetro da fazenda")
            text += translate(" A NASA POWER estima {0} mm ({1}{2}%) — {3}.", format(power_rain_year, '.0f'), '+' if diff >= 0 else '', diff, agree)
        if gpm.get("last12_anomaly_pct") is not None:
            a = gpm["last12_anomaly_pct"]
            text += translate(" Últimos 12 meses: {0} mm ({1}{2}% em relação à média).", gpm['last12_mm'], '+' if a >= 0 else '', a)
        out.append({"key": "gpm", "text": text, "datasets": ["GPM", "POWER"], "period": f"{gpm['coverage']['start'][:4]}–{gpm['coverage']['end'][:4]}"})
    eco = ed.get("ecostress")
    if eco:
        out.append({"key": "ecostress", "text": (
            translate(
                "Estresse da planta no próprio talhão (ECOSTRESS, 70 m, {0} passagens sem nuvem): índice de estresse evaporativo mediano de {1} — estresse {2}; em {3}% das passagens a vegetação evaporou menos de 30% do possível.",
                len(eco['observations']),
                br(eco['median_esi'], 2),
                translate(eco['stress']),
                eco['high_stress_pct'],
            )),
            "datasets": ["ECOSTRESS"], "period": f"{eco['observations'][0]['datetime'][:4]}–{eco['latest']['datetime'][:4]}"})
    gr = ed.get("grace")
    if gr:
        trend = gr.get("trend_cm_per_decade")
        p = gr.get("trend_p_value")
        sig = p is not None and p < 0.1
        text = (translate("Água armazenada na região (GRACE/GRACE-FO, blocos de ~300 km): hoje {0} cm em relação a 2004–2009", br(gr['latest']['cm'], 1))
                + (translate(", com tendência de {0}{1} cm por década (Mann-Kendall p = {2})", '+' if trend > 0 else '', br(trend, 1), br(p, 2)) if trend is not None and sig else "")
                + translate(". Menor nível da série: {0} ({1} cm).", gr['record_low']['date'][:7], br(gr['record_low']['cm'], 1)))
        if sig and trend is not None and trend < 0:
            text += translate(" Aquíferos e rios da região perdendo água pedem cautela com irrigação e culturas exigentes.")
        out.append({"key": "grace", "text": text, "datasets": ["GRACE-FO"], "period": f"{gr['coverage']['start'][:4]}–{gr['coverage']['end'][:4]}"})
    return out


def veg_period(veg: dict[str, Any]) -> str:
    return f"{veg['coverage']['start'][:4]}–{veg['coverage']['end'][:4]}"


def veg_primary(veg: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """NDVI de referência: HLS 30 m (escala do talhão) quando cobre ao menos 10 meses; senão MODIS 250 m."""
    hls = veg.get("hls")
    if hls and sum(m["p50"] is not None for m in hls["monthly"]) >= 10:
        return hls, "HLS"
    return veg, "MODIS"


def vegetation_highlights(veg: dict[str, Any], bare: set[int]) -> list[dict[str, Any]]:
    """Destaques do NDVI, cruzados com o solo descoberto que o produtor informou."""
    out: list[dict[str, Any]] = []
    prim, code = veg_primary(veg)
    ref = {"datasets": [code], "period": veg_period(prim)}
    scale = "30 m" if code == "HLS" else "250 m"
    low = prim["low_green_months"]
    peak = prim.get("peak")
    peak_txt = translate("; pico de verde em {0} (NDVI {1})", translate(peak['name']), br(peak['ndvi'], 2)) if peak else ""
    if low:
        text = (translate(
            "O satélite ({0}, {1}) vê pouca vegetação verde (NDVI mediano abaixo de {2}) em {3}{4}.",
            code,
            scale,
            br(prim['thresholds']['low_green'], 2),
            months_txt(low),
            peak_txt,
        ))
        both = sorted(bare & set(low))
        if both:
            text += translate(" Coincide com o solo descoberto do seu histórico em {0}.", months_txt(both))
        out.append({"key": "ndvi_low", "text": text, **ref})
    else:
        out.append({"key": "ndvi_low", "text": translate(
            "O satélite ({0}, {1}) vê vegetação verde no talhão o ano todo (NDVI mediano acima de {2}){3}.",
            code,
            scale,
            br(prim['thresholds']['low_green'], 2),
            peak_txt,
        ), **ref})
    rec = prim["recent"]
    if rec.get("below_p10") and rec.get("anomaly") is not None and rec["days_ago"] <= 60:
        out.append({"key": "ndvi_recent", "text": translate(
            "NDVI recente ({0} em {1}) abaixo do normal para a época ({2}): confira no campo se há seca, falha de estande ou colheita antecipada.",
            br(rec['ndvi'], 2),
            rec['date'],
            br(rec['anomaly'], 2),
        ), **ref})
    tr = veg["trend"]
    if tr.get("per_year") is not None and tr.get("p_value") is not None and tr["p_value"] < 0.1:
        out.append({"key": "ndvi_trend", "text": translate(
            "Verde médio do talhão com tendência de {0}{1} de NDVI por década (Mann-Kendall p = {2}, {3} anos).",
            '+' if tr['per_year'] > 0 else '',
            br(tr['per_year'] * 10, 2),
            br(tr['p_value'], 2),
            tr['years'],
        ),
                    "datasets": ["MODIS"], "period": veg_period(veg)})
    return out


def stress_highlights(stress: dict[str, Any], monthly: dict[int, dict[str, Any]], rain_mm_year: float | None) -> list[dict[str, Any]]:
    """Temperatura da superfície (MODIS LST) × temperatura do ar (POWER) e ET/PET (MODIS)."""
    out: list[dict[str, Any]] = []
    lst = stress.get("lst")
    if lst and lst.get("hottest"):
        h = lst["hottest"]
        gaps = [(m["month"], m["p50"] - monthly[m["month"]]["tmax_c"]) for m in lst["monthly"]
                if m["p50"] is not None and monthly[m["month"]].get("tmax_c") is not None]
        period = f"{lst['coverage']['start'][:4]}–{lst['coverage']['end'][:4]}"
        if lst["hot_months"]:
            text = (translate(
                "Superfície quente (acima de {0} °C na mediana, por volta das 10h30) em {1}; pico em {2} ({3} °C, até {4} °C em 1 de cada 10 semanas).",
                br(lst['thresholds']['warm_c'], 0),
                months_txt(lst['hot_months']),
                translate(h['name']),
                br(h['p50'], 1),
                br(h['p90'], 1),
            ))
        else:
            text = translate("A superfície não passa de {0} °C na mediana; o mês mais quente é {1} ({2} °C).", br(lst['thresholds']['warm_c'], 0), translate(h['name']), br(h['p50'], 1))
        worst = max(gaps, key=lambda g: g[1]) if gaps else None
        if worst and worst[1] >= 3:
            text += (translate(
                " Em {0} ela fica {1} °C acima da máxima do ar (POWER): sinal de solo exposto ou de planta sem água para transpirar.",
                translate(MONTH_NAMES[worst[0] - 1]),
                br(worst[1], 1),
            ))
        out.append({"key": "lst", "text": text, "datasets": ["MODIS LST", "POWER"], "period": period})
    et = stress.get("et")
    if et:
        years = et["yearly"]
        text = (translate(
            "A vegetação evaporou ~{0} mm/ano, {1}% do que o ar pediria ({2} mm): estresse hídrico observado {3}. Ano mais seco: {4} ({5}%).",
            format(et['et_mm'], '.0f'),
            round(100 * et['ratio']),
            format(et['pet_mm'], '.0f'),
            translate(et['stress']),
            et['driest_year']['year'],
            round(100 * et['driest_year']['ratio']),
        ))
        if rain_mm_year:
            text += translate(" A chuva média é de {0} mm/ano.", format(rain_mm_year, '.0f'))
        out.append({"key": "et_ratio", "text": text, "datasets": ["MODIS ET"], "period": f"{years[0]['year']}–{years[-1]['year']}"})
    return out


# ======================================================================= pontuação
def weights_from(priorities: dict[str, int]) -> dict[str, float]:
    w = {k: float(v) for k, v in priorities.items()}
    if sum(w.values()) == 0:
        w = {k: 1.0 for k in w}
    w["climate_risk"] = float(CLIMATE_RISK_WEIGHT)
    return w


def score_rotation(ctx: Ctx, rot: Rotation, weights: dict[str, float]) -> dict[str, Any]:
    crits: dict[str, Criterion] = {k: f(ctx, rot) for k, f in CRITERIA_FUNCS.items()}
    wsum = sum(weights.values())
    total = sum(weights[k] * crits[k].score for k in crits) / wsum
    conf = sum(weights[k] * crits[k].confidence for k in crits) / wsum
    ys = crits["save_water"].details.get("yearly_scores") or []
    rng = None
    if ys:
        other = total * wsum - weights["save_water"] * crits["save_water"].score
        alt = sorted((other + weights["save_water"] * y) / wsum for y in ys)
        rng = {"p10": round(alt[int(0.1 * (len(alt) - 1))]), "p90": round(alt[int(0.9 * (len(alt) - 1))])}
    return {"rotation": rot, "criteria": crits, "score": total, "confidence": conf, "range": rng}


def dominant(scored: dict[str, Any], ref: dict[str, Any] | None, weights: dict[str, float]) -> str:
    def gain(k: str) -> float:
        base = ref["criteria"][k].score if ref else 50
        return (scored["criteria"][k].score - base) * (weights[k] + 0.5)
    return max((k for k in scored["criteria"] if k != "climate_risk"), key=gain)


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def select(candidates: list[dict[str, Any]], ref: dict[str, Any] | None, weights: dict[str, float], k: int = 3) -> list[dict[str, Any]]:
    """Melhores notas com diversidade: evita três variações da mesma coisa (doc 06 §2.4)."""
    pool = sorted(candidates, key=lambda s: s["score"], reverse=True)
    chosen: list[dict[str, Any]] = []
    for s in pool:
        crops = set(s["rotation"].crop_slugs())
        dom = dominant(s, ref, weights)
        too_close = any(
            jaccard(crops, set(c["rotation"].crop_slugs())) > 0.6 or (dom == c["dominant"] and jaccard(crops, set(c["rotation"].crop_slugs())) > 0.3)
            for c in chosen
        )
        if not too_close:
            s["dominant"] = dom
            chosen.append(s)
        if len(chosen) == k:
            break
    for s in pool:  # completa se a diversidade deixou faltar
        if len(chosen) >= k:
            break
        if s not in chosen:
            s["dominant"] = dominant(s, ref, weights)
            chosen.append(s)
    return chosen


# ======================================================================= explicação
def explain(ctx: Ctx, s: dict[str, Any], ref: dict[str, Any] | None, diag: dict[str, Any], weights: dict[str, float], req: AnalysisRequest) -> dict[str, Any]:
    rot: Rotation = s["rotation"]
    cr: dict[str, Criterion] = s["criteria"]
    cat = ctx.catalog
    hl = {h["key"]: h for h in diag["highlights"]}

    # ---- justificativa
    if rot.is_current:
        rationale = translate("É o que você já faz; serve de referência para comparar as alternativas.")
    else:
        ctx_bits = []
        dom = s.get("dominant")
        if dom in ("erosion_control", "soil_structure", "organic_matter", "forage", "n_fixation", "pest_break") and "bare_soil" in hl:
            ctx_bits.append(hl["bare_soil"]["text"])
        if dom in ("save_water", "climate_risk") and "dry_spell" in hl:
            ctx_bits.append(hl["dry_spell"]["text"])
        if dom in ("save_water",) and "water_deficit" in hl:
            ctx_bits.append(hl["water_deficit"]["text"])
        if dom == "erosion_control" and "heavy_rain" in hl:
            ctx_bits.append(hl["heavy_rain"]["text"])
        if dom == "erosion_control" and "slope" in hl and (ctx.terrain or {}).get("ls_relative", 1) > 1.2:
            ctx_bits.append(hl["slope"]["text"])
        if not ctx_bits and diag["highlights"]:
            ctx_bits.append(diag["highlights"][0]["text"])
        rationale = " ".join(ctx_bits[:2]) + translate(" Foco desta opção: {0}.", rot.focus[0].lower() + rot.focus[1:])
        if dom and ref:
            delta = s["criteria"][dom].score - ref["criteria"][dom].score
            if delta > 0:
                rationale += translate(" Comparada ao que você faz hoje, o maior ganho é em {0} (+{1} pontos).", translate(CRITERIA_LABELS[dom]).lower(), format(delta, '.0f'))
        elif dom:
            rationale += translate(" Ponto mais forte: {0}.", translate(CRITERIA_LABELS[dom]).lower())

    # ---- evidências (dado + fonte + período)
    ev: list[dict[str, Any]] = []
    for key in ("water_deficit", "dry_spell", "heavy_rain", "bare_soil", "heat", "frost"):
        if key in hl and len(ev) < 3:
            ev.append({"text": hl[key]["text"], "datasets": hl[key]["datasets"], "period": hl[key]["period"], "indicator": key})
    ev.append({"text": translate("Uso de água: {0}", cr['save_water'].explanation), "datasets": ["POWER", translate("Catálogo GeoSafra")], "period": ctx.period, "indicator": "water_balance"})
    ev.append({"text": translate("Erosão: {0}", cr['erosion_control'].explanation),
               "datasets": ["POWER", *(["SRTM"] if ctx.terrain else []), translate("Catálogo GeoSafra")], "period": ctx.period, "indicator": "erosion_cover"})
    if "ndvi_low" in hl:
        ev.append({"text": translate("Cobertura observada: {0}", hl['ndvi_low']['text']), "datasets": hl["ndvi_low"]["datasets"],
                   "period": hl["ndvi_low"]["period"], "indicator": "ndvi"})
    if "et_ratio" in hl:
        ev.append({"text": translate("Água observada: {0}", hl['et_ratio']['text']), "datasets": hl["et_ratio"]["datasets"],
                   "period": hl["et_ratio"]["period"], "indicator": "et_ratio"})
    for key, prefix in (("ecostress", translate("Estresse no talhão")), ("grace", translate("Água na região"))):
        if key in hl:
            ev.append({"text": f"{prefix}: {hl[key]['text']}", "datasets": hl[key]["datasets"], "period": hl[key]["period"], "indicator": key})
    ev.append({"text": translate("Pragas:{0}", cr['pest_break'].explanation), "datasets": [translate("Catálogo GeoSafra (hipótese)")], "period": "—", "indicator": "pest_break"})

    # ---- benefícios (comparação com a atual)
    benefits: list[str] = []
    if ref and not rot.is_current:
        rc = ref["criteria"]
        for k, c in cr.items():
            d = c.score - rc[k].score
            if d >= 10:
                benefits.append(translate("{0}: +{1} pontos em relação ao que você faz hoje", translate(CRITERIA_LABELS[k]), format(d, '.0f')))
        bare_now = len(ref["criteria"]["soil_structure"].details.get("bare_months", []))
        bare_new = len(cr["soil_structure"].details.get("bare_months", []))
        if bare_now > bare_new:
            benefits.append(translate("{0} mês(es) a menos de solo descoberto", bare_now - bare_new))
        dw_now = rc["save_water"].details.get("deficit_frac_p50")
        dw_new = cr["save_water"].details.get("deficit_frac_p50")
        if dw_now and dw_new is not None and dw_new < dw_now * 0.85:
            if dw_new < 0.02:
                benefits.append(translate(
                    "Praticamente sem falta de água estimada num ano típico (a atual tem ~{0}%)",
                    round(100 * dw_now),
                ))
            else:
                benefits.append(translate("−{0}% de falta de água estimada num ano típico", round(100 * (1 - dw_new / dw_now))))
    n = cr["n_fixation"].details.get("n_kg_ha", 0)
    if n >= 40:
        benefits.append(translate("~{0} kg N/ha deixados para a próxima cultura (estimativa)", n))
    if cr["forage"].details.get("forage_months", 0) >= 2:
        benefits.append(translate("Forragem na entressafra seca"))
    if rot.is_current and not benefits:
        benefits.append(translate("Sistema conhecido: sem custo de aprendizado nem de sementes novas"))

    # ---- lacunas de informação
    gaps: list[str] = []
    if not req.soil or req.soil.source == "unknown":
        gaps.append(translate("Sem análise de solo: textura e pH não confirmados (água no solo assumida em 70 mm)."))
    elif req.soil.source == "farmer_estimate":
        gaps.append(translate("Solo estimado pelo produtor, sem análise de laboratório."))
    gaps.extend(translate("{0}: mercado comprador não informado.", x) for x in cr["market_fit"].details.get("unknown", []))
    if ctx.terrain:
        gaps.append(translate(
            "Declividade estimada pelo SRTM (pixel de 30 m) com rampa assumida de {0} m: terraços, curvas de nível e sulcos não aparecem no satélite.",
            format(ctx.terrain['slope_length_assumed_m'], '.0f'),
        ))
    else:
        gaps.append(translate("Declividade não disponível para este talhão: a erosão considera só chuva e cobertura."))
    veg = ctx.vegetation
    if veg:
        prim, code = veg_primary(veg)
        if code == "HLS":
            gaps.append(translate(
                "NDVI de 30 m (HLS) só de 2 anos e com poucas imagens sem nuvem nos meses chuvosos; palhada seca aparece com NDVI baixo, parecido com solo exposto.",
            ))
        else:
            gaps.append(translate(
                "NDVI MODIS com pixel de 250 m (~6 ha): em talhão pequeno ou estreito mistura a vegetação vizinha, e palhada seca aparece com NDVI baixo, parecido com solo exposto.",
            ))
        bare_hist = set(diag["current"].get("bare_months") or []) if diag.get("current") else set()
        sat_only = sorted(set(prim["low_green_months"]) - bare_hist)
        if bare_hist and sat_only:
            gaps.append(translate(
                "O satélite vê pouco verde em {0}, mas seu histórico não indica solo descoberto: pode ser palhada seca, cultura senescente ou safra não informada — vale conferir.",
                months_txt(sat_only),
            ))
    else:
        gaps.append(translate("Cobertura verde por satélite (NDVI MODIS) indisponível para este talhão."))
    st = ctx.stress or {}
    if st.get("lst") or st.get("et"):
        gaps.append(translate(
            "Temperatura da superfície (1 km) e evapotranspiração (500 m) do MODIS incluem a vizinhança do talhão e não substituem a observação da lavoura no campo.",
        ))
    else:
        gaps.append(translate("Estresse térmico e hídrico observado por satélite (MODIS LST e ET) indisponível para este talhão."))
    ed = ctx.earthdata or {}
    missing_ed = [n for n, k in (("SMAP", "smap"), ("GPM", "gpm"), ("ECOSTRESS", "ecostress"), ("GRACE-FO", "grace")) if not ed.get(k)]
    if ed and len(missing_ed) < 4:
        gaps.append(translate("SMAP (9 km) e GRACE-FO (~300 km) descrevem a região; só o ECOSTRESS (70 m) enxerga o talhão, e nuvens limitam as passagens."))
    if missing_ed:
        gaps.append(translate("Sem {0} nesta análise (conjuntos que exigem login NASA Earthdata).", ', '.join(missing_ed)))
    if ctx.profile["source"].get("missing_optional"):
        gaps.append(translate("Umidade do solo da NASA POWER indisponível para este ponto."))
    hyp = sorted({cat.crop(c).name for c in rot.crop_slugs()})
    gaps.append(translate("Atributos de {0} vêm de um catálogo simplificado com hipóteses a validar.", ', '.join(hyp)))
    gaps.append(translate("Dado climático em grade de ~50 km: não capta o microclima do talhão."))

    # ---- riscos para revisão local
    risks: list[str] = []
    for c in rot.crop_slugs():
        risks.extend(cat.crop(c)["local_review_risks"])
    for st in rot.steps:
        if st.note:
            risks.append(st.note)
    for stp in cr["climate_risk"].details.get("steps", []):
        if stp["loss"] >= 0.25 and stp["reasons"]:
            risks.append(f"{cat.crop(stp['crop']).name}: " + "; ".join(stp["reasons"]))
    if ctx.terrain and ctx.terrain["slope_pct"]["mean"] >= 12 and cr["erosion_control"].details.get("exposed_rainy_months"):
        risks.append(translate(
            "Declividade de ~{0}% com solo exposto em meses chuvosos: confirme terraceamento, plantio em nível e manutenção da palhada.",
            br(ctx.terrain['slope_pct']['mean']),
        ))
    if cr["forage"].details.get("forage_months", 0) >= 2 and not req.constraints.has_livestock:
        risks.append(translate("Forragem só gera valor se houver gado próprio ou comprador."))

    # ---- conflitos explícitos
    conflicts = []
    hi = [k for k, c in cr.items() if c.score >= 70 and weights.get(k, 0) > 0]
    lo = [k for k, c in cr.items() if c.score <= 35 and weights.get(k, 0) > 0]
    if hi and lo:
        conflicts.append(translate("Boa para {0}, mas fraca em {1}.", ', '.join((translate(CRITERIA_LABELS[k]).lower() for k in hi[:2])), ', '.join((translate(CRITERIA_LABELS[k]).lower() for k in lo[:2]))))

    conf = s["confidence"]
    return {
        "key": rot.key,
        "is_current": rot.is_current,
        "title": rot.title,
        "focus": rot.focus,
        "steps": [st.as_dict(cat) for st in rot.steps],
        "cover_by_month": [{"month": m, "factor": f, "kind": kind} for m, (f, kind) in sorted(rot.cover_by_month(cat).items())],
        "score": round(s["score"]),
        "score_range": s["range"],
        "confidence": {"value": round(conf, 2), "level": level(conf)},
        "low_confidence_badge": conf < 0.5,
        "criteria": [
            {
                "key": k, "label": translate(CRITERIA_LABELS[k]), "score": round(c.score),
                "weight": weights[k], "weighted": round(weights[k] * c.score / sum(weights.values()), 1),
                "confidence": round(c.confidence, 2), "explanation": c.explanation,
                "delta_vs_current": (round(c.score - ref["criteria"][k].score) if ref and not rot.is_current else None),
            }
            for k, c in cr.items()
        ],
        "rationale": rationale.strip(),
        "evidences": ev,
        "benefits": list(dict.fromkeys(benefits)),
        "information_gaps": list(dict.fromkeys(gaps)),
        "local_review_risks": list(dict.fromkeys(risks)),
        "conflicts": conflicts,
    }


# ======================================================================= entrada principal
def run(req: AnalysisRequest, catalog: Catalog | None = None) -> dict[str, Any]:
    catalog = (catalog or load_catalog()).localized()
    profile = apply_scenario(req.climate, req.scenario.rain_delta_pct, req.scenario.temp_delta_c)
    cur, hmeta = current_rotation(req.history, catalog)
    terrain = req.terrain if req.terrain and req.terrain.get("slope_pct") else None
    vegetation = req.vegetation if req.vegetation and len(req.vegetation.get("monthly") or []) == 12 else None
    stress = req.stress if req.stress and (req.stress.get("lst") or req.stress.get("et")) else None
    earthdata = req.earthdata if req.earthdata and any(req.earthdata.get(k) for k in ("smap", "gpm", "ecostress", "grace")) else None
    ctx = Ctx(profile=profile, catalog=catalog, field=req.field, soil=req.soil, constraints=req.constraints, current=cur,
              terrain=terrain, vegetation=vegetation, stress=stress, earthdata=earthdata)
    diag = build_diagnosis(ctx, hmeta)
    weights = weights_from(req.priorities.model_dump())

    ref = score_rotation(ctx, cur, weights) if cur and cur.steps else None
    discarded, candidates = [], []
    for tpl in catalog.templates:
        rot = rotation_from_template(tpl)
        if cur and rot.signature() == cur.signature():
            continue
        reasons = hard_filters(ctx, rot)
        if reasons:
            discarded.append({"key": rot.key, "title": rot.title, "reasons": reasons})
            continue
        candidates.append(score_rotation(ctx, rot, weights))

    chosen = select(candidates, ref, weights, k=3)
    ordered = ([ref] if ref else []) + chosen
    strategies = []
    for i, s in enumerate(ordered):
        out = explain(ctx, s, ref, diag, weights, req)
        out["label"] = LABELS[i] if i < len(LABELS) else str(i + 1)
        strategies.append(out)

    bbox = catalog.region_bbox
    region_ok = bbox["lat_min"] <= req.field.latitude <= bbox["lat_max"] and bbox["lon_min"] <= req.field.longitude <= bbox["lon_max"]
    warnings = []
    if not region_ok:
        warnings.append(translate("O catálogo e os modelos de rotação foram montados para o Cerrado brasileiro; fora dessa região, trate as sugestões como exploratórias."))
    if not cur:
        warnings.append(translate("Sem histórico de safras: não há estratégia atual (A) para comparar e o solo descoberto não foi estimado."))
    if terrain and terrain["slope_pct"]["mean"] >= 20:
        warnings.append(translate(
            "Relevo {0} (~{1}% de declividade): culturas anuais com preparo de solo têm alto risco de erosão; priorize cobertura permanente e consulte um técnico sobre conservação do solo.",
            translate(terrain['relief_class']),
            br(terrain['slope_pct']['mean']),
        ))

    sources = [
        {"code": "POWER", "name": "NASA POWER (Prediction Of Worldwide Energy Resources)", "citation": profile["source"]["citation"],
         "period": ctx.period, "resolution": profile["source"]["grid_note"], "api_version": profile["source"].get("api_version")},
    ]
    if terrain:
        sources.append({"code": "SRTM", "name": "NASA SRTM (Shuttle Radar Topography Mission) GL1", "citation": terrain.get("citation"),
                        "period": "2000", "resolution": "~30 m"})
    if vegetation:
        sources.append({"code": "MODIS", "name": translate("NASA MODIS NDVI (MOD13Q1/MYD13Q1 v061, Terra e Aqua)"), "citation": vegetation.get("citation"),
                        "period": veg_period(vegetation), "resolution": translate("250 m, composições de 16 dias")})
        if vegetation.get("hls"):
            h = vegetation["hls"]
            sources.append({"code": "HLS", "name": translate("NASA HLS v2.0 (Landsat 8/9 + Sentinel-2 harmonizados)"), "citation": h.get("citation"),
                            "period": veg_period(h), "resolution": translate("30 m, a cada 2–5 dias (sem nuvem)")})
    if stress and stress.get("lst"):
        lst = stress["lst"]
        sources.append({"code": "MODIS LST", "name": translate("NASA MODIS temperatura da superfície (MOD11A2 v061)"), "citation": lst.get("citation"),
                        "period": f"{lst['coverage']['start'][:4]}–{lst['coverage']['end'][:4]}", "resolution": translate("1 km, composições de 8 dias")})
    if stress and stress.get("et"):
        et = stress["et"]
        sources.append({"code": "MODIS ET", "name": translate("NASA MODIS evapotranspiração (MOD16A3GF v061)"), "citation": et.get("citation"),
                        "period": f"{et['yearly'][0]['year']}–{et['yearly'][-1]['year']}", "resolution": translate("500 m, anual")})
    for key, code, name, res in (("smap", "SMAP", translate("NASA SMAP umidade do solo (SPL3SMP_E v6)"), translate("9 km, diário (amostrado)")),
                                 ("gpm", "GPM", translate("NASA GPM IMERG Final V07 (chuva mensal)"), translate("0,1° (~11 km), mensal")),
                                 ("ecostress", "ECOSTRESS", translate("NASA ECOSTRESS índice de estresse evaporativo (ECO_L4T_ESI v002)"), translate("70 m, por passagem")),
                                 ("grace", "GRACE-FO", translate("NASA/JPL GRACE e GRACE-FO mascons (RL06.3 v04 CRI)"), translate("~300 km, mensal"))):
        d = (earthdata or {}).get(key)
        if d:
            cov = d.get("coverage") or {}
            start = cov.get("start") or (d.get("observations") or [{}])[0].get("datetime", "")
            end = cov.get("end") or (d.get("latest") or {}).get("datetime", "")
            sources.append({"code": code, "name": name, "citation": d.get("citation"), "period": f"{str(start)[:4]}–{str(end)[:4]}", "resolution": res})
    sources.append({"code": "CATALOGO", "name": translate("Catálogo GeoSafra de culturas"), "citation": catalog.disclaimer, "period": None, "resolution": None})

    return {
        "engine_version": ENGINE_VERSION,
        "catalog_version": catalog.version,
        "disclaimer": DISCLAIMER,
        "scenario": req.scenario.model_dump(),
        "weights": [{"key": k, "label": translate(CRITERIA_LABELS[k]), "weight": w, "adjustable": k != "climate_risk"} for k, w in weights.items()],
        "diagnosis": diag,
        "strategies": strategies,
        "discarded": discarded,
        "warnings": warnings,
        "human_judgment": [translate(item) for item in HUMAN_JUDGMENT],
        "sources": sources,
    }
