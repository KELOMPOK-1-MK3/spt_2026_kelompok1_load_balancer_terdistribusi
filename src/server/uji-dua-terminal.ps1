# uji-dua-terminal.ps1
# Uji dua terminal: server + 3 pengguna, seperti yang akan dilihat user.
# Setara dengan uji-dua-terminal.sh — dipakai di Windows.
#
# Cara menjalankan (dari PowerShell):
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   cd src\server
#   .\uji-dua-terminal.ps1
#
# Catatan: perintah daya (matikan/restart/kunci) butuh hak Administrator.
# Skrip ini TIDAK mengirim perintah daya sungguhan — hanya mensimulasikan
# skenario chat dan perintah biasa supaya aman dijalankan tanpa risiko.

$ErrorActionPreference = "Stop"

# Pindah ke folder skrip ini berada
Set-Location $PSScriptRoot

$PORT   = 5099
$WEB    = 8199
$DB     = "data\uji-terminal.db"
$KLIEN  = "..\user\client.py"
$TMP    = $env:TEMP

# Berkas keluaran sementara
$logSrv    = Join-Path $TMP "spt-srv.txt"
$logKlien1 = Join-Path $TMP "spt-k1.txt"
$logKlien2 = Join-Path $TMP "spt-k2.txt"
$logKlien3 = Join-Path $TMP "spt-k3.txt"

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
function Tulis-Judul($teks) {
    Write-Host ""
    Write-Host ("############ " + $teks + " ############") -ForegroundColor Cyan
}

function Http-Get($url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8
        return $resp.Content
    } catch {
        Write-Host "  [!] Gagal mengambil ${url}: $_" -ForegroundColor Red
        return $null
    }
}

function Api-Keadaan {
    $isi = Http-Get "http://127.0.0.1:$WEB/api/keadaan"
    if ($isi) { return $isi | ConvertFrom-Json }
    return $null
}

function Bersihkan-Proses {
    # Memakai WMI untuk memeriksa argumen — lebih andal daripada CommandLine
    # yang kadang tidak tersedia di semua versi Windows.
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
foreach ($f in @($logSrv, $logKlien1, $logKlien2, $logKlien3)) {
    "" | Set-Content $f
}

# ================================================================ SERVER
Tulis-Judul "TERMINAL 1 — SERVER"

$procSrv = Start-Process $PYTHON `
    -ArgumentList @("server.py", "--port", $PORT, "--web", $WEB, "--db", $DB) `
    -RedirectStandardOutput $logSrv `
    -RedirectStandardError  $logSrv `
    -PassThru -WindowStyle Hidden

Write-Host "  Server PID: $($procSrv.Id) — menunggu 3 detik..."
Start-Sleep -Seconds 3

if ($procSrv.HasExited) {
    Write-Host "  [!] Server gagal menyala. Cek apakah port $PORT sudah dipakai." -ForegroundColor Red
    exit 1
}
Write-Host "  Server berjalan." -ForegroundColor Green

Write-Host ""
Get-Content $logSrv -ErrorAction SilentlyContinue | Select-Object -First 14

# ================================================================ DASHBOARD
Tulis-Judul "MEMBUKA DASHBOARD"

foreach ($jalur in @("/", "/api/keadaan")) {
    $url = "http://127.0.0.1:$WEB$jalur"
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8
        Write-Host ("  GET " + $jalur.PadRight(18) + " -> " + $r.StatusCode) -ForegroundColor Green
    } catch {
        Write-Host ("  GET " + $jalur.PadRight(18) + " -> GAGAL") -ForegroundColor Red
    }
}

# ================================================================ 3 PENGGUNA
Tulis-Judul "MEMBUKA 3 PENGGUNA"

$argK = @($KLIEN, "--server", "127.0.0.1", "--port", $PORT, "--tunggu")

$procK1 = Start-Process $PYTHON `
    -ArgumentList ($argK + @("--nama", "PC-PARIS")) `
    -RedirectStandardOutput $logKlien1 -RedirectStandardError $logKlien1 `
    -PassThru -WindowStyle Hidden
Start-Sleep -Milliseconds 400

$procK2 = Start-Process $PYTHON `
    -ArgumentList ($argK + @("--nama", "PC-DESKI")) `
    -RedirectStandardOutput $logKlien2 -RedirectStandardError $logKlien2 `
    -PassThru -WindowStyle Hidden
Start-Sleep -Milliseconds 400

$procK3 = Start-Process $PYTHON `
    -ArgumentList ($argK + @("--nama", "PC-WIRA")) `
    -RedirectStandardOutput $logKlien3 -RedirectStandardError $logKlien3 `
    -PassThru -WindowStyle Hidden

Write-Host "  PC-PARIS (PID $($procK1.Id)), PC-DESKI (PID $($procK2.Id)), PC-WIRA (PID $($procK3.Id))"
Write-Host "  Menunggu 3 detik supaya semua tersambung..."
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "  --- yang dilihat PC-PARIS saat menyambung ---" -ForegroundColor Yellow
Get-Content $logKlien1 -ErrorAction SilentlyContinue |
    Select-Object -Skip 6 | Select-Object -First 6

Write-Host ""
Write-Host "  --- server melihat ---" -ForegroundColor Yellow
Get-Content $logSrv -ErrorAction SilentlyContinue |
    Where-Object { $_ -match "\[masuk\]|\[pesan\]|\[perintah\]|\[hasil\]" }

# ================================================================ SIARAN
Tulis-Judul "SERVER MENGIRIM PESAN SIARAN"

$r = Http-Get "http://127.0.0.1:$WEB/api/pesan?tujuan=semua&isi=Kumpul+jam+3+di+lab"
Write-Host "  API -> $r"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  --- yang dilihat PC-DESKI ---" -ForegroundColor Yellow
Get-Content $logKlien2 -ErrorAction SilentlyContinue | Select-Object -Last 6

# ================================================================ PESAN PRIBADI
Tulis-Judul "SERVER MENGIRIM PESAN PRIBADI KE PC-WIRA"

$r = Http-Get "http://127.0.0.1:$WEB/api/pesan?tujuan=PC-WIRA&isi=Bagian+kamu+mana%3F"
Write-Host "  API -> $r"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  --- yang dilihat PC-WIRA ---" -ForegroundColor Yellow
Get-Content $logKlien3 -ErrorAction SilentlyContinue | Select-Object -Last 6

Write-Host ""
Write-Host "  --- PC-PARIS (harusnya TIDAK dapat pesan pribadi itu) ---" -ForegroundColor Yellow
Get-Content $logKlien1 -ErrorAction SilentlyContinue | Select-Object -Last 4

# ================================================================ PERINTAH
Tulis-Judul "UJI PERINTAH 'pesan' KE PC-PARIS"
# Hanya mengirim perintah 'pesan' yang aman.
# Perintah matikan/restart/kunci diuji terpisah via uji-pengaman.py.

$r = Http-Get "http://127.0.0.1:$WEB/api/perintah?sasaran=PC-PARIS&aksi=pesan&keterangan=Tes+dari+uji+Windows"
Write-Host "  API -> $r"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  --- yang dilihat PC-PARIS ---" -ForegroundColor Yellow
Get-Content $logKlien1 -ErrorAction SilentlyContinue | Select-Object -Last 5

Write-Host ""
Write-Host "  --- catatan di server ---" -ForegroundColor Yellow
Get-Content $logSrv -ErrorAction SilentlyContinue |
    Where-Object { $_ -match "\[hasil\]" } | Select-Object -Last 3

# ================================================================ KEADAAN AKHIR
Tulis-Judul "KEADAAN AKHIR"

$keadaan = Api-Keadaan
if ($keadaan) {
    $namaOnline = $keadaan.online | ForEach-Object { $_.nama }
    Write-Host ("  laptop online  : " + ($namaOnline -join ", "))
    Write-Host ("  jumlah pesan   : " + $keadaan.jumlah.pesan)
    Write-Host ("  jumlah perintah: " + $keadaan.jumlah.perintah)
    Write-Host "  kejadian       :"
    foreach ($k in $keadaan.kejadian) {
        $jam = $k.waktu.Substring($k.waktu.Length - 8)
        Write-Host ("     $jam  " + $k.nama.PadRight(14) + " " + $k.jenis)
    }
    if ($keadaan.perintah.Count -gt 0) {
        Write-Host "  perintah terakhir:"
        foreach ($p in $keadaan.perintah) {
            Write-Host ("     " + $p.aksi.PadRight(10) + " -> " + $p.sasaran.PadRight(14) + ": " + $p.hasil)
        }
    }
} else {
    Write-Host "  [!] Tidak bisa membaca keadaan dari API." -ForegroundColor Red
}

# ================================================================ BERSIH-BERSIH
Tulis-Judul "MEMBERSIHKAN"

foreach ($proc in @($procK1, $procK2, $procK3, $procSrv)) {
    if ($null -ne $proc -and -not $proc.HasExited) {
        $proc.Kill()
        $proc.WaitForExit(3000) | Out-Null
        Write-Host "  Proses PID $($proc.Id) dihentikan."
    }
}

Start-Sleep -Milliseconds 800
Bersihkan-Proses

if (Test-Path $DB) {
    Remove-Item $DB -Force
    Write-Host "  Basis data uji dihapus."
}

Write-Host ""
Write-Host "SELESAI — semua proses dimatikan." -ForegroundColor Green
