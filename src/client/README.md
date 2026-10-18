# Aplikasi Client — MKKL1030

Halaman web yang memantau layanan melalui load balancer.

## Cara menjalankan

```bash
docker compose up --build -d
```

Lalu buka:

**http://localhost:8080/klien/**

Halaman ini **dilayani oleh Nginx itu sendiri** (lihat `location /klien/` pada
`nginx/nginx.conf`), sehingga halaman dan titik akhir yang dipanggilnya berada di
**alamat yang sama**. Dengan begitu client benar-benar hanya mengenal satu
alamat, dan tidak ada permintaan lintas-asal (CORS) yang harus diakali.

## Yang ditampilkan

| Bagian | Isi |
|---|---|
| Kartu | total permintaan, app server yang menjawab, waktu respons, dan pembagian beban (%) |
| Tabel riwayat | 14 permintaan terakhir: nomor, server, waktu respons, jam, catatan |
| Grafik | waktu respons per permintaan; warna batang menunjukkan app1 (hijau) atau app2 (biru) |

Halaman mengirim satu permintaan ke `/` setiap **1 detik** secara otomatis.

## Percobaan: matikan satu app server saat client berjalan

Ini percobaan yang paling penting — biarkan halaman terbuka, lalu jalankan:

```bash
docker compose stop app1
```

**Yang akan terlihat di layar:**

1. Satu-dua permintaan berikutnya butuh **~2.010 ms** (bukan ~7 ms). Batangnya
   muncul **kuning** di grafik, dan muncul kotak peringatan di atas tabel.
2. Setelah itu waktu respons kembali normal, dan kolom **Dilayani** berisi
   **app2** terus-menerus.
3. Kartu **Pembagian beban** bergeser dari 50%:50% ke arah app2 — ini normal,
   karena app1 memang sedang mati.

```bash
docker compose start app1
```

Setelah app1 hidup lagi, sekitar **2–4 detik** kemudian kolom **Dilayani** mulai
menampilkan **app1** lagi — app1 kembali masuk perputaran, dan pembagian bebannya
perlahan kembali mendekati 50%:50%.

### Kenapa ada jeda ~2 detik itu

Itu **bukan kegagalan**, melainkan kerja `proxy_connect_timeout 2s` di
`nginx/nginx.conf`. Selama Nginx belum tahu app1 mati, ia masih mencoba
menghubungi app1 dan menunggu sampai batas 2 detik habis, baru kemudian
memindahkan permintaan ke app2.

Angka ini sudah diukur terpisah dan hasilnya konsisten — lihat
[`../../docs/waktu-peralihan.md`](../../docs/waktu-peralihan.md).

**Penting:** permintaan **tidak pernah gagal**. Klien tetap menerima jawaban
(HTTP 200), hanya lebih lambat beberapa permintaan pertama. Yang perlu
diperhatikan: kalau halaman ini dimuat langsung setelah `stop app1` (app1 sudah
mati sejak awal), Nginx belum pernah mencoba app1, jadi lonjakan 2 detik itu
**tidak muncul** — permintaan langsung dilayani app2.

## Menguji tanpa Docker

Bisa juga dibuka langsung dengan `python3 -m http.server` dari folder ini, lalu
arahkan ke load balancer yang sedang jalan:

```
http://localhost:8000/?url=http://localhost:8080
```

## Menyesuaikan

| Parameter | Arti | Bawaan |
|---|---|---|
| `?url=` | alamat load balancer yang dihubungi | alamat halaman itu sendiri |
| `JEDA_MS` | jeda antar permintaan (ms) | `1000` |
| `MAKS_BARIS` | jumlah baris tabel | `14` |
| `MAKS_TITIK` | jumlah titik pada grafik | `70` |

## Bukti

Tangkapan layar ada di [`../../docs/bukti/`](../../docs/bukti/):

- `klien-normal.png` — keadaan normal, permintaan bergantian app1/app2
- `klien-app1-mati.png` — saat app1 dimatikan: batang kuning ~2.020 ms di grafik

## Catatan

- Halaman ini **hanya mengetahui satu alamat**. Tidak ada app1 maupun app2 yang
  disebut di dalam kode — itu memang inti dari load balancer.
- Tidak ada pustaka pihak ketiga; seluruhnya HTML + JavaScript + `<canvas>`.
