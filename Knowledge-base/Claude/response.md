# WaveQLab3D `response` System — Detailed Analysis

**Scope:** `Claude/WQ/src/` — the `response` namelist option and everything downstream of it (block physics selection, attenuation/plasticity data model, per-point RHS kernels, and RK time integration).
**Method:** direct reading of `domain.f90`, `block.f90`, `datatypes.f90`, `material.f90`, `withers_tables.f90`, `plastic.f90`, `RHS_Interior.f90`, `JU_xJU_yJU_z6.f90` (grep-sampled), `elastic.f90`, `fields.f90`, `preprocessor.f90`. Cross-referenced against `Knowledge-base/Claude/FQ.md` (the Withers, Olsen & Day 2015 BSSA paper this code partially implements).

## 1. What `response` is

`response` is a top-level `character(256)` namelist parameter (`&problem_list`, read in `domain.f90:88`) that selects the constitutive physics applied *within* each block, on top of the base elastic wave equation. It is validated once (master rank only, then broadcast) in `domain.f90:126-146`:

```fortran
select case (response_norm)
case ('elastic','plastic','anelastic','low-pass','anelastic-Q','anelastic-Q8','anelastic-Qf', &
      'constant-Q-4M','constant-Q-8M','frequency-Q-4M','frequency-Q-8M')
  ! ok
case default
  invalid_response = .true.   ! -> MPI_FINALIZE + exit(1)
end select
```

An invalid string aborts the run cleanly via `c_exit` (a bound C `exit()`), which is a reasonable pattern (avoids each rank printing separately). The validated string is stored as `D%response` and passed down through `init_block` (`block.f90:31`) to select which `init_*_properties` routine(s) run.

## 2. The eleven `response` options and their namelist parameters

| `response` string | Underlying flag(s) set | Init routine | Namelist group | Parameters (defaults) |
|---|---|---|---|---|
| `elastic` | (none) | — | — | pure elastic wave equation, no extra state |
| `plastic` | uses `D%plastic_model` | `init_plastic_material` (`plastic_material.f90`) | `&plastic_list` (not traced in this pass) | Drucker-Prager `mu_beta_eta` (friction, dilatancy, viscosity) from `block_temp_parameters` |
| `low-pass` / `anelastic` | `M%anelastic` | `init_anelastic_properties` | `&anelastic_list` | `c` (=1.0), `weight_exp` (0.0), `fref` (1.0 Hz) |
| `anelastic-Q` | `M%anelastic_Q` | `init_anelastic_Q_properties` | `&anelastic_Q_list` | `c` (=1.0), `fref` (1.0 Hz) |
| `anelastic-Q8` | `M%anelastic_Q8` | `init_anelastic_Q8_properties` | `&anelastic_Q8_list` | `c` (=1.0), `fref` (1.0 Hz) |
| `anelastic-Qf` | `M%anelastic_Qf` | `init_anelastic_Qf_properties` | `&anelastic_Qf_list` | `c` (=1.0), `gamma` (0.0, clamped to [0,0.9]), `f_trans` (1.0 Hz), `fref` (1.0 Hz) |
| `frequency-Q-4M` | `M%anelastic_Qf` (identical to `anelastic-Qf`) | `init_anelastic_Qf_properties` (same call) | `&anelastic_Qf_list` | same as `anelastic-Qf` — **this is a literal alias, not a distinct implementation** (`block.f90:166-188`) |
| `constant-Q-4M` | `M%anelastic_const_Q_4M` | `init_const_Q_4M_properties` | `&constant_Q_4M_list` | `c` (1.0), `fmin` (0.05 Hz), `fmax` (20.0 Hz), `target_Q` (50.0), `weight_method` (`'nnls'`\|`'withers'`\|`'lookup'`), `manual_weights(4)` (0 = auto), `fref` (1.0 Hz) |
| `constant-Q-8M` | `M%anelastic_const_Q_8M` **and** `M%anelastic_const_Q_4M` (both set `.true.`, see §4.3) | `init_const_Q_8M_properties` | `&constant_Q_8M_list` | same shape as 4M, 8-element `manual_weights` |
| `frequency-Q-8M` | `M%anelastic_Qf8` **and** `M%anelastic_Qf` (both set `.true.`) | `init_anelastic_Qf8_properties` | `&anelastic_Qf8_list` | `c` (1.0), `gamma` (0.0), `f_trans` (1.0 Hz), `fref` (1.0 Hz) |

Every anelastic variant stores per-point `Qp_inv`, `Qs_inv` (from `Qs = c·Vs`, `Qp = 2·Qs` — a hardcoded `Qp/Qs = 2` ratio in all seven anelastic init routines) and 6 stress-component memory-variable arrays × N mechanisms (`eta4..eta9`, `Deta4..Deta9`, suffix-tagged per variant), all allocated via `allocate_array_body(..., ghost_nodes=.true.)`. `datatypes.f90:38-129` documents this exhaustively — it is a lot of duplicated boilerplate (six near-identical array pairs × seven variants = ~84 allocatable arrays in `block_material`).

`plastic` is mutually exclusive with every anelastic-Q* variant by construction, since `response` is a single string (`plastic.f90:50`: `if (response/='plastic') return`) — off-fault plasticity and memory-variable attenuation cannot be combined in one run.

## 3. Relationship to the Withers, Olsen & Day (2015) paper (`Knowledge-base/Claude/FQ.md`)

`withers_tables.f90` is a direct, literal port of that paper's Tables 1 and 2:
- `TAU_MIN`/`TAU_MAX`/`W_HIGH_Q`/`A_COEF`/`B_COEF` arrays reproduce the paper's published numbers verbatim for all 10 tabulated `γ` values (0.0–0.9).
- `get_relaxation_times` implements the paper's Eq. 15 (log-uniform `τ_k` spacing).
- `get_withers_weights` implements the paper's high-Q linear-scaling rule (`w_k(Q) = table/Q`, Eq. 11-ish) for `Q > 200`, and the low-Q interpolation formula `w_k = a_k/Q² + b_k/Q` (Eq. 16) for `15 ≤ Q ≤ 200`, clamping below 15 to the paper's stated validity floor.
- It adds one thing the paper doesn't need: linear interpolation *between* the ten tabulated `γ` values (`find_gamma_indices`), since the paper only tabulates at 0.1 increments — a reasonable, correctly-implemented extension.
- `get_relaxation_times_Qf` / `get_withers_weights_Qf` just truncate the 8-mechanism table to the first 4 entries for the `anelastic-Qf`/`frequency-Q-4M` (N=4) variants.

This is the most faithful, well-documented piece of the whole `response` subsystem.

## 4. Implementation architecture — how a `response` selection reaches the RHS

```
domain.f90 (namelist read + validation)
   -> block.f90:init_block()  (per-block, per-response dispatch to init_*_properties)
       -> material.f90:init_*_properties()  (allocate eta/Deta arrays, fit tau/weight, correct unrelaxed moduli)
   -> [time loop] elastic.f90:set_rates_elastic()
       -> RHS_Interior.f90:RHS_Center()        <- bulk interior, uses JU_xJU_yJU_z6.f90 generated stencils
       -> RHS_Interior.f90:RHS_near_boundaries() <- thin near-face shell, general (non-generated) stencil
   -> fields.f90:scale_rates_interior() / update_fields_interior()  (RK-integrates eta arrays alongside F/DF)
```

### 4.1 Per-point kernel structure (consistent across all seven anelastic variants)

Every `apply_<variant>_point(...)` subroutine in `RHS_Interior.f90` follows the same GSLS (generalized standard linear solid) pattern, matching FQ.md Eq. 3-5/17-19:
- Subtract the summed memory variables from the elastic stress-rate: `DU(4..9) -= Σ_l eta<comp>(l)`.
- Compute the memory-variable rate: `Deta<comp>(l) += (weight(l)·(stiffness·strain terms) − eta<comp>(l)) / tau(l)`.
- A `_pml` variant exists for every kernel, replacing raw strain (`Ux(1)`, etc.) with PML-corrected strain via `pml_damping_and_q`.
- A `_dispatch` wrapper picks the PML vs. non-PML kernel via `point_in_pml(...)`.

### 4.2 The memory-variable ODE is integrated explicitly, not exactly

FQ.md Eq. 5 (Day, 1998) specifies an *exact* exponential update for the memory-variable ODE, chosen specifically because it is unconditionally stable regardless of the ratio `dt/τ`. This codebase instead treats `eta` exactly like a wave field: `fields.f90:169-222` does
```fortran
F%M%Deta4 = A*F%M%Deta4          ! scale_rates_interior (RK stage)
...
F%M%eta4 = F%M%eta4 + dt*F%M%Deta4   ! update_fields_interior
```
i.e., the same explicit low-storage RK integrator used for velocities/stresses is applied to the stiff relaxation ODE `dη/dt = (forcing − η)/τ`. **No file couples the simulation `dt` (set purely from the elastic CFL condition in `domain.f90:190-199`/`block.f90:block_time_step`) to the minimum relaxation time `τ_min` of whichever attenuation model is active.** For `constant-Q-4M`/`8M`, `fmax` is a free user parameter (default 20 Hz, `τ_min = 1/(2π·fmax)` ≈ 8 ms) — a user raising `fmax` to resolve higher frequencies, or running on a coarse grid with a large CFL-limited `dt`, can silently violate the stiffness requirement `dt ≪ τ_min` with no warning, degrading accuracy or destabilizing the memory-variable update. This is a latent numerical-robustness gap relative to the reference method.

### 4.3 `constant-Q-8M` and `frequency-Q-8M` reuse the 4-mechanism flags — a working but fragile trick

`block.f90:148-194` gates each `init_*` call on `trim(response) == '<string>'`, and in the `else` branch always resets the corresponding flag to `.false.`:
```fortran
if (trim(response) == 'constant-Q-4M') then
  call init_const_Q_4M_properties(...)
else
  B%M%anelastic_const_Q_4M = .false.
end if
if (trim(response) == 'constant-Q-8M') then
  call init_const_Q_8M_properties(...)
else
  B%M%anelastic_const_Q_8M = .false.
end if
```
Because the two `if` blocks run in sequence, when `response == 'constant-Q-8M'`, the first block's `else` sets `anelastic_const_Q_4M = .false.`, and then `init_const_Q_8M_properties` (`material.f90:1609-1610`) sets **both** `M%anelastic_const_Q_8M = .true.` **and** `M%anelastic_const_Q_4M = .true.`, overwriting the prior `.false.`. The same pattern applies to `frequency-Q-8M` / `init_anelastic_Qf8_properties` (`material.f90:1738-1739`, sets both `anelastic_Qf8` and `anelastic_Qf`).

This matters because `RHS_Interior.f90`'s near-boundary loop only guards on the 4-mechanism flags:
```fortran
if (M%anelastic_const_Q_4M) call apply_const_Q_4M_point_dispatch(...)   ! also fires for 8M!
if (M%anelastic_Qf) call apply_anelastic_Qf_point_dispatch(...)          ! also fires for Qf8!
```
and the dispatch routines themselves branch on `allocated(M%eta4_8M)` / `allocated(M%eta4Qf8)` to route to the real 8-mechanism kernel (`apply_const_Q_8M_point*`, `apply_anelastic_Qf8_point*`) instead of the 4-mechanism one. **This does work correctly** (verified by tracing the exact call order), but it is a confusing, order-dependent design: it silently depends on (a) the two `if/else` blocks in `block.f90` running in a specific sequence, and (b) `allocated()` as a implicit type discriminator instead of checking the dedicated `anelastic_const_Q_8M`/`anelastic_Qf8` booleans directly. Reordering the response-validation blocks, or adding a future response variant that also allocates `eta4_8M`-shaped arrays, would silently break the routing with no compiler error.

### 4.4 The bulk interior (`JU_xJU_yJU_z6.f90`) only implements three of the seven anelastic variants — the most significant finding

`RHS_Center` (called first, for every point *away* from block faces, i.e. the overwhelming majority of a typical domain's volume) dispatches into the ~23,000-line generated-stencil module `JU_xJU_yJU_z6.f90`. Grepping that entire file for attenuation flags:

```
M%anelastic     -> 32 occurrences
M%anelastic_Q   -> 32 occurrences
M%anelastic_Q8  -> 32 occurrences
M%anelastic_Qf, M%anelastic_Qf8, M%anelastic_const_Q_4M, M%anelastic_const_Q_8M -> 0 occurrences (all four)
```

`RHS_near_boundaries` (`RHS_Interior.f90:133`, explicitly commented "used only for points near boundaries" — a stencil-width-wide band adjacent to each of the block's 6 logical faces, `G%C%mbq/pbq` etc.) is the **only** place that ever calls `apply_anelastic_Qf_point_dispatch` / `apply_const_Q_4M_point_dispatch` (and, via §4.3, their 8-mechanism siblings).

**Consequence:** for `response ∈ {'anelastic-Qf', 'frequency-Q-4M', 'frequency-Q-8M', 'constant-Q-4M', 'constant-Q-8M'}` — five of the seven anelastic response strings — attenuation physics is applied *only* within a stencil-width-thin shell adjacent to each block face, and is completely absent from `RHS_Center`'s bulk-interior evaluation, which covers the vast majority of grid points in any domain larger than a handful of cells. In practice, a simulation run with one of these five `response` values will be almost indistinguishable from pure `elastic` — the `eta` memory variables away from block faces are allocated, zero-initialized, and then multiplied/added by zero forever, since nothing ever computes a non-zero `Deta` for them there. Only `elastic`, `plastic`, `anelastic`/`low-pass`, `anelastic-Q`, and `anelastic-Q8` are fully wired end-to-end (bulk interior + near-boundary + PML + RK integration).

This is silent: none of these response strings produce a warning, error, or diagnostic indicating that attenuation is geometrically incomplete. A user selecting `constant-Q-8M` expecting broadband attenuation across the whole domain would get it only in a thin near-face skin.

### 4.5 A duplicate dispatch call doubles the near-boundary forcing for constant-Q-4M/8M

Within `RHS_near_boundaries`'s *first* near-face loop block only (`RHS_Interior.f90:257-258`):
```fortran
if (M%anelastic_const_Q_4M) call apply_const_Q_4M_point_dispatch(F, M, G, x, y, z, Ux, Uy, Uz, DU)
if (M%anelastic_const_Q_4M) call apply_const_Q_4M_point_dispatch(F, M, G, x, y, z, Ux, Uy, Uz, DU)
```
The identical guarded call appears twice in a row. Every subsequent near-face loop block (there are roughly 16 of them, one per face/edge region) calls it exactly once. Because the kernel accumulates (`DU(4) = DU(4) - (...)`, `Deta4_4M = Deta4_4M + (...)`), this specific near-face region gets the `constant-Q-4M`/`constant-Q-8M` attenuation stress-correction and memory-variable forcing applied **twice**, i.e. roughly double-strength attenuation, in that one region only — a localized but genuine double-counting bug, confined to whichever face/edge that first loop block governs.

### 4.6 `constant-Q-4M`/`8M`'s weight-fitting methods do not consistently honor `target_Q`

`material.f90:1341-1578` implements three `weight_method` choices for `constant-Q-4M`/`8M`. All three feed into the *same* RHS kernel formula (`apply_const_Q_4M_point`/`apply_const_Q_8M_point`), which — matching the convention used by `anelastic-Q`/`anelastic-Q8`/`anelastic-Qf` — multiplies the fitted weight by an independent per-point `Qs_inv_const_Q_4M(x,y,z)` factor (`= 1/(c·Vs)`, derived from the unrelated `c` namelist parameter and local shear speed):

- **`'nnls'` (the default)**: `compute_weights_nnls(tau_vals, target_Q, fmin, fmax, weights_out, N)` fits weights so that `compute_Q_response` (`Q_resp = 1/(2·Σ w_k/(1+(ωτ_k)²))`) directly equals the **absolute** `target_Q` value over the test-frequency band — i.e., the fitted weights already encode the desired attenuation level in full, the way FQ.md's Eq. 8 does for a *specific* Q, not a Q*=1 reference. But the kernel then multiplies these already-absolute weights by `Qs_inv_const_Q_4M` (the independent, `c`-derived 1/Q) a second time. The two Q-scalings are unrelated and multiply together, so the delivered attenuation generally matches neither `target_Q` nor the `c`-derived Q alone.
- **`'withers'`**: `compute_weights_withers` calls `get_withers_weights(0.0_wp, 1.0_wp, ...)` — hardcoded `γ=0`, `Q=1.0` — returning the paper's Q*=1 reference-table weights (correctly meant to be scaled by `1/Q` downstream, matching the `anelastic-Q` convention). This path is *not* double-scaled, but as a direct consequence it **silently ignores the `target_Q` namelist parameter entirely** — the delivered Q is whatever `c`/`Vs` produce, no matter what `target_Q` is set to. `compute_weights_withers` also computes a `scale_factor` from `fmin`/`fmax` (intended to adapt the fixed [0.05, 20] Hz reference band to the user's band) that is **never applied** to either `tau` or the weights — a dead local variable.
- **`'lookup'`**: `compute_weights_lookup` starts from the same raw Q*=1 table (via `compute_weights_withers`) and then applies `weights_out = weights_out * target_Q / 50.0_wp` — a linear-in-`target_Q` scaling. This is backwards relative to the correct `1/Q` relationship used everywhere else in the code (`compute_high_q_weights` explicitly divides by `Q`; here it multiplies by `target_Q`), and it stacks on top of the same downstream `Qs_inv` kernel multiplication described above — a third, uncontrolled interaction between `target_Q`, the hardcoded reference value 50, and the `c`-derived Q.

Net effect: only `weight_method='withers'` avoids double-scaling, but at the cost of making `target_Q` a no-op; `'nnls'` (the default) and `'lookup'` both apply `target_Q` on top of an unrelated, independently-scaled `Qs_inv` factor already baked into the shared kernel, so the effective Q delivered by `constant-Q-4M`/`8M` will generally not match the user's requested `target_Q`.

`compute_weights_nnls` itself is also a simplified, hand-rolled Gauss-Newton-with-projection scheme (not a true active-set NNLS), capped at 100 iterations with no convergence warning if `max_iter` is reached without meeting `tol` — it will silently return whatever it has after 100 iterations even if not converged.

### 4.7 Minor findings

- **`frequency-Q-4M` is a byte-for-byte alias of `anelastic-Qf`** — both call `init_anelastic_Qf_properties` and set the identical `M%anelastic_Qf` flag (`block.f90:166-188`). Two distinct, user-facing namelist strings for one implementation; likely to confuse config authors into thinking they differ.
- **`preprocessor.f90:16`** declares `character(len=256) :: name, problem, response, ifname` but `response` is never referenced again in that file — dead/vestigial variable in the mesh-preprocessing executable (`pre_wql3d`), consistent with attenuation being irrelevant to pure mesh generation, but the variable should either be removed or documented as intentionally unused.
- **Response validation happens once, globally** (`domain.f90`), but each *block* independently re-derives its own per-response init call in `block.f90` using the same shared `response` string for both blocks — there is no per-block override, so a two-block domain cannot mix e.g. an elastic block with an anelastic one.
- **`update_fields_plastic`'s signature comment** (`plastic.f90:10`, commented-out old version) and the live version both retain a large amount of dead/commented-out code (hardcoded `mu`/`eta` values, a `STOP` debug statement) directly above the live logic — consistent with the broader codebase's pattern of leaving debug scaffolding in place (also noted in the general `initial_report.md`).

## 5. Summary

The `response` mechanism is a well-structured, single-string physics selector with real, working support for five modes (`elastic`, `plastic`, `anelastic`/`low-pass`, `anelastic-Q`, `anelastic-Q8`) and a faithful implementation of the Withers, Olsen & Day (2015) frequency-dependent-Q weight/relaxation-time tables (`withers_tables.f90`). However, the newer, more ambitious variants — `anelastic-Qf`, `frequency-Q-4M` (its alias), `frequency-Q-8M`, `constant-Q-4M`, and `constant-Q-8M` — have a substantial implementation gap: their attenuation physics is wired into the near-boundary RHS path only, never into the dominant bulk-interior generated-stencil code (`JU_xJU_yJU_z6.f90`), so across most of a domain's volume these five response options behave as pure elastic despite passing validation and fully allocating/initializing their attenuation state. On top of that gap, `constant-Q-4M`/`8M` also have an internal Q-scaling inconsistency across their three weight-fitting methods that makes the user-facing `target_Q` parameter unreliable, and a localized double-counting bug in one near-boundary loop block. These are the priority items if this attenuation feature set is meant to be production-ready; `anelastic-Q`/`anelastic-Q8` (and the base `anelastic` mode) are the response options currently safe to rely on for physically complete attenuation coverage.
