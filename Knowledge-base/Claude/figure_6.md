# Figure 6 (Withers, Olsen & Day 2015) — Test Specification and WaveQLab3D `response` Setup

**Built from:** `Knowledge-base/Claude/figure_3.md`, `figure_4.md`, `figure_5.md` (shared setup), `Knowledge-base/Claude/FQ.md`, `Knowledge-base/Claude/response.md`, and direct reading of `Claude/WQ/src/material.f90`.

## 1. What Figure 6 is

Caption: *"Layered-model point-source test: comparison of f-k and FD results for a Q(f) model with γ = 0.6."* Same source and (implied, per the paper's pattern of reusing "the same surface station") receiver geometry as Figures 3–5, but the medium is now a **two-layer model** (paper's Table 3) instead of a uniform half-space: a thin, low-velocity, low-Q layer over a higher-velocity, higher-Q half-space. This specifically stresses the coarse-grained method's handling of (a) a sharp material/Q discontinuity and (b) Love-wave (surface-wave) propagation, neither of which Figures 3–5's uniform half-space exercises.

## 2. What changes relative to Figure 5

| Parameter | Figure 5 (uniform half-space) | Figure 6 (layered) |
|---|---|---|
| Medium | Uniform half-space, Vp=6000/Vs=3464/ρ=2700 | **Two layers** (paper's Table 3): |
| Layer 1 (shallow) | — | Vp=5196 m/s, Vs=3000 m/s, ρ=2550 kg/m³, thickness=1000 m, `Qp0=Qs0=20`, `γ=0.6` |
| Layer 2 (half-space below) | — | Vp=6000 m/s, Vs=3464 m/s, ρ=2700 kg/m³, `Qp0=Qs0=210`, `γ=0.6` |
| `γ` | 0.6 | 0.6 (same, both layers) |
| Reported accuracy | EM<2%, PM<1% | EM 5–10%, PM 1–2% (worse than Fig. 5 — attributed to the coarse-grained scheme's known limitation at sharp material discontinuities, larger for later surface-wave arrivals) |
| Source, receiver, grid spacing, `dt`, domain extent | — | unchanged (paper reuses the same station/source configuration pattern established in Figs. 3–5) |

The paper explicitly notes the shallow layer's Q is harmonically averaged and the half-space's Q arithmetically averaged over the coarse-grained cell (per Graves & Day 2003's finding that harmonic averaging is more accurate for `Q<200`) — this is the same effective-Q machinery already described in `FQ.md` §2 (Eqs. 9–14), not a new mechanism.

## 3. `response` setup — same blocking gap as Figure 5, plus a material-setup gap

### 3.1 Attenuation: identical blocker to Figure 5

This is still a `γ=0.6` power-law-Q test, so it requires `response='frequency-Q-8M'` (or the N=4 fallback `'anelastic-Qf'`/`'frequency-Q-4M'`) exactly as in `figure_5.md`. **The same bulk-interior gap documented there applies without modification** — `anelastic_Qf`/`anelastic_Qf8` are not handled in `JU_xJU_yJU_z6.f90`'s bulk-interior stencils, only in the thin near-boundary shell — so this figure is equally unreproducible until that gap is fixed. See `figure_5.md` §3.1 for the full argument; it is not repeated here.

An additional wrinkle specific to this figure: `Qp0=Qs0` differs *per layer* (20 vs. 210), and both layers are supposed to share the *same* `γ=0.6`. The code's per-point `Qs_inv`/`Qp_inv` arrays (`M%Qs_inv_Qf8`, `M%Qp_inv_Qf8`) are computed as `1/(c·Vs(x,y,z))` at every grid point (`material.f90:1783`), so they naturally vary spatially with the local `Vs` field already — **but `c` itself is a single scalar read once per block from `&anelastic_Qf8_list`**, not a spatially-varying field. Since `Qs(x) = c·Vs(x)`, getting `Qs0=20` in the shallow layer and `Qs0=210` in the half-space from one constant `c` would require the *velocity ratio* `Vs_layer/Vs_halfspace` (3000/3464 ≈ 0.866) to reproduce the *Q ratio* `20/210 ≈ 0.095` — it does not (0.866 ≠ 0.095). **A single global `c` cannot reproduce Table 3's per-layer Q values**, independent of the bulk-interior bug. Reproducing this exactly would need either per-block-region `c` values (not supported — `c` is one number per `&anelastic_Qf8_list`, and there is only one such namelist read per block in `block.f90`) or a source-level change to make `c`/`Qs0` spatially assignable per material region. The universal `Qp0=2·Qs0` hardcoding (see `figure_4.md` §3.2) applies here too, on top of this.

### 3.2 Material: no exact built-in match for Table 3, either

`material.f90:596-639` has a hardcoded `'LOH1'` problem case that is structurally similar (a thin layer over a half-space, selected by a coordinate threshold) but uses **different, non-dimensional velocity values** (Vp=4/Vs=2/ρ=2.6 in the layer, Vp=6/Vs=3.464/ρ=2.7 below — the classic SCEC LOH.1 benchmark, likely in km/s-scaled units) that do not match the paper's Table 3 (Vp=5196/Vs=3000/ρ=2550 over Vp=6000/Vs=3464/ρ=2700, SI units). `LOH1` is not a byte-exact reproduction of Table 3, though it is close in spirit and the *same layer-over-halfspace structure*. Note also that `LOH1`'s layering condition checks `G%x(l,j,k,1)` — the array's **first spatial coordinate**, not necessarily depth/`z` — worth confirming this codebase's coordinate ordering (see the same open item flagged in `figure_3.md` §4) before assuming `LOH1`'s layering axis matches "depth."

For an exact reproduction of Table 3, use `material_source='file'` (`block.f90:139-140` → `material.f90:init_material_from_file`) and supply three pre-generated distributed binary files (`lambda`, `mu`, `rho`, per `material_path(1:3)` in `block_temp_parameters`) with the exact two-layer Vp/Vs/ρ values from Table 3 at a 1000 m depth boundary — this is an offline mesh/material-generation step outside `response`/namelist configuration, using `mpi3dio.f90`'s distributed-file format (not traced in this pass).

### 3.3 Everything else

Source (moment tensor + `'cosine'` time function), receiver offset, `t_final`, and external post-processing are unchanged from `figure_3.md`–`figure_5.md`.

## 4. Summary checklist to reproduce Figure 6

1. Start from the Figure 3/4/5 configuration.
2. **Blocked, same as Figure 5:** `anelastic_Qf`/`anelastic_Qf8` bulk-interior gap must be fixed first (`response.md` §4.4).
3. **Additionally blocked:** a single scalar `c` in `&anelastic_Qf8_list` cannot reproduce Table 3's two different `Qs0` values (20 vs. 210) from the layers' velocity ratio alone — would need a source-level change for spatially-varying `c`/`Qs0`.
4. Material: no exact built-in `problem='...'` case matches Table 3; use `material_source='file'` with a custom-generated two-layer profile, or accept `problem='LOH1'` as a structurally-similar but numerically different substitute.
5. Universal `Qp0=2·Qs0` hardcoding (from `figure_4.md`) still applies once/if the above are resolved.
6. Source, receiver, grid, and external comparison unchanged from Figures 3–5.
7. Expected result once fully working: EM 5–10%, PM 1–2%, worse than Figure 5's uniform half-space due to the coarse-grained scheme's known accuracy limit at sharp Q/velocity discontinuities, most visible in later surface-wave (Love-wave) arrivals.
