python3 ./Script/xyz_to_rtv.py --E=+X --N=+Z --U=+Y --flip-r --data-dir temp --out-dir temp_rtv
rm -rf temp/*
mv temp_rtv/* data/
