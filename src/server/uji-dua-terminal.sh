#!/usr/bin/env bash
# Uji dua terminal: server + 3 pengguna, seperti yang akan dilihat user.
#
#   bash uji-dua-terminal.sh
#
# Semua proses dimatikan di akhir.
set -u
cd "$(dirname "$0")"

PORT=5099
WEB=8199
DB="data/uji-terminal.db"
KLIEN="../user/client.py"      # program pengguna ada di folder sebelah

pkill -f "server.py --port $PORT" 2>/dev/null
sleep 0.5
rm -f "$DB"

echo "############ TERMINAL 1 — SERVER ############"
python3 server.py --port $PORT --web $WEB --db "$DB" > /tmp/srv-tampar.txt 2>&1 &
SRV=$!
sleep 2.5
head -14 /tmp/srv-tampar.txt

echo
echo "############ MEMBUKA DASHBOARD ############"
curl -s -o /dev/null -w "  GET /            -> %{http_code}\n" "http://127.0.0.1:$WEB/"
curl -s -o /dev/null -w "  GET /api/keadaan -> %{http_code}\n" "http://127.0.0.1:$WEB/api/keadaan"

echo
echo "############ MEMBUKA 3 PENGGUNA ############"
python3 "$KLIEN" --server 127.0.0.1 --port $PORT --nama PC-PARIS --tunggu > /tmp/klien-1.txt 2>&1 &
C1=$!
sleep 0.4
python3 "$KLIEN" --server 127.0.0.1 --port $PORT --nama PC-DESKI --tunggu > /tmp/klien-2.txt 2>&1 &
C2=$!
sleep 0.4
python3 "$KLIEN" --server 127.0.0.1 --port $PORT --nama PC-WIRA --tunggu > /tmp/klien-3.txt 2>&1 &
C3=$!
sleep 3

echo "  --- yang dilihat PC-PARIS saat menyambung ---"
sed -n '7,12p' /tmp/klien-1.txt

echo
echo "  --- server melihat ---"
grep -E "\[masuk\]|\[pesan\]|\[perintah\]|\[hasil\]" /tmp/srv-tampar.txt

echo
echo "############ SERVER MENGIRIM PESAN SIARAN ############"
curl -s "http://127.0.0.1:$WEB/api/pesan?tujuan=semua&isi=Kumpul+jam+3+di+lab" >/dev/null
sleep 1.5
echo "  --- yang dilihat PC-DESKI ---"
tail -6 /tmp/klien-2.txt

echo
echo "############ SERVER MENGIRIM PESAN PRIBADI KE PC-WIRA ############"
curl -s "http://127.0.0.1:$WEB/api/pesan?tujuan=PC-WIRA&isi=Bagian+kamu+mana%3F" >/dev/null
sleep 1.5
echo "  --- yang dilihat PC-WIRA ---"
tail -6 /tmp/klien-3.txt
echo
echo "  --- PC-PARIS (harusnya TIDAK dapat pesan pribadi itu) ---"
tail -4 /tmp/klien-1.txt

echo
echo "############ UJI PENGAMAN: perintah 'kunci' ke Mac ############"
curl -s "http://127.0.0.1:$WEB/api/perintah?sasaran=PC-PARIS&aksi=kunci" >/dev/null
sleep 1.5
echo "  --- yang dilihat PC-PARIS ---"
tail -5 /tmp/klien-1.txt
echo
echo "  --- catatan di server ---"
grep "\[hasil\]" /tmp/srv-tampar.txt | tail -3

echo
echo "############ KEADAAN AKHIR ############"
curl -s "http://127.0.0.1:$WEB/api/keadaan" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  laptop online :', [x['nama'] for x in d['online']])
print('  jumlah pesan  :', d['jumlah']['pesan'])
print('  jumlah perintah:', d['jumlah']['perintah'])
print('  kejadian      :')
for k in d['kejadian']:
    print(f\"     {k['waktu'][-8:]}  {k['nama']:12} {k['jenis']}\")
print('  perintah terakhir:')
for p in d['perintah']:
    print(f\"     {p['aksi']:8} -> {p['sasaran']:12} : {p['hasil']}\")
"

kill $C1 $C2 $C3 $SRV 2>/dev/null
sleep 1
pkill -f "server.py --port $PORT" 2>/dev/null
echo
echo "SELESAI — semua proses dimatikan"
