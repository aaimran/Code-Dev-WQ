#!/bin/bash

# Usage: copy_dat.sh --tdir target_folder --cdir folder1 folder2 ... foldern
# Usage: copy_dat.sh --tdir ./app/temp --cdir dat_1tp_100m dat_1tpx_100m dat_2tp_100m dat_2tpx_100m dat_3tp_100m 
#dat_3tpx_100m dat_4tp_100m dat_4tpx_100m

show_help() {
    echo "Usage: $0 --tdir target_folder --cdir folder1 [folder2 ... foldern]"
    exit 1
}

# Parse arguments
if [ "$1" != "--tdir" ]; then
    show_help
fi
shift
target_dir="$1"
shift
if [ "$1" != "--cdir" ]; then
    show_help
fi
shift

if [ -z "$target_dir" ] || [ $# -lt 1 ]; then
    show_help
fi

# Create target directory if it doesn't exist
mkdir -p "$target_dir"

# Copy all .dat files from each source folder (recursively)
for src in "$@"; do
    if [ -d "$src" ]; then
        find "$src" -type f -name '*.dat' -exec cp {} "$target_dir" \;
    else
        echo "Warning: $src is not a directory, skipping."
    fi
done

echo "All .dat files copied to $target_dir."
