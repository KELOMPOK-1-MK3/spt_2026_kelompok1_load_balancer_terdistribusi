#!/usr/bin/env python3
"""Uji cepat: server + beberapa pengguna, semuanya di satu mesin.

Menyalakan server di latar belakang, menyambungkan 3 pengguna tiruan,
lalu memeriksa pesan dan perintah. Semua proses dimatikan di akhir.

    python3 uji-cepat.py
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
PORT = 5099
WEB = 8199
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
    """Pengguna tiruan untuk pengujian."""

    def __init__(self, nama: str) -> None:
        self.nama = nama
        self.sock = socket.create_connection(("127.0.0.1", PORT), timeout=5)
        self.masuk: list[dict] = []
        self.perintah: list[dict] = []
        self.jalan = True
        self.kirim({"tipe": "daftar", "nama": nama, "sistem": "uji"})
        threading.Thread(target=self._dengar, daemon=True).start()

    def kirim(self, d: dict) -> None:
        try:
            self.sock.sendall((json.dumps(d) + "\n").encode())
        except OSError:
            self.jalan = False

    def _dengar(self) -> None:
        buf = b""
        try:
            while self.jalan:
                p = self.sock.recv(8192)
                if not p:
                    break
                buf += p
                while b"\n" in buf:
                    baris, buf = buf.split(b"\n", 1)
                    if not baris.strip():
                        continue
                    d = json.loads(baris.decode())
                    if d.get("tipe") == "pesan":
                        self.masuk.append(d)
                    elif d.get("tipe") == "perintah":
                        self.perintah.append(d)
                        self.kirim({"tipe": "hasil", "aksi": d.get("aksi"),
                                    "berhasil": True,
                                    "pesan": f"[tiruan] {d.get('aksi')}",
                                    "id_perintah": d.get("id")})
        except OSError:
            pass

    def tutup(self) -> None:
        self.jalan = False
        try:
            self.sock.close()
        except OSError:
            pass


def keadaan() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{WEB}/api/keadaan", timeout=5) as r:
        return json.loads(r.read())


def main() -> int:
    print("=" * 62)
    print("  UJI CEPAT — server + 3 pengguna")
    print("=" * 62)

    db = AKAR / "data" / "uji.db"
    db.unlink(missing_ok=True)

    print(f"\n1. Menyalakan server (socket {PORT}, web {WEB})")
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
        print("\n2. Menyambungkan 3 pengguna")
        a = Tiruan("PC-ALPHA")
        time.sleep(0.3)
        b = Tiruan("PC-BETA")
        time.sleep(0.3)
        c = Tiruan("PC-GAMMA")
        time.sleep(1.2)

        k = keadaan()
        periksa("server melihat 3 laptop",
                len(k["online"]) == 3, f"lihat {len(k['online'])}")
        periksa("nama terbaca benar",
                sorted(x["nama"] for x in k["online"]) == ["PC-ALPHA", "PC-BETA", "PC-GAMMA"],
                str([x["nama"] for x in k["online"]]))

        print("\n3. Siaran dari PC-ALPHA")
        a.kirim({"tipe": "pesan", "ke": "semua", "isi": "HALO-SEMUA"})
        time.sleep(1.2)
        terima = sum(1 for x in (b, c) if any(m["isi"] == "HALO-SEMUA" for m in x.masuk))
        periksa("kedua pengguna lain menerima", terima == 2, f"diterima {terima}")
        periksa("pengirim tidak menerima gemanya", not a.masuk)

        print("\n4. Pesan pribadi dari PC-BETA ke PC-GAMMA")
        b.kirim({"tipe": "pesan", "ke": "PC-GAMMA", "isi": "PESAN-PRIBADI"})
        time.sleep(1.2)
        periksa("PC-GAMMA menerima",
                any(m["isi"] == "PESAN-PRIBADI" for m in c.masuk))
        periksa("PC-ALPHA TIDAK menerima (tidak bocor)",
                not any(m["isi"] == "PESAN-PRIBADI" for m in a.masuk))

        print("\n5. Pesan ke laptop yang tidak ada")
        a.kirim({"tipe": "pesan", "ke": "PC-TIDAK-ADA", "isi": "test"})
        time.sleep(1)

        print("\n6. Perintah lewat dashboard ke PC-BETA saja")
        with urllib.request.urlopen(
                f"http://127.0.0.1:{WEB}/api/perintah?sasaran=PC-BETA&aksi=kunci",
                timeout=5) as r:
            hasil = json.loads(r.read())
        periksa("perintah terkirim", hasil.get("ok") is True, str(hasil))
        time.sleep(1.2)
        periksa("PC-BETA menerima perintah", len(b.perintah) == 1,
                f"dapat {len(b.perintah)}")
        periksa("PC-ALPHA & PC-GAMMA tidak menerima perintah",
                not a.perintah and not c.perintah)

        k = keadaan()
        adaperintah = [p for p in k["perintah"] if p["sasaran"] == "PC-BETA"]
        periksa("perintah tercatat di basis data", len(adaperintah) == 1)
        if adaperintah:
            periksa("laporan hasil tercatat",
                    adaperintah[0]["hasil"] is not None,
                    f"hasil={adaperintah[0]['hasil']}")
            periksa("ditandai berhasil", bool(adaperintah[0]["berhasil"]))

        print("\n7. Nama yang sudah dipakai")
        kembar = Tiruan("PC-ALPHA")
        time.sleep(1)
        k = keadaan()
        periksa("nama kembar ditolak (tetap 3 laptop)", len(k["online"]) == 3,
                f"lihat {len(k['online'])}")
        kembar.tutup()

        print("\n8. Pengguna putus")
        c.tutup()
        time.sleep(1.5)
        k = keadaan()
        periksa("server melihat 2 laptop tersisa", len(k["online"]) == 2,
                f"lihat {len(k['online'])}")
        putus = [x for x in k["kejadian"] if x["jenis"] == "putus"]
        periksa("kejadian putus tercatat", any(x["nama"] == "PC-GAMMA" for x in putus))

        print("\n9. Dashboard menjawab")
        for jalur in ("/", "/api/keadaan"):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{WEB}{jalur}",
                                            timeout=5) as r:
                    periksa(f"GET {jalur} → {r.status}", r.status == 200)
            except Exception as e:
                periksa(f"GET {jalur}", False, str(e))

        a.tutup()
        b.tutup()

    finally:
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
