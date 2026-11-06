# Laporan Tugas Kelompok
## Sistem Chat dan Kendali Terpusat Antar Laptop

**Mata Kuliah:** Sistem Paralel dan Terdistribusi (MKKL1030) · Semester 7
**Program Studi:** Ilmu Komputer — Fakultas Sains, Teknologi dan Ilmu Kesehatan
**Universitas:** Bina Bangsa Getsempena
**Dosen Pengampu:** Ahmad Mujahid Abdurrahman, S.Kom, M.T.

---

## Anggota Kelompok

| No | Nama | NIM | Peran |
|---|---|---|---|
| 1 | Yogi Prasetya Sadewa | 23210060 | Ketua; server socket, dashboard web, skenario pengujian |
| 2 | Paris Mursidan Aufal | 23210125 | Basis data pesan dan perintah di sisi server |
| 3 | M. Sidiq Prasetio | 23210075 | Aplikasi pengguna yang menyambung ke server |
| 4 | Deski Taiza | 23210003 | Riwayat pesan dan pengujian ketahanan data |
| 5 | Wira | 23210045 | Pengujian beberapa pengguna dan pencatatan hasil |
| 6 | T. Zain Wardana | 23210001 | Skrip pengujian dan pengolahan hasil menjadi tabel laporan |

---

## 1. Pendahuluan

### 1.1 Latar Belakang

Dalam praktik sistem terdistribusi nyata, komunikasi antar node menjadi
tantangan utama: bagaimana memastikan pesan sampai ke tujuan yang benar,
bagaimana satu node yang lambat tidak menghambat node lain, dan bagaimana
administrator dapat mengendalikan semua node dari satu titik tanpa harus
berpindah-pindah mesin.

Tugas ini membangun sistem yang menjawab ketiga tantangan tersebut dalam skala
kecil: enam laptop mahasiswa di jaringan lokal kampus.

### 1.2 Tujuan

1. Membangun sistem komunikasi terdistribusi berbasis socket TCP antar beberapa
   komputer dalam jaringan lokal.
2. Menerapkan model pemrosesan paralel (satu thread per klien) sehingga satu
   klien yang lambat tidak memblokir klien lain.
3. Menyediakan antarmuka kendali terpusat (dashboard web) yang memungkinkan
   administrator mengirim perintah ke komputer tertentu.
4. Mendokumentasikan dan membuktikan perilaku sistem melalui pengujian otomatis
   yang dapat diulang.

### 1.3 Ruang Lingkup

Sistem ini mencakup:
- Komunikasi **satu-ke-semua** (siaran/broadcast)
- Komunikasi **satu-ke-satu** (pesan pribadi)
- **Kendali jarak jauh** terbatas: tampilkan pesan, kunci layar, restart, matikan
- **Dashboard web** untuk pemantauan dan kendali
- **Penyimpanan** riwayat pesan dan perintah di basis data lokal

---

## 2. Landasan Teori

### 2.1 Sistem Terdistribusi

Sistem terdistribusi adalah sekumpulan komputer yang saling terhubung melalui
jaringan dan berkoordinasi untuk menyelesaikan suatu pekerjaan bersama. Ciri
utamanya: tidak ada memori bersama — setiap node hanya berkomunikasi lewat
pengiriman pesan melalui jaringan.

Pada sistem ini, koordinasi dilakukan oleh **satu server pusat** yang menerima
pesan dari semua klien dan memutuskan ke mana pesan diteruskan. Model ini
disebut **client-server terpusat** (centralized client-server).

### 2.2 Pemrosesan Paralel dengan Thread

Thread adalah unit eksekusi terkecil dalam sebuah proses. Berbeda dengan
proses, thread berbagi memori yang sama sehingga lebih ringan untuk dibuat
dan dihancurkan.

Pada server ini, **setiap klien yang menyambung dilayani oleh satu thread
tersendiri**. Artinya, jika ada 5 klien, server menjalankan 5 thread secara
bersamaan (paralel). Keunggulannya: jika satu klien mengirim data lambat,
thread klien lain tidak terpengaruh — mereka terus berjalan di jalurnya.

Pola ini dikenal sebagai **thread-per-connection**, umum dipakai pada server
jaringan sederhana.

### 2.3 Socket TCP

TCP (Transmission Control Protocol) adalah protokol transport yang menjamin:
- **Urutan** — paket data tiba dalam urutan yang sama seperti dikirim
- **Keandalan** — data yang hilang dikirim ulang secara otomatis
- **Aliran byte** — tidak ada batas antar pesan; penerima menentukan sendiri
  di mana satu pesan berakhir dan pesan berikutnya dimulai

Karena TCP adalah aliran byte, sistem ini menggunakan karakter baris baru
(`\n`) sebagai pemisah. Setiap pesan adalah satu objek JSON diakhiri `\n`.

### 2.4 Format JSON Satu Baris

JSON dipilih karena:
- Bisa dibaca manusia — mudah di-debug dengan `print()`
- Didukung langsung oleh Python (`import json`) tanpa dependensi tambahan
- Fleksibel: setiap tipe pesan bisa punya kolom berbeda asalkan ada `"tipe"`

---

## 3. Perancangan Sistem

### 3.1 Arsitektur Keseluruhan

Satu server di tengah, lima klien di sekelilingnya. Semua koneksi dimulai
dari klien menuju server (koneksi keluar), sehingga tidak diblokir firewall.

```
  PC-PARIS  ──────────────────────────────────────┐
  PC-SIDIQ  ──────────────────────────────────┐   │
  PC-DESKI  ──────────────────────────────┐   │   │
  PC-WIRA   ──────────────────────────┐   │   │   │
  PC-ZAIN   ──────────────────────┐   │   │   │   │
                                  ▼   ▼   ▼   ▼   ▼
                             [ SERVER :5000 TCP ]
                             [ SQLite chat.db  ]
                                  │
                             [ Dashboard :8081 HTTP ]
```

### 3.2 Komponen Sistem

| Komponen | File | Peran |
|---|---|---|
| Server | `src/server/server.py` | Terima koneksi, routing pesan, kirim perintah, HTTP API |
| Dashboard | `src/server/static/index.html` | Antarmuka web pemantauan dan kendali |
| Klien | `src/user/client.py` | Kirim/terima pesan, jalankan perintah |
| Basis data | `src/server/data/chat.db` | Riwayat pesan, perintah, kejadian |

### 3.3 Keputusan Teknis Penting

| Keputusan | Alasan |
|---|---|
| Satu thread per klien di server | Klien lambat tidak menahan klien lain |
| JSON + pemisah `\n` | TCP adalah aliran byte; tanpa pemisah dua pesan bisa tercampur |
| Koneksi dimulai dari klien | Koneksi keluar tidak diblokir firewall Windows |
| Daftar putih perintah | Server tidak boleh bisa menjalankan perintah bebas di laptop orang lain |
| Perintah daya ditolak di macOS | Mac dipakai sebagai server; salah kirim bisa matikan mesin presentasi |
| HTTP untuk dashboard | Dashboard hanya perlu baca keadaan sesekali; tidak perlu koneksi terus terbuka |
