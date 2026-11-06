# SERVER — MK Sistem Paralel

Bagian **server** dari sistem chat & kendali terpusat.
Buka folder ini di Kiro (atau editor apa pun), lalu jalankan.

---

## Cara menjalankan

```bash
cd ~/Documents/TUGAS\ 3\ MK/MK\ SISTEM\ PARALEL/server
python3 server.py
```

Setelah jalan, layar akan menampilkan:

```
================================================================
  SERVER — MK SISTEM PARALEL DAN TERDISTRIBUSI
================================================================
  Port socket    : 5000
  Dashboard      : http://localhost:8081
  Basis data     : .../server/data/chat.db

  Alamat untuk laptop pengguna:
      192.168.1.7:5000
================================================================
```

**Catat alamat itu** — itulah yang dipakai laptop pengguna untuk menyambung.

## Membuka dashboard

Setelah server jalan, buka di peramban:

**http://localhost:8081**

## Menghentikan

Tekan `Ctrl+C` di terminal server.

---

## Pilihan yang tersedia

| Pilihan | Artinya | Bawaan |
|---|---|---|
| `--port N` | Port socket | `5000` |
| `--web N` | Port dashboard | `8081` |
| `--db PATH` | Lokasi basis data | `data/chat.db` |

Contoh:

```bash
python3 server.py --port 5050 --web 8085
```

---

## Isi folder

```
server/
├── server.py            program utamanya
├── static/
│   └── index.html       dashboard (dilayani server)
├── data/
│   └── chat.db          basis data (dibuat otomatis)
└── README.md
```

## Basis data

Dibuat otomatis saat pertama dijalankan. Isinya empat tabel:

| Tabel | Isinya |
|---|---|
| `laptop` | Daftar laptop yang pernah menyambung |
| `pesan` | Setiap pesan yang lewat |
| `perintah` | Perintah yang dikirim + jawaban dari laptop |
| `kejadian` | Catatan laptop yang tersambung dan terputus |

Melihat isinya:

```bash
sqlite3 data/chat.db "SELECT * FROM kejadian ORDER BY id DESC LIMIT 10;"
```

Menghapus dan mulai dari nol:

```bash
rm data/chat.db
```

---

## Cara kerja singkat

- Server membuka port socket dan menunggu laptop menyambung.
- **Setiap laptop dilayani satu thread sendiri.** Inilah yang membuatnya
  paralel — satu laptop yang lambat tidak menahan laptop lain.
- Pesan dipertukarkan dalam bentuk **satu baris JSON per pesan**, supaya dua
  pesan tidak pernah tercampur.
- Dashboard membaca keadaan lewat HTTP di `/api/keadaan`, dan mengirim perintah
  lewat `/api/perintah`.

Bentuk pesannya lengkap ada di `../PROTOKOL.md`.

---

## Kalau ada masalah

| Gejala | Sebab dan obat |
|---|---|
| `Address already in use` | Port sudah dipakai program lain. Jalankan dengan `--port 5050`. |
| Dashboard kosong, tidak ada laptop | Pengguna belum menyambung, atau beda jaringan WiFi. |
| Port 5000 dipakai AirPlay (macOS) | Matikan di System Settings → General → AirDrop & Handoff → AirPlay Receiver, atau pakai `--port 5050`. |

---

## Bagian terkait

- `../user/` — program untuk laptop anggota
- `../PROTOKOL.md` — bentuk pesan yang dipertukarkan
- `../FRD.md` — daftar kebutuhan dashboard
