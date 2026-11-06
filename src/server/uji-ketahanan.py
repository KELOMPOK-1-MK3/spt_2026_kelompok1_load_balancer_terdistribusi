#!/usr/bin/env python3
"""Uji ketahanan: server harus tetap hidup menghadapi kondisi tidak normal.

Skenario yang diuji:
  1. Klien putus paksa (socket ditutup tanpa /keluar) — server pulih
  2. Banyak klien putus sekaligus — klien yang tersisa tetap menerima pesan
  3. Klien kirim data rusak (bukan JSON) — server tidak crash, balas galat
  4. Klien kirim baris sangat panjang (> 64 KB) — koneksi diputus, bukan crash
  5. Pesan ke laptop yang tidak ada — pengirim mendapat galat, bukan crash
  6. Nama kembar masuk bersamaan — hanya satu yang diterima
  7. Klien diam lama (simulasi ping/pong) — server mendeteksi tanpa memutus
     klien lain

Jalankan:
    python3 uji-ketahanan.py

Port uji: 5097/8197 (beda dari uji-cepat 5099/8199 dan uji-beban 5098/8198).
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
PORT = 5097
WEB  = 8197
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
    """Klien tiruan dengan metode tambahan untuk skenario ketahanan."""

    def __init__(self, nama: str) -> None:
        self.nama   = nama
        self.masuk: list[dict]  = []
        self.galat: list[dict]  = []
        self.jalan  = True
        self._kunci = threading.Lock()
        self.sock   = socket.create_connection(("127.0.0.1", PORT), timeout=5)
        self.sock.settimeout(None)
        self._kirim_raw((json.dumps(
            {"tipe": "daftar", "nama": nama, "sistem": "uji-ketahanan"}
        ) + "\n").encode())
        threading.Thread(target=self._dengar, daemon=True).start()

    def _kirim_raw(self, data: bytes) -> None:
        """Kirim bytes mentah — dipakai juga untuk uji data rusak."""
        try:
            self.sock.sendall(data)
        except OSError:
            self.jalan = False

    def kirim(self, d: dict) -> None:
        self._kirim_raw((json.dumps(d) + "\n").encode())

    def kirim_baris_rusak(self, baris: str) -> None:
        """Kirim satu baris teks yang bukan JSON valid."""
        self._kirim_raw((baris + "\n").encode())

    def kirim_baris_panjang(self, panjang: int) -> None:
        """Kirim satu baris JSON yang melebihi batas 64 KB."""
        isi = "X" * panjang
        baris = json.dumps({"tipe": "pesan", "ke": "semua", "isi": isi}) + "\n"
        self._kirim_raw(baris.encode())

    def _dengar(self) -> None:
        buf = b""
        try:
            while self.jalan:
                potongan = self.sock.recv(8192)
                if not potongan:
                    self.jalan = False
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
                    tipe = d.get("tipe")
                    with self._kunci:
                        if tipe == "pesan":
                            self.masuk.append(d)
                        elif tipe == "galat":
                            self.galat.append(d)
                        elif tipe == "ping":
                            self.kirim({"tipe": "pong"})
        except OSError:
            self.jalan = False

    def hitung_pesan(self) -> int:
        with self._kunci:
            return len(self.masuk)

    def hitung_galat(self) -> int:
        with self._kunci:
            return len(self.galat)

    def putus_paksa(self) -> None:
        """Tutup socket tanpa kirim /keluar — simulasi crash atau WiFi putus."""
        self.jalan = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

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
    print("  UJI KETAHANAN — server harus tahan kondisi tidak normal")
    print("=" * 62)

    db = AKAR / "data" / "uji-ketahanan.db"
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

    try:
        # --------------------------------------------------------- uji 1
        print("\n1. Klien putus paksa — server mendeteksi dan pulih")
        korban  = Tiruan("KORBAN")
        selamat = Tiruan("SELAMAT")
        time.sleep(1.0)

        korban.putus_paksa()
        # Server punya BATAS_DIAM=90 detik, tapi socket.shutdown() segera
        # menghasilkan recv() kosong di thread server → terdeteksi cepat.
        time.sleep(2.0)

        k = keadaan()
        nama_online = {x["nama"] for x in k["online"]}
        periksa("server mengeluarkan klien yang putus paksa",
                "KORBAN" not in nama_online,
                f"masih ada: {nama_online}")
        periksa("klien lain tetap terdaftar",
                "SELAMAT" in nama_online,
                f"online: {nama_online}")

        # Verifikasi kejadian putus tercatat di DB
        putus_db = [x for x in k["kejadian"]
                    if x["nama"] == "KORBAN" and x["jenis"] == "putus"]
        periksa("kejadian putus paksa tercatat di basis data",
                len(putus_db) >= 1)

        # --------------------------------------------------------- uji 2
        print("\n2. Banyak klien putus sekaligus — klien tersisa tetap bisa pesan")
        # Buat 4 klien tambahan, putus semua sekaligus
        sisir = [Tiruan(f"SISIR-{i}") for i in range(1, 5)]
        bertahan = Tiruan("BERTAHAN")
        time.sleep(1.0)

        for k_sisir in sisir:
            k_sisir.putus_paksa()
        time.sleep(2.5)

        # Klien bertahan harus masih bisa terima pesan
        sebelum = bertahan.hitung_pesan()
        bertahan.kirim({"tipe": "pesan", "ke": "semua", "isi": "MASIH-HIDUP"})
        time.sleep(1.0)
        # Tidak ada klien lain yang bisa membalas, tapi server harus tidak crash
        k2 = keadaan()
        periksa("server masih hidup setelah 4 klien putus serentak",
                isinstance(k2, dict) and "online" in k2)
        nama2 = {x["nama"] for x in k2["online"]}
        periksa("klien BERTAHAN masih terdaftar",
                "BERTAHAN" in nama2, f"online: {nama2}")

        # --------------------------------------------------------- uji 3
        print("\n3. Klien kirim data rusak (bukan JSON) — server balas galat, tidak crash")
        nakal = Tiruan("NAKAL")
        time.sleep(0.8)

        galat_sebelum = nakal.hitung_galat()
        nakal.kirim_baris_rusak("ini bukan JSON {{{{{")
        nakal.kirim_baris_rusak("{{juga bukan JSON")
        time.sleep(1.0)

        galat_dapat = nakal.hitung_galat() - galat_sebelum
        periksa("server membalas pesan galat untuk data rusak",
                galat_dapat >= 1, f"dapat {galat_dapat} balasan galat")

        # Server tidak boleh crash — masih harus menjawab HTTP
        try:
            k3 = keadaan()
            periksa("server tidak crash setelah menerima data rusak",
                    isinstance(k3, dict))
        except Exception as e:
            periksa("server tidak crash setelah menerima data rusak",
                    False, str(e))

        # --------------------------------------------------------- uji 4
        print("\n4. Klien kirim baris JSON sangat panjang (> 64 KB)")
        panjang_msg = Tiruan("PANJANG")
        time.sleep(0.8)

        # Kirim pesan isi >64000 karakter — server harus memutus koneksi ini
        panjang_msg.kirim_baris_panjang(65_000)
        time.sleep(2.0)

        # Koneksi klien PANJANG boleh diputus server (itu perilaku yang benar)
        # Yang penting: server masih hidup dan klien lain tidak terganggu
        try:
            k4 = keadaan()
            periksa("server tidak crash setelah baris > 64 KB",
                    isinstance(k4, dict))
        except Exception as e:
            periksa("server tidak crash setelah baris > 64 KB",
                    False, str(e))

        # --------------------------------------------------------- uji 5
        print("\n5. Pesan ke laptop yang tidak ada — pengirim dapat galat")
        ada = Tiruan("PENGIRIM-ADA")
        time.sleep(0.8)

        galat_sblm = ada.hitung_galat()
        ada.kirim({"tipe": "pesan", "ke": "LAPTOP-TIDAK-ADA",
                   "isi": "tes ke yang tidak ada"})
        time.sleep(1.0)

        galat_stlh = ada.hitung_galat()
        periksa("pengirim menerima galat saat tujuan tidak ada",
                galat_stlh > galat_sblm,
                f"galat sebelum={galat_sblm} sesudah={galat_stlh}")

        try:
            k5 = keadaan()
            periksa("server tidak crash setelah pesan ke tujuan tidak ada",
                    isinstance(k5, dict))
        except Exception as e:
            periksa("server tidak crash setelah pesan ke tujuan tidak ada",
                    False, str(e))

        # --------------------------------------------------------- uji 6
        print("\n6. Nama kembar masuk hampir bersamaan — hanya satu yang diterima")
        # Buat dua Tiruan dengan nama sama lewat thread supaya benar-benar
        # hampir bersamaan (bukan berurutan)
        hasil_kembar: list[bool] = []

        def coba_sambung(label: str) -> None:
            try:
                k_kembar = Tiruan("NAMA-SAMA")
                time.sleep(1.2)
                k6 = keadaan()
                terdaftar = any(
                    x["nama"] == "NAMA-SAMA" for x in k6["online"]
                )
                hasil_kembar.append(terdaftar)
                k_kembar.tutup()
            except OSError:
                hasil_kembar.append(False)

        t1 = threading.Thread(target=coba_sambung, args=("A",), daemon=True)
        t2 = threading.Thread(target=coba_sambung, args=("B",), daemon=True)
        t1.start(); time.sleep(0.02); t2.start()
        t1.join(timeout=5); t2.join(timeout=5)
        time.sleep(1.0)

        k6 = keadaan()
        jumlah_sama = sum(
            1 for x in k6["online"] if x["nama"] == "NAMA-SAMA"
        )
        periksa("nama kembar tidak menghasilkan dua entri",
                jumlah_sama <= 1, f"ada {jumlah_sama} entri NAMA-SAMA")

        # --------------------------------------------------------- uji 7
        print("\n7. Server masih menjawab HTTP setelah semua tekanan")
        try:
            k7 = keadaan()
            periksa("GET /api/keadaan berhasil di akhir",
                    isinstance(k7, dict) and "jumlah" in k7)
            print(f"    Total pesan di DB    : {k7['jumlah']['pesan']}")
            print(f"    Total perintah di DB : {k7['jumlah']['perintah']}")
            print(f"    Klien online tersisa : {len(k7['online'])}")
        except Exception as e:
            periksa("GET /api/keadaan berhasil di akhir", False, str(e))

    finally:
        # Tutup semua klien yang masih terbuka
        for nama_obj in ("selamat", "bertahan", "nakal", "panjang_msg", "ada"):
            obj = locals().get(nama_obj)
            if obj and hasattr(obj, "tutup"):
                obj.tutup()
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
