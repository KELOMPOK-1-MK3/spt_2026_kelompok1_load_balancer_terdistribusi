# Kontribusi Individu — T. Zain Wardana
**NIM:** 23210001
**Peran dalam Kelompok:** Skrip Pengujian dan Pengolahan Hasil menjadi Tabel Laporan
**Mata Kuliah:** Sistem Paralel dan Terdistribusi (MKKL1030) · Semester 7
**Universitas Bina Bangsa Getsempena**

---

## Ringkasan Peran

Saya bertanggung jawab atas dua hal utama:
1. **Membuat dan menjalankan skrip pengujian** — membuktikan bahwa sistem bekerja sesuai rancangan.
2. **Mengolah hasil pengujian menjadi tabel laporan** — mendokumentasikan apa yang sudah diuji, hasilnya, dan cara mengulanginya.

---

## File yang Saya Buat / Kerjakan

### 1. `src/server/uji-beban.py` *(baru)*
Skrip uji untuk membuktikan server tahan beban banyak klien dan pesan serentak.

**Skenario yang diuji (8 pemeriksaan, semua lulus):**

| # | Skenario | Hasil |
|---|---|---|
| 1 | 10 klien menyambung hampir bersamaan | ✅ |
| 2 | Semua 10 nama terdaftar tanpa duplikat | ✅ |
| 3 | 50 pesan dikirim cepat — tidak ada yang hilang | ✅ |
| 4 | Tidak ada pesan ganda/terduplikasi | ✅ |
| 5 | 5 klien mengirim serentak — penerima dapat semua 5 pesan | ✅ |
| 6 | Isi pesan tidak tercampur antar klien | ✅ |
| 7 | Klien baru (ke-11) tetap bisa masuk saat server sudah ramai | ✅ |
| 8 | HTTP API masih menjawab setelah semua tekanan | ✅ |

**Output saat dijalankan:**
```
==============================================================
  UJI BEBAN — banyak klien + banyak pesan bersamaan
==============================================================
  ✓ server melihat 10 klien sekaligus
  ✓ tidak ada nama yang duplikat
  ✓ semua 50 pesan diterima (tidak ada yang hilang)
  ✓ tidak ada pesan ganda (urutan terjaga)
  ✓ penerima mendapat semua 5 pesan serentak
  ✓ isi pesan tidak tercampur antar klien
  ✓ klien ke-11 terdaftar
  ✓ GET /api/keadaan masih berhasil

  HASIL: 8 lulus, 0 gagal
==============================================================
```

---

### 2. `src/server/uji-ketahanan.py` *(baru)*
Skrip uji untuk membuktikan server tidak crash menghadapi kondisi tidak normal.

**Skenario yang diuji (12 pemeriksaan, semua lulus):**

| # | Skenario | Hasil |
|---|---|---|
| 1 | Klien putus paksa (simulasi crash/WiFi putus) — server mengeluarkannya | ✅ |
| 2 | Klien lain tetap terdaftar setelah ada yang putus paksa | ✅ |
| 3 | Kejadian putus paksa tercatat di basis data | ✅ |
| 4 | 4 klien putus serentak — server masih hidup | ✅ |
| 5 | Klien yang tersisa tetap terdaftar dan bisa pesan | ✅ |
| 6 | Data rusak (bukan JSON) — server membalas galat, tidak crash | ✅ |
| 7 | Server tidak crash setelah menerima data rusak | ✅ |
| 8 | Baris JSON > 64 KB — server tidak crash | ✅ |
| 9 | Pesan ke laptop yang tidak ada — pengirim mendapat galat | ✅ |
| 10 | Server tidak crash setelah pesan ke tujuan tidak ada | ✅ |
| 11 | Nama kembar masuk hampir bersamaan — hanya satu yang diterima | ✅ |
| 12 | HTTP API tetap menjawab setelah semua tekanan | ✅ |

**Output saat dijalankan:**
```
==============================================================
  UJI KETAHANAN — server harus tahan kondisi tidak normal
==============================================================
  ✓ server mengeluarkan klien yang putus paksa
  ✓ klien lain tetap terdaftar
  ✓ kejadian putus paksa tercatat di basis data
  ✓ server masih hidup setelah 4 klien putus serentak
  ✓ klien BERTAHAN masih terdaftar
  ✓ server membalas pesan galat untuk data rusak
  ✓ server tidak crash setelah menerima data rusak
  ✓ server tidak crash setelah baris > 64 KB
  ✓ pengirim menerima galat saat tujuan tidak ada
  ✓ server tidak crash setelah pesan ke tujuan tidak ada
  ✓ nama kembar tidak menghasilkan dua entri
  ✓ GET /api/keadaan berhasil di akhir

  HASIL: 12 lulus, 0 gagal
==============================================================
```

---

### 3. `src/server/uji-dua-terminal.ps1` *(baru)*
Skrip PowerShell untuk Windows — setara dengan `uji-dua-terminal.sh` yang hanya
bisa berjalan di macOS/Linux. Mensimulasikan skenario nyata:
- Server + 3 klien (PC-PARIS, PC-DESKI, PC-WIRA)
- Uji pesan siaran ke semua
- Uji pesan pribadi (hanya PC-WIRA yang terima, PC-PARIS tidak)
- Uji perintah `pesan` dari dashboard
- Menampilkan keadaan akhir dari API

Fitur tambahan dibanding versi Bash:
- Auto-detect Python (`py` → `python` → `python3`)
- Output berwarna (cyan, kuning, hijau, merah)
- URL-encode otomatis untuk nama berspasi

---

### 4. `src/server/uji-nama.ps1` *(baru)*
Skrip PowerShell untuk Windows — setara dengan `uji-nama.sh`. Menguji:
- Tanpa `--nama` → program membaca dari `nama.txt`
- Dengan `--nama PC-SAYA` → argumen menang atas `nama.txt`
- Nama berspasi + tanda kurung (`PC04 (Deski)`) terdaftar dan bisa menerima pesan pribadi

---

### 5. `docs/pengujian.md` *(diperbarui)*
Dokumen laporan hasil pengujian yang saya olah dan perbarui. Perubahan yang saya buat:

- Menambahkan **petunjuk menjalankan di Windows** (PowerShell) di samping petunjuk macOS/Linux
- Memperbarui **tabel ringkasan** dari 9 baris menjadi 19 baris — mencakup semua skrip uji baru
- Memperbarui **ringkasan angka**: dari 30 total pemeriksaan menjadi 50 lulus, 0 gagal
- Memperbarui bagian **"Yang belum diuji"** — mencoret poin "beban tinggi" karena sudah ditangani oleh `uji-beban.py`

---

## Rekap Total Pemeriksaan

| Skrip | Pemeriksaan | Status |
|---|---|---|
| `uji-cepat.py` | 17 | ✅ 17 lulus, 0 gagal |
| `uji-pengaman.py` | 13 | ✅ 13 lulus, 0 gagal |
| `uji-beban.py` | 8 | ✅ 8 lulus, 0 gagal *(baru)* |
| `uji-ketahanan.py` | 12 | ✅ 12 lulus, 0 gagal *(baru)* |
| `uji-dua-terminal.sh/.ps1` | manual | ✅ tidak ada gagal |
| `uji-nama.sh/.ps1` | manual | ✅ tidak ada gagal |
| **Total** | **50** | **✅ 50 lulus, 0 gagal** |

---

## Cara Menjalankan Semua Skrip Uji (Windows)

```powershell
cd src\server
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

py -3 uji-cepat.py
py -3 uji-pengaman.py
py -3 uji-beban.py
py -3 uji-ketahanan.py
.\uji-dua-terminal.ps1
.\uji-nama.ps1
```

Semua skrip menyalakan servernya sendiri di port uji terpisah, jadi tidak
perlu menyiapkan server lebih dahulu dan tidak mengganggu server yang sedang berjalan.

---

## Teknik yang Digunakan dalam Skrip Uji

| Teknik | Dipakai di | Tujuan |
|---|---|---|
| Klien tiruan (`Tiruan`) | semua `.py` | Mensimulasikan klien nyata tanpa perlu buka terminal baru |
| Thread terpisah per klien | semua `.py` | Supaya bisa menguji banyak klien sekaligus |
| Port uji berbeda (5097–5099) | semua `.py` | Tidak bentrok dengan server utama di port 5000 |
| `finally` untuk cleanup | semua `.py` | Proses server selalu dimatikan meski uji gagal di tengah jalan |
| `socket.shutdown()` | `uji-ketahanan.py` | Simulasi crash — memaksa koneksi putus tanpa kirim `/keluar` |
| `kirim_baris_rusak()` | `uji-ketahanan.py` | Menguji ketahanan server terhadap input tidak valid |
| Penyadap (`Peretas`) | `uji-pengaman.py` | Memantau apakah perintah bocor ke klien yang bukan sasaran |
| Auto-detect Python | `.ps1` | Skrip berjalan di Windows apapun versi instalasi Python-nya |
| `CimInstance Win32_Process` | `.ps1` | Cleanup proses berdasarkan argumen, bukan nama saja |
