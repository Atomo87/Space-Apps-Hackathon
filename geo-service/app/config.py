"""Configuração do geo-service via variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Lê geo-service/.env (segredos locais) sem sobrescrever variáveis já definidas no ambiente."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    power_base_url: str = os.environ.get("POWER_BASE_URL", "https://power.larc.nasa.gov").rstrip("/")
    power_timeout: float = float(_env_int("POWER_TIMEOUT", 90))
    power_concurrency: int = _env_int("POWER_CONCURRENCY", 4)
    start_year: int = _env_int("POWER_START_YEAR", 2005)
    end_year: int = _env_int("POWER_END_YEAR", 2025)
    community: str = "ag"
    time_standard: str = "lst"
    # Obrigatórias: ETo FAO-56 precisa de temperatura, umidade (orvalho), vento, radiação e pressão.
    core_parameters: tuple[str, ...] = (
        "T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS",
    )
    # Opcionais: se a API recusar (HTTP 422), refazemos sem elas e registramos a lacuna.
    optional_parameters: tuple[str, ...] = ("GWETROOT", "GWETTOP")
    # Elevação SRTM GL1 (~30 m, NASA/USGS) servida pela API pública OpenTopoData (sem chave, até 100 pontos por chamada).
    terrain_base_url: str = os.environ.get("TERRAIN_BASE_URL", "https://api.opentopodata.org/v1/srtm30m").rstrip("/")
    terrain_timeout: float = float(_env_int("TERRAIN_TIMEOUT", 30))
    # Produtos da NASA (LP DAAC) espelhados no Microsoft Planetary Computer — públicos, sem chave.
    pc_stac_url: str = os.environ.get("PC_STAC_URL", "https://planetarycomputer.microsoft.com/api/stac/v1").rstrip("/")
    pc_data_url: str = os.environ.get("PC_DATA_URL", "https://planetarycomputer.microsoft.com/api/data/v1").rstrip("/")
    pc_concurrency: int = _env_int("PC_CONCURRENCY", 10)
    pc_timeout: float = float(_env_int("PC_TIMEOUT", 20))
    ndvi_years: int = _env_int("NDVI_YEARS", 5)  # MODIS NDVI 250 m
    hls_years: int = _env_int("HLS_YEARS", 2)  # HLS NDVI 30 m (0 desliga)
    lst_years: int = _env_int("LST_YEARS", 3)  # MODIS LST 1 km (Terra)
    et_years: int = _env_int("ET_YEARS", 5)  # MODIS ET/PET anual 500 m
    # Token de serviço NASA Earthdata (SMAP, GPM, ECOSTRESS, GRACE-FO). Vazio = esses conjuntos ficam desligados.
    earthdata_token: str = os.environ.get("EARTHDATA_TOKEN", "")
    earthdata_concurrency: int = _env_int("EARTHDATA_CONCURRENCY", 10)
    earthdata_timeout: float = float(_env_int("EARTHDATA_TIMEOUT", 60))
    smap_years: int = _env_int("SMAP_YEARS", 2)
    smap_step_days: int = _env_int("SMAP_STEP_DAYS", 5)  # uma passagem a cada N dias (cada leitura é uma requisição)
    gpm_years: int = _env_int("GPM_YEARS", 10)
    ecostress_years: int = _env_int("ECOSTRESS_YEARS", 2)
    cache_dir: Path = Path(os.environ.get("CACHE_DIR", Path(__file__).resolve().parent.parent / "cache"))
    # Token compartilhado com o Laravel (cabeçalho X-GeoSafra-Token). Vazio = sem verificação (dev).
    api_token: str = os.environ.get("GEOSAFRA_TOKEN", "")
    cors_origins: list[str] = field(
        default_factory=lambda: [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
    )


settings = Settings()

POWER_CITATION = (
    "NASA Langley Research Center (LaRC) POWER Project, financiado pelo NASA Earth Science/"
    "Applied Science Program. https://power.larc.nasa.gov"
)
POWER_GRID_NOTE = (
    "Dados em grade (~0,5° × 0,625° para meteorologia, MERRA-2; ~1° para radiação, CERES). "
    "Representam a região do talhão, não uma estação dentro dele."
)
SRTM_CITATION = (
    "NASA Shuttle Radar Topography Mission (SRTM) Global 1 arc second (~30 m), NASA JPL / USGS EROS. "
    "https://doi.org/10.5066/F7PR7TFT — consultado via OpenTopoData (https://www.opentopodata.org)."
)
MODIS_CITATION = (
    "Didan, K. (2021). MODIS/Terra e MODIS/Aqua Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 "
    "(MOD13Q1/MYD13Q1). NASA EOSDIS Land Processes DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.061 — "
    "consultado via Microsoft Planetary Computer (https://planetarycomputer.microsoft.com)."
)
HLS_CITATION = (
    "NASA Harmonized Landsat and Sentinel-2 (HLS) v2.0 — HLSL30 e HLSS30, 30 m. NASA LP DAAC. "
    "https://doi.org/10.5067/HLS/HLSL30.002 e https://doi.org/10.5067/HLS/HLSS30.002 — via Microsoft Planetary Computer."
)
LST_CITATION = (
    "Wan, Z., Hook, S., Hulley, G. (2021). MODIS/Terra Land Surface Temperature/Emissivity 8-Day L3 Global 1km "
    "SIN Grid V061 (MOD11A2). NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD11A2.061 — via Microsoft Planetary Computer."
)
ET_CITATION = (
    "Running, S., Mu, Q., Zhao, M., Moreno, A. (2021). MODIS/Terra Net Evapotranspiration Gap-Filled Yearly L4 Global "
    "500m SIN Grid V061 (MOD16A3GF). NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD16A3GF.061 — via Microsoft Planetary Computer."
)
SMAP_CITATION = (
    "O'Neill, P. E. et al. (2023). SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture, "
    "Version 6 (SPL3SMP_E). NASA NSIDC DAAC. https://doi.org/10.5067/M20OXIZHY3RJ — via OPeNDAP Earthdata Cloud."
)
GPM_CITATION = (
    "Huffman, G. J. et al. (2023). GPM IMERG Final Precipitation L3 1 month 0.1° × 0.1° V07 (GPM_3IMERGM). "
    "NASA GES DISC. https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07 — via OPeNDAP Earthdata Cloud."
)
ECOSTRESS_CITATION = (
    "Fisher, J. B. et al. ECOSTRESS Tiled Evaporative Stress Index PT-JPL Instantaneous L4 Global 70 m V002 (ECO_L4T_ESI). "
    "NASA LP DAAC. https://doi.org/10.5067/ECOSTRESS/ECO_L4T_ESI.002"
)
GRACE_CITATION = (
    "Wiese, D. N. et al. (2023). JPL GRACE and GRACE-FO Mascon Ocean, Ice, and Hydrology Equivalent Water Height "
    "Coastal Resolution Improvement (CRI) Filtered RL06.3Mv04. NASA PO.DAAC. https://doi.org/10.5067/TEMSC-3JC63"
)
ENGINE_VERSION = "0.5.0-spaceapps"
DISCLAIMER = (
    "Esta ferramenta apoia, mas não substitui, o conhecimento do agricultor e da assistência técnica local."
)
