#!/usr/bin/env python3
"""
xyz_to_rtz.py

Convert ASCII files with columns:  t vx vy vz  (components along simulation +X,+Y,+Z)
into:                              t vR vT vZ (RTZ, with Z meaning vertical component)

You control how simulation axes map to ENU via:
  --E=+X / -X / +Y / -Y / +Z / -Z
  --N=...
  --U=...

Rotation convention:
  - azimuth clockwise from North
  - radial points source -> station
  - transverse chosen so R × T = Up (right-handed in ENU)

New options:
  --flip-r  flips ONLY vR sign
  --flip-t  flips ONLY vT sign
  --flip-v  flips ONLY vZ sign

These flips apply to VELOCITIES only (not time).

python3 xyz_to_rtz.py --E=+X --N=+Z --U=+Y --flip-r --data-dir data --out-dir data_rtz

python3 ./Script/xyz_to_rtv.py --E=+X --N=+Z --U=+Y --flip-r --data-dir temp --out-dir temp_rtv
"""

import argparse
import math
from pathlib import Path
from typing import Tuple, Optional

AxisExpr = Tuple[str, float]  # (axis 'X'|'Y'|'Z', sign +1|-1)


def parse_axis_expr(s: str) -> AxisExpr:
    ss = s.strip().upper()
    if not ss:
        raise ValueError("empty axis expression")
    sign = 1.0
    if ss[0] == "+":
        ss = ss[1:]
    elif ss[0] == "-":
        sign = -1.0
        ss = ss[1:]
    if ss not in ("X", "Y", "Z"):
        raise ValueError(f"bad axis expression '{s}'. Use +X/-X/+Y/-Y/+Z/-Z.")
    return ss, sign


def validate_mapping(E_map: AxisExpr, N_map: AxisExpr, U_map: AxisExpr) -> None:
    axes = [E_map[0], N_map[0], U_map[0]]
    if len(set(axes)) != 3:
        raise ValueError(f"Invalid mapping: E,N,U must use distinct axes, got {axes}.")


def parse_xyz(s: str) -> Tuple[float, float, float]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 3:
        raise ValueError("expected x,y,z")
    return float(parts[0]), float(parts[1]), float(parts[2])


def get_component(vec_xyz: Tuple[float, float, float], axis: str) -> float:
    x, y, z = vec_xyz
    if axis == "X":
        return x
    if axis == "Y":
        return y
    if axis == "Z":
        return z
    raise ValueError(axis)


def map_xyz_to_ENU(
    vec_xyz: Tuple[float, float, float],
    E_map: AxisExpr,
    N_map: AxisExpr,
    U_map: AxisExpr,
) -> Tuple[float, float, float]:
    axE, sE = E_map
    axN, sN = N_map
    axU, sU = U_map
    E = sE * get_component(vec_xyz, axE)
    N = sN * get_component(vec_xyz, axN)
    U = sU * get_component(vec_xyz, axU)
    return E, N, U


def azimuth_from_EN(src_EN: Tuple[float, float], sta_EN: Tuple[float, float]) -> float:
    dE = sta_EN[0] - src_EN[0]
    dN = sta_EN[1] - src_EN[1]
    az = math.degrees(math.atan2(dE, dN))
    if az < 0:
        az += 360.0
    return az


def unit_vectors_RT(az_deg: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    a = math.radians(az_deg)
    ur = (math.sin(a), math.cos(a))       # (E,N)
    ut = (-math.cos(a), math.sin(a))      # (E,N) ensures R×T=Up
    return ur, ut


def extract_coords_from_name(name: str) -> Optional[Tuple[float, float, float]]:
    parts = Path(name).stem.split("_")
    if len(parts) < 3:
        return None
    try:
        x = float(parts[-3])
        y = float(parts[-2])
        z = float(parts[-1])
        return x, y, z
    except Exception:
        return None


def convert_file(
    inpath: Path,
    outpath: Path,
    E_map: AxisExpr,
    N_map: AxisExpr,
    U_map: AxisExpr,
    ur_EN: Tuple[float, float],
    ut_EN: Tuple[float, float],
    flip_r: bool,
    flip_t: bool,
    flip_v: bool,
) -> int:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    converted = 0

    with inpath.open("r") as fi, outpath.open("w") as fo:
        for line in fi:
            s = line.strip()
            if not s:
                fo.write(line)
                continue
            parts = s.split()
            if len(parts) < 4:
                fo.write(line)
                continue
            try:
                t = float(parts[0])
                vx = float(parts[1])
                vy = float(parts[2])
                vz = float(parts[3])
            except Exception:
                fo.write(line)
                continue

            # Map sim velocities (vx,vy,vz) in XYZ basis to ENU
            vE, vN, vU = map_xyz_to_ENU((vx, vy, vz), E_map, N_map, U_map)

            # Rotate EN -> RT
            vR = vE * ur_EN[0] + vN * ur_EN[1]
            vT = vE * ut_EN[0] + vN * ut_EN[1]
            vZ = vU  # vertical component (whatever you mapped as Up)

            # Optional polarity flips (velocities only)
            if flip_r:
                vR = -vR
            if flip_t:
                vT = -vT
            if flip_v:
                vZ = -vZ

            fo.write(f"{t:.6f} {vR:.6f} {vT:.6f} {vZ:.6f}\n")
            converted += 1

    return converted


def main():
    p = argparse.ArgumentParser(description="Convert t vx vy vz -> t vR vT vZ with explicit axis mapping")

    p.add_argument("--data-dir", default="data", help="input directory containing .dat files")
    p.add_argument("--out-dir", default="data_rtz", help="output directory to write converted .dat files")
    p.add_argument("--pattern", default="*.dat", help="glob pattern for input files")

    # Explicit ENU mapping from sim axes
    p.add_argument("--E", required=True, help="Map East to signed sim axis, e.g. +X or -X")
    p.add_argument("--N", required=True, help="Map North to signed sim axis, e.g. +Z or -Z")
    p.add_argument("--U", required=True, help="Map Up to signed sim axis, e.g. -Y")

    # Geometry for azimuth
    p.add_argument("--src", default="0,0,0", help="source sim coords x,y,z (same axes as files)")
    p.add_argument("--azimuth", type=float, help="override azimuth (deg clockwise from North)")
    p.add_argument("--station", type=str, help="station sim coords x,y,z (used if azimuth not given)")

    # New polarity flips (velocities only)
    p.add_argument("--flip-r", action="store_true", help="Flip radial velocity sign")
    p.add_argument("--flip-t", action="store_true", help="Flip transverse velocity sign")
    p.add_argument("--flip-v", action="store_true", help="Flip vertical velocity sign")

    args = p.parse_args()

    E_map = parse_axis_expr(args.E)
    N_map = parse_axis_expr(args.N)
    U_map = parse_axis_expr(args.U)
    validate_mapping(E_map, N_map, U_map)

    # Source in ENU (mapped from sim XYZ)
    src_xyz = parse_xyz(args.src)
    src_E, src_N, _src_U = map_xyz_to_ENU(src_xyz, E_map, N_map, U_map)

    indir = Path(args.data_dir)
    outdir = Path(args.out_dir)
    files = sorted(indir.glob(args.pattern))
    if not files:
        raise SystemExit(f"No files matching {args.pattern} in {indir}")

    # Determine azimuth:
    # - If --azimuth set: use for all files
    # - else if --station set: compute one global azimuth
    # - else compute per-file azimuth from coords embedded in filename _x_y_z
    global_az: Optional[float] = None
    if args.azimuth is not None:
        global_az = float(args.azimuth)
    elif args.station is not None:
        sta_xyz = parse_xyz(args.station)
        sta_E, sta_N, _sta_U = map_xyz_to_ENU(sta_xyz, E_map, N_map, U_map)
        global_az = azimuth_from_EN((src_E, src_N), (sta_E, sta_N))

    total = 0
    for f in files:
        if global_az is not None:
            az_use = global_az
        else:
            coords = extract_coords_from_name(f.name)
            if coords is None:
                print(f"SKIP (no coords in filename and no --station/--azimuth): {f}")
                continue
            sta_E, sta_N, _sta_U = map_xyz_to_ENU(coords, E_map, N_map, U_map)
            az_use = azimuth_from_EN((src_E, src_N), (sta_E, sta_N))

        ur, ut = unit_vectors_RT(az_use)

        outp = outdir / f.name
        nconv = convert_file(
            f,
            outp,
            E_map,
            N_map,
            U_map,
            ur,
            ut,
            flip_r=args.flip_r,
            flip_t=args.flip_t,
            flip_v=args.flip_v,
        )
        total += nconv
        print(f"{f} -> {outp} : {nconv} lines (azimuth={az_use:.6f}°)")

    print(f"Done. Total converted numeric lines: {total}.")


if __name__ == "__main__":
    main()