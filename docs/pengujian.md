# Pengujian

Dokumen ini mencatat apa yang sudah diuji, hasilnya, dan cara mengulanginya.

## Cara mengulang seluruh pengujian

```bash
cd src/server
python3 uji-cepat.py              # 17 pemeriksaan: pesan, perintah, kejadian
python3 uji-pengaman.py           # 13 pemeriksaan: perintah daya harus ditolak
bash uji-dua-terminal.sh          # uji dengan dua terminal sungguhan
```

Ketiga skrip menyalakan servernya sendiri di port uji (5099/8199), jadi cukup
satu perintah dan server yang sedang dipakai di port 5000 tidak terganggu.
`uji-dua-terminal.sh` memakai port uji berbeda karena ia membuka jendela
terminal sungguhan.

---

## Lingkungan pengujian

| | |
|---|---|
| Tanggal | 18 Oktober 2026 |
| Mesin | macOS (Darwin 25.6.0), satu mesin |
| Klien | 3–5 klien otomatis, semuanya dari `127.0.0.1` |
| Basis data | SQLite, dibuat ulang sebelum setiap rangkaian uji |

> **Batas yang wajib disebutkan saat melaporkan.** Seluruh pengujian di bawah
> dijalankan dengan beberapa klien di dalam **satu mesin yang sama**, bukan dengan
> lima laptop yang benar-benar terpisah. Yang sudah terbukti adalah **kebenaran
> logika dan protokolnya** — pesan sampai ke tujuan yang benar, pesan pribadi tidak
> bocor, perintah hanya dijalankan klien yang dituju, dan klien yang putus
> terdeteksi. Yang **belum** terbukti adalah perilaku jaringan sungguhan: latensi,
> pengaruh WiFi, dan perbedaan sistem operasi antar laptop.

---

## 1. Beberapa klien tersambung bersamaan

```bash
python3 uji-cepat.py
```

```
1. Menyalakan server (socket 5099, web 8199)
  ✓ server hidup
2. Tiga pengguna tersambung
  ✓ ketiganya terdaftar
```

Dashboard menampilkan setiap laptop dengan tombol perintahnya masing-masing.

✅ **Hasil: klien bergabung bersamaan, satu thread per klien.**

## 2. Pesan siaran sampai ke semua klien lain

```
3. Pesan siaran dari PC-ALPHA
  ✓ kedua pengguna lain menerima
  ✓ pengirim tidak menerima gemanya
```

Pengirimnya sendiri **tidak** menerima gemanya — perilaku yang disengaja supaya
pengirim tidak melihat pesannya sendiri dua kali.

✅ **Hasil: sampai ke semua yang seharusnya, tanpa gema.**

## 3. Pesan pribadi tidak bocor ke klien lain

```
4. Pesan pribadi dari PC-BETA ke PC-GAMMA
  ✓ PC-GAMMA menerima
  ✓ PC-ALPHA TIDAK menerima (tidak bocor)
```

Klien yang **tidak** menjadi tujuan tidak menerima apa pun. Ini bagian
yang paling penting untuk dibuktikan, karena kesalahan penyaluran pesan adalah
kegagalan paling serius pada sistem seperti ini.

✅ **Hasil: sampai ke tujuan, tidak sampai ke yang bukan tujuan.**

## 4. Perintah hanya dijalankan klien yang dituju

```
6. Perintah lewat dashboard ke PC-BETA saja
  ✓ perintah terkirim
  ✓ PC-BETA menerima perintah
  ✓ PC-ALPHA & PC-GAMMA tidak menerima perintah
  ✓ perintah tercatat di basis data
  ✓ laporan hasil tercatat
  ✓ ditandai berhasil
```

✅ **Hasil: hanya klien yang dituju menerima perintah, dan hasilnya tercatat.**

## 5. Klien yang terputus terdeteksi server

```
8. Pengguna putus
  ✓ server melihat 2 laptop tersisa
  ✓ kejadian putus tercatat
```

Server mengenali putusnya koneksi, mengeluarkannya dari daftar, dan mencatat
kejadiannya ke tabel `kejadian`.

✅ **Hasil: terdeteksi, dan laptop lain tetap tersambung.**

## 6. Nama kembar ditolak

```
7. Nama yang sudah dipakai
  ✓ nama kembar ditolak (tetap 3 laptop)
```

Dua laptop dengan nama sama akan membingungkan dashboard dan membuat pesan
pribadi salah alamat, jadi nama kedua ditolak.

✅ **Hasil: nama kembar tidak menggantikan laptop yang sudah tersambung.**

## 7. Perintah daya ditolak di macOS

```bash
python3 uji-pengaman.py
```

Uji ini menjalankan klien sungguhan di mesin ini, lalu mengirim ketiga perintah
daya. Klien lain dipasang sebagai penyadap untuk memastikan perintah daya tidak
nyasar ke laptop yang tidak dituju.

```
3. Klien sungguhan menolak semuanya (Mac tetap hidup)
  ✓ ketiga perintah daya ditolak (3x)
  ✓ 'kunci' sampai ke klien dan ditolak
  ✓ 'restart' sampai ke klien dan ditolak
  ✓ 'matikan' sampai ke klien dan ditolak
4. Perintah daya TIDAK menyentuh klien lain
  ✓ penyadap tidak menerima perintah daya untuk dirinya — dapat 0
5. Klien lain tetap melayani perintah biasa
  ✓ perintah biasa tetap diteruskan — dapat 1
6. Mac ini masih hidup
  ✓ proses klien masih berjalan
  ✓ Mac menjawab (tidak sedang dimatikan)
```

Di layar klien, penolakannya terlihat begini:

```
  ⚡ PERINTAH DARI SERVER: matikan
     ✗ ditolak di macOS (mode aman). Mac ini dipakai sebagai server/untuk presentasi.
```

✅ **Hasil: ketiga perintah daya ditolak, `pesan` tetap berjalan.**

**Kenapa pengaman ini ada.** Mac ketua dipakai sebagai server *dan* sebagai
komputer kerja. Tanpa pengaman ini, satu perintah yang salah kirim saat
presentasi bisa mematikan komputer yang sedang dipakai presentasi. Pengamannya
ditaruh **di dalam kode** (`user/client.py`), bukan hanya dihindari oleh skrip
uji — jadi perintah daya tetap ditolak walau dikirim dari mana pun.

---

## Ringkasan

| No | Yang diuji | Alat | Hasil |
|---|---|---|---|
| 1 | Tiga klien tersambung bersamaan | `uji-cepat.py` | ✅ |
| 2 | Siaran sampai ke semua klien lain | `uji-cepat.py` | ✅ |
| 3 | Pesan pribadi tidak bocor | `uji-cepat.py` | ✅ |
| 4 | Perintah hanya ke klien yang dituju | `uji-cepat.py` | ✅ |
| 5 | Klien terputus terdeteksi | `uji-cepat.py` | ✅ |
| 6 | Nama kembar ditolak | `uji-cepat.py` | ✅ |
| 7 | Dashboard menjawab | `uji-cepat.py` | ✅ |
| 8 | Perintah daya ditolak di macOS | `uji-pengaman.py` | ✅ |
| 9 | Perintah biasa tetap berjalan | `uji-pengaman.py` | ✅ |

```
uji-cepat.py      → 17 lulus, 0 gagal
uji-pengaman.py   → 13 lulus, 0 gagal
```

## Yang belum diuji

Hal-hal berikut **belum** dibuktikan dan tidak boleh diklaim sudah:

1. **Lima laptop sungguhan yang terpisah.** Pengujian masih satu mesin. Ini langkah
   berikutnya, dan yang paling penting sebelum presentasi.
2. **Perintah daya di Windows.** Baru diuji bahwa perintahnya *ditolak* di macOS.
   Apakah di Windows benar-benar berjalan masih perlu dibuktikan — termasuk apakah
   perlu hak administrator.
3. **WiFi kampus.** Ada kemungkinan jaringan WiFi memisahkan antar-laptop sehingga
   laptop tidak dapat saling menyambung. Ini **harus diuji lebih dahulu** dengan dua
   laptop, jauh sebelum hari presentasi. Kalau terjadi, pakai hotspot dari ponsel.
4. **Beban tinggi.** Belum diukur berapa klien yang bisa dilayani bersamaan sebelum
   server mulai lambat.
5. **Percobaan sambung ulang.** Kalau WiFi sempat putus, klien saat ini tidak
   menyambung ulang sendiri.

## Bukti

| Berkas | Isi |
|---|---|
| `docs/bukti/dashboard.png` | Dashboard dengan lima laptop tersambung |
| `docs/bukti/animasi-pesan-masuk.png` | Animasi pesan masuk (server → laptop) |
| `docs/bukti/animasi-pesan-keluar.png` | Animasi pesan keluar (laptop → server) |

## Berkas data mentah

Basis data hasil pengujian ada di `src/server/data/chat.db` dan bisa dibuka dengan:

```bash
sqlite3 src/server/data/chat.db "SELECT * FROM pesan;"
sqlite3 src/server/data/chat.db "SELECT * FROM perintah;"
sqlite3 src/server/data/chat.db "SELECT * FROM kejadian;"
```
