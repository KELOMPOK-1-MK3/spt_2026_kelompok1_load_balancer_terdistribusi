"""Uji pengaman perintah daya — membuktikan Mac TIDAK ikut mati.

Kenapa ini ada:
    Server bisa mengirim perintah "matikan", "restart", dan "kunci" ke laptop
    anggota. Kalau pengamannya tidak bekerja, satu perintah yang salah kirim
    bisa mematikan komputer yang sedang dipakai presentasi — dan itu terjadi
    di depan dosen.

Uji ini menjalankan klien sungguhan di mesin ini, lalu memastikan ketiga
perintah daya DITOLAK secara bawaan. Kalau ada yang lolos, uji gagal.

Jalankan (server harus sudah hidup):
    python3 uji-pengaman.py
    python3 uji-pengaman.py --port 5099 --web 8199
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent

# Port uji. Sengaja beda dari port bawaan (5000/8081) supaya server yang
# sedang dipakai tidak terganggu.
PORT, WEB = 5099, 8199
lulus, gagal = 0, 0


def periksa(nama: str, benar: bool, tambahan: str = "") -> None:
    global lulus, gagal
    tanda = "✓" if benar else "✗"
    if benar:
        lulus += 1
    else:
        gagal += 1
    print(f"  {tanda} {nama}" + (f" — {tambahan}" if tambahan else ""))


class Peretas:
    """Klien palsu yang menyamar jadi klien biasa untuk mencuri perintah.

    Ia mendaftar seperti klien sungguhan, lalu merekam setiap perintah yang
    diterima dari server — tanpa menjalankannya. Ini cara menguji apakah
    server benar-benar mengirim perintah daya, tanpa risiko Mac ini mati.
    """

    def __init__(self, host: str, port: int, nama: str) -> None:
        self.nama = nama
        self.perintah: list[dict] = []
        self.soket = socket.create_connection((host, port), timeout=10)
        self.soket.settimeout(None)
        self.berkas = self.soket.makefile("rwb")
        self._kirim({"tipe": "daftar", "nama": nama, "sistem": "uji-pengaman"})
        self.hidup = True
        self.utas = threading.Thread(target=self._dengar, daemon=True)
        self.utas.start()

    def _kirim(self, isi: dict) -> None:
        self.berkas.write((json.dumps(isi) + "\n").encode())
        self.berkas.flush()

    def _dengar(self) -> None:
        try:
            while self.hidup:
                baris = self.berkas.readline()
                if not baris:
                    break
                try:
                    pesan = json.loads(baris.decode().strip())
                except Exception:
                    continue
                if pesan.get("tipe") == "perintah":
                    self.perintah.append(pesan)
                elif pesan.get("tipe") == "ping":
                    self._kirim({"tipe": "pong"})
        except Exception:
            pass

    def tutup(self) -> None:
        self.hidup = False
        try:
            self.soket.close()
        except Exception:
            pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--web", type=int, default=WEB)
    p.add_argument("--server-luar", action="store_true",
                   help="pakai server yang sudah berjalan, jangan nyalakan sendiri")
    a = p.parse_args()
    print("=" * 62)
    print("  UJI PENGAMAN PERINTAH DAYA")
    print("=" * 62)

    # Uji ini menyalakan servernya sendiri supaya bisa dijalankan dengan satu
    # perintah saja, tanpa perlu menyiapkan jendela server lebih dahulu.
    srv = None
    if not a.server_luar:
        print(f"\n0. Menyalakan server uji (socket {a.port}, web {a.web})")
        db = AKAR / "data" / "uji-pengaman.db"
        db.unlink(missing_ok=True)
        (AKAR / "data").mkdir(parents=True, exist_ok=True)
        srv = subprocess.Popen(
            [sys.executable, str(AKAR / "server.py"),
             "--port", str(a.port), "--web", str(a.web), "--db", str(db)],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        time.sleep(2.5)
        if srv.poll() is not None:
            print("  ✗ server gagal menyala")
            return 1
        print("  ✓ server menyala")

    # Daftar aksi daya yang harus ditolak, dan alasan penolakannya.
    AKSI_DAYA = ["kunci", "restart", "matikan"]

    print("\n1. Menyalakan klien sungguhan + klien penyadap")
    # Keluaran klien ditulis ke BERKAS, bukan dibaca dari pipa.
    # Membaca pipa di sini pernah bikin uji gagal palsu: isinya belum
    # ter-flush saat dibaca, jadi penolakan yang sebenarnya terjadi
    # tidak terlihat. Berkas tidak punya masalah itu.
    berkas_keluar = AKAR / "data" / "keluaran-uji-pengaman.txt"
    berkas_keluar.parent.mkdir(parents=True, exist_ok=True)
    berkas_keluar.write_text("")
    _f = open(berkas_keluar, "w")
    klien = subprocess.Popen(
        [sys.executable, str(AKAR.parent / "user" / "client.py"),
         "--server", "127.0.0.1", "--port", str(a.port),
         "--nama", "PC-UJI-DAYA", "--tunggu"],
        stdout=_f, stderr=subprocess.STDOUT, text=True)
    time.sleep(2.5)
    penyadap = Peretas("127.0.0.1", a.port, "PC-PENYADAP")
    time.sleep(1)
    periksa("klien sungguhan hidup", klien.poll() is None)
    periksa("klien penyadap tersambung", penyadap.hidup)

    try:
        print("\n2. Server menerima perintah daya (harus diterima, lalu ditolak klien)")
        for aksi in AKSI_DAYA:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{a.web}/api/perintah"
                    f"?sasaran=PC-UJI-DAYA&aksi={aksi}", timeout=5) as r:
                hasil = json.loads(r.read())
            periksa(f"perintah '{aksi}' diterima server", hasil.get("ok") is True,
                    str(hasil)[:70])
            time.sleep(0.4)

        # Tunggu sampai ketiga penolakan benar-benar tercatat (maks 10 dtk).
        _f.flush()
        for _ in range(20):
            keluaran = berkas_keluar.read_text(errors="replace")
            if keluaran.lower().count("ditolak") >= len(AKSI_DAYA):
                break
            time.sleep(0.5)

        print("\n3. Klien sungguhan menolak semuanya (Mac tetap hidup)")
        jumlah_tolak = keluaran.lower().count("ditolak")
        periksa(f"ketiga perintah daya ditolak ({jumlah_tolak}x)",
                jumlah_tolak >= len(AKSI_DAYA), f"catatan: {jumlah_tolak}x")
        for aksi in AKSI_DAYA:
            # Tiap perintah harus punya baris "PERINTAH DARI SERVER: <aksi>"
            # yang diikuti penolakan.
            ada = f"PERINTAH DARI SERVER: {aksi}" in keluaran
            periksa(f"'{aksi}' sampai ke klien dan ditolak", ada)

        print("\n4. Perintah daya TIDAK menyentuh klien lain")
        periksa("penyadap tidak menerima perintah daya untuk dirinya",
                len(penyadap.perintah) == 0,
                f"dapat {len(penyadap.perintah)}")

        print("\n5. Klien lain tetap melayani perintah biasa")
        penyadap.perintah.clear()
        with urllib.request.urlopen(
                f"http://127.0.0.1:{a.web}/api/perintah"
                f"?sasaran=PC-PENYADAP&aksi=pesan&keterangan=halo",
                timeout=5) as r:
            hasil = json.loads(r.read())
        time.sleep(1.2)
        periksa("perintah biasa tetap diteruskan", len(penyadap.perintah) == 1,
                f"dapat {len(penyadap.perintah)}")

        print("\n6. Mac ini masih hidup")
        periksa("proses klien masih berjalan", klien.poll() is None)
        periksa("Mac menjawab (tidak sedang dimatikan)",
                subprocess.run(["true"]).returncode == 0)
    finally:
        penyadap.tutup()
        klien.terminate()
        try:
            _f.close()
        except Exception:
            pass
        if srv is not None:
            srv.terminate()
            try:
                srv.wait(timeout=5)
            except Exception:
                srv.kill()
        try:
            klien.wait(timeout=5)
        except Exception:
            klien.kill()

    print("\n" + "=" * 62)
    print(f"  HASIL: {lulus} lulus, {gagal} gagal")
    print("=" * 62)
    return 0 if gagal == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
