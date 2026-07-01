# Claude Summary: Figure 5 (Withers et al. 2015) Test Setup + WaveQLab3D `response` Mapping

## Source

- Built from: `Knowledge-base/Claude/figure_3.md`, `figure_4.md`, `response_Claude.md`
- Detailed spec: `Knowledge-base/Claude/figure_5.md`

## What Figure 5 is

Same half-space/source/receiver as Figures 3–4, now with **power-law, frequency-dependent Q(f)**: `γ=0.6`, `Qs0=Qp0=50`, transition frequency `fT=1 Hz` (paper's Eq. 2). This is the paper's headline result — better accuracy than constant-Q (EM<2%, PM<1% vs. Fig. 4's EM<6%, PM<2%) because high-frequency energy is no longer over-attenuated.

## `response` setup — blocked by a known bug

Structurally correct choice: **`response='frequency-Q-8M'`** (`N=8`, matches the paper; its weight table in `withers_tables.f90` is a verified, faithful port of the paper's own formulas). But **this cannot currently produce valid results**: per `response_Claude.md`'s headline finding, `anelastic-Qf`/`anelastic-Qf8` attenuation is wired only into a thin near-boundary shell (`RHS_near_boundaries`), never into the bulk-interior code (`JU_xJU_yJU_z6.f90`) that covers the vast majority of a domain's grid points. For a domain sized to avoid boundary reflections at a 15 km receiver (as Fig. 3–5 require), the source-to-receiver path runs entirely through the untreated bulk interior — the run would silently produce elastic-only output indistinguishable from Figure 3, with no warning.

**Figure 5 is not currently reproducible with this codebase until that bulk-interior gap is fixed.**

Intended configuration once fixed:
```fortran
response = 'frequency-Q-8M'
&anelastic_Qf8_list
  c = 0.014434, gamma = 0.6, f_trans = 1.0, fref = 1.0
/
```
The same `Qp0=2·Qs0` hardcoding noted in `figure_4_Claude.md` applies here too (universal across all 7 anelastic variants) — paper wants `Qp0=Qs0=50`, code always gives `Qp=2·Qs`.

## Everything else

Domain, grid, moment-tensor source, `'cosine'` source-time function, receiver, and external post-processing unchanged from Figures 3/4.

## Flag for cross-AI comparison

- **Confidence:** high on the blocking-bug conclusion (directly re-derived from `response_Claude.md`'s verified finding, applied to this specific test's domain-scale requirement) and on the `Qp0` gap (verified in `material.f90`). This is the first figure in the series where the implementation gap actually prevents a valid reproduction, not just an exact-value mismatch.
