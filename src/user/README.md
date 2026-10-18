# USER — MK Sistem Paralel

Bagian **pengguna** dari sistem chat & kendali terpusat.
Ini yang dijalankan di laptop tiap anggota.

> **Nama folder sengaja "user", bukan "client".** Supaya di daftar folder
> langsung terbaca: mana **server**, mana **user**.
> Nama berkasnya sendiri tetap `client.py` karena itu istilah yang tepat
> secara teknis, dan supaya tidak salah dengan folder `user`.

---

## Nama laptop

Nama laptop diambil dari berkas **`nama.txt`** di folder ini:

```
PC01 (Yogi)
```

Kalau berkasnya belum ada, program akan **menanyakan sekali** lalu
menyimpannya — jadi tidak perlu diketik ulang tiap kali menjalankan.

Kenapa pakai berkas, bukan ditulis di dalam program? Supaya folder `user/` ini
bisa **disalin ke laptop anggota mana pun**. Setiap orang tinggal mengubah isi
`nama.txt` di laptopnya sendiri, tanpa menyentuh programnya.

Isi yang dipakai kelompok ini:

| Nama | Untuk |
|---|---|
| `PC01 (Yogi)` | laptop ketua — sekaligus server |
| `PC02 (Paris)` | laptop anggota |
| `PC03 (Sidiq)` | laptop anggota |
| `PC04 (Deski)` | laptop anggota |
| `PC05 (Wira)` | laptop anggota |
| `PC06 (Zain)` | laptop anggota |

Mengganti nama untuk **sekali jalan** saja, tanpa mengubah `nama.txt`:

```bash
python3 client.py --server 127.0.0.1 --nama "PC04 (Deski)"
```

---

## Alamat server

Alamat diambil dari berkas **`server.txt`**:

```
192.168.1.7:5000
```

Boleh ditulis alamatnya saja (`192.168.1.7`) — port-nya dianggap `5000`.
Baris yang diawali `#` diabaikan.

Kalau `server.txt` belum ada, program akan **menanyakan sekali** lalu
menyimpannya.

## Cara menjalankan (satu terminal)

```bash
cd ~/Documents/TUGAS\ 3\ MK/MK\ SISTEM\ PARALEL/user
python3 client.py
```

**Tidak perlu mengetik IP** — sudah dibaca dari `server.txt`.

Ganti isi `server.txt` kalau alamat server berubah, atau timpa sekali jalan:

```bash
python3 client.py --server 127.0.0.1
```

Contoh kalau server di laptop yang sama (buat uji coba): isi `server.txt`
dengan `127.0.0.1`.

## Cara mengetik pesan

Setelah tersambung, langsung ketik saja:

```
  > halo semua, ini dari laptop saya
```

Itu otomatis terkirim ke **semua** laptop lain.

| Yang diketik | Artinya |
|---|---|
| `halo semua` | Kirim ke semua laptop |
| `/ke PC04 (Deski) halo` | Kirim hanya ke laptop itu |
| `/online` | Lihat siapa saja yang sedang aktif |
| `/keluar` | Keluar |

## Mode tunggu (paling enak untuk demo)

Kalau tidak perlu mengetik apa pun, cuma ingin menampilkan pesan yang masuk:

```bash
python3 client.py --server 127.0.0.1 --tunggu
```

---

## Pilihan yang tersedia

| Pilihan | Artinya | Bawaan |
|---|---|---|
| `--server IP` | Alamat laptop server | isi `server.txt` |
| `--port N` | Port server | `5000` |
| `--nama NAMA` | Ganti nama sekali jalan saja | isi `nama.txt` |
| `--tunggu` | Hanya menerima, tidak usah mengetik | mati |
| `--izinkan-daya` | Izinkan perintah matikan/restart/kunci di macOS | mati (ditolak) |

Contoh lengkap:

```bash
python3 client.py --server 192.168.1.7 --nama PC-DESKI --tunggu
```

---

## Perintah dari server

Server bisa mengirim perintah ke laptop ini. Yang terlihat di layar:

```
  ⚡ PERINTAH DARI SERVER: kunci
     ✓ layar dikunci
```

| Perintah | Yang terjadi |
|---|---|
| `pesan` | Muncul kotak berisi pesan dari server |
| `kunci` | Layar dikunci |
| `restart` | Laptop restart (jeda 30 detik, bisa dibatalkan) |
| `matikan` | Laptop mati (jeda 30 detik, bisa dibatalkan) |
| `batal` | Membatalkan restart/matikan yang sedang menunggu |

### ⚠️ Penting untuk macOS

Perintah **matikan, restart, dan kunci ditolak secara bawaan** di macOS. Ini
disengaja: Mac sering dipakai sebagai server atau untuk presentasi, dan tidak
boleh ikut mati gara-gara perintah yang salah kirim.

Kalau memang ingin mengizinkan (misalnya saat menguji di Mac sendiri):

```bash
python3 client.py --server 127.0.0.1 --izinkan-daya
```

### ⚠️ Penting untuk Windows

Perintah daya (matikan/restart/kunci) **butuh hak administrator**.

1. Cari **Terminal** atau **Command Prompt** di Start Menu
2. Klik kanan → **Run as Administrator**
3. Baru jalankan perintahnya

Kalau tidak, perintahnya akan gagal dengan pesan "Access is denied".

---

## Isi folder

```
user/
├── client.py     program utamanya
├── nama.txt      nama laptop ini
├── server.txt    alamat laptop server
└── README.md
```

## Tidak ada yang perlu dipasang

Program ini hanya memakai modul bawaan Python (`socket`, `json`, `threading`).
Tidak ada `pip install` yang diperlukan.

Cek Python sudah ada:

```bash
python3 --version
```

Kalau belum ada, unduh dari [python.org](https://www.python.org/downloads/).
**Windows:** saat memasang, centang **"Add Python to PATH"**.

> **Catatan untuk Windows.** Terminal Windows memakai pengodean lama yang tidak
> mengenal karakter ⚡ ✓ ✗ 💬 → dan garis kotak. Program ini sudah mengamankan
> diri (`errors="replace"`), jadi simbol yang tidak bisa ditampilkan hanya
> diganti tanda tanya — program tetap jalan.

---

## Kalau ada masalah

| Gejala | Sebab dan obat |
|---|---|
| `Gagal menyambung ke ...` | Server belum jalan, atau alamat IP salah, atau beda jaringan WiFi |
| `nama 'PC-X' sudah dipakai laptop lain` | Ada laptop lain memakai nama yang sama. Jalankan dengan `--nama` yang berbeda |
| `[!] Sambungan ke server terputus` | Server dimatikan, atau WiFi putus. Jalankan ulang program ini |
| Pesan tidak sampai ke teman | Pastikan tujuannya ada di daftar `/online` |

---

## Bagian terkait

- `../server/` — program server
- `../PROTOKOL.md` — bentuk pesan yang dipertukarkan
