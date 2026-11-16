<#
.SYNOPSIS
  Envia para a Hostinger só os arquivos que mudaram desde o último deploy.

.DESCRIPTION
  Guarda em .deploy\manifest.tsv o hash de cada arquivo publicado. A cada execução:
    1. roda os testes e o build (a menos que você pule);
    2. compara o projeto com o manifesto e lista o que foi criado, alterado ou apagado;
    3. empacota só isso, envia por SSH, faz backup no servidor do que será trocado,
       copia o que é de public/ para public_html/geosafra (sem mexer no index.php de lá),
       roda as migrations quando há migration nova e refaz os caches do Laravel;
    4. confere se o site responde e só então atualiza o manifesto.

  O .env nunca é enviado.

.EXAMPLE
  .\deploy.cmd                  # testa, compila, mostra as mudanças e pede confirmação
.EXAMPLE
  .\deploy.cmd -DryRun          # só mostra o que seria enviado
.EXAMPLE
  .\deploy.cmd -Yes -SkipTests  # envia sem perguntar e sem rodar os testes
.EXAMPLE
  .\deploy.cmd -Seed AssistantKnowledgeSeeder   # roda também esse seeder no servidor
.EXAMPLE
  .\deploy.cmd -Baseline        # marca o estado local atual como já publicado (não envia nada)
#>
param(
    [switch]$DryRun,
    [switch]$Baseline,
    [switch]$SkipTests,
    [switch]$SkipBuild,
    [switch]$Yes,
    [string[]]$Seed = @()
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# ---- Configuração do servidor -------------------------------------------------
$SshKey    = Join-Path $HOME '.ssh\geosafra_hostinger'
$SshPort   = 65002
$SshTarget = 'u781005858@185.239.210.33'
$SiteUrl   = 'https://geosafra.softrix.com.br'
# Caminhos no servidor ficam no script bash mais abaixo (APP e PUB).

# ---- O que é publicado --------------------------------------------------------
$Include = @(
    'app', 'bootstrap', 'config', 'database', 'lang', 'public', 'resources', 'routes',
    'vendor', 'docs', 'geo-service/app/catalog', 'artisan', 'composer.json', 'composer.lock'
)
$ExcludeRegex = '^(bootstrap/cache/|public/hot$|public/storage(/|$)|vendor/pestphp/pest/\.temp/)|(^|/)\.env|(^|/)(\.DS_Store|Thumbs\.db)$'

$StateDir = Join-Path $Root '.deploy'
$Manifest = Join-Path $StateDir 'manifest.tsv'
$Utf8     = New-Object System.Text.UTF8Encoding $false

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "ERRO: $text" -ForegroundColor Red; exit 1 }

# ---- Testes e build -----------------------------------------------------------
if (-not $DryRun -and -not $Baseline) {
    if (-not $SkipTests) {
        Step 'Rodando os testes'
        php artisan test
        if ($LASTEXITCODE -ne 0) { Fail 'os testes falharam; nada foi enviado.' }
    }
    if (-not $SkipBuild) {
        Step 'Compilando o front-end (npm run build)'
        npm run build
        if ($LASTEXITCODE -ne 0) { Fail 'o build falhou; nada foi enviado.' }
    }
}

# ---- Detecta as mudanças ------------------------------------------------------
Step 'Procurando alterações'
$old = @{}
if (Test-Path $Manifest) {
    foreach ($line in [IO.File]::ReadAllLines($Manifest, $Utf8)) {
        $p = $line.Split("`t")
        if ($p.Count -eq 4) { $old[$p[0]] = $p }
    }
}

$sha = [Security.Cryptography.SHA1]::Create()
function Get-Hash([string]$path) {
    $s = [IO.File]::OpenRead($path)
    try { [BitConverter]::ToString($sha.ComputeHash($s)).Replace('-', '') } finally { $s.Dispose() }
}

$current = @{}
$changed = New-Object System.Collections.Generic.List[string]
$prefix  = $Root.Length + 1
foreach ($item in $Include) {
    $full = Join-Path $Root $item
    if (Test-Path $full -PathType Leaf) { $files = @(Get-Item $full -Force) }
    elseif (Test-Path $full) { $files = Get-ChildItem $full -Recurse -File -Force }
    else { continue }

    foreach ($f in $files) {
        $rel = $f.FullName.Substring($prefix).Replace('\', '/')
        if ($rel -match $ExcludeRegex) { continue }
        $size  = [string]$f.Length
        $ticks = [string]$f.LastWriteTimeUtc.Ticks
        $prev  = $old[$rel]
        if ($prev -and $prev[1] -eq $size -and $prev[2] -eq $ticks) { $hash = $prev[3] }
        else { $hash = Get-Hash $f.FullName }
        $current[$rel] = @($rel, $size, $ticks, $hash)
        if (-not $prev -or $prev[3] -ne $hash) { $changed.Add($rel) }
    }
}
$deleted = @($old.Keys | Where-Object { -not $current.ContainsKey($_) } | Sort-Object)

function Save-Manifest {
    if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory $StateDir | Out-Null }
    $lines = $current.Values | ForEach-Object { $_ -join "`t" } | Sort-Object
    [IO.File]::WriteAllLines($Manifest, [string[]]$lines, $Utf8)
}

if ($Baseline) {
    Save-Manifest
    Write-Host "Estado atual marcado como publicado ($($current.Count) arquivos). Nada foi enviado." -ForegroundColor Green
    exit 0
}
if (-not (Test-Path $Manifest)) {
    Write-Host 'Ainda não há manifesto: todos os arquivos seriam enviados.' -ForegroundColor Yellow
    Write-Host 'Se o servidor já está atualizado, rode primeiro:  .\deploy.cmd -Baseline' -ForegroundColor Yellow
}

if ($changed.Count -eq 0 -and $deleted.Count -eq 0 -and $Seed.Count -eq 0) {
    Write-Host 'Nada mudou desde o último deploy.' -ForegroundColor Green
    exit 0
}

$changed.Sort()
Write-Host ("{0} arquivo(s) novo(s) ou alterado(s), {1} apagado(s):" -f $changed.Count, $deleted.Count)
$changed | Group-Object { ($_ -split '/')[0] } | Sort-Object Name | ForEach-Object {
    Write-Host ("  {0,-12} {1,5} arquivo(s)" -f $_.Name, $_.Count)
}
$changed | Where-Object { $_ -notmatch '^(vendor|public/build)/' } | Select-Object -First 40 | ForEach-Object { Write-Host "    + $_" -ForegroundColor DarkGray }
$deleted | Where-Object { $_ -notmatch '^(vendor|public/build)/' } | Select-Object -First 20 | ForEach-Object { Write-Host "    - $_" -ForegroundColor DarkYellow }
if ($changed | Where-Object { $_ -like 'database/migrations/*' }) { Write-Host '  (há migration nova: o servidor vai rodar migrate)' -ForegroundColor Yellow }
if ($Seed.Count) { Write-Host "  Seeders a rodar: $($Seed -join ', ')" -ForegroundColor Yellow }

if ($DryRun) { Write-Host "`n(DryRun: nada foi enviado.)" -ForegroundColor Green; exit 0 }

if (-not $Yes) {
    $answer = Read-Host "`nEnviar para $SiteUrl? (s/N)"
    if ($answer -notmatch '^(s|sim|y|yes)$') { Write-Host 'Cancelado.'; exit 0 }
}

# ---- Empacota -----------------------------------------------------------------
Step 'Empacotando'
$work = Join-Path $env:TEMP ("geosafra-deploy-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $work | Out-Null
$pending = Join-Path $Root '.deploy\pending'
New-Item -ItemType Directory $pending -Force | Out-Null
try {
    [IO.File]::WriteAllText((Join-Path $pending 'deleted.txt'), (($deleted | ForEach-Object { "$_`n" }) -join ''), $Utf8)
    [IO.File]::WriteAllText((Join-Path $pending 'seed.txt'), (($Seed | ForEach-Object { "$_`n" }) -join ''), $Utf8)
    $list = Join-Path $work 'files.txt'
    [IO.File]::WriteAllLines($list, [string[]](@($changed) + '.deploy/pending/deleted.txt' + '.deploy/pending/seed.txt'), $Utf8)
    $pkg = Join-Path $work 'deploy.tgz'
    tar -czf $pkg -T $list
    if ($LASTEXITCODE -ne 0) { Fail 'não consegui criar o pacote.' }
    Write-Host ("Pacote: {0:N1} MB" -f ((Get-Item $pkg).Length / 1MB))

    Step 'Enviando'
    scp -q -i $SshKey -P $SshPort $pkg "${SshTarget}:geosafra-deploy.tgz"
    if ($LASTEXITCODE -ne 0) { Fail 'falha no envio (scp).' }

    Step 'Aplicando no servidor'
    $remote = @'

set -e
APP=~/domains/softrix.com.br/geosafra
PUB=~/domains/softrix.com.br/public_html/geosafra
PKG=~/geosafra-deploy.tgz
TS=$(date +%Y%m%d-%H%M%S)
BK=~/backups/deploy-$TS
mkdir -p "$BK"
cd "$APP"

tar -tzf "$PKG" | grep -v '/$' | grep -v '^\.deploy/' > "$BK/files.txt" || true
tar -xzf "$PKG" -O .deploy/pending/deleted.txt > "$BK/deleted.txt"
tar -xzf "$PKG" -O .deploy/pending/seed.txt > "$BK/seed.txt"

# Backup do que vai ser sobrescrito ou apagado
cat "$BK/files.txt" "$BK/deleted.txt" | while IFS= read -r f; do [ -n "$f" ] && [ -f "$f" ] && printf '%s\n' "$f"; done > "$BK/existing.txt" || true
if [ -s "$BK/existing.txt" ]; then tar -czf "$BK/before.tgz" -T "$BK/existing.txt"; fi

tar -xzf "$PKG"
rm -rf .deploy/pending

# Arquivos apagados localmente
while IFS= read -r f; do
  [ -n "$f" ] || continue
  rm -f "$APP/$f"
  case "$f" in public/index.php) ;; public/*) rm -f "$PUB/${f#public/}" ;; esac
done < "$BK/deleted.txt"

# public/ -> public_html/geosafra (o index.php de lá é próprio do servidor)
grep '^public/' "$BK/files.txt" | grep -v '^public/index\.php$' | while IFS= read -r f; do
  d="$PUB/${f#public/}"; mkdir -p "$(dirname "$d")"; cp "$f" "$d"
done || true

mkdir -p bootstrap/cache
php artisan optimize:clear > /dev/null
if grep -q -e '^vendor/' -e '^composer\.' "$BK/files.txt"; then php artisan package:discover > /dev/null; fi
if grep -q '^database/migrations/' "$BK/files.txt"; then php artisan migrate --force; fi
while IFS= read -r s; do [ -n "$s" ] && php artisan db:seed --class="$s" --force; done < "$BK/seed.txt"
php artisan config:cache > /dev/null
php artisan route:cache > /dev/null
php artisan view:cache > /dev/null
rm -f "$PKG"
echo "Backup: $BK"
echo "DEPLOY_OK"
'@
    $OutputEncoding = $Utf8
    try { [Console]::InputEncoding = $Utf8 } catch { }   # evita o BOM no início do script remoto
    $out = $remote.Replace("`r`n", "`n") | ssh -i $SshKey -p $SshPort $SshTarget 'bash -s'
    $out | Where-Object { $_ -ne 'DEPLOY_OK' } | ForEach-Object { Write-Host "  $_" }
    if (-not ($out -contains 'DEPLOY_OK')) { Fail 'o servidor não confirmou o deploy. O manifesto não foi atualizado; rode de novo depois de corrigir.' }
}
finally {
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $pending -Recurse -Force -ErrorAction SilentlyContinue
}

Save-Manifest

# ---- Confere o site -----------------------------------------------------------
Step 'Conferindo o site'
try {
    $code = (Invoke-WebRequest $SiteUrl -UseBasicParsing -TimeoutSec 60).StatusCode
    Write-Host "$SiteUrl respondeu $code." -ForegroundColor Green
}
catch {
    Write-Host "Atenção: $SiteUrl não respondeu bem: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host "`nDeploy concluído." -ForegroundColor Green
