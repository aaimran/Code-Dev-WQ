# Claude Summary: WaveQLab3D `response` System (physics/attenuation selector)

## Source

- Analyzed: `Claude/WQ/src/` — `response` namelist option (`domain.f90`, `block.f90`, `datatypes.f90`, `material.f90`, `withers_tables.f90`, `RHS_Interior.f90`, `JU_xJU_yJU_z6.f90`, `elastic.f90`, `fields.f90`)
- Detailed notes: `Knowledge-base/Claude/response.md`
- Related: `Knowledge-base/Claude/FQ.md` — the Withers, Olsen & Day (2015) paper this feature partially implements

## What it is

`response` is a single namelist string selecting the constitutive physics for a block: `elastic`, `plastic`, `anelastic`/`low-pass`, `anelastic-Q`, `anelastic-Q8`, `anelastic-Qf`, `constant-Q-4M`, `constant-Q-8M`, `frequency-Q-4M`, `frequency-Q-8M`. Validated once in `domain.f90` (invalid strings abort cleanly via MPI_FINALIZE+exit). Each anelastic variant is a GSLS (memory-variable) attenuation model with its own namelist group, per-point `Qp_inv`/`Qs_inv` arrays, and N=4 or N=8 relaxation mechanisms with 6 stress-component memory-variable arrays each.

`withers_tables.f90` is a faithful, correctly-implemented port of the referenced paper's Tables 1–2 (relaxation times + weight-fitting formulas for power-law Q(f)), extended with linear γ-interpolation.

## Headline finding: five of seven anelastic response modes are geometrically incomplete

The dominant bulk-interior RHS path (`RHS_Center` → the ~23,000-line generated stencil file `JU_xJU_yJU_z6.f90`, which covers the overwhelming majority of grid points) only implements attenuation for `anelastic`, `anelastic-Q`, and `anelastic-Q8` (verified via exhaustive grep — zero references to the other flags). `anelastic-Qf`, `frequency-Q-4M`/`8M`, and `constant-Q-4M`/`8M` are wired **only** into `RHS_near_boundaries`, a stencil-width-thin shell adjacent to each block face. Away from block faces — i.e. across most of any realistic domain — these five response options silently behave as pure `elastic`, despite passing input validation and fully allocating/initializing their memory-variable state. No warning is emitted.

## Other verified issues, by severity

| Issue | Where | Effect |
|---|---|---|
| Bulk-interior attenuation gap (above) | `JU_xJU_yJU_z6.f90` vs `RHS_Interior.f90` | 5 of 7 anelastic modes are non-functional outside a thin near-face shell |
| `constant-Q-4M`/`8M` weight methods mis-scale `target_Q` | `material.f90` (`compute_weights_nnls/withers/lookup` + kernel's `Qs_inv` multiply) | `'nnls'` (default) and `'lookup'` double-apply Q scaling (kernel multiplies already-absolute NNLS weights by an unrelated `c`-derived `1/Q` again); `'lookup'` also scales `∝ target_Q` where physics requires `∝ 1/target_Q`; `'withers'` silently ignores `target_Q` entirely. Net: delivered Q rarely matches the requested `target_Q`. |
| Duplicate dispatch call | `RHS_Interior.f90:257-258`, one near-face loop block only | `constant-Q-4M`/`8M` attenuation forcing applied ~2x in that one face region |
| 8M flags piggyback on 4M flags | `block.f90` + `material.f90` init routines | Works (verified by tracing call order), but is an order-dependent, `allocated()`-based dispatch trick rather than using the dedicated `anelastic_const_Q_8M`/`anelastic_Qf8` flags directly — fragile to future refactors |
| No `dt`/`τ_min` stability coupling | domain-wide | The memory-variable ODE is integrated with the same explicit RK scheme as wave fields (not the exact exponential update the reference method specifies for unconditional stability); `dt` is set purely from elastic CFL with no check against attenuation `τ_min` |
| `frequency-Q-4M` is a literal alias of `anelastic-Qf` | `block.f90:166-188` | Two namelist strings, one implementation — likely to confuse users |
| Dead `response` variable | `preprocessor.f90:16` | Declared, never used (preprocessor doesn't need attenuation) |

## What's solid

`elastic`, `plastic`, `anelastic`/`low-pass`, `anelastic-Q`, and `anelastic-Q8` are fully wired end-to-end (bulk interior + near-boundary + PML variants + RK integration of memory variables) and are the response options currently safe to rely on. `withers_tables.f90` is an accurate implementation of the underlying published method.

## Flag for cross-AI comparison

- **Topic class:** deep-dive into one subsystem (attenuation/`response`), not a full-codebase pass — complements `initial_report_Claude.md`.
- **Confidence:** high on all listed findings — each was verified by reading the actual subroutine bodies and tracing call sites/guard conditions across `block.f90`, `material.f90`, `fields.f90`, and both RHS files, not inferred from comments or naming alone.
- **Suggested priority if this feature is meant to ship:** (1) wire `anelastic-Qf`/`Qf8`/`const-Q-4M`/`8M` into `JU_xJU_yJU_z6.f90`'s bulk interior, (2) fix the `target_Q` double-scaling in `constant-Q-4M`/`8M`, (3) remove the duplicate dispatch call, (4) add a `dt` vs. `τ_min` stability check/warning.
