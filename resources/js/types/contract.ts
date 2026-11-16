/**
 * Contrato B1 — resposta de GET /api/v1/fields/{id}/analysis (repasse de POST /v1/analysis do geo-service).
 * Documentação: docs/contrato-b1.md · Exemplo (dados SINTÉTICOS): docs/exemplos/analysis.sintetico.json
 */

export type Level = 0 | 1 | 2;
export type ConfidenceLevel = 'alta' | 'media' | 'baixa';

export interface Evidence {
    text: string;
    datasets: string[];
    period: string;
    indicator?: string;
}

export interface CalendarMonth {
    month: number;
    name: string;
    heat: Level;
    frost: Level;
    drought: Level;
    heavy_rain: Level;
    bare_soil: Level;
    /** Pouca vegetação verde no satélite (NDVI MODIS). Ausente quando não há NDVI. */
    low_green?: Level;
    ndvi_p50?: number | null;
    /** Superfície quente no satélite (MODIS LST). Ausente quando não há LST. */
    hot_surface?: Level;
    lst_p50?: number | null;
    /** Solo seco para o próprio ponto (SMAP). Ausente sem SMAP. */
    soil_dry?: Level;
    sm_p50?: number | null;
    current_crops: string[];
}

export interface MonthlyClimate {
    month: number;
    name: string;
    rain_mm: { mean: number | null; p10: number | null; p50: number | null; p90: number | null };
    eto_mm: number | null;
    water_balance_mm: number | null;
    tmax_c: number | null;
    tmin_c: number | null;
    tmean_c: number | null;
    dry_spell_max_days: number | null;
    extreme_rain_days: number | null;
    soil_moisture_root: number | null;
    frost_days_mean: number | null;
    heat_days_34: number | null;
    frost_prob: number | null;
}

export interface Trend {
    per_decade: number | null;
    p_value: number | null;
    n_years: number;
}

export interface SourceInfo {
    dataset: string;
    dataset_code: string;
    api_version: string | null;
    parameters: Record<string, { units: string; longname: string }>;
    period: { start: string; end: string; years: number };
    location: { latitude: number; longitude: number; elevation_m: number | null };
    fetched_at: string;
    messages: string[];
    missing_optional: string[];
    grid_note: string;
    citation: string;
}

export interface Step {
    crops: string[];
    crop_names: string[];
    sow_month: number;
    end_month: number;
    months: number[];
    label: string;
    purpose: 'cash' | 'cover' | 'forage' | 'green_manure';
    note: string | null;
}

export interface Diagnosis {
    calendar: CalendarMonth[];
    current: null | {
        title: string;
        steps: Step[];
        window: { start: string; end: string } | null;
        bare_days: number | null;
        bare_months: number[];
        entries: number;
    };
    current_crop_vulnerable: { month: number; name: string; crops: string[]; risks: string[] }[];
    highlights: (Evidence & { key: string })[];
    monthly: MonthlyClimate[];
    season: {
        rainy_months: number[];
        dry_spells: { season: string; max_dry_spell_days: number }[];
        dry_spell_mean_max_days: number | null;
        dry_spell_p90_days: number | null;
        pct_seasons_dry_spell_ge_10: number | null;
        pct_seasons_dry_spell_ge_15: number | null;
    };
    extremes: {
        p95_wet_day_mm: number | null;
        annual_max_1day_mm_mean: number | null;
        annual_max_5day_mm_mean: number | null;
        annual_max_1day_mm_record: number | null;
    };
    trends: { rain_mm: Trend; tmax_c: Trend; tmin_c: Trend };
    recent: { years: number[]; rain_anomaly_pct: number | null; tmax_anomaly_c: number | null };
    yearly: { years: number[]; rain_mm: (number | null)[]; tmax_c: (number | null)[]; tmin_c: (number | null)[] };
    source: SourceInfo;
    confidence: { value: number; level: ConfidenceLevel; notes: string[] };
    scenario: null | { rain_delta_pct: number; temp_delta_c: number; notes: string[] };
    /** Relevo pelo SRTM (~30 m). null quando a elevação não pôde ser obtida. */
    terrain?: Terrain | null;
    /** Cobertura verde pelo NDVI MODIS (250 m). null quando o serviço de imagens falhou. */
    vegetation?: Vegetation | null;
    /** Estresse observado por satélite (MODIS LST e ET/PET). null quando o serviço falhou. */
    stress?: Stress | null;
    /** SMAP, GPM, ECOSTRESS e GRACE-FO (login NASA Earthdata). null sem token ou se tudo falhou. */
    earthdata?: Earthdata | null;
}

export interface Earthdata {
    smap: null | {
        dataset: string;
        source_note: string;
        citation: string;
        monthly: { month: number; name: string; n: number; p50: number | null; p10: number | null; level: Level }[];
        dry_months: number[];
        driest: string | null;
        wettest: string | null;
        recent: { sm: number | null; n: number; anomaly: number | null };
        series: { date: string; sm: number }[];
        coverage: { observations: number; valid: number; start: string; end: string };
    };
    gpm: null | {
        dataset: string;
        source_note: string;
        citation: string;
        monthly: { month: number; name: string; mean_mm: number | null; p10_mm: number | null }[];
        annual_mm: number;
        yearly: { year: number; mm: number }[];
        last12_mm: number;
        last12_anomaly_pct: number | null;
        power_annual_mm?: number;
        vs_power_pct?: number;
        coverage: { months: number; start: string; end: string };
    };
    ecostress: null | {
        dataset: string;
        source_note: string;
        citation: string;
        passes: number;
        observations: { datetime: string; esi: number }[];
        median_esi: number;
        high_stress_pct: number;
        latest: { datetime: string; esi: number };
        stress: 'baixo' | 'moderado' | 'alto';
        thresholds: { high_below: number; moderate_below: number };
    };
    grace: null | {
        dataset: string;
        source_note: string;
        citation: string;
        series: { date: string; cm: number }[];
        trend_cm_per_decade: number | null;
        trend_p_value: number | null;
        latest: { date: string; cm: number };
        recent12_mean_cm: number;
        record_low: { date: string; cm: number };
        coverage: { months: number; start: string; end: string };
    };
    notes: string[];
}

export interface Vegetation extends NdviSummary {
    composite_days: number;
    /** NDVI de 30 m (HLS). null quando faltou imagem sem nuvem ou o serviço falhou. */
    hls?: NdviSummary | null;
}

export interface Stress {
    lst: null | {
        dataset: string;
        resolution_m: number;
        source_note: string;
        citation: string;
        monthly: { month: number; name: string; n: number; p50: number | null; p90: number | null; hot_pct: number | null; level: Level }[];
        hot_months: number[];
        hottest: { month: number; name: string; p50: number; p90: number } | null;
        coverage: { observations: number; valid: number; start: string; end: string };
        thresholds: { warm_c: number; hot_c: number };
    };
    et: null | {
        dataset: string;
        resolution_m: number;
        source_note: string;
        citation: string;
        yearly: { year: number; et_mm: number; pet_mm: number; ratio: number }[];
        et_mm: number;
        pet_mm: number;
        ratio: number;
        stress: 'baixo' | 'moderado' | 'alto';
        driest_year: { year: number; et_mm: number; pet_mm: number; ratio: number };
    };
    notes: string[];
}

export interface NdviSummary {
    dataset: string;
    resolution_m: number;
    source_note: string;
    citation: string;
    monthly: { month: number; name: string; n: number; p10: number | null; p50: number | null; p90: number | null; level: Level }[];
    low_green_months: number[];
    peak: { month: number; name: string; ndvi: number } | null;
    trough: { month: number; name: string; ndvi: number } | null;
    recent: { date: string; days_ago: number; ndvi: number; anomaly: number | null; below_p10: boolean };
    trend: { per_year: number | null; p_value: number | null; years: number };
    series: { date: string; ndvi: number; image_date?: string; platform?: 'terra' | 'aqua' }[];
    coverage: { observations: number; valid: number; valid_pct: number; start: string; end: string };
    thresholds: { low_green: number; very_low_green: number };
}

export interface Terrain {
    dataset: string;
    resolution_m: number;
    source_note: string;
    citation: string;
    slope_pct: { mean: number; p90: number; max: number };
    elevation_m: { min: number; max: number; mean: number };
    relief_class: string;
    ls_factor: number;
    ls_relative: number;
    slope_length_assumed_m: number;
}

export type CriterionKey =
    | 'save_water'
    | 'soil_structure'
    | 'n_fixation'
    | 'erosion_control'
    | 'organic_matter'
    | 'pest_break'
    | 'forage'
    | 'extra_income'
    | 'market_fit'
    | 'climate_risk';

export interface CriterionScore {
    key: CriterionKey;
    label: string;
    score: number;
    weight: number;
    weighted: number;
    confidence: number;
    explanation: string;
    delta_vs_current: number | null;
}

export interface Strategy {
    key: string;
    label: 'A' | 'B' | 'C' | 'D' | string;
    is_current: boolean;
    title: string;
    focus: string;
    steps: Step[];
    cover_by_month: { month: number; factor: number; kind: string }[];
    score: number;
    score_range: { p10: number; p90: number } | null;
    confidence: { value: number; level: ConfidenceLevel };
    low_confidence_badge: boolean;
    criteria: CriterionScore[];
    rationale: string;
    evidences: Evidence[];
    benefits: string[];
    information_gaps: string[];
    local_review_risks: string[];
    conflicts: string[];
}

export interface AnalysisResponse {
    field_id: number;
    engine_version: string;
    catalog_version: string;
    disclaimer: string;
    scenario: { rain_delta_pct: number; temp_delta_c: number };
    weights: { key: CriterionKey; label: string; weight: number; adjustable: boolean }[];
    diagnosis: Diagnosis;
    strategies: Strategy[];
    discarded: { key: string; title: string; reasons: string[] }[];
    warnings: string[];
    human_judgment: string[];
    sources: { code: string; name: string; citation: string; period: string | null; resolution: string | null; api_version?: string | null }[];
    planting?: Planting | null;
}

/** Janela de plantio calculada no GeoSafra com a chuva e a temperatura diárias da NASA POWER. */
export interface PlantingWeek {
    date: string;
    label: string;
    years: number;
    score: number;
    p_onset: number | null;
    p_dry_spell: number;
    p_water: number;
    p_frost: number | null;
    heat_days: number;
}
export interface PlantingSeason {
    key: 'verao' | 'safrinha' | 'inverno' | string;
    label: string;
    crops: string;
    need_mm: number;
    weeks: PlantingWeek[];
    best: { start: string | null; end: string | null; score: number; level: 'good' | 'medium' | 'low' } | null;
}
export interface Planting {
    source: string;
    period: { start: number; end: number };
    rules: { onset_mm: number; dry_spell_days: number; frost_tmin_c: number; heat_tmax_c: number };
    seasons: PlantingSeason[];
}

/** Focos de queimada da NASA FIRMS perto do talhão. */
export interface Fires {
    configured: boolean;
    mode?: 'api' | 'regional';
    days: number;
    radius_km: number;
    source: string;
    points: { lat: number; lon: number; distance_km: number; date: string | null; time: string | null; frp: number | null; confidence: string | null; satellite: string }[];
    counts: Record<string, number> | null;
    nearest_km: number | null;
    fetched_at?: string;
}

export interface FieldStatus {
    id: number;
    status: 'pending' | 'processing' | 'ready' | 'error';
    message: string | null;
    analyzed_at: string | null;
    /** Andamento gravado no servidor (0–100) e segundos desde o início — a tela retoma daqui ao voltar. */
    progress?: number | null;
    elapsed_s?: number | null;
}

export type PriorityKey = Exclude<CriterionKey, 'climate_risk'>;
export type Priorities = Record<PriorityKey, number>;
