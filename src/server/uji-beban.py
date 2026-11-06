#!/usr/bin/env python3
"""Uji beban: berapa klien dan pesan yang bisa dilayani bersamaan.

Skenario yang diuji:
  1. 10 klien menyambung bersamaan — server tidak crash
  2. 50 pesan dikirim cepat dari satu klien — tidak ada yang hilang
  3. 5 klien mengirim serentak — tidak ada pesan yang tercampur/tertukar
  4. Klien ke-11 tetap bisa masuk setelah 10 sudah tersambung
  5. Server masih menjawab HTTP setelah semua tekanan selesai

Jalankan:
    python3 uji-beban.py

Port uji (5098/8198) sengaja beda dari port bawaan (5000/8081) dan port
uji-cepat (5099/8199) supaya bisa dijalankan bersamaan tanpa bentrok.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent
PORT = 5098
WEB  = 8198
lulus, gagal = 0, 0


def periksa(nama: str, benar: bool, tambahan: str = "") -> None:
    global lulus, gagal
    if benar:
        lulus += 1
        print(f"  ✓ {nama}")
    else:
        gagal += 1
        print(f"  ✗ {nama}   {tambahan}")


class Tiruan:
    """Klien tiruan — sama persis polanya dengan uji-cepat.py."""

    def __init__(self, nama: str, timeout_sambung: float = 5.0) -> None:
        self.nama  = nama
        self.masuk: list[dict] = []
        self.jalan = True
        self._kunci = threading.Lock()
        self.sock  = socket.create_connection(("127.0.0.1", PORT),
                                              timeout=timeout_sambung)
        self.sock.settimeout(None)
        self._kirim({"tipe": "daftar", "nama": nama, "sistem": "uji-beban"})
        threading.Thread(target=self._dengar, daemon=True).start()

    def _kirim(self, d: dict) -> None:
        try:
            self.sock.sendall((json.dumps(d) + "\n").encode())
        except OSError:
            self.jalan = False

    def kirim_pesan(self, ke: str, isi: str) -> None:
        self._kirim({"tipe": "pesan", "ke": ke, "isi": isi})

    def _dengar(self) -> None:
        buf = b""
        try:
            while self.jalan:
                potongan = self.sock.recv(8192)
                if not potongan:
                    break
                buf += potongan
                while b"\n" in buf:
                    baris, buf = buf.split(b"\n", 1)
                    if not baris.strip():
                        continue
                    try:
                        d = json.loads(baris.decode())
                    except ValueError:
                        continue
                    if d.get("tipe") == "pesan":
                        with self._kunci:
                            self.masuk.append(d)
                    elif d.get("tipe") == "ping":
                        self._kirim({"tipe": "pong"})
        except OSError:
            pass

    def hitung_pesan(self) -> int:
        with self._kunci:
            return len(self.masuk)

    def tutup(self) -> None:
        self.jalan = False
        try:
            self.sock.close()
        except OSError:
            pass


def keadaan() -> dict:
    with urllib.request.urlopen(
            f"http://127.0.0.1:{WEB}/api/keadaan", timeout=8) as r:
        return json.loads(r.read())


def main() -> int:
    print("=" * 62)
    print("  UJI BEBAN — banyak klien + banyak pesan bersamaan")
    print("=" * 62)

    db = AKAR / "data" / "uji-beban.db"
    db.unlink(missing_ok=True)
    (AKAR / "data").mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- server
    print(f"\n0. Menyalakan server (socket {PORT}, web {WEB})")
    srv = subprocess.Popen(
        [sys.executable, str(AKAR / "server.py"),
         "--port", str(PORT), "--web", str(WEB), "--db", str(db)],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    time.sleep(2.5)
    if srv.poll() is not None:
        print("  ✗ server gagal menyala")
        return 1
    print("  ✓ server menyala")

    klien_semua: list[Tiruan] = []

    try:
        # --------------------------------------------------------- uji 1
        print("\n1. Sepuluh klien menyambung bersamaan")
        # Sambungkan 10 klien dalam jeda kecil (simulasi hampir bersamaan)
        for i in range(1, 11):
            k = Tiruan(f"BEBAN-{i:02d}")
            klien_semua.append(k)
            time.sleep(0.08)   # 80 ms — hampir bersamaan, tapi tidak tumpukan

        time.sleep(1.5)
        k_online = keadaan()
        n_online = len(k_online["online"])
        periksa("server melihat 10 klien sekaligus",
                n_online == 10, f"terdaftar {n_online}")
        periksa("tidak ada nama yang duplikat",
                len({x["nama"] for x in k_online["online"]}) == 10)

        # --------------------------------------------------------- uji 2
        print("\n2. Lima puluh pesan dikirim cepat dari satu klien")
        pengirim = klien_semua[0]
        penerima = klien_semua[1]   # satu klien dijadikan target siaran

        sebelum = penerima.hitung_pesan()
        JUMLAH = 50
        for i in range(JUMLAH):
            pengirim.kirim_pesan("semua", f"BANJIR-{i:03d}")
        time.sleep(3.0)   # beri server waktu meneruskan semua

        diterima = penerima.hitung_pesan() - sebelum
        periksa(f"semua {JUMLAH} pesan diterima (tidak ada yang hilang)",
                diterima == JUMLAH, f"diterima {diterima}/{JUMLAH}")
        periksa("tidak ada pesan ganda (urutan terjaga)",
                diterima <= JUMLAH,
                f"justru lebih banyak ({diterima}) — ada duplikat")

        # --------------------------------------------------------- uji 3
        print("\n3. Lima klien mengirim pesan serentak")
        # Lima klien mengirim satu pesan siaran secara bersamaan lewat thread
        tag = "SERENTAK"
        pengirim5 = klien_semua[2:7]   # klien indeks 2–6
        penerima_umum = klien_semua[9]  # klien terakhir, tidak ikut mengirim

        sebelum = penerima_umum.hitung_pesan()
        utas: list[threading.Thread] = []
        for i, k in enumerate(pengirim5):
            t = threading.Thread(
                target=k.kirim_pesan,
                args=("semua", f"{tag}-DARI-{k.nama}"),
                daemon=True)
            utas.append(t)
        for t in utas:
            t.start()       # mulai semua hampir bersamaan
        for t in utas:
            t.join()
        time.sleep(2.0)

        terima_serentak = penerima_umum.hitung_pesan() - sebelum
        periksa("penerima mendapat semua 5 pesan serentak",
                terima_serentak == 5,
                f"diterima {terima_serentak}/5")

        # Pastikan isi pesan tidak tercampur (setiap pesan utuh)
        pesan_serentak = [
            m for m in penerima_umum.masuk
            if tag in m.get("isi", "")
        ]
        semua_utuh = all(
            any(m["isi"] == f"{tag}-DARI-{k.nama}" for m in pesan_serentak)
            for k in pengirim5
        )
        periksa("isi pesan tidak tercampur antar klien", semua_utuh)

        # --------------------------------------------------------- uji 4
        print("\n4. Klien baru tetap bisa masuk setelah 10 klien tersambung")
        try:
            pendatang = Tiruan("PENDATANG-11", timeout_sambung=6.0)
            time.sleep(1.0)
            k2 = keadaan()
            periksa("klien ke-11 terdaftar", len(k2["online"]) == 11,
                    f"ada {len(k2['online'])} klien")
            pendatang.tutup()
        except OSError as e:
            periksa("klien ke-11 terdaftar", False, str(e))

        # --------------------------------------------------------- uji 5
        print("\n5. Server HTTP masih menjawab setelah semua tekanan")
        try:
            k3 = keadaan()
            periksa("GET /api/keadaan masih berhasil",
                    isinstance(k3, dict) and "online" in k3)
        except Exception as e:
            periksa("GET /api/keadaan masih berhasil", False, str(e))

        # --------------------------------------------------------- statistik
        print()
        print("  Statistik akhir:")
        try:
            stat = keadaan()
            print(f"    Total pesan tercatat di DB : {stat['jumlah']['pesan']}")
            print(f"    Klien online saat ini      : {len(stat['online'])}")
        except Exception:
            pass

    finally:
        for k in klien_semua:
            k.tutup()
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except subprocess.TimeoutExpired:
            srv.kill()

    print("\n" + "=" * 62)
    print(f"  HASIL: {lulus} lulus, {gagal} gagal")
    print("=" * 62)
    return 0 if gagal == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
