# Figure 4 Reproduction Specification: Constant-Q Half-Space

## 1. Reference

This specification targets Figure 4 of Withers, Olsen, and Day (2015), “Memory-Efficient Simulation of Frequency-Dependent Q,” using the elastic Figure 3 setup documented in Knowledge-base/Codex/figure_3.md as its baseline.

Figure 4 compares f–k and finite-difference results for a homogeneous viscoelastic half-space with constant Q, represented by the paper’s power-law framework at gamma = 0.

## 2. Test objective

The test isolates the constant-Q constitutive implementation. Relative to the accepted Figure 3 elastic baseline, it should verify:

- attenuation of body and surface waves;
- causal phase dispersion;
- reference-frequency modulus correction;
- memory-variable integration;
- free-surface behavior in a lossy medium;
- agreement between FD and f–k velocity waveforms and spectra.

The paper reports envelope misfit below 6% and phase misfit below 2% for all components.

## 3. Published setup

All source, receiver, grid, and half-space parameters are unchanged from Figure 3:

| Item | Value |
|---|---|
| Vp | 6.000 km/s |
| Vs | 3.464 km/s |
| Density | 2.700 g/cm³ |
| Qp0 | 50 |
| Qs0 | 50 |
| gamma | 0.0 |
| Reference frequency | 1 Hz |
| Source | Right-lateral double couple, strike/dip/rake 90/90/0 |
| Source location | (0, 0, 1.8) km |
| Moment | 10^16 N m |
| Source duration | 0.2 s cosine bell |
| Grid spacing | 0.040 km |
| Time step | 0.002 s |
| Receiver | (12, 9, 0) km |
| Receiver range/azimuth | 15 km, 53.13 degrees from north |
| Processing | Fourth-order zero-phase Butterworth, 0.2–10 Hz |

The target model is constant Q because gamma = 0. The paper uses low-Q effective/coarse-grained coefficients from Table 2.

## 4. Domain, boundaries, source, and output

Use the Figure 3 domain specification unchanged:

- x = -15 to 30 km;
- y = -15 to 30 km;
- z = 0 to 20 km, positive downward;
- free surface at z = 0;
- characteristic external sides/bottom;
- no PML in the strict reproduction;
- t_final = 6.0 s;
- output every 0.002 s.

Until one-block and source-ownership defects are fixed, use the same two homogeneous blocks:

- block 1 x = -15 to 5 km, Nq = 501;
- block 2 x = 5 to 30 km, Nq = 626;
- Nr = 1126 and Ns = 501;
- locked interface and identical material/attenuation on both sides.

Reuse the Figure 3 tensor source:

    'cosine' 0.2 0.0  0 0 0  0.01 0 0  0 0 1.8  0

The final zero selects the centered fourth-order discrete delta. Moment sign and amplitude must already have been calibrated in the elastic test.

## 5. Required response model

### 5.1 Scientific target

The required constitutive model has:

    Qs0 = 50
    Qp0 = 50
    gamma = 0
    f_transition = 1 Hz
    f_reference = 1 Hz
    mechanisms = 8

Eight mechanisms are preferred because the paper’s implementation used eight relaxation times and its low-Q effective coefficients.

### 5.2 Intended WaveQLab3D selector

After correcting the response implementation, use:

    response = 'frequency-Q-8M'

with:

    &anelastic_Qf8_list
      Qs0    = 50.0
      Qp0    = 50.0
      gamma  = 0.0
      f_trans = 1.0
      fref    = 1.0
    /

Qs0 and Qp0 are required conceptual inputs; the current namelist does not provide them independently.

An alternative corrected selector is constant-Q-8M, but only if its weights reproduce the same Table-2 target and its target_Q/local-Q ambiguity is removed.

## 6. Why the current response cannot reproduce Figure 4

Current WaveQLab3D behavior differs in several material ways:

1. Qs is computed as c times Vs.
2. Qp is hard-coded to 2 Qs.
3. The paper requires Qp = Qs = 50.
4. frequency-Q-8M requests Withers weights at Q = 1; the table routine clamps this to Q = 15.
5. The RHS then multiplies those weights by local inverse Q again.
6. Withers tables contain coarse-grained weights, while WaveQLab3D stores every mechanism at every point.
7. f_trans is ignored, though gamma = 0 makes its spectral effect less visible here.

Choosing:

    c = 50/3.464 = 14.43418

would produce Qs = 50 but Qp = 100. That is not the Figure 4 model and must be labeled an approximation.

The current constant-Q-8M path is also unsuitable without repair:

- one RHS region calls the dispatcher twice;
- target_Q and c-derived inverse Q both scale attenuation;
- withers/lookup weight methods do not honor their documented controls consistently.

## 7. Required code corrections

Before a faithful run:

1. Add independent scalar or field inputs for Qs0 and Qp0.
2. Set Qs_inverse = 1/50 and Qp_inverse = 1/50 everywhere.
3. Define whether stored weights are normalized shapes or already Q-scaled.
4. For conventional storage, use conventional weights; do not use coarse weights unchanged.
5. Remove the Q = 1 to Q = 15 clamp/double-scaling path.
6. Correct unrelaxed shear and bulk/P-wave moduli at 1 Hz.
7. Remove duplicate constant-Q dispatch.
8. Assert positive tau, nonnegative weights, and positive modulus denominators.
9. Print realized Qp(f), Qs(f), and phase velocities before propagation.

## 8. Weight construction

Two legitimate reproduction paths exist.

### Path A: paper-faithful coarse graining

- Use eight mechanisms distributed over a period-two 3-D cell.
- Use Table 2 low-Q coefficients at Q = 50 and gamma = 0.
- Apply the paper’s effective-medium treatment.
- Preserve deterministic mechanism placement across MPI partitions.

This most closely reproduces the published FD method but requires a new coarse-grained WaveQLab3D layout.

### Path B: conventional WaveQLab3D storage

- Store all eight mechanisms at every point.
- Fit conventional nonnegative weights directly to Qp = Qs = 50 over 0.1–10 Hz.
- Use the exact complex-modulus expression, not the coarse-grained effective-Q formula.
- Verify target Q and dispersion against the f–k constitutive model.

Dividing published coarse weights by eight is a useful diagnostic starting point, not sufficient proof of low-Q equivalence.

## 9. Illustrative corrected input delta

Start from the Figure 3 skeleton and change only:

    &problem_list
      name     = 'data/figure4_constant_q'
      response = 'frequency-Q-8M'
      ...
    /

    &anelastic_Qf8_list
      Qs0     = 50.0
      Qp0     = 50.0
      gamma   = 0.0
      f_trans = 1.0
      fref    = 1.0
    /

The Qs0/Qp0 fields shown here are a required interface change, not currently accepted parameters.

If using the current executable for a non-faithful diagnostic:

    c = 14.43418

and explicitly report that Qp becomes 100.

## 10. Reference f–k solution

The f–k solver must use the same discrete relaxation spectrum and complex modulus as the corrected FD model, including:

- Qp0 = Qs0 = 50;
- gamma = 0;
- reference frequency 1 Hz;
- identical unrelaxed-modulus correction;
- identical source and receiver;
- identical output sampling and filtering.

Comparing an FD coarse-grained model against a different analytic constant-Q law is not a clean implementation test.

## 11. Expected behavior

Relative to Figure 3:

- P, S, Rayleigh, and other phases have reduced amplitude;
- arrivals shift because attenuation implies dispersion;
- Fourier amplitude drops across the plotted band;
- no spurious free-surface oscillation should appear.

The paper specifically reports that the Rayleigh wave around 4.5–5.5 s is reproduced cleanly.

## 12. Processing

Use exactly the Figure 3 processing:

    radial     = 0.8 vx + 0.6 vy
    transverse = 0.6 vx - 0.8 vy
    vertical_up = -vz, if required by reference convention

Apply the same fourth-order zero-phase 0.2–10 Hz Butterworth filter to FD and f–k traces. Preserve raw traces and use identical FFT windows/tapers.

## 13. Acceptance criteria

Paper-reported reference values:

| Metric | Published result |
|---|---:|
| Maximum envelope misfit | < 6% |
| Maximum phase misfit | < 2% |

Additional required checks:

- realized Qp and Qs within 5% of 50 over 0.1–10 Hz;
- reference-frequency phase velocity matches 6.0/3.464 km/s;
- no boundary reflection before 6 s;
- FD/f–k waveform and spectrum agreement quantified per component;
- results invariant under MPI decomposition;
- loss is monotonic and weights are passive.

## 14. Run sequence

1. Pass Figure 3 elastic test.
2. Unit-test the corrected complex modulus at Q = 50.
3. Verify Q(f) and phase velocity at a material point.
4. Run a homogeneous plane-wave attenuation test.
5. Run a reduced-domain source test.
6. Run the full Figure 4 domain.
7. Compare EM, PM, waveform norms, and Fourier ratios.
8. Only then proceed to Figure 5.

## 15. Bottom line

Figure 4 differs from Figure 3 only by the constant-Q constitutive response. The paper requires Qp0 = Qs0 = 50, gamma = 0, and a 1 Hz reference.

Current WaveQLab3D cannot express that model faithfully because it forces Qp = 2 Qs and has weight-scaling/dispatch defects. A valid reproduction therefore requires the response corrections above; setting c to obtain Qs = 50 is only an explicitly labeled approximation.
