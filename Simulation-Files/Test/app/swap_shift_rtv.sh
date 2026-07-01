python3 ./Script/swap_xy.py --dir temp

python3 ./Script/shift_station.py --dir temp --x -5 --z -5

python3 ./Script/xyz_to_rtv.py --E=+X --N=+Z --U=+Y --flip-r --data-dir temp --out-dir temp_rtv

rm -rf temp/*

mv temp_rtv/* data/