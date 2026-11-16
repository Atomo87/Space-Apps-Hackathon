# GeoSafra 🛰️🌾

**Apoio à decisão de rotação de culturas com dados da NASA**: desafio *Virada no Campo: adaptando fazendas com dados da NASA*, NASA Space Apps Challenge 2026, Uberlândia (MG).

Para um talhão, o GeoSafra mostra **quando** ele fica descoberto, **em que meses** a lavoura atual é mais vulnerável (calor, seca/veranico, geada, chuva forte) e **compara a rotação atual com 2 ou 3 alternativas**. Cada alternativa traz o porquê, as evidências (com fonte e período), os benefícios, as lacunas de informação e os riscos que precisam de revisão local. A ferramenta apoia, mas não substitui, o agricultor e o técnico.

## Arquitetura

```
Produtor (celular) ─► Laravel 12 + Inertia/Vue (Hostinger)  ─HTTP─►  geo-service Python/FastAPI (Render)  ─►  NASA POWER (clima)
                       contas, cadastro, MySQL, telas                   clima, ETo FAO-56, indicadores,      ─►  SRTM 30 m (relevo)
                       guarda ClimateProfile + relevo                   declividade/LS, catálogo e motor
```

**Dados da NASA usados:** NASA POWER (clima diário de 2005 a 2025) e SRTM (elevação de ~30 m para declividade e erosão). O mapa ponto a ponto com o texto do desafio está em **[docs/alinhamento-desafio.md](docs/alinhamento-desafio.md)**.

| Parte | Responsável | Pasta |
|---|---|---|
| Aplicação web (A1–A6) | Pessoa A | `app/`, `resources/js/`, `database/`, `routes/` |
| Dados e motor (B2–B5) | Pessoa B | `geo-service/` |
| Contrato entre as partes (B1) | Dupla | `docs/contrato-b1.md`, `resources/js/types/contract.ts`, `docs/exemplos/` |
| Integração (B6) | Dupla | `app/Services/GeoServiceClient.php`, `app/Jobs/AnalyzeFieldJob.php` |

**Fluxo:** o usuário entra na conta e salva o talhão → o navegador chama `POST /api/v1/fields/{id}/process` → o Laravel pede ao geo-service o **ClimateProfile** (cerca de 21 anos de NASA POWER diária, já processados) e o **relevo** (grade SRTM sobre o contorno do talhão) → o Laravel guarda os dois no MySQL. Depois disso, **prioridades e cenários são recalculados sem consultar a NASA de novo** (`GET /api/v1/fields/{id}/analysis`). Se o relevo falhar, a análise segue sem ele e registra a lacuna.

**Contas e privacidade:** cadastro e login por e-mail e senha (sessão do Laravel, CSRF, limite de 5 tentativas por e-mail/IP). Cada usuário vê e altera **só os próprios talhões** (policies `FieldPolicy`/`FarmPolicy`). O **exemplo de Uberlândia** é público e somente leitura: qualquer visitante pode abrir e simular prioridades e cenários sem gravar nada. Quem tem conta ganha uma cópia editável.

## Rodando localmente

Requisitos: PHP 8.2+, Composer, Node 20+, Python 3.11+, MySQL 8 (ou SQLite para testar).

```bash
# 1) geo-service (terminal 1)
cd geo-service
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q                                                 # 51 testes
uvicorn app.main:app --port 8001 --reload

# 2) Laravel (terminal 2)
cp .env.example .env            # ajuste DB_* (ou DB_CONNECTION=sqlite)
composer install
php artisan key:generate
php artisan migrate --seed      # cria tabelas, copia o catálogo e (só em APP_ENV=local) a conta de teste
                                # — e-mail e senha no topo de database/seeders/TestUserSeeder.php
npm install && npm run dev      # ou npm run build
php artisan serve               # http://127.0.0.1:8000
```

Na página inicial, clique em **"Ver exemplo em Uberlândia (MG)"** (não precisa de conta). O exemplo abre um talhão com soja → milho safrinha → pousio e busca os dados reais da NASA. A primeira consulta leva de 20 a 90 s. Depois disso, o resultado fica em cache. Para cadastrar o seu talhão, clique em **Criar conta**.

Testes do Laravel: `php artisan test` (25 testes; usa `Http::fake` e bloqueia qualquer acesso real à internet).
Estilo do PHP: `vendor/bin/pint`. Tipos do front-end: `npm run typecheck`.
Teste manual da integração: `php artisan geosafra:ping` e `php artisan geosafra:analyze {id}`.

**Atualizando de uma versão sem login?** Rode `php artisan migrate` e, depois de criar sua conta em `/cadastro`, atribua a ela os talhões antigos (sem dono) com `php artisan geosafra:claim seu@email.com`.

**CI:** `.github/workflows/ci.yml` roda Pint + Pest (PHP 8.2 e 8.3), typecheck + build do front-end e pytest do geo-service em cada push e pull request.

## Deploy (Hostinger + Render)

Veja **[docs/deploy.md](docs/deploy.md)**. Resumo:
1. **Render:** *New → Blueprint* apontando para este repositório (`render.yaml`). Copie o `GEOSAFRA_TOKEN` gerado.
2. **Hostinger (compartilhada):** envie o projeto **com `vendor/` e `public/build/`** (rode `composer install --no-dev` e `npm run build` na sua máquina), aponte o domínio para `public/`, configure `.env` com `GEO_SERVICE_URL` e `GEO_SERVICE_TOKEN` e rode `php artisan migrate --seed --force`.
3. Opcional: crie um cron com `php artisan schedule:run` a cada minuto. Ele pinga o Render a cada 10 min para o serviço não "dormir" durante a apresentação.

Na hospedagem compartilhada não há worker de fila. O processamento é disparado pelo navegador, com um lock contra duplicidade.

## Decisões de arquitetura (hackathon)

| # | Decisão | Por quê |
|---|---|---|
| 1 | **NASA POWER** para o clima (temperatura, chuva, orvalho, vento, radiação, pressão, umidade do solo GWETROOT) + **SRTM** para o relevo + **MODIS NDVI** e **HLS** (30 m) para a cobertura verde + **MODIS LST** e **MODIS ET/PET** para calor e água observados | APIs REST sem chave: POWER tem série diária desde 1981; SRTM (via OpenTopoData) dá elevação de 30 m em uma chamada por talhão; o NDVI MOD13Q1/MYD13Q1 vem do espelho da NASA LP DAAC no Microsoft Planetary Computer (a API de subconjuntos da ORNL estava instável), assim como HLS, LST (MOD11A2) e ET (MOD16A3GF). SMAP, GPM IMERG, ECOSTRESS e GRACE-FO entram com um token de serviço NASA Earthdata (`EARTHDATA_TOKEN` em `geo-service/.env`, fora do git); para o GPM, a conta precisa ter aceitado o EULA da GES DISC |
| 2 | Python fica **só** na frente B (Render) | A Hostinger compartilhada não roda Python. O Laravel nunca chama a NASA |
| 3 | Geometria como GeoJSON (JSON) + centróide | O POWER responde por ponto, então não precisamos de POLYGON espacial no MVP |
| 4 | Estratégias calculadas sob demanda (determinísticas) | Mudar prioridades ou cenários responde na hora, sem tabelas de cache de estratégia |
| 5 | Motor **regras + multicritério**, sem ML para escolher a rotação | Precisa ser auditável: toda nota é rastreável até um dado e uma regra |
| 6 | 9 critérios ligados 1:1 às 9 prioridades, mais "segurança climática" com peso fixo 3 | Corrige o descasamento entre prioridades e critérios dos docs 05/06 |
| 7 | Catálogo de culturas versionado em JSON (`geo-service/app/catalog/`) | Cada atributo tem fonte ou marca de **hipótese a validar**. O Laravel copia o catálogo pelo seeder |

## Limitações (dizer na apresentação)

- Dado climático em grade de ~50 km: não capta baixadas de geada nem microclima.
- Catálogo simplificado com atributos marcados como hipótese. Precisa ser validado com agrônomos da região.
- A erosão usa chuva, cobertura e declividade (SRTM, pixel de 30 m, rampa assumida de 100 m). O tipo de solo (fator K) e as práticas de conservação ainda não entram.
- Os dados de satélite são lidos no centro do talhão: NDVI HLS (30 m, 2 anos) ou MODIS (250 m), temperatura da superfície (1 km) e evapotranspiração (500 m, anual). Os pixels maiores misturam a vizinhança, e palhada seca parece solo exposto. Por isso eles entram no diagnóstico e nas evidências, mas não alteram a nota.
- A primeira análise de um talhão leva de 2 a 5 minutos (centenas de leituras de pixel no Planetary Computer e na NASA Earthdata); as seguintes usam o cache.
- SMAP (9 km), GPM (~11 km) e GRACE-FO (~300 km) descrevem a região, não o talhão; o ECOSTRESS (70 m) vê o talhão, mas nuvens deixam só ~1 em cada 3 passagens utilizável.
- O token de serviço Earthdata expira (o atual, em 14/01/2027): gere outro em urs.earthdata.nasa.gov e troque `EARTHDATA_TOKEN`.
- Os cenários ajustam o clima histórico. Não são previsão do tempo.
- Sem recuperação de senha por e-mail (precisa de um serviço de e-mail configurado). Os dados podem ser excluídos a qualquer momento pelo botão "Excluir".

## Documentação

- [Alinhamento com o desafio](docs/alinhamento-desafio.md) · [Contrato B1](docs/contrato-b1.md) · [Indicadores (B3)](docs/indicadores.md) · [Motor (B5)](docs/motor.md) · [Deploy](docs/deploy.md) · [Roteiro da apresentação (J2)](docs/apresentacao.md)

## Atribuição

Dados: NASA Langley Research Center (LaRC) POWER Project, financiado pelo NASA Earth Science/Applied Science Program (<https://power.larc.nasa.gov>).
Elevação: NASA Shuttle Radar Topography Mission (SRTM) GL1, NASA JPL / USGS EROS (<https://doi.org/10.5066/F7PR7TFT>), via OpenTopoData.
Erosão: Renard, K. G. et al. (1997). *RUSLE*. USDA Agriculture Handbook 703; McCool, D. K. et al. (1987).
ETo: Allen, R. G.; Pereira, L. S.; Raes, D.; Smith, M. (1998). *Crop evapotranspiration*. FAO Irrigation and Drainage Paper 56.
Mapas: imagens © Esri, Maxar, Earthstar Geographics; © colaboradores do OpenStreetMap.
