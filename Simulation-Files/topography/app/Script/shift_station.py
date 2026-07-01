#!/usr/bin/env python3
"""
Shift the station coordinates in .dat filenames by specified x, y, z values.
Usage: python3 shift_station.py --dir <directory> --x <dx> --y <dy> --z <dz>
Any of --x, --y, --z can be omitted (default 0).

python3 ./Script/shift_station.py --dir temp --x -5 --z -5
python3 ./Script/shift_station.py --dir temp --x -25 --z -25

"""
import argparse
import re
from pathlib import Path

# Regex to match the suffix pattern: ..._<x>_<y>_<z>.dat
SUFFIX_PATTERN = re.compile(r"(.*_)([\d.\-]+)_([\d.\-]+)_([\d.\-]+)(\.dat)")

def shift_station_filename(file_path: Path, dx: float, dy: float, dz: float):
    m = SUFFIX_PATTERN.match(file_path.name)
    if not m:
        print(f"Skipping (pattern not matched): {file_path.name}")
        return
    x, y, z = float(m.group(2)), float(m.group(3)), float(m.group(4))
    new_x = x + dx
    new_y = y + dy
    new_z = z + dz
    # Format with 3 decimals, preserve sign
    new_name = f"{m.group(1)}{new_x:.3f}_{new_y:.3f}_{new_z:.3f}{m.group(5)}"
    new_path = file_path.parent / new_name
    file_path.rename(new_path)
    print(f"Renamed: {file_path.name} -> {new_name}")

def main():
    parser = argparse.ArgumentParser(description="Shift station coordinates in .dat filenames.")
    parser.add_argument('--dir', required=True, help='Directory containing .dat files')
    parser.add_argument('--x', type=float, default=0.0, help='Shift in x (default 0)')
    parser.add_argument('--y', type=float, default=0.0, help='Shift in y (default 0)')
    parser.add_argument('--z', type=float, default=0.0, help='Shift in z (default 0)')
    args = parser.parse_args()
    fdir = Path(args.dir)
    for file in fdir.glob('*.dat'):
        shift_station_filename(file, args.x, args.y, args.z)

if __name__ == '__main__':
    main()
