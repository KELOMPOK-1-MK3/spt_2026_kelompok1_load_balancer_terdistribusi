# Protokol Pesan — MK Sistem Paralel

Server dan klien bertukar pesan dalam bentuk **satu objek JSON per baris**.
Setiap pesan diakhiri karakter baris baru (`\n`).

## Kenapa satu baris per pesan

TCP itu aliran byte, bukan kumpulan pesan. Kalau dua pesan dikirim berurutan tanpa
pemisah yang jelas, penerima tidak punya cara tahu di mana pesan pertama berakhir —
datanya bisa tercampur jadi satu potongan yang tidak bisa dibaca.

Karena itu setiap pesan JSON diakhiri `\n`, dan penerima memotong data yang masuk
pada setiap karakter itu. Cara ini sederhana, bisa dibaca manusia, dan tidak perlu
pustaka tambahan.

## Bentuk Umum

```json
{"tipe": "...", ...}
```

Setiap pesan **wajib** punya `tipe`. Sisanya tergantung tipenya.

---

## 1. Klien → Server

### 1.1 Mendaftar (`daftar`)

Dikirim **sekali**, tepat setelah sambungan terbuka. Tanpa ini, server tidak tahu
siapa yang baru tersambung.

```json
{"tipe": "daftar", "nama": "PC-PARIS", "sistem": "Windows 11"}
```

| Kolom | Wajib | Isi |
|---|---|---|
| `nama` | ya | Nama laptop. Kalau kosong, server pakai nama mesin. |
| `sistem` | tidak | Sistem operasi, untuk ditampilkan di dashboard |

### 1.2 Mengirim pesan (`pesan`)

```json
{"tipe": "pesan", "ke": "semua", "isi": "Kumpul jam 3 di lab"}
{"tipe": "pesan", "ke": "PC-DESKI", "isi": "Bagianmu sudah selesai?"}
```

| Kolom | Wajib | Isi |
|---|---|---|
| `ke` | ya | `"semua"` atau satu nama laptop |
| `isi` | ya | Teks pesan, paling banyak 2000 karakter |

### 1.3 Laporan hasil perintah (`hasil`)

Dikirim setelah klien menjalankan perintah dari server.

```json
{"tipe": "hasil", "aksi": "kunci", "berhasil": true,
 "pesan": "layar dikunci", "id_perintah": 12}
```

| Kolom | Wajib | Isi |
|---|---|---|
| `aksi` | ya | Perintah yang dijalankan |
| `berhasil` | ya | `true` / `false` |
| `pesan` | ya | Keterangan singkat untuk ditampilkan di dashboard |
| `id_perintah` | tidak | Nomor perintah di basis data, supaya bisa dicocokkan |

---

## 2. Server → Klien

### 2.1 Sambutan (`selamat`)

Balasan atas `daftar`.

```json
{"tipe": "selamat", "nama_kamu": "PC-PARIS", "online": ["PC-PARIS", "PC-SIDIQ"]}
```

### 2.2 Daftar yang tersambung (`online`)

Dikirim setiap kali ada laptop yang tersambung atau terputus.

```json
{"tipe": "online", "daftar": [
  {"nama": "PC-PARIS", "sistem": "Windows 11", "ip": "192.168.1.12"}
]}
```

### 2.3 Pesan masuk (`pesan`)

```json
{"tipe": "pesan", "dari": "PC-SIDIQ", "ke": "semua",
 "isi": "Kumpul jam 3 di lab", "waktu": "2026-10-18 14:05:11"}
```

### 2.4 Perintah (`perintah`)

```json
{"tipe": "perintah", "aksi": "kunci", "keterangan": "", "id": 12}
```

Server mengirim `id` supaya klien bisa menyebutkannya lagi di laporan hasil.

### 2.5 Pemberitahuan (`info`) dan galat (`galat`)

```json
{"tipe": "info", "pesan": "terkirim ke semua (4 laptop)"}
{"tipe": "galat", "pesan": "laptop 'PC-WIRA' tidak sedang tersambung"}
```

### 2.6 Ping / Pong

Supaya sambungan yang diam tidak diputus dan supaya server tahu klien masih hidup.

```json
{"tipe": "ping"}     ← server kirim tiap 20 detik
{"tipe": "pong"}     ← klien balas
```

---

## 3. Ringkasan Semua Tipe

| Tipe | Arah | Arti |
|---|---|---|
| `daftar` | klien → server | Laptop ini baru tersambung |
| `pesan` | klien → server | Ada pesan untuk dikirim |
| `hasil` | klien → server | Perintah sudah dijalankan |
| `pong` | klien → server | Masih hidup |
| `selamat` | server → klien | Pendaftaran diterima |
| `online` | server → klien | Daftar laptop yang aktif |
| `pesan` | server → klien | Ada pesan masuk |
| `perintah` | server → klien | Perintah untuk dijalankan |
| `info` | server → klien | Pemberitahuan biasa |
| `galat` | server → klien | Ada yang tidak berhasil |
| `ping` | server → klien | Menanyakan apakah klien masih hidup |

## 4. Perintah yang Dikenal

| Aksi | Yang dilakukan klien |
|---|---|
| `pesan` | Menampilkan pesan dari server |
| `kunci` | Mengunci layar |
| `restart` | Menyalakan ulang (jeda 30 detik, bisa dibatalkan) |
| `matikan` | Mematikan laptop (jeda 30 detik, bisa dibatalkan) |
| `batal` | Membatalkan perintah restart/matikan yang sedang menunggu |

Aksi di luar daftar ini **ditolak** oleh klien dan dilaporkan sebagai gagal.

## 5. Batas dan Aturan

| Hal | Batas | Kalau dilanggar |
|---|---|---|
| Panjang isi pesan | 2000 karakter | Dipotong, klien diberi tahu |
| Panjang satu baris JSON | 64 KB | Sambungan diputus |
| Panjang nama laptop | 40 karakter | Dipotong |
| Data yang tidak bisa dibaca | — | Dibalas `galat`, sambungan tidak diputus |
| Klien diam lebih dari 60 detik | — | Server menganggapnya terputus |
