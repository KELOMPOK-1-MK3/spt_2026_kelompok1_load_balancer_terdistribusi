# uji-nama.ps1
# Uji: dari mana nama laptop diambil, dan mana yang menang.
# Setara dengan uji-nama.sh — dipakai di Windows.
#
# Cara menjalankan (dari PowerShell):
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   cd src\server
#   .\uji-nama.ps1

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$PORT   = 5099
$WEB    = 8199
$DB     = "data\uji-nama.db"
$KLIEN  = "..\user\client.py"
$TMP    = $env:TEMP

$logSrv = Join-Path $TMP "spt-nama-srv.txt"
$logK1  = Join-Path $TMP "spt-nama-k1.txt"
$logK2  = Join-Path $TMP "spt-nama-k2.txt"
$logK3  = Join-Path $TMP "spt-nama-k3.txt"

# ------------------------------------------------------------------ deteksi Python
function Cari-Python {
    foreach ($cmd in @("py", "python", "python3")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$ver" -match "Python 3") {
                return $cmd
            }
        } catch {}
    }
    Write-Host "[!] Python 3 tidak ditemukan. Pasang dari https://python.org" `
               "dan centang 'Add Python to PATH'." -ForegroundColor Red
    exit 1
}

$PYTHON = Cari-Python
Write-Host "Memakai: $PYTHON ($( & $PYTHON --version 2>&1 ))" -ForegroundColor DarkGray

# ------------------------------------------------------------------ fungsi bantu
function Tulis-Bagian($no, $judul) {
    Write-Host ""
    Write-Host ("=== $no. $judul ===") -ForegroundColor Cyan
}

function Http-Get($url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8
        return $r.Content
    } catch {
        Write-Host "  [!] Gagal: ${url}: $_" -ForegroundColor Red
        return $null
    }
}

function Bersihkan-Proses {
    try {
        Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match "server\.py.*--port\s+$PORT" -or
                           $_.CommandLine -match "client\.py.*--port\s+$PORT" } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    } catch {}
}

# ================================================================ MULAI
Bersihkan-Proses
Start-Sleep -Milliseconds 500

if (Test-Path $DB) { Remove-Item $DB -Force }
New-Item -ItemType Directory -Path "data" -Force | Out-Null
foreach ($f in @($logSrv, $logK1, $logK2, $logK3)) { "" | Set-Content $f }

# Nyalakan server
$procSrv = Start-Process $PYTHON `
    -ArgumentList @("server.py", "--port", $PORT, "--web", $WEB, "--db", $DB) `
    -RedirectStandardOutput $logSrv -RedirectStandardError $logSrv `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

if ($procSrv.HasExited) {
    Write-Host "[!] Server gagal menyala." -ForegroundColor Red
    exit 1
}
Write-Host "Server berjalan (PID $($procSrv.Id))." -ForegroundColor Green

# ============================================================
Tulis-Bagian 1 "TANPA --nama -> harus baca nama.txt"

$namaTxt = "..\user\nama.txt"
if (Test-Path $namaTxt) {
    $namaFile = (Get-Content $namaTxt -Raw).Trim()
    Write-Host "  nama.txt berisi: '$namaFile'"
} else {
    Write-Host "  nama.txt belum ada — klien akan menanyakan nama saat pertama jalan." -ForegroundColor Yellow
}

$procK1 = Start-Process $PYTHON `
    -ArgumentList @($KLIEN, "--server", "127.0.0.1", "--port", $PORT, "--tunggu") `
    -RedirectStandardOutput $logK1 -RedirectStandardError $logK1 `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

Get-Content $logK1 -ErrorAction SilentlyContinue |
    Select-Object -Skip 3 | Select-Object -First 7

# ============================================================
Tulis-Bagian 2 "DENGAN --nama PC-SAYA -> argumen menang, dan diberi tahu"

$procK2 = Start-Process $PYTHON `
    -ArgumentList @($KLIEN, "--server", "127.0.0.1", "--port", $PORT, "--tunggu", "--nama", "PC-SAYA") `
    -RedirectStandardOutput $logK2 -RedirectStandardError $logK2 `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

Get-Content $logK2 -ErrorAction SilentlyContinue |
    Select-Object -Skip 3 | Select-Object -First 9

# ============================================================
Tulis-Bagian 3 "Nama berspasi + tanda kurung"

$procK3 = Start-Process $PYTHON `
    -ArgumentList @($KLIEN, "--server", "127.0.0.1", "--port", $PORT, "--tunggu", "--nama", "PC04 (Deski)") `
    -RedirectStandardOutput $logK3 -RedirectStandardError $logK3 `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

Get-Content $logK3 -ErrorAction SilentlyContinue |
    Where-Object { $_ -match "Laptop\s+:" }

# ============================================================
Tulis-Bagian 4 "Dashboard melihat siapa saja yang online"

$raw = Http-Get "http://127.0.0.1:$WEB/api/keadaan"
if ($raw) {
    $data = $raw | ConvertFrom-Json
    $namaOnline = $data.online | ForEach-Object { $_.nama }
    Write-Host ("  online: " + ($namaOnline -join ", "))
}

# ============================================================
Tulis-Bagian 5 "Pesan pribadi ke nama berspasi (PC04 (Deski))"

# URL-encode spasi dan tanda kurung
$tujuan = [System.Uri]::EscapeDataString("PC04 (Deski)")
$isi    = [System.Uri]::EscapeDataString("tes nama berspasi")
$r = Http-Get "http://127.0.0.1:$WEB/api/pesan?tujuan=$tujuan&isi=$isi"
Write-Host "  API -> $r"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  --- diterima PC04 (Deski) ---" -ForegroundColor Yellow
Get-Content $logK3 -ErrorAction SilentlyContinue | Select-Object -Last 5

# ============================================================
Tulis-Bagian 6 "Catatan di server"

Get-Content $logSrv -ErrorAction SilentlyContinue |
    Where-Object { $_ -match "\[masuk\]|\[pesan\]" }

# ================================================================ BERSIH
Write-Host ""
foreach ($proc in @($procK1, $procK2, $procK3, $procSrv)) {
    if ($null -ne $proc -and -not $proc.HasExited) {
        $proc.Kill()
        $proc.WaitForExit(3000) | Out-Null
    }
}
Start-Sleep -Milliseconds 500
Bersihkan-Proses

if (Test-Path $DB) { Remove-Item $DB -Force }

Write-Host ""
Write-Host "SELESAI." -ForegroundColor Green
