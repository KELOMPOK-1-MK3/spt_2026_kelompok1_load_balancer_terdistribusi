#!/usr/bin/env bash
# Jalankan seluruh skenario uji 1030 secara berurutan dari satu perintah.
#
#   bash src/tests/jalankan-semua.sh
#
# Urutan: enam skenario kegagalan, lalu pengukuran waktu peralihan.
# Sistem harus sudah jalan: docker compose up --build -d
set -u

cd "$(dirname "$0")/../.." || exit 1

echo "=== Memastikan sistem jalan ==="
if ! curl -sf -o /dev/null http://localhost:8080/; then
  echo "  sistem belum jalan — menjalankan docker compose up --build -d"
  docker compose up --build -d || exit 1
  for _ in $(seq 1 30); do
    curl -sf -o /dev/null http://localhost:8080/ && break
    sleep 2
  done
fi
curl -sf -o /dev/null http://localhost:8080/ && echo "  siap" || { echo "  GAGAL: layanan tidak menjawab"; exit 1; }

echo
echo "############ BAGIAN 1: enam skenario kegagalan ############"
bash src/tests/uji_kegagalan.sh

echo
echo "############ BAGIAN 2: waktu peralihan (4 percobaan) ############"
python3 src/tests/uji_waktu_peralihan.py --ulang 4 --durasi 30 \
  --laju 100 --thread 4 --t-mati 6 --t-nyala 16 --jeda-antar 4

echo
echo "############ SELESAI ############"
echo "Data mentah: docs/data-peralihan/"
echo "Hasil: docs/hasil-uji-kegagalan.md dan docs/waktu-peralihan.md"
