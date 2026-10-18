# Sistem Chat dan Kendali Terpusat Antar Laptop

**Mata kuliah:** Sistem Paralel dan Terdistribusi (MKKL1030) · Semester 7
**Program Studi Ilmu Komputer — Fakultas Sains, Teknologi dan Ilmu Kesehatan**
**Universitas Bina Bangsa Getsempena**
**Dosen Pengampu:** Ahmad Mujahid Abdurrahman, S.Kom, M.T.

Enam laptop yang saling terhubung dalam satu jaringan lokal: **satu laptop
menjadi server**, **lima laptop lain menjadi pengguna**. Lewat terminal, tiap
laptop dapat mengirim pesan ke semua orang atau ke satu orang saja. Server juga
dapat mengirim perintah ke laptop tertentu (menampilkan pesan, mengunci layar,
menyalakan ulang, mematikan) lewat dashboard web.

Seluruh komunikasi memakai **socket TCP** dengan pesan berbentuk satu baris JSON.
Tidak ada pustaka tambahan — hanya modul bawaan Python.

## Anggota Kelompok

| No | Nama | NIM | Peran |
|---|---|---|---|
| 1 | Paris Mursidan Aufal | 23210125 | Basis data pesan dan perintah di sisi server |
| 2 | Yogi Prasetya Sadewa | 23210060 | Ketua kelompok; server socket, dashboard web, dan skenario pengujian |
| 3 | M. Sidiq Prasetio | 23210075 | Aplikasi pengguna yang menyambung ke server |
| 4 | Deski Taiza | 23210003 | Riwayat pesan dan pengujian ketahanan data |
| 5 | Wira | 23210045 | Pengujian beberapa pengguna dan pencatatan hasil |
| 6 | T. Zain Wardana | 23210001 | Skrip pengujian dan pengolahan hasil menjadi tabel laporan |

> Kelompok berjumlah 6 orang; setiap anggota mengerjakan satu bagian dan
> melakukan commit dari akun GitHub masing-masing.

## Struktur Repositori

```
├── PROTOKOL.md              bentuk pesan yang dipertukarkan server & pengguna
├── docs/
│   ├── arsitektur.md        komponen, keputusan teknis, alur satu pesan
│   ├── pengujian.md         apa yang sudah diuji, hasilnya, cara mengulanginya
│   ├── diagrams/            gambar arsitektur, ERD, alur pesan
│   └── bukti/               tangkapan layar dashboard dan animasi
└── src/
    ├── server/              server socket + dashboard web
    │   ├── server.py
    │   ├── static/index.html
    │   └── uji-*.py|sh      skrip pengujian
    └── user/                program yang dijalankan tiap anggota
        └── client.py
```

## Cara Menjalankan

### Kebutuhan

- Python 3.10 atau lebih baru
- Semua laptop berada di **jaringan WiFi yang sama**

Tidak ada `pip install`. Kedua program hanya memakai modul bawaan.

### 1. Nyalakan server (di laptop ketua)

```bash
cd src/server
python3 server.py
```

Server akan mencetak alamatnya, misalnya:

```
  Menunggu klien di port TCP   : 5000
  Dashboard web                : http://localhost:8081
  Alamat yang dipakai klien (berikan ke anggota):
      192.168.1.7:5000
```

### 2. Jalankan di tiap laptop anggota

```bash
cd src/user
python3 client.py --server 192.168.1.7
```

Ganti `192.168.1.7` dengan alamat yang dicetak server.

Nama laptop diambil dari berkas `src/user/nama.txt`. Tiap anggota mengubah
isinya sesuai namanya, misalnya `PC04 (Deski)`. Kalau berkasnya belum ada,
program akan menanyakannya sekali lalu menyimpannya.

### 3. Buka dashboard

**http://localhost:8081** — di sini terlihat semua laptop yang tersambung,
riwayat pesan dan perintah, serta tombol untuk mengirim pesan atau perintah.

## Cara Memakai Terminal Pengguna

```
halo semua              → kirim ke semua orang
/ke PC04 (Deski) halo   → kirim ke satu orang saja
/online                 → lihat siapa saja yang aktif
/keluar                 → keluar
```

## Yang Sudah Terbukti

| Kemampuan | Status |
|---|---|
| Banyak pengguna tersambung bersamaan (satu thread per pengguna) | ✅ |
| Pesan siaran ke semua orang, tanpa gema ke pengirim | ✅ |
| Pesan pribadi ke satu orang (tidak bocor ke yang lain) | ✅ |
| Nama kembar ditolak | ✅ |
| Pengguna putus terdeteksi & tercatat | ✅ |
| Perintah hanya dijalankan laptop yang dituju | ✅ |
| Perintah daya **ditolak** di macOS (lihat catatan di bawah) | ✅ |
| Dashboard: daftar laptop, kirim pesan, riwayat, ekspor CSV | ✅ |
| Dashboard muat satu layar tanpa menggulir | ✅ |

Rincian lengkap dan cara mengulanginya: [`docs/pengujian.md`](docs/pengujian.md)

## Pengaman Penting

Perintah **matikan, restart, dan kunci ditolak di macOS** secara bawaan.

Ini disengaja: Mac ketua dipakai sebagai server *sekaligus* komputer kerja.
Tanpa pengaman ini, satu perintah yang salah kirim saat presentasi bisa
mematikan komputer yang sedang dipakai presentasi. Pengamannya ada **di dalam
kode**, bukan hanya dihindari oleh skrip uji — jadi perintah daya tetap ditolak
walau dikirim dari mana pun.

Di Windows, perintah daya butuh terminal **Run as Administrator**.

## Yang Belum Diuji

Dicatat terbuka, bukan disembunyikan:

1. **Enam laptop sungguhan yang terpisah.** Pengujian masih di satu mesin.
2. **Perintah daya di Windows.** Baru dibuktikan bahwa perintahnya *ditolak* di
   macOS.
3. **WiFi kampus.** Perlu diuji dengan dua laptop lebih dahulu sebelum hari
   presentasi, untuk memastikan WiFi tidak memisahkan antar-laptop.
4. **Beban tinggi.** Belum diukur berapa pengguna yang bisa dilayani bersamaan.
5. **Sambung ulang otomatis.** Kalau WiFi sempat putus, program pengguna harus
   dijalankan ulang.

## Dokumen Terkait

- [`PROTOKOL.md`](PROTOKOL.md) — bentuk pesan yang dipertukarkan
- [`docs/arsitektur.md`](docs/arsitektur.md) — komponen dan keputusan teknis
- [`docs/pengujian.md`](docs/pengujian.md) — hasil pengujian
- [`src/server/README.md`](src/server/README.md) — penjelasan rinci sisi server
- [`src/user/README.md`](src/user/README.md) — penjelasan rinci sisi pengguna

---

> **Catatan nama repositori.** Repositori ini masih memakai nama tema
> sebelumnya. Isinya sudah sepenuhnya memakai tema chat dan kendali terpusat.
