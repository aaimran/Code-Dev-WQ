# Comparison: Claude/WQ/src/ vs Codex/WQ/src/ vs Gemini/WQ/src/

**Method:** direct `diff` of the three `src/` trees (not independent re-analysis) — all three share an almost byte-identical baseline (same `response` system, same 11 response options, even identical bug-fix comments in `material.f90`), so the meaningful comparison is in what each AI actually *changed* relative to that shared baseline, specifically around the `anelastic-Q8` `Qp0`/`Qs0` fix from this session (see `Knowledge-base/Claude/response.md`, `figure_4.md`).

## 1. File-level diff summary

| Comparison | Files with differences | File count identical |
|---|---|---|
| Claude vs Codex | `material.f90` (152 diff lines), `datatypes.f90` (3 diff lines) | all other 41 files byte-identical; identical file listing (43 files each) |
| Claude vs Gemini | `material.f90` (17 diff lines — this is just "my fix vs. no fix", not an independent Gemini change) | all other matching files byte-identical; **Gemini has 3 extra files** not present in Claude/Codex: `attenuation_mod.f90` (41 lines), `config_mod.f90` (50 lines), `main.f90.new` (30 lines) |

None of the three touched `RHS_Interior.f90`, `JU_xJU_yJU_z6.f90`, `block.f90`, or `fields.f90` — meaning none of them addressed the bulk-interior attenuation gap, the duplicate-dispatch bug, or the `constant-Q-4M`/`8M` `target_Q` double-scaling bug documented in `response.md` §4.4–4.6. All observed work across all three AIs is scoped to the single `anelastic-Q8` `Qp0=2·Qs0` issue.

## 2. Claude's fix (this session)

`material.f90::init_anelastic_Q8_properties` — added optional `cp` namelist field: `Qp = cp·Vp`, sentinel default `cp=-1.0` falls back to legacy `Qp=2·Qs`. Minimal diff, preserves the existing "proportionality-constant tied to local velocity" convention used by `c`/`Qs`. No new input validation added. Verified via an isolated standalone syntax/logic check (full project build was not achievable in this environment — see §5) plus a numeric check confirming `Qs=Qp=50` is achieved for Figure 4's target values, versus the forced `Qp=100` before the fix.

## 3. Codex's fix — more thorough, catches an accuracy issue Claude missed

`datatypes.f90`: adds `Qs0_Q8`, `Qp0_Q8`, `explicit_Q8` fields to `block_material`.
`material.f90::init_anelastic_Q8_properties`: ~150 changed lines, substantially more than the minimum needed to fix `Qp0`/`Qs0`:

- **Interface choice:** exposes `Qs0`/`Qp0` as direct absolute-value namelist parameters (not proportionality constants like `c`/`cp`) — when both are positive, `Qs_inv = 1/Qs0`, `Qp_inv = 1/Qp0` are applied *uniformly* across the domain, abandoning per-point velocity scaling in that mode. Falls back to the legacy `c`-based, velocity-scaled mode only when `Qs0`/`Qp0` are omitted. This is a materially different design decision than Claude's `cp` approach: simpler and more directly matches "set Q to this number," at the cost of losing spatial variation with local velocity in heterogeneous media when used.
- **Input validation added:** rejects `Qs0`/`Qp0` ≤ 0 (must both be set together), rejects non-positive `mu`/`rho` at any point, rejects the legacy `c` ≤ 0, rejects `fref` ≤ 0 — all via the codebase's existing `error()`/`warning()` utilities (`mpi3dbasic`), consistent with existing idiom.
- **Catches a genuine unhandled failure mode:** checks `val_S`/`val_P` (the weight/Q sum in the unrelaxed-modulus correction) `< 1`, calling `error()` if violated — this guards against a case that would otherwise silently produce a negative or nonsensical unrelaxed modulus. **Neither the original baseline nor Claude's fix checks this.**
- **Re-fit the 8 `weight_Q8` values themselves** (2 of 8 are now exactly `0.0`; all 8 changed from the shared baseline), with a new comment stating the fit is "optimized at Q=50 over [0.08, 15] Hz" — a materially different claim than the baseline's comment ("Q0*=1... scale by 1/Q_S at runtime... max Q error < 5%, mean < 0.1%," implying general-purpose validity via linear rescaling). Per the reference paper analyzed in `FQ.md` §2, linear rescaling from a Q0*=1 reference is only accurate for **Q > 200**; Figure 4's target is Q=50, well inside the regime the paper says requires the nonlinear low-Q correction (Eqs. 9–14, Table 2). Codex's refit appears to be a direct response to this — optimizing specifically for the Q≈50 regime this feature is actually being used for, rather than trusting the inherited high-Q-oriented weights.
- **Adds a runtime self-check**, `q8_max_relative_error`: numerically evaluates the actual GSLS `Q(f)` response (`Q_model = |Re(M)/Im(M)|` swept over `[0.08,15] Hz`) against the target `Q`, and calls `warning()` if realized error exceeds 5%. This means Codex's version will **tell the user at runtime** if a chosen `Qs0`/`Qp0` falls outside the validity range of the fixed 8-mechanism weight set — something neither the original baseline nor Claude's fix does at all.
- Adds diagnostic `write` output on master rank echoing the configured `Qs0`/`Qp0`/`fref`, the resulting `tau`/`weight` arrays, and the measured max Q error.

**Assessment:** Codex's fix is a genuine superset of Claude's in rigor — same core problem solved, plus real input validation, plus (the most valuable addition) a runtime accuracy check that catches a subtlety about the paper's stated Q>200 validity range for linear weight rescaling that Claude's session did not independently verify (it took the inherited "<5% error" comment at face value). Codex's own `response.md` (written earlier, listing `anelastic-Q8` as "Operational but untested") does not reflect this later fix, suggesting it was made in a follow-up pass after the initial report, similar to how this fix emerged mid-session for Claude too.

## 4. Gemini's contribution — an unwired, non-functional sketch, not a fix

`material.f90` is **unchanged** from the pre-fix baseline — Gemini did not address the `Qp0`/`Qs0` issue in the actual code path at all. Instead, three new files were added:

- **`config_mod.f90`** (50 lines): defines a `config_t` derived type (`response`, `iord`, `ifault`, `Qp_inv`, `Qs_inv`, `Q_op_f_trans`, `Q_op_gamma`) and two subroutines. `config_read()` is a stub — it only `PRINT *`s `"Reading configuration..."` and does not open a file, read any namelist, or populate `cfg`. `config_validate()` has exactly one real check (`Qs_inv <= 0` for `constant-Q-8M`).
- **`attenuation_mod.f90`** (41 lines): `attenuation_init()` only prints the configuration values already read (nothing is computed — no weights, no relaxation times, no memory-variable array allocation). `attenuation_update_constant_q_8m()` and `attenuation_update_frequency_q_8m()` are **empty subroutines** with a comment: `! Actual implementation of memory variable updates ... goes here.`
- **`main.f90.new`** (30 lines): a from-scratch, simplified alternate `main` program illustrating the intended call sequence (`config_read` → `config_validate` → `attenuation_init` → conceptual time loop). Does not initialize MPI, does not call `init_domain`, and its "main time loop" is entirely commented-out pseudocode.

None of these three files appear in `CMakeLists.txt`'s `WQL3D_SRC` list — they are not part of the build at all. Beyond being incomplete, they would **fail to compile** if added: both `config_mod.f90` and `attenuation_mod.f90` declare `USE datatypes, ONLY: real_wp`, but `real_wp` is not defined anywhere in Gemini's (or Claude's/Codex's, since this file is identical across all three) `datatypes.f90` or `common.f90` — the actual kind parameter used throughout this codebase is `wp`, not `real_wp`.

**Context from Gemini's own `response.md`:** its "Modernization and Refactoring Plan" (step 2) explicitly proposes "Create a Configuration Module (`config_mod`...)" as a *future* recommendation within a larger refactor. The three orphaned files are evidently a rough proof-of-concept sketch of that proposal, not an attempt to fix the specific `Qp0`/`Qs0` bug that was the actual task at hand this session.

**Assessment:** this is architecturally interesting as a direction (splitting configuration and attenuation physics into dedicated modules is a reasonable idea, and is consistent with `response.md`'s own critique of the current design's fragility), but it delivers zero functional improvement to the actual attenuation system, adds three new dead files to the tree, and one of them (`main.f90.new`) sits right next to the real `main.f90` in a way that could confuse a future maintainer about which is authoritative.

## 5. Build/verification notes (applies to all three; a shared environment constraint, not a code-quality finding)

A full project build was not achievable via plain `mpif90`/`mpiifort` in this session's environment: the Intel oneAPI `mpif90` wrapper here has a bug causing infinite self-recursion when probed by CMake (`mpif90 --version` spawning another `mpif90 --version`, and so on) — this was hit and resolved by killing the specific process group it spawned under (`kill -9 -<pgid>`), with no impact outside that group. A separate, working toolchain was later discovered via the project's own run script (`jakar.sh`): `module load compiler-rt/2024.0.0 ifort/2024.0.0 mpi/2021.13`. Claude's fix was verified via isolated logic/syntax checks with plain `gfortran` instead (full dependency-chain compilation blocked by an unrelated, pre-existing strict-interface-checking issue in `mpi3dio.f90` under gfortran's modern `use mpi` module). Codex's and Gemini's changes were not independently build-tested in this pass — assessed by direct source reading only.

## 6. Bottom line, ranked

1. **Codex** — best delivered fix: same core problem solved as Claude's, plus real input validation, plus a runtime accuracy self-check that catches a genuine subtlety (linear Q-rescaling validity range) neither Claude's fix nor the original code addressed.
2. **Claude** — correct, verified (in isolation) fix, but thinner: no input validation, no runtime accuracy check, did not re-examine whether the inherited weight table is actually valid at the Q=50 regime the feature is used for.
3. **Gemini** — no working fix delivered. Three new files are unwired into the build and would not compile if they were (undefined `real_wp` symbol). Represents an abandoned/proof-of-concept architectural sketch, not a bug fix.

All three leave the larger issues identified in `response.md` (bulk-interior attenuation gap for 5 of 7 response modes, the duplicate-dispatch bug, the `constant-Q-4M`/`8M` `target_Q` double-scaling bug) completely untouched.
