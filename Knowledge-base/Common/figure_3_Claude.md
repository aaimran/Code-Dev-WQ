# Claude Summary: Figure 3 (Withers et al. 2015) Test Setup + WaveQLab3D `response` Mapping

## Source

- Built from: `Knowledge-base/Common/FQ_Claude.md`, `Knowledge-base/Common/response_Claude.md`
- Detailed spec: `Knowledge-base/Claude/figure_3.md`

## What Figure 3 is

The paper's **elastic-only baseline verification**: an FD vs. frequency–wavenumber (f-k) semi-analytical comparison for a uniform elastic half-space, with **no attenuation** (Q infinite). It establishes the FD solver itself is correct before Figs. 4–6 add constant/power-law Q on top of the identical setup.

## Test parameters (as published)

| Parameter | Value |
|---|---|
| Medium | Elastic half-space: Vp=6000 m/s, Vs=3464 m/s, ρ=2700 kg/m³ |
| Source | Buried double-couple, strike/dip/rake = 90°/90°/0°, depth 1.8 km |
| Source time function | Cosine-bell moment rate, `Ṁ(t)=M0(1−cos(2πt/T))`, T=0.2 s, M0=10¹⁶ N·m (Mw≈4.6) |
| Grid / dt | 40 m spacing, 0.002 s time step, 4th-order-space/2nd-order-time staggered FD |
| Receiver | 15 km horizontal distance, azimuth 53.13° (→ 12 km east / 9 km north — a 9-12-15 triangle) |
| Domain | Large enough (or absorbing) that no reflection reaches the receiver in the ~6–7 s window |
| Verification | Compared to f-k semi-analytical solver; near-exact agreement expected |

## `response` setup to reproduce it

**`response = 'elastic'`** — this is a pure elastic test; none of the seven anelastic `response` variants apply. Per `response_Claude.md`, this is one of the fully-functional, safe-to-use response modes.

Key WaveQLab3D configuration mapping (see `figure_3.md` for full detail and file:line citations):

1. `&problem_list`: `response='elastic'`, `nblocks=1`, Cartesian mesh, `material_source='hardcode'`.
2. `btp(1)%rho_s_p = (2700, 3464, 6000)` — confirmed order is `(ρ, Vs, Vp)` from `material.f90:592-594`.
3. Source: WaveQLab3D takes raw moment-tensor components (`mXX..mYZ`), not strike/dip/rake, via a delimited `!---begin:tensor_listU---` block (not a namelist) read by `moment_tensor.f90`. For this exact mechanism the tensor reduces to **`mXY = -1e16`, all other 5 components zero** (standard double-couple algebra for strike=90°/dip=90°/rake=0°) — sign/axis convention not independently verified.
4. Source time function: use **`source_type='cosine'`** (`A=1−cos(2πt/duration)`, exact match to the paper's Eq. 20) — **not** `'Cos-Bell'`, which has a parameter-binding bug (uses `t_init` instead of `duration` as its pulse width, so it won't respond to a `duration=0.2` setting the way a user would expect).
5. `t_final ≈ 6–7 s`; domain sized (or PML'd on non-free-surface faces) to avoid boundary reflection at the receiver within that window.
6. Seismogram station at the 15 km/53.13° offset; bandpass filtering (0.2–10 Hz) and f-k comparison happen **outside** WaveQLab3D — no in-code equivalent.

## Notable implementation finding surfaced during this mapping

`moment_tensor.f90` has two similar-looking cosine-type source options, `'cosine'` and `'Cos-Bell'`, and only one of them (`'cosine'`) actually uses the `duration` namelist field as the pulse width; `'Cos-Bell'` silently substitutes the source start-time offset (`t_init`) instead. This is an easy trap when configuring this exact test and is not documented anywhere in the source.

## Open items (not yet verified against source, flagged rather than guessed)

- Exact `(x,y,z)` ↔ (north/east/down) axis convention — affects only the source-tensor sign/polarity, not amplitude.
- Default boundary treatment (free-surface vs. absorbing) for a face with neither PML nor an interface enabled — `pml_lqrs`/`pml_rqrs`/`npml` fields exist in `block_temp_parameters`, but this pass didn't trace the non-PML default.
- Full per-station coordinate list format in `seismogram.f90` (the `output_list` namelist toggle was confirmed; the station-list syntax itself wasn't fully traced).

## Flag for cross-AI comparison

- **Topic class:** applied config-mapping exercise (paper test → this repo's input format), not a general code or paper summary.
- **Confidence:** high on the physical/paper specification and on the `response='elastic'` recommendation and the `'cosine'` vs `'Cos-Bell'` distinction (verified directly in `moment_tensor.f90`); medium on the moment-tensor sign convention and default boundary behavior (explicitly flagged as unverified rather than asserted).
