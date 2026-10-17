# Waktu Peralihan saat Satu App Server Dimatikan — MKKL1030

Catatan ini melengkapi [`hasil-uji-kegagalan.md`](hasil-uji-kegagalan.md).
Skenario 3 di dokumen itu hanya membuktikan *"layanan tetap hidup"*; di sini
pertanyaannya lebih tajam: **berapa lama layanan terasa terganggu saat satu node
mati, dan berapa lama node itu kembali masuk perputaran?**

## Cara menjalankan

```bash
docker compose up --build -d
python3 src/tests/uji_waktu_peralihan.py --ulang 4
```

Skrip menekan `http://localhost:8080/` terus-menerus dari luar Docker sambil
memerintahkan `docker compose stop app1`, lalu `start app1`. Setiap respons
dicatat (kode HTTP, latensi, app server yang melayani) ke CSV di
[`data-peralihan/`](data-peralihan/).

## Lingkungan pengujian

| | |
|---|---|
| Mesin | macOS, Docker Desktop, satu host |
| Container | 4 (nginx, app1, app2, redis) dalam satu jaringan bridge |
| Klien penguji | skrip Python di host, 4 thread, 39–47 permintaan/detik nyata |
| Konfigurasi | apa adanya dari repo — `proxy_connect_timeout 2s`, `max_fails=2 fail_timeout=10s` |
| Tanggal | 17 Oktober 2026 |

> **Batas yang wajib disebut saat melaporkan:** seluruh container berjalan pada
> satu mesin. Latensi yang terukur (≈6,7 ms) **tidak mewakili jaringan
> sungguhan** — ia mengukur loopback dalam mesin yang sama, bukan kabel. Yang
> tetap sahih adalah **urutan kejadian dan waktu peralihan**, karena keduanya
> ditentukan oleh Nginx, bukan kecepatan jaringan.

## Hasil — 4 percobaan berurutan

Tiap percobaan: detik ke-6 `stop app1`, detik ke-16 `start app1`, durasi 30 detik.

| # | Permintaan | Gagal | app1 berhenti melayani | app1 kembali melayani | app1 sehat (healthcheck) | Latensi puncak |
|---|---|---|---|---|---|---|
| 1 | 1.310 | **0** | +1,17 s | +3,85 s | +5,93 s | 2.012 ms |
| 2 | 1.390 | **0** | +1,09 s | +1,55 s | +5,95 s | 103 ms |
| 3 | 1.407 | **0** | +1,07 s | +1,39 s | +5,95 s | 16 ms |
| 4 | 1.330 | **0** | +1,10 s | +4,18 s | +5,93 s | 2.012 ms |

Kolom waktu dihitung **relatif terhadap perintah docker**. "+1,10 s" berarti app1
masih melayani selama 1,10 detik setelah perintah `stop` dikirim.

### Temuan utama

1. **Nol permintaan gagal.** Dari **5.437 permintaan** pada empat percobaan,
   **tidak ada satu pun** yang menerima kode selain `200`. Klien tidak pernah
   melihat layanan hilang — peralihan terjadi di belakang load balancer.
2. **app1 berhenti melayani +1,07 s sampai +1,17 s** setelah perintah `stop`.
   Ini stabil (rentang 0,10 s) karena semata-mata waktu Docker menghentikan
   container dengan rapi.
3. **app1 kembali melayani 1,39 s – 4,18 s** setelah perintah `start`, rata-rata
   **2,74 s**. Perhatikan: app1 sudah melayani **sebelum** healthcheck
   menyatakannya `healthy` (+5,93 s). Begitu prosesnya hidup dan bisa dihubungi,
   Nginx langsung mengembalikannya ke perputaran — jadi angka 5,93 s itu **bukan**
   waktu pulih yang dirasakan klien.
4. **Latensi masa tenang rata-rata 6,7 ms** (median 6,8 ms). Dari 5.437
   permintaan, **8 permintaan** (0,147%) tertahan 2,005–2,012 ms — semuanya tetap
   dijawab `200`, seluruhnya oleh app2.

## Kenapa ada lonjakan ~2 detik (versi panjang, untuk kalau ditanya dosen)

Ini bagian yang paling mungkin dipancing saat presentasi. Jawabannya ada di log
Nginx, bukan dugaan.

Ketika app1 sudah berhenti, koneksi ke app1 bisa gagal dengan **dua cara berbeda**,
dan keduanya terlihat di log:

```
[error] connect() failed (111: Connection refused) while connecting to upstream
        ... upstream: "http://172.20.0.3:5001/"

[error] upstream timed out (110: Operation timed out) while connecting to upstream
        ... upstream: "http://172.20.0.3:5001/"
```

| Cara gagal | Yang dirasakan klien | Muncul di |
|---|---|---|
| `Connection refused` (111) | app1 mati mendadak — Nginx tahu seketika, langsung pindah ke app2 | percobaan 2 & 3 |
| `Operation timed out` (110) | koneksi **menggantung sampai `proxy_connect_timeout 2s` habis** → klien menunggu ~2.010 ms | percobaan 1 & 4 |

Karena itu lonjakan yang terukur **2.005–2.012 ms** — praktis sama dengan nilai
`proxy_connect_timeout 2s` di `nginx/nginx.conf`. Ini bukan kebetulan: angka
lonjakan itu *adalah* batas waktu tersebut.

**Jumlah lonjakan = jumlah thread klien.** Percobaan dengan 4 thread menghasilkan
tepat **4** lonjakan (satu per thread), percobaan dengan 6 thread menghasilkan
tepat **6**. Setelah tiap thread kena satu kali, Nginx sudah menandai app1 gagal
(`max_fails=2`) dan membuangnya dari perputaran; permintaan berikutnya mengalir
ke app2 dengan latensi normal ≈6,7 ms.

**Kapan `refused` dan kapan `timeout`?** Diukur, bukan ditebak: keduanya muncul
pada percobaan yang berbeda dengan konfigurasi yang sama. Penyebabnya adalah
`fail_timeout=10s`: node yang sudah ditandai gagal dicoba ulang setelah 10 detik.
Kalau saat pencobaan ulang itu masih ada sisa record gagal, Nginx menolak lebih
cepat (`refused`); kalau tidak, koneksi menggantung sampai batas waktu. Keduanya
tercatat di log pada detik yang berbeda dalam satu sesi yang sama.

**Kalau ingin peralihan lebih halus,** harga 2 detik terlalu mahal untuk layanan
yang ramai. Yang bisa disetel: turunkan `proxy_connect_timeout` (mis. `500ms`),
dan/atau turunkan `max_fails`/`fail_timeout` supaya node mati lebih cepat dibuang.
Keduanya **tidak diubah** pada pengukuran ini supaya angka yang dilaporkan
mewakili konfigurasi yang benar-benar ada di repo — bukan konfigurasi yang sudah
dipoles khusus untuk demo.

## Yang dibuktikan dan yang belum

**Terbukti:**

- Toleransi kegagalan berjalan otomatis — **0 dari 5.437 permintaan gagal**.
- Node yang mati kembali ke perputaran tanpa tindakan manual — rata-rata 2,74 s
  setelah dinyalakan, dan **sebelum** healthcheck selesai.
- Besarnya gangguan yang dirasakan klien terukur: latensi normal 6,7 ms vs
  puncak 2.012 ms, pada 0,147% permintaan.

**Belum terbukti (jangan diklaim sudah):**

- **Pengujian antar-mesin.** Semua container masih di satu host; ini tidak
  membuktikan perilaku saat load balancer dan app server benar-benar terpisah
  jaringan.
- **Kegagalan jalur jaringan yang putus mendadak**, bukan container yang
  dimatikan rapi. Keduanya bisa memberi `refused` vs `timeout` yang berbeda,
  dan itu belum diuji.
- Angka latensi absolut tidak mewakili jaringan sungguhan (lihat catatan di atas).

## Syarat pengujian antar-mesin (belum dikerjakan)

Belum ada mesin kedua yang tersedia di lingkungan ini.

1. **Perangkat kedua** — laptop lain di jaringan WiFi yang sama, atau satu mesin
   virtual. Cara paling praktis di Mac: pasang Colima atau Lima
   (`brew install colima`), jalankan vm Linux, lalu taruh app server di dalamnya.
2. **Pecah container ke dua host:** Nginx + app2 + Redis di mesin A, app1 di
   mesin B. Arahkan `upstream` Nginx ke alamat IP mesin B, bukan nama service
   Docker.
3. **Catat dua angka berbeda:** latensi antar-mesin (kini ≈6,7 ms karena
   loopback) dan waktu peralihan saat koneksi ke mesin B putus.
4. Catat spesifikasi perangkat dan waktu pengujian di kedua mesin — hasil uji
   beban bergantung pada perangkat (lihat rencana proyek bagian 8).

## Berkas

| Berkas | Isi |
|---|---|
| `src/tests/uji_waktu_peralihan.py` | skrip pengukuran, bisa dijalankan ulang |
| `docs/data-peralihan/peralihan-p*.csv` | data mentah tiap permintaan (detik, kode, latensi, server) |
| `docs/hasil-uji-kegagalan.md` | enam skenario kegagalan yang sudah ada |
