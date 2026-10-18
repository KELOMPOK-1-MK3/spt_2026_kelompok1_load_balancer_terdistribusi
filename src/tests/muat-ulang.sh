#!/usr/bin/env bash
# Memuat ulang konfigurasi (app1, app2, nginx) lalu MEMVERIFIKASI bahwa yang
# benar-benar dipakai container sama dengan yang ada di repository.
#
#   bash src/tests/muat-ulang.sh
#
# Kenapa perlu --force-recreate dan bukan `up -d` biasa:
# di macOS, bind-mount dapat berhenti memantulkan berkas host — berkas di dalam
# container jadi hilang/kosong tanpa peringatan, padahal Nginx tetap jalan
# dengan konfigurasi lama. Kejadian nyata: `git checkout`/`git pull` mengganti
# berkas di host, lalu `/klien/` balas 403 karena folder di container kosong.
set -u
# Naik ke akar repository (src/tests -> akar) supaya path volume benar.
cd "$(dirname "$0")/../.." || exit 1

GAGAL=0

echo "=== terapkan ulang konfigurasi ==="
docker compose up -d --force-recreate app1 app2 nginx

echo
echo "=== tunggu semua container sehat ==="
for c in app1 app2 redis; do
  for _ in $(seq 1 25); do
    s=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' \
        "mkkl1030-loadbalancer-redis-${c}-1" 2>/dev/null)
    [ "$s" = "healthy" ] && { echo "  $c: healthy"; break; }
    sleep 2
  done
done

echo
echo "=== uji nginx.conf di dalam container nginx yang berjalan ==="
docker compose exec -T nginx nginx -t 2>&1 || GAGAL=1

echo
echo "=== VERIFIKASI: nginx.conf di container identik dengan repo? ==="
docker compose exec -T nginx cat /etc/nginx/nginx.conf > /tmp/nginx-live.conf 2>/dev/null
if [ ! -s /tmp/nginx-live.conf ]; then
  echo "  ✗ GAGAL: /etc/nginx/nginx.conf di dalam container kosong/tidak ada."
  echo "    Nginx mungkin masih jalan dengan konfigurasi lama dari memori."
  GAGAL=1
elif diff -q /tmp/nginx-live.conf nginx/nginx.conf >/dev/null; then
  echo "  ✓ identik dengan nginx/nginx.conf di repository"
else
  echo "  ✗ GAGAL: isi di container BERBEDA dari repository:"
  diff /tmp/nginx-live.conf nginx/nginx.conf | head -20
  GAGAL=1
fi

echo
echo "=== VERIFIKASI: aplikasi client benar-benar terpasang di container? ==="
if docker compose exec -T nginx test -f /usr/share/nginx/html/klien/index.html; then
  echo "  ✓ src/client/index.html terbaca dari dalam container"
else
  echo "  ✗ GAGAL: /usr/share/nginx/html/klien/index.html tidak ditemukan."
  echo "    Bind-mount ./src/client tidak terpasang — /klien/ akan balas 403."
  GAGAL=1
fi

echo
echo "=== VERIFIKASI: titik akhir menjawab? ==="
for u in "/" "/klien/" "/health"; do
  kode=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:8080${u}")
  if [ "$kode" = "200" ]; then
    echo "  ✓ ${u} -> 200"
  else
    echo "  ✗ GAGAL: ${u} -> ${kode}"
    GAGAL=1
  fi
done

echo
echo "=== status container ==="
docker compose ps

echo
if [ "$GAGAL" -eq 0 ]; then
  echo "SELESAI — semua pemeriksaan lulus."
else
  echo "SELESAI DENGAN MASALAH — ada pemeriksaan yang gagal di atas."
fi
exit "$GAGAL"
