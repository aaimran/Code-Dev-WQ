# Paper Notes: Memory-Efficient Simulation of Frequency-Dependent Q

**Source:** `Knowledge-base/Common/FQ.pdf`
**Citation:** Withers, K. B., K. B. Olsen, and S. M. Day (2015), Memory-Efficient Simulation of Frequency-Dependent Q, *Bulletin of the Seismological Society of America*, 105(6), 3129–3142, doi:10.1785/0120150020.
**Authors' affiliation:** San Diego State University, Dept. of Geological Sciences.

## 1. Problem statement

Anelastic attenuation in numerical wave propagation is conventionally implemented with the memory-variable method, approximating a target quality factor `Q` by a discrete sum of relaxation mechanisms (Day and Minster, 1984; Emmerich and Korn, 1987). Most prior work fixes `Q` to be **frequency-independent**, which is a reasonable approximation only below roughly 1 Hz. Observations (Liu et al., 1976; Erickson et al., 2004; Phillips et al., 2013) show `Q` increasing with frequency above ~1 Hz, commonly modeled as a power law:

```
Q(f) = Q0 * (f / f0)^γ                                   (1)
```

with `Q0`, `f0` reference values and exponent `γ` (region/geology dependent; e.g., California `γ ≈ 0.6–0.7`, eastern US `γ ≈ 0.3–0.4`). As simulations push to higher frequencies (toward ~10 Hz) for physics-based ground-motion and seismic-hazard work, a frequency-independent `Q` becomes inadequate, but conventional memory-variable methods scale storage/compute linearly with the number of relaxation mechanisms `N`, which is expensive in large 3-D runs.

**Goal of the paper:** extend the *memory-efficient, coarse-grained* memory-variable technique (Day, 1998; Day and Bradley, 2001) — originally built for constant `Q` — to support a target `Q(f)` that is constant below a transition frequency `fT` and follows a power law above it:

```
Q(f) = Q0                  for 0 < f < fT
Q(f) = Q0 * (f/fT)^γ       for f > fT                     (2)
```

## 2. Background: the conventional memory-variable formalism

- Stress relates to strain through `N` memory variables `ξk(t)`:
  `σ(t) = Mu[ε(t) − Σ_{k=1}^{N} ξk(t)]`                    (3)
- Each memory variable obeys a first-order ODE with relaxation time `τk` and weight `λk`:
  `τk dξk/dt + ξk(t) = λk ε(t)`                              (4)
- Exact time update over a step `δt` (Day, 1998):
  `ξk(t+δt) = e^(−δt/τk) ξk(t) + λk(1 − e^(−δt/τk)) ε(t)`     (5)
- Complex modulus: `M(ω) = Mu(1 − Σ λk/(1+iωτk))`            (6)
- `Q^-1(ω) = Im[M(ω)]/Re[M(ω)]`                               (7)
- Low-loss approximation (valid `Q ≳ 20`, assumes `δM ≪ Mu`):
  `Q^-1(ω) = Σ λk ωτk / (1+(ωτk)^2)`                          (8)

For low `Q` (< 200), the paper uses an "effective Q" via the coarse-grained harmonic average of moduli over the coarse cell (Eqs. 9–14), following Graves and Day (2003), who showed harmonic averaging is more accurate than Eq. 6 directly when `Q < 200`.

The **coarse-grained** approach (Day, 1998; Day and Bradley, 2001) distributes the `N` relaxation mechanisms spatially across a periodic unit cell instead of storing all `N` memory variables at every grid node — i.e., each node carries only **one** relaxation time, cycling through `N` distinct values with a fixed spatial period. This is what makes the method "memory efficient": storage and compute scale with `N` only once per period, not per node.

## 3. New contribution: fitting weights for a power-law Q(f)

1. **Relaxation times** are spaced **log-uniformly** between a minimum `τm` and maximum `τM` (the absorption-band limits):
   `ln τk = ln τm + (2k−1)/16 * (ln τM − ln τm)`             (15)
   Best fits occur when `τm`/`τM` (i.e., the absorption band) extend **outside** the bandwidth of computational interest.
2. **Weights `λk`** are found by **nonnegative constrained least squares** (conjugate-gradient method) fitting Eq. 8 (or the effective-Q form, Eq. 11–14, for low Q) to the target `Q(f)` of Eq. 2, for every integer `Q` from **15 to 220**, for each of several power-law exponents `γ ∈ {0.0, 0.1, ..., 0.9}`, using `N = 8` mechanisms.
   - Weights must be nonnegative for thermodynamic stability (energy dissipation), and bounded so their sum is < 1.
   - `γ > 1` is impossible (`Q^-1` cannot fall off faster than `ω` given the Debye-peak shape), so the practical range is `γ ∈ [0.0, 0.9]`.
3. **Analytic interpolation formula** so coefficients don't need to be tabulated/inverted for every possible Q: fit
   `λk = ak/Q² + bk/Q`                                       (16)
   The `ak`, `bk` coefficients (Table 2) reproduce the per-Q least-squares weights to within 5% (often better) over `0.1–10 Hz`.
4. The chosen transition is `fT = 1 Hz`, with a smoothing transition region `0.8–1.2 Hz` where the spectrum is itself a (gentler, `γ/2`) power law, because a sharp kink is not well represented by the superposition of Debye peaks. This keeps the fit within ~5% across the full band (Fig. 1, Fig. 2).
5. **Reusing weights across bulk and shear attenuation:** if `Qκ` and `Qμ` (bulk and shear `Q`) share the same `γ` (only differ in `Q0`), the *same* set of weights can be reused for both, scaled by their respective `Q0` (valid for `Q > 200`; for `Q < 200`, or differing spectral shapes, separate weight sets are required) — see Eqs. 17–19.
6. Tables in the paper:
   - **Table 1**: `τm`, `τM`, and `w1..w8` (`= N·λk`, `N=8`) for `γ = 0.0` to `0.9`, normalized to `Q0* = 1` (scalable to any `Q0 > 20` by linear scaling).
   - **Table 2**: interpolation coefficients `ak`, `bk` (k=1..8) for Eq. 16, valid for `Q` in `[15, 220]`.
   - **Table 3**: example two-layer velocity model used for verification (Vp, Vs, ρ, Qp0, Qs0, γ, thickness).

## 4. Numerical implementation

- Implemented in a **4th-order-in-space, 2nd-order-in-time, staggered-grid velocity-stress finite-difference code** (Cui et al., 2010), using Day and Bradley's (2001) coarse-grained scheme with relaxation-time periodicity of 2 nodes per dimension (`N = 2³ = 8` for full 3-D periodicity).
- Memory variables `ξij` are collocated with stress components `σij`.
- Verification source: buried double-couple point source, strike 90°, dip 90°, rake 0°, cosine-bell moment-rate time function (Eq. 20), `Mw ≈ 4.6` (`M0 = 10^16` N·m, `T = 0.2 s`), grid spacing 40 m, time step 0.002 s.
- Verified against a **frequency–wavenumber (f-k) semi-analytical code** (modified from Zhu and Rivera, 2002) for:
  - Elastic (infinite Q) half-space — near-exact agreement (Fig. 3).
  - Constant-Q half-space (`γ=0.0`, `Q0=50`) — EM (envelope misfit) < 6%, PM (phase misfit) < 2% (Fig. 4), using the Kristekova et al. (2009) time–frequency misfit criteria.
  - Power-law Q half-space (`γ=0.6`, `Q0=50`) — even better fit (EM < 2%, PM < 1%) (Fig. 5).
  - Layered model with strong Q and velocity contrast (`Qs0 = 20` shallow layer over `Qs0 = 210` half-space, `γ=0.6`) — EM 5–10%, PM 1–2%, slightly worse for later surface-wave arrivals, attributed to the coarse-grained cell not resolving sharp discontinuities perfectly (Fig. 6; consistent with known coarse-grained limitations per Kristek and Moczo, 2003).

## 5. Application: 2008 Mw 5.4 Chino Hills, California earthquake

- Finite-fault source model adapted from Shao et al. (2012) (inversion of local earthquake records, reliable only to ~2.5 Hz per Taborda and Bielak, 2014, though run here to higher frequency anyway).
- Velocity model: SCEC Community Velocity Model v4 (Magistrale et al., 2000; Kohler et al., 2003), `Vs` floor 200 m/s, `Vp` floor 600 m/s.
- `Q0` tied to `Vs`: `Qs0 = Vs * 0.1`, `Qp0 = 2*Qs0` (`Vs` in km/s) — guarantees `Q0 > 20` (method's required lower bound).
- Domain: 56 km (E–W) × 40 km (N–S) × 24 km deep, grid spacing 8 m, resolves up to ~4 Hz (6.25 points per minimum shear wavelength). Cerjan sponge-zone absorbing boundaries.
- Two end-member runs compared against 110 strong-motion stations (data from the Center for Engineering Strong Motion Data): `γ = 0.0` (constant Q) vs. `γ = 0.8` (upper estimate from Song and Jordan, 2013, for southern California).
- **Findings:**
  - The two models diverge above ~1 Hz as expected (Fig. 8), with `Q(f)` carrying more high-frequency energy, especially in the coda.
  - Near the fault (< 25 km rupture distance) the choice of Q model matters less — misfit there is dominated by source/site-effect inaccuracies.
  - At larger distances (> 25 km), constant-`Q` synthetics systematically under-predict amplitude/energy by a factor of **3–5** relative to both the data and the `γ=0.8` model (Figs. 9–12 — cumulative energy, spectral acceleration at 3 s and 0.4 s periods, Fourier amplitude at 3.5 Hz).
  - The `γ=0.8` power-law model consistently tracks observed amplitude decay with distance better than constant Q, particularly at higher frequencies and shorter periods.
  - It is **not** clear from individual-station comparisons alone which model is "right" — the statistical/aggregate (distance-binned) comparison is what reveals the systematic difference.

## 6. Discussion and limitations (as stated by the authors)

- Q-spectrum fits are accurate to within 5% across 2–3 decades of bandwidth, for both half-space and layered verification cases (body and surface waves).
- Practical lower bound `Q = 15` chosen so the rapid low-Q coefficient variation can still be fit by the simple interpolation formula; this is not a fundamental limit but covers "almost all regions except very-low-velocity sediments."
- Thermodynamic constraint: sum of `λk` (point-wise) or `wk` (coarse-grained) must stay below 1 to guarantee positive `Q` everywhere.
- The method is general: usable with conventional (every-node) or coarse-grained memory-variable storage, and is compatible with other grid types (structured/unstructured) and methods (finite-difference, finite-element, spectral-element) as long as the coarse-graining periodicity stays below half the shortest wavelength of interest.
- Storage cost: only `3N` coefficients (24 numbers for `N=8`) must be tabulated/stored per `Q(f)` model — the rest is computed by the linear-scaling and interpolation formulas, making this attractive for memory-constrained hardware (the authors explicitly mention GPUs as a future consideration once memory becomes less constrained, at which point a simpler/non-coarse-grained interpolation scheme might become preferable).
- Open issues / future work flagged by the authors:
  - Disentangling **intrinsic attenuation** (this paper's focus) from **scattering attenuation** due to unresolved small-scale heterogeneity — both lengthen the coda and may trade off against each other in any given `Q0`/`γ` fit to data.
  - Including **nonplanar topography**, expected to also influence high-frequency scattering.
  - Regional calibration of `Q0` and `γ` against velocity, lithology, and tectonic setting.
  - Whether the frequency-dependent attenuation parameter `κ` (Anderson and Hough, 1984, high-frequency spectral decay) is itself explained by `Q(f)` depth variation — left open.

## 7. Why this is relevant to the WaveQLab3D codebase

This is background literature on a technique for adding **memory-efficient frequency-dependent anelastic attenuation (Q(f))** to a finite-difference earthquake-rupture/wave-propagation solver — the same problem class addressed by `Claude/WQ/src/material.f90`, `plastic.f90`/`plastic_material.f90`, and the RHS/stress-update modules (`RHS_Interior.f90`, `Interface_Condition.f90`) in this repository's WaveQLab3D code. WaveQLab3D as currently analyzed (see `initial_report.md`) does not appear to implement memory-variable attenuation at all (no `Q`, `tau`, or relaxation-time handling was found in the material/constitutive modules); this paper would be the natural reference if/when frequency-dependent Q is added to that solver, since:

- The coarse-grained storage trick (one relaxation time per node, periodic cycling) is the natural fit for a high-order, GPU/MPI-targeted curvilinear SBP-SAT code like WaveQLab3D, where adding `N` full memory-variable fields per stress component would be costly.
- The stress-update equation (Eq. 19) is structurally a small addition to an existing velocity-stress (elastic) update — `σij = 2μu εij + (κu − 2/3 μu) εkk δij − ξij` — i.e., it requires only one extra memory-variable array per stress component (under coarse-graining) and one extra first-order ODE update per time step (Eq. 5), which would slot into `time_step.f90`/`RHS_Interior.f90`'s existing stress-rate evaluation.
- The `Qs0 = f(Vs)`, `Qp0 = 2·Qs0` empirical scaling used in the Chino Hills application is a reasonable default rule if material modules need a placeholder Q model tied to existing Vs/Vp fields.

## 8. Key equations quick-reference

| Eq. | Meaning |
|---|---|
| (1)–(2) | Power-law target Q(f), with constant-Q plateau below transition frequency `fT` |
| (3)–(5) | Memory-variable stress-strain relation, ODE, and exact exponential time update |
| (6)–(8) | Complex modulus, Q definition, low-loss approximation |
| (9)–(14) | Effective-Q (harmonic-average, coarse-grained) formulation for low Q (<200) |
| (15) | Log-uniform spacing of relaxation times between band limits `τm`, `τM` |
| (16) | Analytic interpolation `λk = ak/Q² + bk/Q` for arbitrary Q in [15,220] |
| (17)–(19) | Combined bulk+shear memory-variable stress update, coarse-grained form |
| (20) | Cosine-bell moment-rate source time function used for verification |
