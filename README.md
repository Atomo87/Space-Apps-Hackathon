# GeoSafra 🛰️🌾

**Crop rotation decision support with NASA data**: challenge *Turning Point in the Field: adapting farms with NASA data*, NASA Space Apps Challenge 2026, Uberlândia (MG, Brazil).

For a given field, GeoSafra shows **when** it is left uncovered, **in which months** the current crop is most vulnerable (heat, drought/dry spells, frost, heavy rain), and **compares the current rotation with 2 or 3 alternatives**. Each alternative comes with the reasoning, the evidence (with source and period), the benefits, the information gaps, and the risks that need local review. The tool supports the farmer and the agronomist but does not replace them.

## Architecture

```
Farmer (phone) ─► Laravel 12 + Inertia/Vue (Hostinger)  ─HTTP─►  Python/FastAPI geo-service (Render)  ─►  NASA POWER (climate)
                   accounts, registration, MySQL, UI         climate, FAO-56 ETo, indicators,      ─►  SRTM 30 m (terrain)
                   stores ClimateProfile + terrain           slope/LS, catalog and engine
```

**NASA data used:** NASA POWER (daily climate from 2005 to 2025) and SRTM (~30 m elevation for slope and erosion). The point-by-point mapping to the challenge text is in **[docs/alinhamento-desafio.md](docs/alinhamento-desafio.md)**.

| Part | Owner | Folder |
|---|---|---|
| Web application (A1–A6) | Person A | `app/`, `resources/js/`, `database/`, `routes/` |
| Data and engine (B2–B5) | Person B | `geo-service/` |
| Contract between the parts (B1) | Both | `docs/contrato-b1.md`, `resources/js/types/contract.ts`, `docs/exemplos/` |
| Integration (B6) | Both | `app/Services/GeoServiceClient.php`, `app/Jobs/AnalyzeFieldJob.php` |

**Flow:** the user signs in and saves the field → the browser calls `POST /api/v1/fields/{id}/process` → Laravel asks the geo-service for the **ClimateProfile** (about 21 years of daily NASA POWER data, already processed) and the **terrain** (SRTM grid over the field boundary) → Laravel stores both in MySQL. From then on, **priorities and scenarios are recalculated without querying NASA again** (`GET /api/v1/fields/{id}/analysis`). If the terrain request fails, the analysis continues without it and records the gap.

**Accounts and privacy:** sign-up and login with email and password (Laravel session, CSRF, limit of 5 attempts per email/IP). Each user sees and edits **only their own fields** (`FieldPolicy`/`FarmPolicy` policies). The **Uberlândia example** is public and read-only: any visitor can open it and simulate priorities and scenarios without saving anything. Users with an account get an editable copy.

## Running locally

Requirements: PHP 8.2+, Composer, Node 20+, Python 3.11+, MySQL 8 (or SQLite for testing).

```bash
# 1) geo-service (terminal 1)
cd geo-service
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q                                                 # 51 tests
uvicorn app.main:app --port 8001 --reload

# 2) Laravel (terminal 2)
cp .env.example .env            # set DB_* (or DB_CONNECTION=sqlite)
composer install
php artisan key:generate
php artisan migrate --seed      # creates tables, copies the catalog and (only with APP_ENV=local) the test account
                                # — email and password at the top of database/seeders/TestUserSeeder.php
npm install && npm run dev      # or npm run build
php artisan serve               # http://127.0.0.1:8000
```

On the home page, click **"Ver exemplo em Uberlândia (MG)"** ("See the Uberlândia example"; no account needed). The example opens a field with soybean → second-crop corn → fallow and fetches real NASA data. The first request takes 20 to 90 s. After that, the result is cached. To register your own field, click **Criar conta** ("Create account").

Laravel tests: `php artisan test` (25 tests; uses `Http::fake` and blocks any real internet access).
PHP style: `vendor/bin/pint`. Front-end types: `npm run typecheck`.
Manual integration test: `php artisan geosafra:ping` and `php artisan geosafra:analyze {id}`.

**Upgrading from a version without login?** Run `php artisan migrate` and, after creating your account at `/cadastro`, assign the old (ownerless) fields to it with `php artisan geosafra:claim you@email.com`.

**CI:** `.github/workflows/ci.yml` runs Pint + Pest (PHP 8.2 and 8.3), front-end typecheck + build, and the geo-service pytest on every push and pull request.

## Deployment (Hostinger + Render)

See **[docs/deploy.md](docs/deploy.md)**. Summary:
1. **Render:** *New → Blueprint* pointing to this repository (`render.yaml`). Copy the generated `GEOSAFRA_TOKEN`.
2. **Hostinger (shared hosting):** upload the project **with `vendor/` and `public/build/`** (run `composer install --no-dev` and `npm run build` on your machine), point the domain to `public/`, set `GEO_SERVICE_URL` and `GEO_SERVICE_TOKEN` in `.env`, and run `php artisan migrate --seed --force`.
3. Optional: create a cron job running `php artisan schedule:run` every minute. It pings Render every 10 min so the service doesn't "sleep" during the presentation.

Shared hosting has no queue worker. Processing is triggered by the browser, with a lock to prevent duplicates.

## Architecture decisions (hackathon)

| # | Decision | Why |
|---|---|---|
| 1 | **NASA POWER** for climate (temperature, rainfall, dew point, wind, radiation, pressure, GWETROOT soil moisture) + **SRTM** for terrain + **MODIS NDVI** and **HLS** (30 m) for green cover + **MODIS LST** and **MODIS ET/PET** for observed heat and water | Keyless REST APIs: POWER has a daily series since 1981; SRTM (via OpenTopoData) gives 30 m elevation in one call per field; MOD13Q1/MYD13Q1 NDVI comes from the NASA LP DAAC mirror on Microsoft Planetary Computer (the ORNL subsetting API was unstable), as do HLS, LST (MOD11A2) and ET (MOD16A3GF). SMAP, GPM IMERG, ECOSTRESS and GRACE-FO are added with a NASA Earthdata service token (`EARTHDATA_TOKEN` in `geo-service/.env`, kept out of git); for GPM, the account must have accepted the GES DISC EULA |
| 2 | Python stays **only** on the B side (Render) | Hostinger shared hosting can't run Python. Laravel never calls NASA |
| 3 | Geometry as GeoJSON (JSON) + centroid | POWER answers per point, so we don't need a spatial POLYGON in the MVP |
| 4 | Strategies computed on demand (deterministic) | Changing priorities or scenarios responds instantly, with no strategy cache tables |
| 5 | **Rules + multi-criteria** engine, no ML to choose the rotation | It must be auditable: every score is traceable to a piece of data and a rule |
| 6 | 9 criteria mapped 1:1 to the 9 priorities, plus "climate safety" with a fixed weight of 3 | Fixes the mismatch between priorities and criteria in docs 05/06 |
| 7 | Crop catalog versioned in JSON (`geo-service/app/catalog/`) | Every attribute has a source or is flagged as a **hypothesis to be validated**. Laravel copies the catalog through the seeder |

## Limitations (mention in the presentation)

- Climate data on a ~50 km grid: it doesn't capture frost-prone lowlands or microclimates.
- Simplified catalog with attributes flagged as hypotheses. It needs to be validated with agronomists from the region.
- Erosion uses rainfall, cover and slope (SRTM, 30 m pixel, assumed 100 m slope length). Soil type (K factor) and conservation practices are not included yet.
- Satellite data is read at the center of the field: HLS NDVI (30 m, 2 years) or MODIS (250 m), land surface temperature (1 km) and evapotranspiration (500 m, annual). Larger pixels mix in the surroundings, and dry straw looks like bare soil. That's why they feed the diagnosis and the evidence but don't change the score.
- The first analysis of a field takes 2 to 5 minutes (hundreds of pixel reads on Planetary Computer and NASA Earthdata); later ones use the cache.
- SMAP (9 km), GPM (~11 km) and GRACE-FO (~300 km) describe the region, not the field; ECOSTRESS (70 m) sees the field, but clouds leave only ~1 in 3 passes usable.
- The Earthdata service token expires (the current one on 2027-01-14): generate a new one at urs.earthdata.nasa.gov and replace `EARTHDATA_TOKEN`.
- Scenarios adjust historical climate. They are not weather forecasts.
- No password recovery by email (it requires a configured email service). Data can be deleted at any time with the "Excluir" ("Delete") button.

## Documentation

- [Challenge alignment](docs/alinhamento-desafio.md) · [B1 contract](docs/contrato-b1.md) · [Indicators (B3)](docs/indicadores.md) · [Engine (B5)](docs/motor.md) · [Deployment](docs/deploy.md) · [Presentation script (J2)](docs/apresentacao.md)

## Attribution

Data: NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science/Applied Science Program (<https://power.larc.nasa.gov>).
Elevation: NASA Shuttle Radar Topography Mission (SRTM) GL1, NASA JPL / USGS EROS (<https://doi.org/10.5066/F7PR7TFT>), via OpenTopoData.
Erosion: Renard, K. G. et al. (1997). *RUSLE*. USDA Agriculture Handbook 703; McCool, D. K. et al. (1987).
ETo: Allen, R. G.; Pereira, L. S.; Raes, D.; Smith, M. (1998). *Crop evapotranspiration*. FAO Irrigation and Drainage Paper 56.
Maps: imagery © Esri, Maxar, Earthstar Geographics; © OpenStreetMap contributors.
