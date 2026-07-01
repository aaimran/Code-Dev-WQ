# Figure 5 Reproduction Specification: Frequency-Dependent-Q Half-Space

## 1. Reference

This specification targets Figure 5 of Withers, Olsen, and Day (2015). It uses the same homogeneous half-space, source, receiver, discretization, and processing as Figures 3 and 4, but changes the attenuation spectrum to a power-law model with gamma = 0.6 above 1 Hz.

## 2. Test objective

Figure 5 verifies that the frequency-dependent memory-variable model reproduces:

- Q that is constant below 1 Hz;
- Q increasing as f^0.6 above 1 Hz;
- the associated causal phase dispersion;
- body and surface-wave amplitudes/phases in a half-space;
- the expected retention of high-frequency energy relative to Figure 4.

The paper reports envelope misfit below 2% and phase misfit below 1%.

## 3. Published setup

| Item | Value |
|---|---|
| Vp | 6.000 km/s |
| Vs | 3.464 km/s |
| Density | 2.700 g/cm³ |
| Qp0 | 50 |
| Qs0 | 50 |
| gamma | 0.6 |
| Transition frequency fT | 1 Hz |
| Reference frequency fref | 1 Hz |
| Source | Figure 3 right-lateral double couple |
| Source location | (0,0,1.8) km |
| Receiver | (12,9,0) km |
| Grid spacing | 0.040 km |
| Time step | 0.002 s |
| Comparison interval | approximately 2–6 s |
| Filter | Fourth-order zero-phase 0.2–10 Hz Butterworth |

Target:

    Q(f) = 50                       below 1 Hz
    Q(f) = 50 (f/1 Hz)^0.6          above 1 Hz

The same target applies independently to P and S attenuation.

Examples:

| Frequency | Target Q |
|---:|---:|
| 0.2 Hz | 50.0 |
| 1 Hz | 50.0 |
| 2 Hz | 75.8 |
| 5 Hz | 131.3 |
| 10 Hz | 199.1 |

## 4. Reused Figure 3 configuration

Use the domain, two-block workaround, boundary codes, source tensor, receiver, CFL, output cadence, rotation, and filtering defined in Knowledge-base/Codex/figure_3.md.

Primary numerical values:

    dx = dy = dz = 0.04 km
    dt = 0.002 s
    CFL = 0.34641016
    t_final = 6.0 s
    fd_type = 'upwind'
    order = 4

The WaveQLab3D operator differs from the paper’s fourth-order staggered-grid/second-order-time method, so convergence and f–k agreement—not bitwise reproduction—are the criteria.

## 5. Required response model

After corrections:

    response = 'frequency-Q-8M'

Conceptual namelist:

    &anelastic_Qf8_list
      Qs0     = 50.0
      Qp0     = 50.0
      gamma   = 0.6
      f_trans = 1.0
      fref    = 1.0
    /

Eight mechanisms match the paper. The weights must be appropriate to conventional storage or the solver must implement the paper’s period-two coarse graining.

## 6. Current implementation mismatch

The present frequency-Q-8M response is not paper-faithful:

1. f_trans is read and stored but never used to scale tau.
2. Qp is fixed at 2 Qs instead of Qp = Qs.
3. c defines Qs = c Vs rather than accepting Qs0 directly.
4. get_withers_weights(gamma, 1) clamps Q to 15.
5. The RHS multiplies these weights by inverse local Q again.
6. Published w_k values are coarse-grained weights, but WaveQLab3D stores all eight mechanisms per point.
7. The dedicated Qf8 flag is bypassed; dispatch relies on the Qf flag and allocation detection.

Setting c = 14.43418 yields Qs0 = 50 but Qp0 = 100. It is not an acceptable final reproduction.

## 7. Required response corrections

1. Accept independent Qs0 and Qp0.
2. Scale relaxation times for fT:

       tau_k(fT) = tau_k(table at 1 Hz) / fT

3. Use gamma = 0.6 Table-1/Table-2 data with a documented coarse/conventional convention.
4. At Q = 50, use the low-Q interpolation or a direct conventional nonlinear fit.
5. Do not clamp a nominal unscaled request and then apply inverse Q twice.
6. Correct unrelaxed moduli so Vp and Vs are honored at 1 Hz.
7. Print the realized Q and phase-velocity curves.

## 8. Weight strategy

### Paper-faithful path

- Eight relaxation times.
- Period-two coarse-grained placement.
- Table 2 low-Q interpolation at Q = 50 and gamma = 0.6.
- Harmonic/effective treatment as described by the paper.

### Conventional WaveQLab3D path

- Eight mechanisms at every point.
- Fit nonnegative conventional weights to the exact complex-modulus target.
- Match Q(f) over at least 0.1–10 Hz.
- Match reference phase velocity at 1 Hz.

The two paths should be treated as different numerical realizations of the same macroscopic target and compared at material-point level before wave propagation.

## 9. Illustrative corrected input delta

Start from Figure 3 and change:

    &problem_list
      name     = 'data/figure5_frequency_q'
      response = 'frequency-Q-8M'
      ...
    /

    &anelastic_Qf8_list
      Qs0     = 50.0
      Qp0     = 50.0
      gamma   = 0.6
      f_trans = 1.0
      fref    = 1.0
    /

Qs0 and Qp0 are required additions to the current input interface.

## 10. Pre-wave material test

Before running the source model, sample the implemented complex modulus on a dense log-frequency grid:

    0.05 to 20 Hz, at least 200 samples

Verify:

- Qp and Qs follow the piecewise target;
- maximum relative Q error is below 5% over 0.1–10 Hz;
- Q is approximately 50 below 1 Hz;
- Q is approximately 199 at 10 Hz;
- weights are nonnegative;
- attenuation is passive;
- phase velocity equals input Vp/Vs at 1 Hz;
- no discontinuity or artificial spike occurs at fT.

## 11. Reference f–k solution

The reference must use the same relaxation spectrum/complex modulus, not merely an ideal power-law formula, unless the comparison purpose is explicitly changed.

Match:

- P and S Q0 = 50;
- gamma = 0.6;
- fT = fref = 1 Hz;
- source and receiver;
- sampling/filtering;
- modulus correction.

## 12. Expected differences from Figure 4

Below 1 Hz, Figures 4 and 5 should be similar. Above 1 Hz:

- Figure 5 Q increases;
- less energy is attenuated;
- Fourier amplitude is larger;
- high-frequency waveform detail is stronger;
- phase dispersion differs.

These differences should grow with frequency but not appear as a discontinuity at exactly 1 Hz.

## 13. Processing and plots

Use identical component rotation and filtering for Figures 3–5. Produce:

1. Figure-5-style radial/transverse/vertical overlays.
2. Fourier amplitudes.
3. FD/f–k spectral ratios.
4. Figure 5/Figure 4 spectral ratio.
5. Realized Qp/Qs and phase-velocity curves.
6. Envelope and phase misfit histories.

Do not independently normalize traces; amplitude retention is the physical signal under test.

## 14. Acceptance criteria

Published:

| Metric | Published result |
|---|---:|
| Maximum envelope misfit | < 2% |
| Maximum phase misfit | < 1% |

Required:

- target Q error <= 5% over 0.1–10 Hz;
- reference-frequency velocity error negligible relative to FD error;
- Figure 5 has more energy than Figure 4 above 1 Hz;
- no difference attributable to source/filter/domain changes;
- no artificial boundary reflection before 6 s;
- MPI-decomposition invariance.

## 15. Run sequence

1. Pass Figure 3.
2. Pass Figure 4.
3. Repair and unit-test f_trans.
4. Verify gamma = 0.6 table interpolation and normalization.
5. Run material-point and plane-wave tests.
6. Run reduced-domain FD/f–k comparison.
7. Run full Figure 5 test.
8. Compare Figure 4 and Figure 5 with one common processing script.

## 16. Bottom line

Figure 5 is the central homogeneous frequency-dependent-Q verification: Qp0 = Qs0 = 50, gamma = 0.6, with transition and velocity-reference frequencies at 1 Hz.

Current WaveQLab3D accepts a similarly named response but does not implement these parameters consistently. A faithful result requires independent P/S Q, active transition-frequency scaling, corrected weight normalization, and material-point verification before the wave test.
