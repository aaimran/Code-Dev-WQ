# Figure 3 (Withers, Olsen & Day 2015) — Test Specification and WaveQLab3D `response` Setup

**Built from:** `Knowledge-base/Common/FQ_Claude.md`, `Knowledge-base/Common/response_Claude.md`, cross-checked against `Knowledge-base/Claude/FQ.md` (§4, paper source text) and direct reading of `Claude/WQ/src/moment_tensor.f90`, `material.f90`, `domain.f90`, `block.f90`, `datatypes.f90` for the configuration mapping.

## 1. What Figure 3 is

Figure 3 in Withers, Olsen & Day (2015) is captioned: *"Half-space point-source test: comparison of frequency–wavenumber (f-k) and finite-difference (FD) results **for an elastic medium**."* It is the paper's baseline sanity check, run *before* any attenuation (`Q(f)`) machinery is turned on — it validates that the underlying elastic FD solver alone (grid, source injection, free surface, absorbing boundaries) reproduces a semi-analytical reference to high accuracy. Figures 4–6 then layer constant-Q and power-law-Q onto this identical setup and compare misfit growth relative to this elastic baseline. **Figure 3 therefore exercises no memory-variable/Q code at all** — it is a pure elastic verification.

## 2. Full test specification (as published)

| Parameter | Value | Paper reference |
|---|---|---|
| Medium | Uniform elastic half-space | §"Numerical Tests" |
| Vp | 6000 m/s | text preceding Fig. 3 |
| Vs | 3464 m/s | same |
| ρ (density) | 2700 kg/m³ | same |
| Q | infinite (no attenuation) | Fig. 3 caption |
| Source type | Buried double-couple point source | §"Numerical Tests" |
| Strike / dip / rake | 90° / 90° / 0° | same |
| Source depth | 1.8 km | same |
| Source time function | Cosine-bell moment rate: `Ṁ(t) = M0·(1 − cos(2πt/T))` for `0 < t < T`, else 0 (paper Eq. 20) | Eq. 20 |
| Duration `T` | 0.2 s | same |
| Scalar moment `M0` | 10¹⁶ N·m (→ **Mw ≈ 4.6**) | same |
| Numerical method | 4th-order-space / 2nd-order-time staggered-grid velocity-stress FD (Cui et al., 2010) | §"Method"/"Numerical Tests" |
| Grid spacing | 40 m | same |
| Time step | 0.002 s | same |
| Receiver | Free-surface station, 15 km horizontal distance from epicenter, azimuth 53.13° from north | text at Fig. 3 |
| Reference/verification method | Frequency–wavenumber (f-k) semi-analytical code (modified Zhu & Rivera, 2002) | same |
| Post-processing | Bandpass 0.2–10 Hz, 4th-order zero-phase Butterworth filter; unrelaxed-modulus reference frequency `f0 = 1 Hz` (irrelevant here since Q=∞, but kept for consistency with Figs. 4–6) | text after Fig. 4 |
| Domain sizing | "Large enough to have no reflections from boundaries at the receiver station during the simulated time" (i.e., effectively an unbounded half-space over the ~6 s window plotted) | text preceding Fig. 3 |
| Expected result | Near-exact agreement between FD and f-k radial/transverse/vertical velocity seismograms and Fourier spectra (Fig. 3a,b) | Fig. 3 |

Since Q is infinite, none of the paper's Q-fitting apparatus (Eqs. 1–19, Tables 1–2) is exercised by this figure — it isolates numerical/geometric correctness of the FD scheme itself.

## 3. How to set up `response` (and the surrounding configuration) in WaveQLab3D to reproduce this test

### 3.1 `response`: use `'elastic'`

Per `Knowledge-base/Claude/response.md` §2, `response = 'elastic'` selects pure elastic wave propagation with none of the memory-variable (`eta`/`Deta`) attenuation state allocated. This is the *only* correct mapping for Figure 3 — none of the seven anelastic `response` variants (`anelastic`, `anelastic-Q`, `anelastic-Q8`, `anelastic-Qf`, `constant-Q-4M`, `constant-Q-8M`, `frequency-Q-4M`/`8M`) should be used here, since Figure 3 has no Q to model. (If this test is later extended to reproduce Figures 4–6, `response = 'anelastic-Q'` or `'anelastic-Q8'` are the *only* two variants confirmed fully wired end-to-end per `response.md` §4.4 for a constant-Q, `γ=0` reproduction of Fig. 4; a power-law `γ=0.6` reproduction of Fig. 5 would need `anelastic-Qf`, which per `response.md` §4.4 currently only applies attenuation in a thin near-boundary shell, not the bulk interior — flag this gap before attempting Fig. 5/6.)

In `&problem_list` (`domain.f90:88`):
```fortran
&problem_list
  name        = 'FQ_Fig3_elastic_halfspace'
  problem     = 'TPV5'        ! placeholder; not physically used when material_source='hardcode' and no fault is active
  response    = 'elastic'
  nblocks     = 1              ! single half-space block; no second block/interface needed for a point-source test
  CFL         = 0.5            ! reduce if instability observed; paper's dt=0.002s at h=40m implies a specific Vp*dt/h — verify against this code's stability limit for the chosen fd_type/order
  fd_type     = 'traditional'  ! or 'upwind'/'upwind_drp' — paper uses a standard staggered-grid scheme; 'traditional' SBP-SAT is the closest analog available here
  order       = 4              ! paper's FD is 4th-order in space
  t_final     = 6.0            ! seconds; paper plots out to ~6-7 s (Figs. 3-6)
  mesh_source = 'compute'
  type_of_mesh= 'cartesian'
  material_source = 'hardcode'
  interpol    = .false.
  use_topography = .false.
/
```
Note `D%dt` in this code is *not* a free input — `domain.f90:190-199` computes it from `block_time_step` (`CFL·h / sqrt(Vs²+Vp²)`), not set directly to the paper's 0.002 s. To match the paper's `dt = 0.002 s` at `h = 40 m`, tune `CFL` so the computed `dt` lands close to 0.002 s (or accept whatever the code's own CFL-stable `dt` is, since matching the exact FD scheme step-for-step is secondary to matching physical accuracy).

### 3.2 Material properties (`&block_list` / `block_temp_parameters`, `btp(1)`)

`material_source = 'hardcode'` routes through `material.f90:init_material`, which reads `rho_s_p = (ρ, Vs, Vp)` (confirmed order from `material.f90:592-594`: `lambda = ρ(Vp²−2Vs²)`, `mu = ρ·Vs²`, `rho = ρ`). Set:
```fortran
btp(1)%rho_s_p = (/ 2700.0, 3464.0, 6000.0 /)   ! rho [kg/m^3], Vs [m/s], Vp [m/s]
```
Grid extent (`aqrs`, `bqrs`, `nqrs`) must be sized so no boundary reflection reaches the 15 km / 53.13°-azimuth receiver within the ~6–7 s plotted window, per the paper's explicit requirement. A conservative box is at least `Vp·t_final` beyond the farthest receiver in every direction the domain isn't otherwise absorbing (e.g., ≥ 15 km + 6000 m/s·7 s ≈ 57 km lateral half-extent) *unless* PML is enabled on the non-free-surface faces — combine a generous domain size with PML (`btp(1)%npml`, `btp(1)%pml_lqrs`/`pml_rqrs` set `.true.` on all faces except the top `z`-face, which should remain the physical free surface) to keep the mesh tractable at 40 m spacing. At 40 m spacing a domain this large is ~1400+ points per horizontal axis — expect this to be the dominant cost driver; consider whether the paper's exact domain size is reproducible at this resolution or whether a scaled-down verification (smaller M0/distance, same physics) is more practical first.

### 3.3 Source: convert strike/dip/rake to WaveQLab3D's moment-tensor input format

WaveQLab3D does **not** take strike/dip/rake directly — `moment_tensor.f90` reads raw moment-tensor components `mXX, mYY, mZZ, mXY, mXZ, mYZ` from a delimited block in the input file (not a Fortran namelist), read via `init_moment_tensor` (`moment_tensor.f90:36-135`):
```
!---begin:tensor_listU---
'cosine'  0.2  0.0   0.0 0.0 0.0   -1.0e16 0.0 0.0   <x0> <y0> <z0>   2
!---end:tensor_listU---
```
(column order per `moment_tensor.f90:129-133`: `source_type, duration, t_init, mXX, mYY, mZZ, mXY, mXZ, mYZ, location_x, location_y, location_z, alpha`; use `tensor_listV` instead of `tensor_listU` if the source belongs to block 2 — irrelevant here since `nblocks=1`).

For the paper's exact mechanism (strike 90°, dip 90°, rake 0°) the standard double-couple moment-tensor formula (Aki & Richards convention, x=north, y=east, z=down) reduces to a single non-zero shear component:
```
Mxx = Myy = Mzz = Mxz = Myz = 0
Mxy = Myx = -M0   (sign depends on the rake/left-right-lateral convention in use — verify against this code's coordinate handedness before trusting the sign for polarity-sensitive comparisons)
```
This is a convenient special case — it means only `mXY = -1.0e16` needs to be set, all other five components zero. This should be double-checked against WaveQLab3D's actual `(x,y,z)` axis convention (this pass did not trace whether `x`/`y`/`z` map to north/east/down or some other orientation) before treating the seismogram polarities as meaningful; the *amplitude* comparison is unaffected by this sign ambiguity.

Also required, in `&moment_list` (`block.f90:65`, read once per block):
```fortran
&moment_list
  use_moment_tensor = .true.
  order = 2        ! mollifier/injection order for spreading the point source onto the grid — paper doesn't specify an equivalent parameter; start with the code's default and check source-injection convergence with grid refinement
/
```

**Source time function — use `'cosine'`, not `'Cos-Bell'`:** `moment_tensor.f90:851-854` implements `source_time` case `'cosine'` as `A = 1 − cos(2πt/w)` for `0 ≤ t ≤ w`, where `w` is bound to `B%MT%duration(i)` (`moment_tensor.f90:910`) — this is an exact match to the paper's Eq. 20 with `w = T = 0.2`. There is also a `'Cos-Bell'` option (`moment_tensor.f90:843-849`) that looks superficially similar (`A = (1−cos(2πt/t0))/t0`) but is bound to `t0 = B%MT%t_init(i)` (the source *start-time offset*, not the pulse duration) — using `'Cos-Bell'` with the intent of controlling pulse width via `duration` will silently do nothing, since that variant never reads `duration` at all. **Use `source_type = 'cosine'` with `duration = 0.2` and `t_init = 0.0`** (or a small positive delay if the source-time ramp needs to start strictly after `t=0`).

`location_x/y/z` should place the source at 1.8 km depth, at whatever `(x,y)` origin is chosen as the epicenter (commonly the domain's horizontal center, so absorbing boundaries are equidistant).

### 3.4 Receiver / output

Set up a seismogram station at 15 km horizontal distance, azimuth 53.13° from the epicenter, at the free surface (`z=0`), via `&output_list` (`seismogram.f90:43-44`: `output_seismograms=.true.`, plus whatever station-location list format that module reads — this pass confirmed the namelist toggle but did not fully trace the per-station coordinate list format; check `seismogram.f90` around its station-list read logic before finalizing). Horizontal offsets:
```
x_offset = 15000 * sin(53.13°) ≈ 12000 m   (east component, if x=north/y=east)
y_offset = 15000 * cos(53.13°) ≈  9000 m   (north component)
```
(a 3-4-5 triangle — 53.13° is `atan(4/3)`, giving clean 9/12/15 km components, which is very likely *why* the paper chose that specific azimuth).

### 3.5 Post-processing (outside WaveQLab3D)

The paper's comparison is done offline: bandpass the WaveQLab3D velocity seismogram output 0.2–10 Hz with a 4th-order zero-phase Butterworth filter, rotate to radial/transverse/vertical components using the source–receiver azimuth, and compare against an independently-run f-k solver (e.g., a modified Zhu & Rivera 1996 code) for the same source/medium/receiver geometry. WaveQLab3D itself has no f-k solver — this comparison step is external tooling, not a `response` setting.

## 4. Summary checklist to reproduce Figure 3

1. `response = 'elastic'` (no attenuation namelists needed).
2. `nblocks = 1`, Cartesian half-space, `rho_s_p = (2700, 3464, 6000)`.
3. Domain large enough (or PML'd) that no reflection reaches the receiver within the plotted time window; free surface only at `z=0`.
4. `&moment_list use_moment_tensor=.true.`; tensor list with `mXY = -1e16` (all other components 0), `source_type='cosine'`, `duration=0.2`, `location_z` = 1.8 km depth.
5. `t_final ≈ 6–7 s`; grid spacing 40 m; tune `CFL` toward the paper's implied `dt=0.002 s`.
6. Seismogram station at 15 km / azimuth 53.13° (≈ 12 km east, 9 km north, if x=north).
7. Post-process externally: 0.2–10 Hz zero-phase Butterworth, rotate to R/T/Z, compare to an independent f-k reference — WaveQLab3D does not do this step itself.

**Open items flagged during this pass, not yet verified against source:** the exact `(x,y,z)`↔(north/east/down or similar) axis convention (affects only source-tensor sign/polarity, not amplitude); the free-surface boundary-condition mechanism at `z=0` (this pass found PML fields (`npml`, `pml_lqrs/rqrs`) in `block_temp_parameters` but did not trace how a non-PML, non-interface face is treated by default — confirm it defaults to traction-free before relying on it); the full station-list input format in `seismogram.f90` beyond the `output_list` namelist toggle.
