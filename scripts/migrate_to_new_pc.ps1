# ============================================================================
# migrate_to_new_pc.ps1 - Bundle semua yang dibutuhkan untuk migrasi laptop
#
# Cara pakai (jalankan dari PowerShell di laptop LAMA):
#   .\scripts\migrate_to_new_pc.ps1
#   .\scripts\migrate_to_new_pc.ps1 -OutputRoot "E:\backup"
#   .\scripts\migrate_to_new_pc.ps1 -PgPassword "mypass"
#
# Output: folder migrate_barber_<timestamp>/ berisi:
#   - 01_project.zip           (source code, tanpa venv/pycache)
#   - 02_database.sql          (dump PostgreSQL fresh)
#   - 03_env_SENSITIVE.env     (copy .env - WAJIB DILINDUNGI)
#   - 04_cloudflared/          (config tunnel, kalau ada)
#   - README.txt               (checklist restore step-by-step)
# ============================================================================

[CmdletBinding()]
param(
    [string]$ProjectPath  = "D:\Document\barber\bot_barber_2",
    [string]$OutputRoot   = "D:\",
    [string]$PgBinPath    = "C:\Program Files\PostgreSQL\18\bin",
    [string]$PgUser       = "postgres",
    [string]$PgDatabase   = "barbershop_db",
    [string]$PgPassword   = "Latansa11"
)

$ErrorActionPreference = "Stop"

function Write-Info    { param($msg) Write-Host "  -> $msg" -ForegroundColor Cyan }
function Write-OK      { param($msg) Write-Host "  OK $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  X $msg" -ForegroundColor Red }
function Write-Section { param($msg) Write-Host "`n>> $msg" -ForegroundColor Magenta }

# ---- Validasi input ----
Write-Section "Validasi environment"

if (-not (Test-Path $ProjectPath)) {
    Write-Err "Folder project tidak ditemukan: $ProjectPath"
    exit 1
}
Write-OK "Project ada: $ProjectPath"

if (-not (Test-Path (Join-Path $ProjectPath ".env"))) {
    Write-Warn ".env tidak ditemukan di project. Bundle tanpa .env - kamu harus setup manual di laptop baru."
} else {
    Write-OK ".env ada"
}

$pgDump = Join-Path $PgBinPath "pg_dump.exe"
if (-not (Test-Path $pgDump)) {
    Write-Err "pg_dump.exe tidak ditemukan di $PgBinPath"
    Write-Err "Ubah parameter -PgBinPath sesuai lokasi PostgreSQL kamu."
    exit 1
}
Write-OK "pg_dump ada: $pgDump"

# ---- Buat folder output ----
$stamp    = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleDir = Join-Path $OutputRoot "migrate_barber_$stamp"
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null
Write-OK "Output folder: $bundleDir"

# ---- 1. Zip source code ----
Write-Section "1/4 Zip source code (skip venv & cache)"

$zipTarget = Join-Path $bundleDir "01_project.zip"
$stagingDir = Join-Path $env:TEMP "barber_migrate_stage_$stamp"

Write-Info "Copy ke staging (tanpa venv/__pycache__/*.pyc)..."
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

$excludeDirs = @("venv", ".venv", "__pycache__", ".git", "node_modules")
$excludeFiles = @("*.pyc", "*.pyo", "cookies*.txt", "login*.html")
$robocopyArgs = @(
    $ProjectPath, $stagingDir, "/E", "/XD"
) + $excludeDirs + @("/XF") + $excludeFiles + @("/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP")
& robocopy @robocopyArgs | Out-Null

if ($LASTEXITCODE -gt 7) {
    Write-Err "robocopy gagal (exit $LASTEXITCODE)"
    exit 1
}
Write-OK "Staging siap"

Write-Info "Compress ke ZIP..."
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipTarget -Force
Remove-Item $stagingDir -Recurse -Force

$zipSizeMB = [math]::Round((Get-Item $zipTarget).Length / 1MB, 1)
Write-OK ("01_project.zip - {0} MB" -f $zipSizeMB)

# ---- 2. Backup database ----
Write-Section "2/4 Backup PostgreSQL"

$sqlTarget = Join-Path $bundleDir "02_database.sql"
$env:PGPASSWORD = $PgPassword
try {
    & $pgDump -h localhost -U $PgUser -d $PgDatabase -f $sqlTarget 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "pg_dump exit $LASTEXITCODE" }
    $sqlSizeKB = [math]::Round((Get-Item $sqlTarget).Length / 1KB, 1)
    Write-OK ("02_database.sql - {0} KB" -f $sqlSizeKB)
} catch {
    Write-Err "pg_dump gagal: $_"
    Write-Warn "Periksa: PostgreSQL jalan? password benar? DB '$PgDatabase' ada?"
    exit 1
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

# ---- 3. Copy .env sensitive ----
Write-Section "3/4 Copy .env (SENSITIVE)"

$envSrc = Join-Path $ProjectPath ".env"
if (Test-Path $envSrc) {
    Copy-Item $envSrc (Join-Path $bundleDir "03_env_SENSITIVE.env") -Force
    Write-OK "03_env_SENSITIVE.env"
} else {
    Write-Warn "Skip - .env tidak ada di project"
}

# ---- 4. Copy cloudflared config ----
Write-Section "4/5 Copy cloudflared config"

$cfSrc = Join-Path $env:USERPROFILE ".cloudflared"
if (Test-Path $cfSrc) {
    Copy-Item $cfSrc (Join-Path $bundleDir "04_cloudflared") -Recurse -Force
    $cfFileCount = (Get-ChildItem (Join-Path $bundleDir "04_cloudflared") -Recurse -File).Count
    Write-OK ("04_cloudflared - {0} file" -f $cfFileCount)
} else {
    Write-Warn "Skip - folder .cloudflared tidak ada di $env:USERPROFILE"
    Write-Warn "Kalau kamu pakai tunnel, setup ulang di laptop baru via: cloudflared tunnel login"
}

# ---- 5. Copy Claude Code session + memory ----
Write-Section "5/5 Copy Claude Code (chat history + memory)"

$claudeSrc = Join-Path $env:USERPROFILE ".claude"
if (Test-Path $claudeSrc) {
    $claudeDst = Join-Path $bundleDir "05_claude"
    New-Item -ItemType Directory -Path $claudeDst -Force | Out-Null
    # Skip folder besar/transient. Yang penting: projects (session+memory), backups, settings.*
    $skipDirs = @(
        "file-history",     # ratusan MB snapshot file edits — auto-rebuild
        "cache",            # LLM cache
        "paste-cache",
        "shell-snapshots",  # shell env snapshots per session
        "telemetry",
        "debug",
        "downloads",
        "logs",
        "plugins",          # bisa install ulang
        "ide"               # IDE state cache
    )
    $robocopyArgs = @(
        $claudeSrc, $claudeDst, "/E",
        "/XD"
    ) + $skipDirs + @("/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP")
    & robocopy @robocopyArgs | Out-Null
    if ($LASTEXITCODE -gt 7) {
        Write-Warn "robocopy .claude selesai dgn warning (exit $LASTEXITCODE) - biasanya OK"
    }
    $claudeFileCount = (Get-ChildItem $claudeDst -Recurse -File).Count
    $claudeSizeMB = [math]::Round((Get-ChildItem $claudeDst -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-OK ("05_claude - {0} file, {1} MB (chat history + memory, skip file-history & cache)" -f $claudeFileCount, $claudeSizeMB)
} else {
    Write-Warn "Skip - folder .claude tidak ada di $env:USERPROFILE"
    Write-Warn "Chat Claude Code tidak ter-bundle. Kalau perlu, backup manual folder itu."
}

# ---- 5. Generate README ----
Write-Section "Generate README.txt"

$readme = @"
==========================================================================
MIGRASI BARBERSHOP APP - Bundle dibuat: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
==========================================================================

Bundle ini berisi:
  01_project.zip           - source code (tanpa venv)
  02_database.sql          - dump PostgreSQL '$PgDatabase'
  03_env_SENSITIVE.env     - file .env (JANGAN commit / share publik!)
  04_cloudflared/          - config Cloudflare Tunnel (kalau ada)
  05_claude/               - chat history + memory Claude Code (kalau ada)

--------------------------------------------------------------------------
STEP-BY-STEP RESTORE DI LAPTOP BARU
--------------------------------------------------------------------------

1) INSTALL TOOLS (urut, dari installer .exe/.msi)
   a. Python 3.11+  -> https://www.python.org/downloads/
      * Centang "Add Python to PATH"
   b. PostgreSQL 18 -> https://www.postgresql.org/download/windows/
      * Install ke C:\Program Files\PostgreSQL\18\
      * Password postgres user: $PgPassword  (SAMA dengan laptop lama!)
   c. cloudflared (opsional, kalau pakai tunnel)
      -> https://github.com/cloudflare/cloudflared/releases

2) EXTRACT PROJECT
   Extract 01_project.zip ke D:\Document\barber\bot_barber_2\
   (folder tujuan boleh apapun, sesuaikan path)

3) COPY .env
   Copy 03_env_SENSITIVE.env ke:
     D:\Document\barber\bot_barber_2\.env
   (rename: buang prefix - nama file harus tepat ".env")

4) COPY CLOUDFLARED (kalau ada folder 04_cloudflared/)
   Copy folder 04_cloudflared/ ke:
     C:\Users\<username>\.cloudflared\

5) SETUP PYTHON VENV
   Buka PowerShell, cd ke folder project:
     cd D:\Document\barber\bot_barber_2
     python -m venv venv
     .\venv\Scripts\activate
     pip install -r requirements.txt

6) RESTORE DATABASE
   `$env:PGPASSWORD = "$PgPassword"
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -U postgres -c "CREATE DATABASE $PgDatabase;"
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -U postgres -d $PgDatabase -f "02_database.sql"

7) TEST FLASK
     python run_dashboard.py
   Buka browser: http://localhost:5000
   Login pakai password yang sama dengan laptop lama.

8) SETUP CLOUDFLARED SERVICE (kalau perlu)
     cloudflared service install
   Verify di services.msc - cari "cloudflared" running.

9) RESTORE CLAUDE CODE HISTORY + MEMORY (kalau ada 05_claude/)
   Copy folder 05_claude/ ke:
     C:\Users\<username>\.claude\
   Setelah itu semua chat lama & memory tersedia via /resume di Claude Code.

--------------------------------------------------------------------------
CATATAN PENTING
--------------------------------------------------------------------------
* File 03_env_SENSITIVE.env berisi PASSWORD HASH admin & SECRET KEYS.
  Jangan email/upload publik. Kalau bocor, ganti semua secret di .env.
* Kalau password postgres berbeda dengan yang lama, edit DATABASE_URL di .env.
* Fonnte WhatsApp: cuma 1 device connected per token. Kalau ganti PC,
  test kirim WA - kalau gagal, buka dashboard Fonnte -> pair ulang.
"@

$readme | Out-File -FilePath (Join-Path $bundleDir "README.txt") -Encoding UTF8
Write-OK "README.txt"

# ---- Summary ----
Write-Section "SELESAI"

Write-Host ""
Write-Host "  Bundle:  " -NoNewline
Write-Host $bundleDir -ForegroundColor Green
Write-Host ""

$totalSize = [math]::Round((Get-ChildItem $bundleDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host ("  Total ukuran: {0} MB" -f $totalSize)
Write-Host ""
Write-Host "  Isi:" -ForegroundColor Cyan
Get-ChildItem $bundleDir | ForEach-Object {
    if ($_.PSIsContainer) {
        $childCount = (Get-ChildItem $_.FullName -Recurse -File).Count
        Write-Host ("    {0,-32} ({1} file)" -f $_.Name, $childCount)
    } else {
        $size = if ($_.Length -gt 1MB) { "{0:N1} MB" -f ($_.Length / 1MB) }
                elseif ($_.Length -gt 1KB) { "{0:N1} KB" -f ($_.Length / 1KB) }
                else { "{0} B" -f $_.Length }
        Write-Host ("    {0,-32} {1}" -f $_.Name, $size)
    }
}
Write-Host ""
Write-Host "  Langkah berikutnya:" -ForegroundColor Yellow
Write-Host "    1. Copy folder '$bundleDir' ke flashdisk"
Write-Host "    2. Di laptop baru, ikuti README.txt di dalam folder"
Write-Host "    3. Ingat: file 03_env_SENSITIVE.env berisi PASSWORD & SECRET."
Write-Host "       Jangan share publik, hapus flashdisk setelah restore selesai."
Write-Host ""
