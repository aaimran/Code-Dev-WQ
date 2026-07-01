# Figure 5 (Withers, Olsen & Day 2015) — Test Specification and WaveQLab3D `response` Setup

**Built from:** `Knowledge-base/Claude/figure_3.md`, `figure_4.md` (shared setup), `Knowledge-base/Claude/FQ.md`, `Knowledge-base/Claude/response.md`.

## 1. What Figure 5 is

Caption: *"Half-space point-source test: comparison of f-k and FD results for a Q(f) model in which γ = 0.6."* Identical half-space, source, and receiver ("the same surface station as in Figures 3 and 4") as Figures 3–4, but now the medium has **frequency-dependent, power-law Q(f)** (Eq. 2): constant `Q0` below a transition frequency `fT=1 Hz`, then `Q(f) = Q0·(f/fT)^γ` above it. This is the paper's actual headline contribution — everything before this figure was either a pure-elastic check (Fig. 3) or the pre-existing constant-Q coarse-grained method (Fig. 4, already handled by Day & Bradley 2001).

## 2. What changes relative to Figure 4

| Parameter | Figure 4 | Figure 5 |
|---|---|---|
| `γ` (power-law exponent) | 0.0 | **0.6** |
| `Qs0`, `Qp0` | 50, 50 | 50, 50 (same reference values, now the *low-frequency plateau* value below `fT`) |
| Transition frequency `fT` | n/a | 1 Hz (paper default) |
| Weight source | Table 1 fit at `γ=0` | Table 1/2 fit at `γ=0.6`, `N=8`, using the interpolation formula (Eq. 16) rather than a single per-integer-Q solve |
| Reported accuracy | EM<6%, PM<2% | **EM<2%, PM<1%** — better than the constant-Q case, because there is more high-frequency energy that would otherwise be over-attenuated |
| Everything else (source, receiver, grid, domain) | — | unchanged |

## 3. `response` setup — and a blocking implementation gap

### 3.1 The structurally-correct choice is `anelastic-Qf8`, but it does not currently work outside a thin shell

Reproducing `γ≠0` requires one of the frequency-dependent variants: `anelastic-Qf`/`frequency-Q-4M` (N=4, aliases of each other) or `frequency-Q-8M` (N=8, internally `anelastic_Qf8`). `frequency-Q-8M` is the better match to the paper's `N=8` mechanism count and its `withers_tables.f90` weight source is a faithful, verified port of the paper's own Table 1/2 formulas (`response.md` §3) — in principle this is exactly the right tool.

**However**, `response.md` §4.4 documents a verified, severe bug: the bulk-interior RHS path (`RHS_Center` → `JU_xJU_yJU_z6.f90`, which covers the overwhelming majority of grid points in any domain larger than a few cells) has **zero** handling for `anelastic_Qf`/`anelastic_Qf8` — grepping that ~23,000-line file for those flags returns no matches. Attenuation for this response family is only applied in `RHS_near_boundaries`, a stencil-width-thin shell adjacent to each of the block's six logical faces. **A domain built at the scale implied by Figure 5 (a half-space large enough that no boundary reflection reaches a receiver 15 km away within ~6–7 s) would have this thin shell many hundreds of grid points away from both the source and the receiver** — meaning the memory-variable state would never accumulate any signal along the source-to-receiver ray path, and the resulting synthetic would be indistinguishable from the pure-elastic Figure 3 result, not the attenuated Figure 5 result.

**This means Figure 5 cannot currently be validly reproduced with this codebase as-is.** Configuring `response='frequency-Q-8M'` will run without error, allocate and correctly initialize all the Q(f) state (weights, relaxation times, per-point `Qs_inv`/`Qp_inv`), and silently produce elastic-only output.

### 3.2 Configuration to use once/if the bulk-interior gap is fixed

For completeness — this is what the input file should contain once `response.md`'s §4.4 finding is addressed (i.e., `anelastic_Qf`/`anelastic_Qf8` handling is added to `JU_xJU_yJU_z6.f90`):

```fortran
&problem_list
  ... (as in figure_3.md/figure_4.md, unchanged) ...
  response = 'frequency-Q-8M'
/

&anelastic_Qf8_list
  c       = 0.014434_wp   ! Qs = c*Vs = 50 (same c as figure_4.md; note Qp=2*Qs=100 gap applies here too, see below)
  gamma   = 0.6_wp         ! matches paper's power-law exponent
  f_trans = 1.0_wp         ! transition frequency, matches paper's fT=1 Hz
  fref    = 1.0_wp
/
```

The same `Qp0 = 2·Qs0` hardcoding documented in `figure_4.md` §3.2 applies identically here (`material.f90:1784`, `Qp_inv_Qf8 = 0.5·Qs_inv_Qf8`) — the paper's `Qp0=Qs0=50` cannot be set exactly regardless of the bulk-interior gap being fixed.

A lower-fidelity `N=4` fallback (`response='anelastic-Qf'` or the identical alias `'frequency-Q-4M'`, `&anelastic_Qf_list` with the same four fields) is available but subject to the identical bulk-interior gap.

### 3.3 Everything else

Domain, grid, moment-tensor source, `'cosine'` source-time function, receiver location, `t_final`, and external post-processing (0.2–10 Hz Butterworth, R/T/Z rotation, f-k comparison) are unchanged from `figure_3.md`/`figure_4.md`.

## 4. Summary checklist to reproduce Figure 5

1. Start from the Figure 3/4 configuration.
2. **Before running:** confirm whether `JU_xJU_yJU_z6.f90` has been updated to handle `anelastic_Qf`/`anelastic_Qf8` in the bulk interior (per `response.md` §4.4) — as of this analysis pass it has not, and the test below will silently produce elastic-only results.
3. `response = 'frequency-Q-8M'`, `&anelastic_Qf8_list` with `c≈0.014434`, `gamma=0.6`, `f_trans=1.0`.
4. Accept the same `Qp0=2·Qs0` discrepancy noted for Figure 4.
5. Everything else unchanged from Figures 3/4.
6. Expected result if the bulk-interior gap is fixed and the `Qp0` discrepancy doesn't materially affect the comparison: EM<2%, PM<1%, with visibly more high-frequency (>1 Hz) energy retained relative to the Figure 4 constant-Q case.
