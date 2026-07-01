# Figure 4 (Withers, Olsen & Day 2015) — Test Specification and WaveQLab3D `response` Setup

**Built from:** `Knowledge-base/Claude/figure_3.md` (shared setup), `Knowledge-base/Claude/FQ.md`, `Knowledge-base/Claude/response.md`, and direct reading of `Claude/WQ/src/material.f90`.

## 1. What Figure 4 is

Caption: *"Half-space point-source test: comparison of f-k and FD results for a constant Q model with γ = 0.0."* Same source, receiver, and elastic half-space geometry as Figure 3 (see `figure_3.md` §2–3 for the full unchanged setup), but now the medium is **viscoelastic** with a frequency-independent (`γ=0.0`) target Q. This is the first figure that actually exercises the paper's memory-variable weight-fitting machinery (Eqs. 3–14).

## 2. What changes relative to Figure 3

| Parameter | Figure 3 (elastic) | Figure 4 (this figure) |
|---|---|---|
| Q model | infinite (none) | Constant Q, power-law exponent `γ = 0.0` (Eq. 2 reduces to `Q(f)=Q0` for all `f`) |
| `Qs0`, `Qp0` | n/a | **Both set to 50** — paper states `Qs0 = Qp0 = 50` (text preceding Fig. 4) |
| Weight source | n/a | `N=8` mechanisms, weights from Table 1/Eq. 8 (nonnegative least-squares fit at `γ=0`), reused across bulk and shear since `γ` and (implicitly) the shape match |
| Reported accuracy | near-exact | envelope misfit (EM) < 6%, phase misfit (PM) < 2%, all 3 components (Kristekova et al. 2009 criteria) |
| Everything else (source, receiver, grid, `dt`, domain sizing) | — | **unchanged** from Figure 3 |

The paper notes this Fig. 4 fit is *better* than simply setting all `N=8` weights equal (the naive Day & Bradley 2001 approach) — i.e., the optimized-weight fit is specifically what's being validated here.

## 3. `response` setup

### 3.1 Which `response` value to use — and an important limitation

Per `response.md` §4.4, only three anelastic variants are fully wired end-to-end (bulk interior **and** near-boundary): `anelastic`/`low-pass`, `anelastic-Q`, `anelastic-Q8`. All three are constant-Q (`γ=0`) by construction — none of them take a `γ` namelist parameter — so any of them is structurally the right category for Figure 4. **`anelastic-Q8`** is the best match: it uses `N=8` mechanisms (matching the paper's `N=8` exactly) with weights the code's own comments describe as "NNLS-fitted weights for gamma=0 (constant-Q)... max Q error < 5%, mean < 0.1%" over `[0.05, 20]` Hz (`material.f90:363-364`) — i.e., this specific response mode was *already* built and documented as a constant-Q reproduction in the spirit of this exact figure. `anelastic-Q` (N=4) is a lower-fidelity fallback if a 4-mechanism budget is required, with a wider stated error (`max Q error < 18%`, `material.f90:235`).

```fortran
&problem_list
  ... (as in figure_3.md, unchanged) ...
  response = 'anelastic-Q8'
/

&anelastic_Q8_list
  c    = 0.014434_wp   ! Qs = c * Vs  ->  c = target_Qs / Vs = 50 / 3464 ≈ 0.014434
  fref = 1.0_wp         ! reference frequency for unrelaxed-modulus correction, matches paper's f0=1 Hz
/
```
(`anelastic_Q_list` has the identical two fields if using `anelastic-Q` instead.)

### 3.2 A genuine gap: this code cannot set `Qp0 = Qs0`

`material.f90` hardcodes `Qp_inv = 0.5·Qs_inv` (i.e. `Qp = 2·Qs`) **identically in all seven anelastic `response` variants** (verified at `material.f90:81, 218, 347, 503, 1261, 1658, 1784`) — this is not exposed as a namelist option anywhere. The paper's Figure 4 setup explicitly uses `Qs0 = Qp0 = 50` (equal P- and S-wave Q, not the 2:1 ratio this code always applies). Setting `c` to hit `Qs=50` via `anelastic-Q8` will therefore give `Qp=100` in this code, not the paper's `Qp0=50`. This is a real, currently-unavoidable discrepancy for an exact reproduction of Figure 4 (and, as detailed in `figure_5.md`/`figure_6.md`, applies equally there) — it was not previously flagged in `response.md` and should be added there as a known gap if this attenuation feature set is worked on further. A byte-exact reproduction would require either a code change (exposing `Qp0` independently of `Qs0`) or accepting the 2:1 ratio as a deliberate deviation and noting the expected effect on P-wave-sensitive misfit metrics.

### 3.3 Everything else

Domain, grid, source (moment tensor + `'cosine'` source-time function), receiver, `t_final`, and post-processing (0.2–10 Hz zero-phase Butterworth, R/T/Z rotation, external f-k comparison) are all identical to `figure_3.md` §3.2–3.5 — only the `response`/`&anelastic_Q8_list` block above needs to be added on top of that setup, with `response` changed from `'elastic'` to `'anelastic-Q8'`.

## 4. Summary checklist to reproduce Figure 4

1. Start from the Figure 3 configuration (`figure_3.md`).
2. Change `response = 'anelastic-Q8'` (or `'anelastic-Q'` for a lower-fidelity 4-mechanism run).
3. Add `&anelastic_Q8_list` with `c` chosen so `Qs = c·Vs = 50` (`c ≈ 0.014434` for `Vs=3464 m/s`); accept that this code will produce `Qp=100`, not the paper's `Qp0=50` (documented gap, §3.2).
4. Everything else — source, receiver, grid, filtering, external f-k comparison — unchanged from Figure 3.
5. Expect (per the paper, if the `Qp0` discrepancy above doesn't matter for the comparison metric used) EM < 6%, PM < 2%.
