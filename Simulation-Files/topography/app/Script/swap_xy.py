#!/usr/bin/env python3
"""
Swap columns 2 and 3 in all .dat files in a directory and rename files by swapping the first two numeric values in the suffix.
Usage: python swap_xy.py --dir <directory>

python3 ./Script/swap_xy.py --dir temp
"""
import argparse
import os
import re
from pathlib import Path

# Regex to match the suffix pattern: ..._<num1>_<num2>_<num3>.dat
SUFFIX_PATTERN = re.compile(r"(.*_)([\d.]+)_([\d.]+)_([\d.]+)(\.dat)")

def swap_columns_and_rename(file_path: Path):
    # Read and swap columns 2 and 3 (0-based index)
    lines = []
    with file_path.open('r') as f:
        for line in f:
            if line.strip() == '':
                lines.append(line)
                continue
            parts = line.rstrip().split()
            if len(parts) >= 3:
                parts[1], parts[2] = parts[2], parts[1]
            lines.append(' '.join(parts) + '\n')
    # Prepare new filename by swapping first two numeric values in suffix
    m = SUFFIX_PATTERN.match(file_path.name)
    if m:
        new_name = f"{m.group(1)}{m.group(3)}_{m.group(2)}_{m.group(4)}{m.group(5)}"
        new_path = file_path.parent / new_name
    else:
        # If pattern doesn't match, keep original name
        new_path = file_path
    # Write to new file
    with new_path.open('w') as f:
        f.writelines(lines)
    # Remove old file if renamed
    if new_path != file_path:
        file_path.unlink()
    print(f"Processed: {file_path} -> {new_path}")

def main():
    parser = argparse.ArgumentParser(description="Swap columns 2 and 3 and rename .dat files.")
    parser.add_argument('--dir', required=True, help='Directory containing .dat files')
    args = parser.parse_args()
    fdir = Path(args.dir)
    for file in fdir.glob('*.dat'):
        swap_columns_and_rename(file)

if __name__ == '__main__':
    main()
