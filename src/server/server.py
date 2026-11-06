#!/usr/bin/env python3
"""SERVER — MK Sistem Paralel

Satu laptop jadi pusat. Tugasnya:

  1. Menerima sambungan dari banyak laptop pengguna sekaligus.
     Setiap pengguna dilayani SATU THREAD sendiri, supaya satu laptop yang
     lambat tidak menahan laptop lain. Ini inti "paralel"-nya.

  2. Meneruskan pesan: ke semua orang (siaran) atau ke satu orang saja.

  3. Mengirim perintah ke laptop tertentu (kunci, restart, matikan) dan
     menerima laporan hasilnya.

  4. Menyajikan dashboard sederhana di peramban.

  5. Mencatat semuanya ke basis data supaya bisa dibuktikan lagi nanti.

Jalankan:
    python3 server.py
    python3 server.py --port 5000 --web 8081

Hentikan dengan Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import socket
import sqlite3
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# ------------------------------------------------------------------ pengaturan
AKAR = Path(__file__).resolve().parent
DB = AKAR / "data" / "chat.db"
DIR_STATIS = AKAR / "static"

# Perintah yang boleh dikirim server. Sengaja dibatasi (daftar putih) supaya
# server tidak bisa menjalankan perintah bebas di laptop orang lain.
PERINTAH_DIIZINKAN = {"pesan", "kunci", "restart", "matikan", "batal"}

# Kalau pengguna diam lebih lama dari ini, anggap sudah putus.
#
# PENTING: diam itu NORMAL di aplikasi chat — orang bisa berjam-jam tidak
# mengetik. Jadi waktu ini BUKAN "batas diam", melainkan batas setelah
# dipanggil (ping) dan tetap tidak menjawab. Server memanggil tiap PING_TIAP
# detik, dan baru memutus kalau tidak ada jawaban sama sekali sampai
# BATAS_DIAM.
PING_TIAP = 20.0        # server memanggil pengguna tiap 20 detik
BATAS_DIAM = 90.0       # putus kalau 90 detik tidak ada kabar sama sekali

KUNCI = threading.Lock()

# Antrean pesan untuk dicetak oleh thread utama. Semua thread lain menulis ke
# sini, dan hanya thread utama yang mencetak — supaya tampilan terminal tidak
# saling menimpa (berantakan).
CETAK: queue.Queue[str] = queue.Queue()


def catat(teks: str) -> None:
    """Antre satu baris untuk dicetak thread utama."""
    CETAK.put(teks)


def sekarang() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def jam() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ------------------------------------------------------------------ basis data
def siapkan_db() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS laptop (
            nama     TEXT PRIMARY KEY,
            sistem   TEXT,
            ip       TEXT,
            terakhir TEXT
        );
        CREATE TABLE IF NOT EXISTS pesan (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            pengirim TEXT NOT NULL,
            tujuan   TEXT NOT NULL,
            isi      TEXT NOT NULL,
            waktu    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS perintah (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            sasaran  TEXT NOT NULL,
            aksi     TEXT NOT NULL,
            keterangan TEXT,
            dikirim  TEXT NOT NULL,
            dijawab  TEXT,
            berhasil INTEGER,
            hasil    TEXT
        );
        CREATE TABLE IF NOT EXISTS kejadian (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nama   TEXT NOT NULL,
            jenis  TEXT NOT NULL,     -- 'masuk' atau 'putus'
            waktu  TEXT NOT NULL
        );
        """)


def simpan(bentuk: str, nilai: tuple) -> int:
    """Simpan satu baris, kembalikan id-nya."""
    with KUNCI, sqlite3.connect(DB) as db:
        cur = db.execute(bentuk, nilai)
        return cur.lastrowid or 0


# ------------------------------------------------------------------- pengguna
class Pengguna:
    """Satu laptop yang sedang tersambung."""

    def __init__(self, koneksi: socket.socket, alamat: tuple) -> None:
        self.koneksi = koneksi
        self.ip = alamat[0]
        self.port = alamat[1]
        self.nama = f"laptop-{alamat[1]}"
        self.nama_tetap = False          # sudah menyebutkan namanya sendiri
        self.sistem = "?"
        self.masuk = time.time()
        self.terakhir_dengar = time.time()
        self.terakhir_kirim = time.time()
        self.kunci_tulis = threading.Lock()

    # --- kirim ---------------------------------------------------------
    def kirim(self, data: dict) -> bool:
        """Kirim satu objek JSON. Dikunci supaya dua thread tidak saling sisip."""
        baris = json.dumps(data, ensure_ascii=False) + "\n"
        with self.kunci_tulis:
            try:
                self.koneksi.sendall(baris.encode("utf-8"))
                self.terakhir_kirim = time.time()
                return True
            except OSError:
                return False

    def masih_hidup(self) -> bool:
        """Periksa apakah pengguna perlu dipanggil (ping) atau sudah putus.

        Dipanggil dari thread-nya sendiri tiap kali recv habis waktu.
        """
        sekarang_ = time.time()
        # Sudah lama tidak ada kabar sama sekali → anggap putus.
        if sekarang_ - self.terakhir_dengar > BATAS_DIAM:
            return False
        # Sudah waktunya memanggil, dan tidak ada data lain yang dikirim.
        if sekarang_ - self.terakhir_kirim > PING_TIAP:
            self.kirim({"tipe": "ping"})
        return True

    # --- keterangan ----------------------------------------------------
    def lama(self) -> str:
        detik = int(time.time() - self.masuk)
        if detik < 60:
            return f"{detik} detik"
        if detik < 3600:
            return f"{detik // 60} menit"
        return f"{detik // 3600} jam {detik % 3600 // 60} menit"

    def keterangan(self) -> dict:
        return {"nama": self.nama, "sistem": self.sistem, "ip": self.ip,
                "lama": self.lama()}


# --------------------------------------------------------------- daftar pengguna
PENGGUNA: dict[str, Pengguna] = {}
GANTI_DAFTAR = threading.Condition()   # dibangunkan tiap daftar berubah


def daftar_pengguna() -> list[dict]:
    with KUNCI:
        return [p.keterangan() for p in PENGGUNA.values()]


def siarkan(data: dict, kecuali: str | None = None) -> int:
    """Kirim ke semua pengguna. Kembalikan jumlah yang berhasil."""
    berhasil = 0
    with KUNCI:
        sasaran = list(PENGGUNA.items())
    for nama, p in sasaran:
        if nama == kecuali:
            continue
        if p.kirim(data):
            berhasil += 1
    return berhasil


def kabari_daftar() -> None:
    siarkan({"tipe": "online", "daftar": daftar_pengguna()})


# ------------------------------------------------------------------ pengguna
def layani(p: Pengguna) -> None:
    """Satu thread untuk satu pengguna, sampai sambungannya putus."""
    p.koneksi.settimeout(1.0)
    penyangga = b""
    try:
        while True:
            try:
                potongan = p.koneksi.recv(8192)
            except socket.timeout:
                # Tidak ada data masuk. Periksa: perlu dipanggil (ping), atau
                # sudah benar-benar putus.
                if not p.masih_hidup():
                    catat(f"  [!] {p.nama} tidak menjawab {int(BATAS_DIAM)} detik "
                          f"— dianggap putus")
                    break
                continue
            except OSError:
                break

            if not potongan:
                break                      # sambungan ditutup pengguna

            p.terakhir_dengar = time.time()
            penyangga += potongan

            # Satu baris = satu objek JSON.
            while b"\n" in penyangga:
                baris, penyangga = penyangga.split(b"\n", 1)
                if not baris.strip():
                    continue
                if len(baris) > 64_000:
                    p.kirim({"tipe": "galat", "pesan": "baris terlalu panjang"})
                    continue
                try:
                    data = json.loads(baris.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    p.kirim({"tipe": "galat", "pesan": "data tidak bisa dibaca"})
                    continue
                tangani(p, data)
    except OSError:
        pass
    finally:
        lepaskan(p)


def lepaskan(p: Pengguna) -> None:
    """Bersihkan setelah pengguna putus."""
    with KUNCI:
        if PENGGUNA.get(p.nama) is p:
            PENGGUNA.pop(p.nama, None)
    simpan("INSERT INTO kejadian (nama, jenis, waktu) VALUES (?,?,?)",
           (p.nama, "putus", sekarang()))
    catat(f"  [putus] {p.nama}  ({p.ip}) — tersambung {p.lama()}")
    kabari_daftar()
    with GANTI_DAFTAR:
        GANTI_DAFTAR.notify_all()
    try:
        p.koneksi.close()
    except OSError:
        pass


# ------------------------------------------------------------------- tangani
def tangani(p: Pengguna, data: dict) -> None:
    tipe = data.get("tipe")

    # --- mendaftar ------------------------------------------------------
    if tipe == "daftar":
        nama = str(data.get("nama") or "").strip()[:40] or p.nama
        p.sistem = str(data.get("sistem") or "?")[:40]

        # Kalau nama sudah dipakai pengguna lain, tolak dengan jelas.
        with KUNCI:
            sudah_ada = nama in PENGGUNA and PENGGUNA[nama] is not p
        if sudah_ada:
            p.kirim({"tipe": "galat",
                     "pesan": f"nama '{nama}' sudah dipakai laptop lain. "
                              f"Pilih nama lain."})
            catat(f"  [!] {p.ip} memakai nama '{nama}' yang sudah dipakai")
            return

        p.nama = nama
        p.nama_tetap = True
        with KUNCI:
            PENGGUNA[nama] = p
        simpan("""INSERT INTO laptop (nama, sistem, ip, terakhir) VALUES (?,?,?,?)
                  ON CONFLICT(nama) DO UPDATE SET
                    sistem=excluded.sistem, ip=excluded.ip, terakhir=excluded.terakhir""",
               (nama, p.sistem, p.ip, sekarang()))
        simpan("INSERT INTO kejadian (nama, jenis, waktu) VALUES (?,?,?)",
               (nama, "masuk", sekarang()))
        catat(f"  [masuk] {nama}  ({p.sistem}, {p.ip})")

        p.kirim({"tipe": "selamat", "nama_kamu": nama,
                 "online": [x["nama"] for x in daftar_pengguna()]})
        kabari_daftar()
        with GANTI_DAFTAR:
            GANTI_DAFTAR.notify_all()
        return

    # --- pesan ----------------------------------------------------------
    if tipe == "pesan":
        if not p.nama_tetap:
            p.kirim({"tipe": "galat", "pesan": "belum mendaftar"})
            return
        tujuan = str(data.get("ke") or "semua")[:40]
        isi = str(data.get("isi") or "")[:2000]
        if not isi.strip():
            p.kirim({"tipe": "galat", "pesan": "pesan kosong"})
            return

        simpan("INSERT INTO pesan (pengirim, tujuan, isi, waktu) VALUES (?,?,?,?)",
               (p.nama, tujuan, isi, sekarang()))
        keluaran = {"tipe": "pesan", "dari": p.nama, "ke": tujuan,
                    "isi": isi, "waktu": sekarang()}

        if tujuan == "semua":
            jumlah = siarkan(keluaran, kecuali=p.nama)
            p.kirim({"tipe": "info", "pesan": f"terkirim ke {jumlah} laptop"})
            catat(f"  [pesan] {p.nama} → semua ({jumlah}): {isi[:50]}")
        else:
            sasaran = PENGGUNA.get(tujuan)
            if sasaran and sasaran.kirim(keluaran):
                p.kirim({"tipe": "info", "pesan": f"terkirim ke {tujuan}"})
                catat(f"  [pesan] {p.nama} → {tujuan}: {isi[:50]}")
            else:
                p.kirim({"tipe": "galat",
                         "pesan": f"laptop '{tujuan}' tidak sedang tersambung"})
                catat(f"  [!] {p.nama} gagal kirim ke {tujuan} (tidak tersambung)")
        return

    # --- laporan hasil perintah -----------------------------------------
    if tipe == "hasil":
        aksi = str(data.get("aksi") or "")
        berhasil = 1 if data.get("berhasil") else 0
        pesan = str(data.get("pesan") or "")[:300]
        id_perintah = data.get("id_perintah")

        if id_perintah:
            simpan("""UPDATE perintah SET dijawab=?, berhasil=?, hasil=?
                      WHERE id=?""", (sekarang(), berhasil, pesan, id_perintah))
        tanda = "✓" if berhasil else "✗"
        catat(f"  [hasil] {tanda} {p.nama}: {pesan}")
        return

    # --- ping / pong -----------------------------------------------------
    if tipe == "pong":
        return

    if tipe == "ping":
        p.kirim({"tipe": "pong"})
        return

    p.kirim({"tipe": "galat", "pesan": f"tipe tidak dikenal: {tipe}"})


# --------------------------------------------------------------- dari dashboard
def kirim_pesan(tujuan: str, isi: str) -> dict:
    """Kirim pesan CHAT dari dashboard — tercatat di tabel `pesan`."""
    isi = isi[:2000]
    if not isi.strip():
        return {"ok": False, "pesan": "pesannya masih kosong"}

    tujuan = tujuan[:40] or "semua"
    simpan("INSERT INTO pesan (pengirim, tujuan, isi, waktu) VALUES (?,?,?,?)",
           ("SERVER", tujuan, isi, sekarang()))
    keluaran = {"tipe": "pesan", "dari": "SERVER", "ke": tujuan,
                "isi": isi, "waktu": sekarang()}

    if tujuan == "semua":
        jumlah = siarkan(keluaran)
        catat(f"  [pesan] SERVER → semua ({jumlah}): {isi[:50]}")
        return {"ok": True, "terkirim": jumlah}
    if tujuan in PENGGUNA:
        ok = PENGGUNA[tujuan].kirim(keluaran)
        catat(f"  [pesan] SERVER → {tujuan}: {isi[:50]}")
        return {"ok": ok, "terkirim": 1 if ok else 0,
                "pesan": "" if ok else "gagal mengirim"}
    return {"ok": False, "pesan": f"laptop '{tujuan}' tidak sedang tersambung"}


def kirim_perintah(sasaran: str, aksi: str, keterangan: str = "") -> dict:
    if aksi not in PERINTAH_DIIZINKAN:
        return {"ok": False, "pesan": f"aksi '{aksi}' tidak diizinkan"}

    if sasaran == "semua":
        with KUNCI:
            nama_sasaran = list(PENGGUNA.keys())
    else:
        nama_sasaran = [sasaran]

    if not nama_sasaran:
        return {"ok": False, "pesan": "tidak ada laptop yang tersambung"}

    terkirim, gagal = [], []
    for nama in nama_sasaran:
        p = PENGGUNA.get(nama)
        if not p:
            gagal.append(nama)
            continue
        id_perintah = simpan(
            """INSERT INTO perintah (sasaran, aksi, keterangan, dikirim)
               VALUES (?,?,?,?)""", (nama, aksi, keterangan[:2000], sekarang()))
        if p.kirim({"tipe": "perintah", "aksi": aksi,
                    "keterangan": keterangan, "id": id_perintah}):
            terkirim.append(nama)
        else:
            gagal.append(nama)
        catat(f"  [perintah] {aksi} → {nama}")

    return {"ok": bool(terkirim), "terkirim": terkirim, "gagal": gagal}


# ------------------------------------------------------------------ dashboard
class Dashboard(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(DIR_STATIS), **k)

    def log_message(self, *a):
        pass

    def _json(self, objek):
        isi = json.dumps(objek, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(isi)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(isi)

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse

        if self.path.startswith("/api/keadaan"):
            with KUNCI, sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                pesan = [dict(r) for r in db.execute(
                    "SELECT * FROM pesan ORDER BY id DESC LIMIT 40")]
                perintah = [dict(r) for r in db.execute(
                    "SELECT * FROM perintah ORDER BY id DESC LIMIT 20")]
                kejadian = [dict(r) for r in db.execute(
                    "SELECT * FROM kejadian ORDER BY id DESC LIMIT 25")]
                jumlah = {
                    "pesan": db.execute("SELECT COUNT(*) FROM pesan").fetchone()[0],
                    "perintah": db.execute("SELECT COUNT(*) FROM perintah").fetchone()[0],
                }
            self._json({"online": daftar_pengguna(), "pesan": pesan,
                        "perintah": perintah, "kejadian": kejadian,
                        "jumlah": jumlah})
            return

        # Kirim PESAN CHAT dari dashboard. Dibedakan dari /api/perintah supaya
        # chat tercatat di tabel `pesan` dan ikut terhitung di kartu "Pesan
        # terkirim" — kalau lewat jalur perintah, chat tidak pernah tercatat
        # sebagai pesan (ini pernah terjadi dan kartunya selalu 0).
        if self.path.startswith("/api/pesan"):
            q = parse_qs(urlparse(self.path).query)
            self._json(kirim_pesan(q.get("tujuan", ["semua"])[0],
                                   q.get("isi", [""])[0]))
            return

        if self.path.startswith("/api/perintah"):
            q = parse_qs(urlparse(self.path).query)
            self._json(kirim_perintah(q.get("sasaran", ["semua"])[0],
                                      q.get("aksi", [""])[0],
                                      q.get("keterangan", [""])[0]))
            return

        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()


# ---------------------------------------------------------------------- utama
def alamat_lokal() -> list[str]:
    hasil = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        hasil.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return hasil or ["<ip-mesin-ini>"]


def pencetak() -> None:
    """Satu-satunya thread yang menulis ke layar."""
    while True:
        baris = CETAK.get()
        if baris is None:
            return
        print(baris, flush=True)


def utama() -> int:
    p = argparse.ArgumentParser(description="Server chat & kendali — MK Sistem Paralel")
    p.add_argument("--port", type=int, default=5000, help="port socket (bawaan 5000)")
    p.add_argument("--web", type=int, default=8081, help="port dashboard (bawaan 8081)")
    p.add_argument("--db", help="lokasi basis data (bawaan data/chat.db)")
    a = p.parse_args()

    global DB
    if a.db:
        DB = Path(a.db)

    siapkan_db()

    # thread pencetak
    threading.Thread(target=pencetak, daemon=True).start()

    # socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", a.port))
    srv.listen(30)

    # dashboard
    web = HTTPServer(("0.0.0.0", a.web), Dashboard)
    threading.Thread(target=web.serve_forever, daemon=True).start()

    print("=" * 64)
    print("  SERVER — MK SISTEM PARALEL DAN TERDISTRIBUSI")
    print("=" * 64)
    print(f"  Port socket    : {a.port}")
    print(f"  Dashboard      : http://localhost:{a.web}")
    print(f"  Basis data     : {DB}")
    print()
    print("  Alamat untuk laptop pengguna:")
    for ip in alamat_lokal():
        print(f"      {ip}:{a.port}")
    print()
    print("  Tunggu: pengguna menyambung. Tekan Ctrl+C untuk berhenti.")
    print("=" * 64)
    print(flush=True)

    try:
        while True:
            koneksi, alamat = srv.accept()
            pengguna = Pengguna(koneksi, alamat)
            threading.Thread(target=layani, args=(pengguna,), daemon=True).start()
    except KeyboardInterrupt:
        print("\n  Server dihentikan.")
    finally:
        with KUNCI:
            for pengguna in PENGGUNA.values():
                pengguna.kirim({"tipe": "info", "pesan": "server berhenti"})
                try:
                    pengguna.koneksi.close()
                except OSError:
                    pass
        srv.close()
        web.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(utama())
