#!/usr/bin/env python3
"""Ukur waktu peralihan (failover) saat satu app server dimatikan.

Beda dari uji_kegagalan.sh yang hanya membuktikan "layanan tetap hidup",
skrip ini menekan load balancer terus-menerus sambil app1 dimatikan dan
dinyalakan lagi, lalu mengukur untuk setiap percobaan:

  - jumlah permintaan klien yang gagal (kode selain 200)
  - berapa lama setelah perintah stop app1 berhenti melayani
  - berapa lama setelah perintah start app1 kembali masuk perputaran
  - latensi terburuk yang dirasakan klien selama jendela peralihan

Cara pakai (dari akar repo, sistem harus sudah jalan):
    python3 src/tests/uji_waktu_peralihan.py
    python3 src/tests/uji_waktu_peralihan.py --ulang 3 --laju 120
    python3 src/tests/uji_waktu_peralihan.py --durasi 30 --ulang 1

CSV mentah tiap percobaan ditulis ke /tmp/uji-peralihan-<percobaan>.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import requests

NAMA_APP1 = "mkkl1030-loadbalancer-redis-app1-1"


class Perekam:
    """Menekan URL terus-menerus dari beberapa thread, mencatat tiap respons."""

    def __init__(self, url: str, laju: int, jumlah_thread: int) -> None:
        self.url = url
        # jeda per thread: laju total dibagi rata ke seluruh thread
        self.jeda = jumlah_thread / max(laju, 1)
        self.baris: list[tuple[float, int, float, str]] = []
        self._kunci = threading.Lock()
        self._jalan = threading.Event()

    def _pekerja(self) -> None:
        sesi = requests.Session()
        while self._jalan.is_set():
            t0 = time.time()
            try:
                r = sesi.get(self.url, timeout=10)
                kode = r.status_code
                try:
                    server = r.json().get("server", "?")
                except ValueError:
                    server = "?"
            except requests.RequestException:
                kode, server = 0, "?"  # 0 = tidak ada jawaban sama sekali
            dt = (time.time() - t0) * 1000
            with self._kunci:
                self.baris.append((t0, kode, dt, server))
            sisa = self.jeda - (time.time() - t0)
            if sisa > 0:
                time.sleep(sisa)

    def mulai(self, jumlah_thread: int) -> None:
        self._jalan.set()
        self._thread = [threading.Thread(target=self._pekerja, daemon=True)
                        for _ in range(jumlah_thread)]
        for t in self._thread:
            t.start()

    def henti(self) -> None:
        self._jalan.clear()
        for t in self._thread:
            t.join(timeout=15)


def jalankan(*args: str) -> None:
    subprocess.run(args, capture_output=True, text=True, check=False)


def tunggu_sehat(nama: str, batas: float = 60.0) -> float | None:
    """Tunggu container berstatus healthy; kembalikan waktu saat sehat."""
    selesai = time.time() + batas
    while time.time() < selesai:
        status = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", nama],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if status == "healthy":
            return time.time()
        time.sleep(0.25)
    return None


def satu_percobaan(percobaan: int, url: str, args) -> dict:
    print(f"\n{'=' * 68}\nPERCOBAAN {percobaan}\n{'=' * 68}")
    print(f"Menekan {url} terus-menerus (target ~{args.laju} permintaan/detik, "
          f"{args.thread} thread), {args.durasi:.0f} detik per putaran.")
    print("  Laju nyata yang tercapai dicetak di bawah — klien Python satu proses,")
    print("  jadi laju biasanya di bawah target.")
    print(f"  app1 dimatikan pada detik ke-{args.t_mati:.0f}, "
          f"dinyalakan lagi pada detik ke-{args.t_nyala:.0f}")

    rekam = Perekam(url, args.laju, args.thread)
    t_mulai = time.time()
    rekam.mulai(args.thread)

    def tidur_sampai(detik: float) -> None:
        sisa = (t_mulai + detik) - time.time()
        if sisa > 0:
            time.sleep(sisa)

    tidur_sampai(args.t_mati)
    t_stop = time.time()
    print(f"[{t_stop - t_mulai:6.2f}s] docker compose stop app1")
    jalankan("docker", "compose", "stop", "app1")

    tidur_sampai(args.t_nyala)
    t_start = time.time()
    print(f"[{t_start - t_mulai:6.2f}s] docker compose start app1")
    jalankan("docker", "compose", "start", "app1")
    t_sehat = tunggu_sehat(NAMA_APP1)
    if t_sehat:
        print(f"[{t_sehat - t_mulai:6.2f}s] app1 sehat "
              f"({t_sehat - t_start:.2f}s setelah perintah start)")

    tidur_sampai(args.durasi)
    rekam.henti()
    t_akhir = time.time()

    baris = sorted(rekam.baris)
    folder = Path(args.keluaran)
    folder.mkdir(parents=True, exist_ok=True)
    keluaran = folder / f"peralihan-p{percobaan}-{int(t_mulai)}.csv"
    with keluaran.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["detik", "kode_http", "laten_ms", "server"])
        for t, kode, dt, server in baris:
            w.writerow([f"{t - t_mulai:.3f}", kode, f"{dt:.1f}", server])

    # ---- Ringkasan ------------------------------------------------------
    kode = Counter(b[1] for b in baris)
    gagal = [b for b in baris if b[1] != 200]
    app1 = [b for b in baris if b[3] == "app1"]

    # app1 masih melayani sesudah perintah stop, dan kembali lagi sesudah start.
    app1_stop = [b[0] for b in app1 if b[0] < t_start]
    batas_kembali = (t_sehat - 5) if t_sehat else t_start
    app1_kembali = [b[0] for b in app1 if b[0] > max(t_start, batas_kembali)]

    akhir_layanan = max(app1_stop) if app1_stop else None
    awal_kembali = min(app1_kembali) if app1_kembali else None

    rata_laju = len(baris) / (t_akhir - t_mulai)

    print(f"\n  total permintaan   : {len(baris)} "
          f"(~{rata_laju:.0f}/detik)")
    print(f"  sebaran kode HTTP  : {dict(kode)}")
    print(f"  permintaan GAGAL   : {len(gagal)}"
          + (" — klien tidak pernah kehilangan layanan"
             if not gagal else ""))
    if akhir_layanan:
        print(f"  app1 berhenti melayani : {akhir_layanan - t_stop:+.2f}s "
              f"setelah perintah stop")
    if awal_kembali:
        print(f"  app1 kembali melayani  : {awal_kembali - t_start:+.2f}s "
              f"setelah perintah start")
    else:
        print("  app1 BELUM kembali melayani sampai pengukuran berakhir")

    # Latensi: bandingkan masa tenang dengan masa peralihan.
    tenang = [b[2] for b in baris
              if b[0] < t_stop or (t_sehat and b[0] > t_sehat)]
    jendela = [b for b in baris if t_stop <= b[0] <= t_start]
    if tenang:
        print(f"  latensi masa tenang    : rata-rata "
              f"{statistics.mean(tenang):.1f} ms, "
              f"terburuk {max(tenang):.1f} ms")
    if jendela:
        terburuk = max(jendela, key=lambda b: b[2])
        print(f"  latensi saat peralihan : rata-rata "
              f"{statistics.mean([b[2] for b in jendela]):.1f} ms, "
              f"terburuk {terburuk[2]:.1f} ms "
              f"(detik {terburuk[0] - t_mulai:.2f}, "
              f"dilayani {terburuk[3]})")

    return {
        "percobaan": percobaan,
        "total": len(baris),
        "gagal": len(gagal),
        "kode": dict(kode),
        "app1_berhenti_s": (akhir_layanan - t_stop) if akhir_layanan else None,
        "app1_kembali_s": (awal_kembali - t_start) if awal_kembali else None,
        "sehat_s": (t_sehat - t_start) if t_sehat else None,
        "laten_tenang_ms": statistics.mean(tenang) if tenang else None,
        "laten_peralihan_ms": max(b[2] for b in jendela) if jendela else None,
        "csv": str(keluaran),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--durasi", type=float, default=35.0,
                   help="durasi tiap percobaan (detik)")
    p.add_argument("--laju", type=int, default=120,
                   help="perkiraan permintaan per detik")
    p.add_argument("--thread", type=int, default=6, help="jumlah thread")
    p.add_argument("--t-mati", type=float, default=8.0,
                   help="detik ke berapa app1 dimatikan")
    p.add_argument("--t-nyala", type=float, default=20.0,
                   help="detik ke berapa app1 dinyalakan lagi")
    p.add_argument("--ulang", type=int, default=1, help="jumlah percobaan")
    p.add_argument("--jeda-antar", type=float, default=5.0,
                   help="jeda antar percobaan (detik)")
    p.add_argument("--keluaran", default="docs/data-peralihan",
                   help="folder penyimpanan CSV mentah (relatif akar repo)")
    args = p.parse_args()

    try:
        requests.get("http://localhost:8080/", timeout=5)
    except requests.RequestException as exc:
        print(f"Gagal menghubungi http://localhost:8080/ — {exc}")
        print("Jalankan dulu: docker compose up --build -d")
        return 1

    hasil = []
    for i in range(1, args.ulang + 1):
        hasil.append(satu_percobaan(i, "http://localhost:8080/", args))
        if i < args.ulang:
            time.sleep(args.jeda_antar)

    print(f"\n{'=' * 68}\nRINGKASAN {args.ulang} PERCOBAAN\n{'=' * 68}")
    print(f"{'#':>3} {'permintaan':>11} {'gagal':>6} "
          f"{'berhenti':>10} {'kembali':>10} {'laten puncak':>13}")
    for h in hasil:
        print(f"{h['percobaan']:>3} {h['total']:>11} {h['gagal']:>6} "
              f"{h['app1_berhenti_s']:>+9.2f}s {h['app1_kembali_s']:>+9.2f}s "
              f"{h['laten_peralihan_ms']:>10.0f} ms")

    total_gagal = sum(h["gagal"] for h in hasil)
    kembali = [h["app1_kembali_s"] for h in hasil if h["app1_kembali_s"]]
    puncak = [h["laten_peralihan_ms"] for h in hasil if h["laten_peralihan_ms"]]
    print(f"\n  total permintaan gagal di {args.ulang} percobaan: {total_gagal}")
    if kembali:
        print(f"  app1 kembali melayani: "
              + ", ".join(f"{x:.2f}s" for x in kembali)
              + (f" — rata-rata {statistics.mean(kembali):.2f}s"
                 if len(kembali) > 1 else ""))
    if puncak:
        print(f"  latensi puncak peralihan: "
              + ", ".join(f"{x:.0f} ms" for x in puncak))
    return 0


if __name__ == "__main__":
    sys.exit(main())
