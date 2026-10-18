#!/usr/bin/env python3
"""PENGGUNA — MK Sistem Paralel

Program ini jalan di laptop tiap anggota. Tugasnya:

  1. Menyambung KE server (koneksi keluar, jadi tidak diblokir firewall).
  2. Menerima dan menampilkan pesan yang masuk.
  3. Mengirim pesan ke semua orang atau ke satu orang saja.
  4. Menjalankan perintah yang dikirim server (kunci, restart, matikan).

Jalankan:
    python3 client.py --server 192.168.1.7

Nama laptop diambil dari berkas `nama.txt` di folder ini. Kalau berkas itu
belum ada, program akan menanyakannya sekali dan menyimpannya, supaya tidak
perlu diketik ulang tiap kali.

Hanya mendengarkan, tidak perlu mengetik apa pun (bagus untuk demo):
    python3 client.py --server 192.168.1.7 --tunggu

Ganti nama untuk sekali jalan saja (tanpa mengubah nama.txt):
    python3 client.py --server 192.168.1.7 --nama "PC04 (Deski)"

PERINTAHAN DAYA (matikan / restart / kunci):
  macOS   : DITOLAK secara bawaan, supaya Mac yang dipakai jadi server atau
            untuk presentasi tidak pernah ikut mati/kunci. Kalau memang mau,
            tambahkan --izinkan-daya.
  Windows : jalankan terminal sebagai ADMIN (Run as Administrator).
"""
from __future__ import annotations

import sys


def _amankan_layar() -> None:
    """Cegah program berhenti mendadak di Windows saat menampilkan simbol.

    Kenapa ini ada:
        Terminal Windows (cmd.exe) memakai pengodean lama (cp1252/cp437) yang
        TIDAK mengenal karakter seperti ⚡ ✓ ✗ 💬 → dan garis kotak ┌ │ └ ─.
        Tanpa pengaman ini, print("  ⚡ PERINTAH...") langsung berhenti dengan
        UnicodeEncodeError — dan itu justru terjadi di laptop anggota, bukan
        di Mac tempat programnya dibuat.

        Kalau karakter tidak bisa ditampilkan, ia diganti tanda tanya. Program
        tetap jalan; yang hilang cuma hiasannya.
    """
    for aliran in (sys.stdout, sys.stderr):
        try:
            aliran.reconfigure(errors="replace")
        except Exception:
            pass          # Python lama atau aliran tidak bisa diubah — tidak fatal


_amankan_layar()

import argparse
import json
import pathlib
import platform
import queue
import socket
import subprocess
import sys
import threading
import time

# Perintah yang mengubah keadaan daya laptop.
PERINTAH_DAYA = {"matikan", "restart", "kunci"}

IZINKAN_DAYA_DI_MAC = False     # diisi dari --izinkan-daya

# Berkas tempat nama laptop ini disimpan. Namanya sengaja TIDAK di-hardcode di
# dalam program, supaya berkas yang sama bisa dipakai di laptop anggota mana
# pun — setiap orang tinggal mengubah isi nama.txt di laptopnya sendiri.
BERKAS_NAMA = pathlib.Path(__file__).resolve().parent / "nama.txt"


def baca_nama(dari_argumen: str | None) -> tuple[str, str]:
    """Tentukan nama laptop ini.

    Mengembalikan (nama, sumber) — sumber dipakai untuk ditampilkan di layar,
    supaya jelas nama itu datang dari mana kalau ternyata bukan yang diharapkan.

    Urutan: dari argumen --nama, lalu dari nama.txt, lalu tanya sekali.
    """
    if dari_argumen:
        return dari_argumen.strip()[:40], "argumen --nama"

    if BERKAS_NAMA.exists():
        isi = BERKAS_NAMA.read_text(encoding="utf-8").strip()
        if isi:
            return isi[:40], BERKAS_NAMA.name

    # Belum ada nama.txt — tanyakan sekali, lalu simpan.
    bawaan = platform.node() or "laptop-tanpa-nama"
    print()
    print("  Laptop ini belum punya nama.")
    print(f"  Kalau dibiarkan kosong, namanya jadi: {bawaan}")
    print()
    print("  Contoh penulisan yang rapi:")
    print("      PC01 (Yogi)")
    print("      PC04 (Deski)")
    print()
    print("  Nama ini akan disimpan di nama.txt, jadi tidak perlu diisi lagi.")
    print()
    try:
        jawab = input("  Nama laptop ini: ").strip()
    except (EOFError, KeyboardInterrupt):
        jawab = ""

    nama = (jawab or bawaan)[:40]
    try:
        BERKAS_NAMA.write_text(nama + "\n", encoding="utf-8")
        return nama, f"{BERKAS_NAMA.name} (baru disimpan)"
    except OSError as e:
        print(f"  [!] Tidak bisa menyimpan nama: {e}")
        return nama, "nama mesin"


# --------------------------------------------------------- menjalankan perintah
def jalankan(aksi: str, keterangan: str = "") -> tuple[bool, str]:
    """Jalankan perintah di laptop ini.

    Mengembalikan (berhasil, pesan) — pesan inilah yang dikirim balik ke
    server untuk ditampilkan di dashboard.
    """
    sistem = platform.system()

    # --- pengaman macOS -------------------------------------------------
    if sistem == "Darwin" and aksi in PERINTAH_DAYA and not IZINKAN_DAYA_DI_MAC:
        return False, (f"ditolak di macOS (mode aman). Mac ini dipakai sebagai "
                       f"server/untuk presentasi.")

    if aksi not in {"pesan", "kunci", "restart", "matikan", "batal"}:
        return False, f"perintah '{aksi}' tidak dikenal"

    if aksi == "pesan":
        print()
        print("  ┌" + "─" * 60)
        for baris in (keterangan or "(kosong)").split("\n"):
            print(f"  │ {baris}")
        print("  └" + "─" * 60)
        print("  > ", end="", flush=True)
        return True, "pesan ditampilkan"

    if aksi == "matikan":
        if sistem == "Windows":
            subprocess.Popen("shutdown /s /t 30", shell=True)
            return True, "laptop akan mati dalam 30 detik (bisa dibatalkan)"
        if sistem == "Darwin":
            subprocess.Popen(["osascript", "-e",
                              'tell app "System Events" to shut down'])
            return True, "laptop akan mati"
        subprocess.Popen("shutdown -h +1", shell=True)
        return True, "laptop akan mati dalam 1 menit"

    if aksi == "restart":
        if sistem == "Windows":
            subprocess.Popen("shutdown /r /t 30", shell=True)
            return True, "laptop akan restart dalam 30 detik"
        if sistem == "Darwin":
            subprocess.Popen(["osascript", "-e",
                              'tell app "System Events" to restart'])
            return True, "laptop akan restart"
        subprocess.Popen("shutdown -r +1", shell=True)
        return True, "laptop akan restart dalam 1 menit"

    if aksi == "batal":
        if sistem == "Windows":
            hasil = subprocess.run("shutdown /a", shell=True,
                                   capture_output=True, text=True)
            if hasil.returncode == 0:
                return True, "perintah mati/restart dibatalkan"
            return False, "tidak ada perintah mati/restart yang sedang menunggu"
        return False, f"pembatalan otomatis belum didukung di {sistem}"

    if aksi == "kunci":
        if sistem == "Windows":
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return True, "layar dikunci"
        if sistem == "Darwin":
            subprocess.Popen([
                "osascript", "-e",
                'tell application "System Events" '
                'to keystroke "q" using {control down, command down}'])
            return True, "layar dikunci"
        return False, f"perintah kunci belum didukung di {sistem}"

    return False, "perintah tidak dikenal"


# ------------------------------------------------------------------- pengguna
class Pengguna:
    def __init__(self, host: str, port: int, nama: str) -> None:
        self.host = host
        self.port = port
        self.nama = nama
        self.sistem = f"{platform.system()} {platform.release()}"
        self.sock: socket.socket | None = None
        self.jalan = True
        self.online: list[str] = []
        self.tampil = queue.Queue()      # baris yang perlu ditampilkan
        self._kunci = threading.Lock()

    # --- sambungan -------------------------------------------------------
    def sambung(self) -> bool:
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=8)
        except OSError as e:
            print()
            print(f"  ✗ Gagal menyambung ke {self.host}:{self.port}")
            print(f"    Sebab: {e}")
            print()
            print("    Periksa tiga hal ini:")
            print("      1. Server sudah dijalankan di laptop ketua?")
            print("      2. Alamat IP-nya sudah benar? (lihat yang dicetak server)")
            print("      3. Kedua laptop ada di jaringan WiFi yang sama?")
            return False

        # PENTING: batas waktu 8 detik di atas hanya untuk proses menyambung.
        # Kalau dibiarkan, socket akan terus menganggap "diam 8 detik" sebagai
        # kesalahan, dan aplikasi chat MEMANG sering diam lama. Akibatnya
        # program memutus dirinya sendiri padahal tidak ada masalah — jadi
        # batas waktunya dihapus setelah sambungan berhasil.
        self.sock.settimeout(None)

        self.kirim({"tipe": "daftar", "nama": self.nama, "sistem": self.sistem})
        return True

    def kirim(self, data: dict) -> bool:
        if not self.sock:
            return False
        baris = json.dumps(data, ensure_ascii=False) + "\n"
        with self._kunci:
            try:
                self.sock.sendall(baris.encode("utf-8"))
                return True
            except OSError:
                self.jalan = False
                return False

    # --- menerima --------------------------------------------------------
    def dengarkan(self) -> None:
        """Thread terpisah: terus membaca apa pun yang dikirim server."""
        penyangga = b""
        while self.jalan:
            try:
                potongan = self.sock.recv(8192)
            except socket.timeout:
                # Bukan kesalahan — cuma belum ada data. Lanjut menunggu.
                continue
            except OSError as e:
                self.tampil.put("")
                self.tampil.put(f"  [!] Sambungan terputus ({e}).")
                self.tampil.put("")
                self.jalan = False
                return

            if not potongan:
                self.tampil.put("")
                self.tampil.put("  [!] Server menutup sambungan.")
                self.tampil.put("")
                self.jalan = False
                return

            penyangga += potongan
            while b"\n" in penyangga:
                baris, penyangga = penyangga.split(b"\n", 1)
                if not baris.strip():
                    continue
                try:
                    self.tangani(json.loads(baris.decode("utf-8")))
                except (ValueError, UnicodeDecodeError):
                    pass

    def tangani(self, data: dict) -> None:
        tipe = data.get("tipe")

        if tipe == "selamat":
            self.online = data.get("online", [])
            self.tampil.put(f"  ✓ Tersambung. Nama kamu di server: "
                            f"{data.get('nama_kamu')}")
            self.tampil.put(f"    Laptop lain yang aktif: "
                            f"{', '.join(x for x in self.online if x != self.nama) or '(belum ada)'}")
            self.tampil.put("")

        elif tipe == "online":
            self.online = [x["nama"] for x in data.get("daftar", [])]

        elif tipe == "pesan":
            tujuan = data.get("ke", "semua")
            tanda = "siaran" if tujuan == "semua" else "pribadi"
            self.tampil.put("")
            self.tampil.put(f"  💬 [{data.get('waktu', '')[11:]}] "
                            f"{data.get('dari')} ({tanda}):")
            for b in (data.get("isi") or "").split("\n"):
                self.tampil.put(f"       {b}")
            self.tampil.put("")

        elif tipe == "info":
            self.tampil.put(f"  · {data.get('pesan')}")

        elif tipe == "galat":
            self.tampil.put(f"  ✗ {data.get('pesan')}")

        elif tipe == "ping":
            self.kirim({"tipe": "pong"})

        elif tipe == "perintah":
            aksi = data.get("aksi", "")
            self.tampil.put("")
            self.tampil.put(f"  ⚡ PERINTAH DARI SERVER: {aksi}")
            berhasil, pesan = jalankan(aksi, data.get("keterangan", ""))
            tanda = "✓" if berhasil else "✗"
            self.tampil.put(f"     {tanda} {pesan}")
            self.kirim({"tipe": "hasil", "aksi": aksi, "berhasil": berhasil,
                        "pesan": pesan, "id_perintah": data.get("id")})

    # --- mengirim --------------------------------------------------------
    def menu(self) -> None:
        print("  Cara memakai:")
        print("     halo semua              → kirim ke semua orang")
        print("     /ke PC-DESKI halo       → kirim ke satu orang saja")
        print("     /online                 → lihat siapa saja yang aktif")
        print("     /keluar                 → keluar")
        print()

    def tunggu_masukan(self) -> None:
        while self.jalan:
            try:
                baris = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not baris:
                continue
            if baris in ("/keluar", "/exit", "/quit"):
                break

            if baris == "/online":
                orang = [x for x in self.online if x != self.nama]
                if not orang:
                    print("  (belum ada laptop lain yang tersambung)")
                for x in orang:
                    print(f"    • {x}")
                continue

            if baris.startswith("/ke "):
                sisa = baris[4:].strip()
                tujuan, _, isi = sisa.partition(" ")
                if not isi:
                    print("  ✗ formatnya: /ke NAMA pesan")
                    continue
                self.kirim({"tipe": "pesan", "ke": tujuan, "isi": isi})
                continue

            self.kirim({"tipe": "pesan", "ke": "semua", "isi": baris})

        self.jalan = False


# ------------------------------------------------------ penampil (1 thread saja)
def penampil(p: Pengguna) -> None:
    """Cetak antrean tampilan. Satu thread supaya tulisan tidak saling menimpa."""
    while p.jalan or not p.tampil.empty():
        try:
            baris = p.tampil.get(timeout=0.3)
        except queue.Empty:
            continue
        print(baris, flush=True)


# ---------------------------------------------------------------------- utama
def utama() -> int:
    q = argparse.ArgumentParser(description="Pengguna chat — MK Sistem Paralel")
    q.add_argument("--server", required=True, help="IP laptop server, mis. 192.168.1.7")
    q.add_argument("--port", type=int, default=5000, help="port server (bawaan 5000)")
    q.add_argument("--nama", help="nama laptop ini, sekali jalan saja "
                                  "(bawaan: isi nama.txt)")
    q.add_argument("--tunggu", action="store_true",
                   help="hanya menerima, tidak perlu mengetik apa pun")
    q.add_argument("--izinkan-daya", action="store_true",
                   help="izinkan perintah matikan/restart/kunci di macOS "
                        "(bawaan: DITOLAK)")
    a = q.parse_args()

    global IZINKAN_DAYA_DI_MAC
    IZINKAN_DAYA_DI_MAC = a.izinkan_daya

    nama, sumber = baca_nama(a.nama)
    p = Pengguna(a.server, a.port, nama)

    print("=" * 64)
    print("  MK SISTEM PARALEL DAN TERDISTRIBUSI — PENGGUNA")
    print("=" * 64)
    print(f"  Laptop   : {nama}")
    print(f"  Nama dari: {sumber}")
    if sumber == "argumen --nama":
        # Berkas nama boleh saja belum ada — anggota baru sering langsung
        # memakai --nama sebelum sempat mengisi nama.txt. Dulu baris ini
        # membaca berkasnya tanpa memeriksa, dan programnya berhenti dengan
        # FileNotFoundError hanya karena berkas itu tidak ada.
        if BERKAS_NAMA.exists():
            isi = BERKAS_NAMA.read_text(encoding="utf-8").strip()
            print(f"             (nama.txt berisi '{isi}' — argumen menang."
                  f" Jalankan tanpa --nama untuk memakai isi nama.txt.)")
        else:
            print("             (nama.txt belum ada — pakai --nama atau "
                  "jalankan tanpa --nama untuk mengisinya.)")
    print(f"  Sistem   : {p.sistem}")
    print(f"  Server   : {a.server}:{a.port}")
    print("=" * 64, flush=True)

    if not p.sambung():
        return 1

    threading.Thread(target=p.dengarkan, daemon=True).start()
    threading.Thread(target=penampil, args=(p,), daemon=True).start()
    time.sleep(0.8)      # beri waktu pesan sambutan datang

    if a.tunggu:
        print(f"  Kamu tersambung sebagai: {nama}")
        print("  Mode tunggu — pesan masuk akan tampil di sini.")
        print("  Tekan Ctrl+C kalau sudah selesai.")
        print()
        try:
            while p.jalan:
                time.sleep(0.4)
        except KeyboardInterrupt:
            pass
    else:
        print()
        p.menu()
        p.tunggu_masukan()

    print("\n  Keluar.")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
