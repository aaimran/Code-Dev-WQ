# Figure 6 Reproduction Specification: Layered Frequency-Dependent-Q Model

## 1. Reference

This specification targets Figure 6 of Withers, Olsen, and Day (2015): an f–k versus FD comparison for a low-Q shallow layer over a higher-Q elastic half-space, both with gamma = 0.6.

It extends the Figure 5 frequency-dependent-Q test by adding sharp contrasts in:

- Vp;
- Vs;
- density;
- Qp0 and Qs0.

It also tests later surface waves, including Love waves, and attenuation behavior across a discontinuity.

## 2. Published layered model

Table 3 of the paper gives:

| Layer | Thickness | Vp | Vs | Density | Qp0 | Qs0 | gamma |
|---|---:|---:|---:|---:|---:|---:|---:|
| Shallow layer | 1.0 km | 5.196 km/s | 3.000 km/s | 2.550 g/cm³ | 20 | 20 | 0.6 |
| Half-space | Infinite | 6.000 km/s | 3.464 km/s | 2.700 g/cm³ | 210 | 210 | 0.6 |

Use z positive downward:

    layer 1: 0 <= z < 1.0 km
    layer 2: z >= 1.0 km

Derived elastic constants:

| Layer | lambda (GPa) | mu (GPa) |
|---|---:|---:|
| Shallow | approximately 22.946 | 22.950 |
| Half-space | approximately 32.404 | 32.398 |

The 1 km layer boundary is exactly grid-aligned for dx = 0.04 km.

## 3. Source and receiver

The paper describes Figure 6 as a continuation of the same point-source verification sequence. Use the Figure 3–5 source and station unless a more complete source archive specifies otherwise:

    source = (0, 0, 1.8) km
    receiver = (12, 9, 0) km

The source is 0.8 km below the layer interface in the high-Q half-space. The receiver is at the free surface in the low-Q layer.

Retain:

- right-lateral 90/90/0 double couple;
- moment 10^16 N m;
- 0.2 s cosine-bell source;
- dx = 0.04 km;
- dt = 0.002 s;
- radial/transverse/vertical output;
- fourth-order zero-phase 0.2–10 Hz filtering.

Figure 6 plots approximately 2–7 s, so use:

    t_final = 7.0 s
    nt = 3500

and enlarge/recheck domain reflection paths for a 7 s window.

## 4. Domain

Enlarge the Figure 3 domain for the longer 7 s window:

    x = -20 to 35 km
    y = -20 to 35 km
    z = 0 to at least 25 km

For a 7 s comparison, z = 25 km provides safer bottom clearance than the 20 km Figure 3 design.

At 40 m spacing:

    Nx total = 1376
    Ny = 1376
    Nz = 626 for 0–25 km

Blocks:

- block 1 x = -20 to 5 km, Nq = 626;
- block 2 x = 5 to 35 km, Nq = 751;
- locked homogeneous-in-x interface;
- identical vertical layer profile in both blocks.

Boundary codes remain:

| Block | lqrs | rqrs |
|---|---|---|
| 1 | (1,1,2) | (0,1,1) |
| 2 | (0,1,2) | (1,1,1) |

No PML is used in the strict large-domain reproduction.

## 5. Material construction

problem = default cannot create the vertical layer, and problem = LOH1 has different velocities and an x-dependent interface. Use one of:

### Preferred: dedicated figure6 material initializer

Add a named problem that assigns lambda, mu, and rho by physical z:

    if z < 1 km:
       Vp = 5.196, Vs = 3.0, rho = 2.55
    else:
       Vp = 6.0, Vs = 3.464, rho = 2.7

This is transparent, reproducible, and avoids large material files.

### Alternative: distributed material files

Set material_source = file and provide three Fortran-order MPI binary volumes for:

- lambda;
- mu;
- rho.

The files must match each block’s global dimensions, precision, and MPI subarray ordering. Generate them with a documented utility and verify min/max and the z = 1 km interface after reading.

The attenuation Q fields still require code changes; material files currently provide only lambda, mu, and rho.

## 6. Target attenuation

For both P and S:

Shallow layer:

    Q0 = 20
    Q(f) = 20 below 1 Hz
    Q(f) = 20 f^0.6 above 1 Hz

Half-space:

    Q0 = 210
    Q(f) = 210 below 1 Hz
    Q(f) = 210 f^0.6 above 1 Hz

Examples:

| Frequency | Shallow Q | Half-space Q |
|---:|---:|---:|
| 1 Hz | 20.0 | 210.0 |
| 2 Hz | 30.3 | 318.3 |
| 5 Hz | 52.5 | 551.4 |
| 10 Hz | 79.6 | 836.0 |

Reference and transition frequencies are 1 Hz.

## 7. Required response

After correction:

    response = 'frequency-Q-8M'

The response must accept spatial Q fields:

    Qs0(x,y,z) = 20 for z < 1 km, else 210
    Qp0(x,y,z) = 20 for z < 1 km, else 210
    gamma(x,y,z) = 0.6
    f_trans = 1 Hz
    fref = 1 Hz

Conceptual input:

    &anelastic_Qf8_list
      q_source = 'layered'
      Qs0_layer = 20.0, 210.0
      Qp0_layer = 20.0, 210.0
      interface_z = 1.0
      gamma = 0.6
      f_trans = 1.0
      fref = 1.0
    /

These fields are not available in the current namelist.

## 8. Why current WaveQLab3D cannot express Figure 6

Current frequency-Q computes:

    Qs = c Vs
    Qp = 2 Qs

A single global c cannot match both layer values:

    c_shallow = 20/3.0 = 6.6667
    c_halfspace = 210/3.464 = 60.6236

Even with spatial c, Qp would become 40 and 420 rather than 20 and 210.

Further defects:

- f_trans is unused;
- weight lookup/scaling is inconsistent;
- coarse/conventional normalization is unresolved;
- Qf8 dispatch relies on Qf allocation logic;
- no Q discontinuity test exists.

Therefore no current response/input combination is a faithful Figure 6 setup.

## 9. Coarse-grained versus conventional treatment

The paper used:

- harmonic effective averaging in the low-Q shallow layer;
- arithmetic Q treatment in the underlying half-space;
- period-two coarse-grained mechanisms.

This detail matters at the sharp z = 1 km discontinuity.

Two implementation paths:

### Paper-faithful

Implement period-two coarse graining, Table 2 low-Q weights for Q = 20, and Table 1/high-Q behavior for Q = 210. Preserve the layer interface and effective averaging described by the paper.

### Conventional WaveQLab3D

Fit/store all eight mechanisms at every point:

- direct conventional low-Q fit for Q = 20;
- conventional high-Q fit/scaling for Q = 210;
- independent Qp/Qs fields;
- no averaging across the sharp interface unless physically/numerically justified.

The conventional result can be validated against f–k but is not numerically identical to the paper’s coarse-grained realization.

## 10. Relaxation spectrum

Both layers share gamma = 0.6 and fT = 1 Hz, so they may share tau values. Their weights differ because Q0 differs.

Required checks:

- shallow Q uses the valid low-Q formulation;
- half-space Q uses the high-Q formulation because Q = 210;
- weights remain nonnegative;
- the same tau convention is used in FD and f–k;
- no interpolation across the interface creates unintended intermediate Q;
- modulus correction is applied separately in each layer.

## 11. Time step

Using the paper’s dt = 0.002 s remains appropriate. WaveQLab3D derives dt from btp scalar material values, not the material volume.

The maximum velocity is still 6 km/s. Set both block btp values to the maximum/deep material:

    rho_s_p = 2.7, 3.464, 6.0
    CFL = 0.34641016

Then verify reported dt = 0.002 s.

This btp choice is for stability calculation only if material_source = file; actual material arrays must contain the layer values.

## 12. Illustrative corrected input delta

Relative to Figure 5:

    &problem_list
      name            = 'data/figure6_layered_q'
      problem         = 'FIGURE6_LAYERED'
      response        = 'frequency-Q-8M'
      material_source = 'hardcode'
      t_final         = 7.0
      ...
    /

    &anelastic_Qf8_list
      q_source   = 'figure6_layered'
      Qs0_top    = 20.0
      Qp0_top    = 20.0
      Qs0_bottom = 210.0
      Qp0_bottom = 210.0
      interface_z = 1.0
      gamma      = 0.6
      f_trans    = 1.0
      fref       = 1.0
    /

These are required proposed parameters, not currently parsed.

## 13. Reference f–k model

The f–k reference must use exactly the Table 3 layers:

- a 1 km top layer;
- elastic half-space below;
- same complex moduli, relaxation spectra, and reference correction;
- source at 1.8 km;
- station at 15 km horizontal distance;
- same source-time function;
- same sampling/filter.

The source lies in layer 2 and the receiver at the top of layer 1.

## 14. Expected phases and behavior

The shallow layer introduces:

- direct and refracted body waves;
- trapped and guided energy;
- Rayleigh waves;
- Love waves visible particularly on transverse motion;
- later, longer-duration surface-wave arrivals.

The low-Q top layer strongly attenuates trapped high-frequency energy. The high-Q contrast is 10.5:1 at the reference frequency.

The paper reports excellent early-time agreement and larger envelope mismatch for later surface waves.

## 15. Processing

Use the same component rotation:

    radial     = 0.8 vx + 0.6 vy
    transverse = 0.6 vx - 0.8 vy
    vertical_up = -vz when required

Apply identical 0.2–10 Hz fourth-order zero-phase filtering and FFT processing to FD and f–k.

Use at least a 2–7 s plot window. Do not truncate later surface waves when computing the full comparison.

## 16. Acceptance criteria

Paper-reported:

| Interval | Envelope misfit | Phase misfit |
|---|---:|---:|
| First 5 s | <= 5% | <= 2% |
| Later surface waves | 8–10% | about 2% |

The paper reports goodness-of-fit above 9, classified as excellent under the cited metric.

Additional requirements:

- layer properties match Table 3 exactly;
- interface at z = 1 km is grid-aligned;
- realized Q error <= 5% in each layer over 0.1–10 Hz;
- no unintended Q smoothing;
- correct reference-frequency velocities in each layer;
- Love-wave transverse motion present and consistent;
- result invariant across MPI decompositions;
- boundary reflections absent from the 7 s window.

## 17. Diagnostic matrix

Run:

1. Elastic layered model, to isolate material/interface discretization.
2. Uniform Q = 210 layered velocity model.
3. Uniform Q = 20 layered velocity model.
4. Full Q = 20/210 contrast.
5. Smoothed Q interface sensitivity case.
6. Conventional versus coarse-grained response if both exist.
7. Grid refinement around the 1 km layer.

This matrix distinguishes wave-interface errors from Q-interface errors.

## 18. Output artifacts

Produce:

- Figure-6-style velocity and Fourier panels;
- realized Qp/Qs curves for both layers;
- complex phase-velocity curves;
- interface property profile versus depth;
- early and late EM/PM metrics;
- FD/f–k spectral ratios;
- transverse Love-wave zoom;
- metadata and raw traces.

## 19. Run sequence

1. Pass Figures 3–5.
2. Implement exact Table 3 elastic material.
3. Pass elastic layered f–k comparison.
4. Implement spatial independent Qp/Qs.
5. Verify each layer at material-point level.
6. Test a plane wave crossing the Q/material discontinuity.
7. Run reduced-domain Figure 6.
8. Run full reflection-free test and compute early/late misfits.

## 20. Bottom line

Figure 6 is not merely Figure 5 with another Q value. It tests a sharp 1 km material and attenuation contrast, with Q = 20 above Q = 210 and gamma = 0.6 in both layers.

WaveQLab3D currently cannot specify independent spatial Qp/Qs fields or the required equal P/S Q, and its frequency-Q normalization remains defective. A faithful reproduction requires a new layered material definition, spatial Q support, corrected eight-mechanism response, and explicit discontinuity validation.
