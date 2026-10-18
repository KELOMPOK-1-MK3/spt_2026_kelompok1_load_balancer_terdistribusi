#!/usr/bin/env bash
# Uji: dari mana nama laptop diambil, dan mana yang menang.
#
#   bash uji-nama.sh
set -u
cd "$(dirname "$0")"

PORT=5099
WEB=8199
KLIEN="../user/client.py"

pkill -f "server.py --port $PORT" 2>/dev/null
pkill -f "client.py --server 127.0.0.1 --port $PORT" 2>/dev/null
sleep 1
rm -f "data/uji-nama.db"

python3 server.py --port $PORT --web $WEB --db data/uji-nama.db > /tmp/srv-nama.txt 2>&1 &
SRV=$!
sleep 3

echo "=== 1. TANPA --nama → harus baca nama.txt ==="
python3 "$KLIEN" --server 127.0.0.1 --port $PORT --tunggu > /tmp/klien-nama.txt 2>&1 &
K1=$!
sleep 3
sed -n '4,10p' /tmp/klien-nama.txt

echo
echo "=== 2. DENGAN --nama PC-SAYA → argumen menang, dan diberi tahu ==="
python3 "$KLIEN" --server 127.0.0.1 --port $PORT --tunggu --nama PC-SAYA > /tmp/klien-lama.txt 2>&1 &
K2=$!
sleep 3
sed -n '4,12p' /tmp/klien-lama.txt

echo
echo "=== 3. nama berspasi + tanda kurung ==="
python3 "$KLIEN" --server 127.0.0.1 --port $PORT --tunggu --nama "PC04 (Deski)" > /tmp/klien-deski.txt 2>&1 &
K3=$!
sleep 3
grep "Laptop   :" /tmp/klien-deski.txt

echo
echo "=== 4. dashboard melihat: ==="
curl -s "http://127.0.0.1:$WEB/api/keadaan" \
  | python3 -c 'import sys,json; print("  online:", [x["nama"] for x in json.load(sys.stdin)["online"]])'

echo
echo "=== 5. pesan pribadi ke nama berspasi ==="
curl -s "http://127.0.0.1:$WEB/api/pesan?tujuan=PC04%20%28Deski%29&isi=tes+nama+berspasi" >/dev/null
sleep 1.5
echo "  --- diterima PC04 (Deski) ---"
tail -5 /tmp/klien-deski.txt

echo
echo "=== 6. catatan di server ==="
grep -E "\[masuk\]|\[pesan\]" /tmp/srv-nama.txt

kill $K1 $K2 $K3 $SRV 2>/dev/null
sleep 1
pkill -f "server.py --port $PORT" 2>/dev/null
rm -f "data/uji-nama.db"
echo
echo "SELESAI"
