# Claude Summary: Withers, Olsen & Day (2015) — Memory-Efficient Simulation of Frequency-Dependent Q

## Source

- File: `Knowledge-base/Common/FQ.pdf`
- Citation: Withers, K. B., K. B. Olsen, and S. M. Day (2015), *Bull. Seismol. Soc. Am.*, 105(6), 3129–3142, doi:10.1785/0120150020.
- Detailed notes: `Knowledge-base/Claude/FQ.md`

## One-line summary

Extends Day & Bradley's (2001) memory-efficient "coarse-grained" memory-variable method — previously limited to constant Q — to support a **power-law, frequency-dependent Q(f)**, fit with only `N=8` relaxation mechanisms per node and a simple analytic interpolation formula, then validates it against an `f-k` semi-analytical solver and applies it to the 2008 Mw 5.4 Chino Hills earthquake.

## Core method

| Element | Description |
|---|---|
| Target Q model | `Q(f)=Q0` below transition `fT`, `Q(f)=Q0·(f/fT)^γ` above it (Eq. 2), `γ∈[0,0.9]`, `fT=1 Hz` |
| Mechanism count | `N = 8` relaxation times, log-uniformly spaced (Eq. 15) |
| Weight fitting | Nonnegative constrained least squares (conjugate gradient) per integer Q in [15,220] |
| Reusable fit | Analytic formula `λk = ak/Q² + bk/Q` (Eq. 16), accurate to ~5%, avoids re-solving the inversion at runtime |
| Storage trick | "Coarse-grained" — one relaxation time per grid node, cycled with a fixed spatial period, instead of N full memory-variable fields per node (Day, 1998; Day & Bradley, 2001) |
| Implementation | 4th-order-space / 2nd-order-time staggered-grid velocity-stress FD code (Cui et al., 2010) |

## Validation

- f-k vs. FD comparison, double-couple point source, half-space and layered models.
- Elastic case: near-exact match. Constant-Q (`γ=0`): envelope misfit (EM) < 6%, phase misfit (PM) < 2%. Power-law Q (`γ=0.6`): EM < 2%, PM < 1%. Layered/sharp-contrast case: EM 5–10%, PM 1–2% (coarse-graining limitation at discontinuities, consistent with prior literature).

## Application & result (Chino Hills Mw 5.4, 2008)

- 56×40×24 km domain, 8 m grid spacing, resolves to ~4 Hz, SCEC CVM v4 velocity model, 110 strong-motion stations.
- Compared `γ=0.0` (constant Q) vs. `γ=0.8` (regional upper bound, Song & Jordan 2013).
- **Result: constant-Q under-predicts amplitude/energy by a factor of 3–5 at distances > 25 km from the fault**, relative to both data and the power-law model; near-fault (<25 km) misfit is dominated by source/site effects, not the Q model.
- Conclusion: Q(f) materially matters for ground-motion prediction above ~1 Hz; constant-Q assumption breaks down at distance and high frequency.

## Relevance to this repo's WaveQLab3D code (`Claude/WQ/src/`)

WaveQLab3D's current material/constitutive modules (`material.f90`, `plastic.f90`, `plastic_material.f90`) showed no memory-variable/Q handling in the source review (see `Knowledge-base/Claude/initial_report.md`). This paper is the natural reference if anelastic attenuation is ever added to that solver:

- Stress-update addition is small: one extra memory-variable array per stress component (coarse-grained) plus one exponential ODE update per step (Eq. 5) — would slot into the existing stress-rate evaluation in `RHS_Interior.f90`/`time_step.f90`.
- The coarse-grained, single-relaxation-time-per-node storage scheme is well suited to a code already structured around per-node curvilinear SBP-SAT stencils, since it avoids an `N×` blow-up in stress-field storage.
- Provides a ready-made empirical default (`Qs0 = 0.1·Vs`, `Qp0 = 2·Qs0`) for bootstrapping a Q model from existing Vs/Vp material fields.

## Flag for cross-AI comparison

- **Topic class:** numerical method paper (not source code) — informs a *potential future feature* (frequency-dependent attenuation) rather than describing current repo behavior.
- **Confidence:** high — content directly transcribed/summarized from the 14-page PDF, equations and figures cross-checked against page text.
- **Open question for the team:** whether attenuation/Q is in scope for this project's WaveQLab3D variant at all; if not, this remains reference-only material.
