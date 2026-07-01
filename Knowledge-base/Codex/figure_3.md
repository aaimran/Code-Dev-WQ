# Figure 3 Reproduction Specification: Elastic Half-Space FD Test

## 1. Reference and interpretation

No file named FD.md exists in the workspace. This specification therefore interprets “Figure 3 in FD.md” as Figure 3 of the supplied Withers, Olsen, and Day (2015) frequency-dependent-Q paper in Knowledge-base/Common/FQ.pdf.

Figure 3 is the elastic control test, not an attenuation test. It compares three-component surface velocity from:

- a frequency–wavenumber reference solution; and
- a three-dimensional finite-difference solution.

The test establishes the accuracy of the source, free surface, grid, receiver, and elastic propagation before Q is enabled in Figures 4–6.

This document separates:

- values explicitly stated in the paper;
- values derived from the paper;
- WaveQLab3D-specific choices required because the paper does not publish a complete input deck.

## 2. Test objective

The test should answer:

1. Does the FD solution reproduce the f–k elastic half-space waveform?
2. Are P- and S-wave arrival times correct?
3. Are radial, transverse, and vertical amplitudes and polarities correct?
4. Does the Fourier-amplitude spectrum agree over 0.2–10 Hz?
5. Are discrepancies attributable to spatial resolution, source injection, free-surface treatment, receiver staggering, or post-processing rather than attenuation?

Acceptance of this elastic baseline is a prerequisite for evaluating constant-Q or frequency-dependent-Q responses.

## 3. Published Figure 3 setup

### 3.1 Medium

Homogeneous isotropic elastic half-space:

| Property | SI value | WaveQLab3D km–s–GPa value |
|---|---:|---:|
| P-wave speed | 6000 m/s | 6.000 km/s |
| S-wave speed | 3464 m/s | 3.464 km/s |
| Density | 2700 kg/m³ | 2.700 g/cm³ |

Derived elastic constants:

    mu = rho Vs² = 32.3981 GPa
    lambda = rho (Vp² - 2 Vs²) = 32.4038 GPa

The near equality follows from Vp being approximately sqrt(3) Vs.

### 3.2 Source

| Quantity | Value |
|---|---:|
| Source type | Buried double couple |
| Mechanism | Right-lateral strike slip |
| Strike | 90 degrees |
| Dip | 90 degrees |
| Rake | 0 degrees |
| Depth | 1.8 km |
| Scalar moment | 10^16 N m |
| Approximate magnitude | Mw 4.6 |
| Source-time duration T | 0.2 s |

The paper defines a cosine-bell moment-rate function:

    Mdot(t) = M0 [1 - cos(2 pi t/T)]    for 0 < t < T
    Mdot(t) = 0                         otherwise

The exact normalization of M0 must be checked against the solver’s source convention. The paper labels M0 as 10^16 N m, while the displayed function is a moment rate.

### 3.3 Grid and time step

| Quantity | Value |
|---|---:|
| Uniform grid spacing | 40 m = 0.040 km |
| FD time step | 0.002 s |
| Minimum illustrative Vs | 2000 m/s |
| Resolution criterion quoted by paper | 5 points per minimum S wavelength |
| Corresponding upper frequency | 10 Hz |

For the actual homogeneous Vs = 3.464 km/s, the grid has about 8.66 points per S wavelength at 10 Hz.

The paper’s FD implementation is fourth order in space and second order in time. WaveQLab3D uses different operators and a five-stage fourth-order low-storage Runge–Kutta method, so exact truncation-error equivalence is not expected even with the same dx and dt.

### 3.4 Receiver

| Quantity | Value |
|---|---:|
| Receiver type | Surface velocity |
| Horizontal source distance | 15 km |
| Azimuth | 53.13 degrees from north |
| Components plotted | Radial, transverse, vertical |

Using x east and y north:

    x_receiver = 15 sin(53.13 degrees) = 12.0 km
    y_receiver = 15 cos(53.13 degrees) = 9.0 km
    z_receiver = 0.0 km

The source-to-receiver hypocentral distance is:

    sqrt(12² + 9² + 1.8²) = 15.108 km

Approximate direct arrivals:

    tP = 15.108/6.000 = 2.518 s
    tS = 15.108/3.464 = 4.361 s

These values are useful sanity checks, not exact picks after the finite source and free-surface response.

### 3.5 Filtering

The paper bandpasses Figure 3 seismograms from 0.2 to 10 Hz using a fourth-order filter. The implementation family and whether filtering is causal or zero-phase are not fully specified in the extracted text.

For reproducibility:

- use a fourth-order Butterworth bandpass;
- use zero-phase forward/backward application for comparison plots;
- record that this doubles the effective filter order;
- alternatively reproduce a causal fourth-order filter, but do not mix conventions between FD and f–k traces.

Raw unfiltered output must also be retained.

## 4. WaveQLab3D coordinate and unit convention

Use:

- x: east;
- y: north;
- z: positive downward;
- free surface: z = 0;
- distance: km;
- time: s;
- velocity: km/s;
- density: g/cm³;
- stress/modulus: GPa.

With these units:

    1 GPa km³ = 10^18 N m

Therefore a physical moment of 10^16 N m corresponds to 0.01 GPa km³ before accounting for the code’s discrete delta and source-time normalization.

The sign of mXY for the specified right-lateral mechanism depends on WaveQLab3D’s stress and coordinate sign convention. Start with the analytically derived off-diagonal tensor and determine its sign by the expected radial/transverse polarity; do not silently take an absolute value.

## 5. Domain design

### 5.1 Exact-paper requirement

The paper states that the domain was large enough that no artificial boundary reflection reached the station during the plotted interval. It does not publish the domain extents.

The reproduction must therefore derive extents from the maximum comparison time. For a plot through 6 s, require every non-surface reflected P-wave path from source to boundary to receiver to exceed:

    Vp tmax = 6 km/s x 6 s = 36 km

The physical free-surface reflection is not excluded.

### 5.2 Recommended reflection-free extents

A conservative Cartesian domain is:

    x = -15 to 30 km
    y = -15 to 30 km
    z = 0 to 20 km

With dx = 0.04 km, this is approximately:

    Nx = 1126
    Ny = 1126
    Nz = 501

or about 635 million physical grid points before ghost cells. This is an HPC-scale test.

The nearest simple side/bottom reflected paths exceed roughly 36 km for the source at (0,0,1.8) and receiver at (12,9,0). Verify path lengths programmatically for the chosen tmax.

### 5.3 Practical reduced-domain option

For development, use a smaller domain with characteristic boundaries or PML and label it “implementation check,” not an exact Figure 3 reproduction. PML changes the boundary treatment from the paper’s stated large-domain strategy.

Compare reduced- and full-domain receiver traces over the retained time window to prove boundary independence.

## 6. One block versus two blocks

The physical model is one homogeneous half-space. WaveQLab3D advertises one-block support, but the source review found unconditional block-2 references in current domain/source code.

Until those defects are fixed, use two homogeneous Cartesian blocks coupled by a locked interface:

- block 1: x = -15 to 5 km;
- block 2: x = 5 to 30 km;
- both: y = -15 to 30 km;
- both: z = 0 to 20 km;
- identical material in both blocks;
- coupling = locked;
- interface boundary code = 0.

At dx = 0.04 km:

- block 1 Nq = 501;
- block 2 Nq = 626;
- both Nr = 1126;
- both Ns = 501.

The receiver lies in block 2. The source lies in block 1.

This workaround adds an internal numerical interface absent from the paper. A welded-interface transparency test is required: the trace should agree with a corrected one-block calculation or an equivalent homogeneous reference.

## 7. Boundary conditions

WaveQLab3D boundary codes are:

| Code | Meaning |
|---:|---|
| 0 | Material/interface face |
| 1 | Characteristic boundary |
| 2 | Free surface |

Recommended two-block codes:

| Block | lqrs | rqrs |
|---|---|---|
| 1 | (1, 1, 2) | (0, 1, 1) |
| 2 | (0, 1, 2) | (1, 1, 1) |

This places:

- characteristic conditions on external x and y faces and the bottom;
- a free surface at the lower z-index, z = 0;
- a locked interface at x = 5 km.

For the strict large-domain run, boundary conditions should not influence the comparison window. Characteristic boundaries are still preferable as a safeguard.

## 8. Spatial and temporal discretization

### 8.1 Matching the paper

The paper used a fourth-order staggered-grid FD scheme and dt = 0.002 s. WaveQLab3D does not implement that identical scheme.

The closest documented WaveQLab3D choice should be treated as a cross-code reproduction:

    fd_type = 'upwind'
    order = 4

An alternative traditional operator can be run as a sensitivity case, but it should not replace the declared primary discretization.

### 8.2 Setting dt

WaveQLab3D computes:

    dt = CFL h / sqrt(Vs² + Vp²)

For h = 0.04 km, Vs = 3.464 km/s, and Vp = 6 km/s:

    sqrt(Vs² + Vp²) = 6.9282 km/s
    CFL required for dt = 0.002 s = 0.34641

Set:

    CFL = 0.34641016

Then confirm the startup output reports dt = 0.002 s to numerical tolerance. The code computes nt = floor(t_final/dt); use a t_final exactly divisible by dt.

Recommended:

    t_final = 6.0 s
    nt = 3000

If later coda or boundary checks are required, use 7–8 s and enlarge the domain accordingly.

## 9. Material setup

Use problem = default and hard-coded material generation:

    btp(i)%rho_s_p = 2.7, 3.464, 6.0

Despite the name rho_s_p, the entries are:

1. density;
2. Vs;
3. Vp.

material:init_material then computes:

    lambda = rho (Vp² - 2 Vs²)
    mu = rho Vs²
    rho = density

Both blocks must receive identical values.

Do not use problem = LOH1 for Figure 3. LOH1 is layered/discontinuous and corresponds to a different test.

## 10. Source setup

### 10.1 Moment tensor

For x east, y north, z down, a vertical right-lateral strike-slip source with strike 90, dip 90, rake 0 has only an xy shear pair in the ideal tensor:

    Mxx = Myy = Mzz = Mxz = Myz = 0
    Mxy = plus or minus M0

The sign must be checked against the convention used by the f–k reference.

WaveQLab3D tensor-list order is:

    source_type, duration, t_init,
    Mxx, Myy, Mzz, Mxy, Mxz, Myz,
    x, y, z, alpha

An initial code-unit candidate is:

    'cosine' 0.2 0.0  0 0 0  0.01 0 0  0 0 1.8  0

where 0.01 GPa km³ corresponds dimensionally to 10^16 N m.

The final value is alpha, a discrete-source stencil selector. For moment_list order = 4, the implemented choices are 0, 25, 50, and 100; alpha = 0 selects the centered nine-point delta stencil. It is not the finite-difference order.

### 10.2 Important source normalization caveat

WaveQLab3D source_time('cosine') returns:

    1 - cos(2 pi t/duration)

for 0 <= t <= duration. This matches the shape printed in the paper, but the interpretation of the supplied tensor amplitude as moment or moment-rate amplitude must be verified.

Required source calibration:

1. Integrate the implemented source-time function.
2. Include the discrete delta normalization used by singular_source.
3. Confirm the resulting total moment in SI units.
4. Compare a near-field or far-field elastic amplitude with the f–k solution.

Do not tune the moment separately for each component.

### 10.3 Source placement

Place the source at:

    x = 0 km
    y = 0 km
    z = 1.8 km

With dx = 0.04 km, the depth lies exactly on a grid point because 1.8/0.04 = 45. The source should also be aligned horizontally or its off-grid interpolation order documented.

Use moment_list:

    use_moment_tensor = T
    order = 4

Block 1 contains the tensor line; block 2’s tensor section is empty.

## 11. Receiver setup

Enable seismogram output and use physical coordinates:

    station_xyz_index = T
    receiver = (12.0, 9.0, 0.0) km

Place the receiver in block 2’s station_listV section.

The receiver is exactly grid-aligned for dx = 0.04 km:

    12/0.04 = 300
    9/0.04 = 225

The surface velocity components in a staggered-grid reference are effectively half-grid below the traction-free surface; the paper averaged horizontal components to better match target geometry. WaveQLab3D is not the same staggered arrangement. Document whether its boundary-node velocity is used directly or interpolated to z = 0.

Save all native components vx, vy, vz every time step. The current output stride should be 1.

## 12. Response setup

### 12.1 Figure 3 response

Figure 3 is elastic:

    response = 'elastic'

No anelastic namelist should be supplied. Verify after initialization that:

- all attenuation flags are false;
- no eta/Deta arrays are allocated;
- no plastic state is active;
- lambda and mu retain the values derived from Vp, Vs, and rho;
- the RHS never calls an attenuation kernel.

This is the only scientifically correct response setting for Figure 3.

### 12.2 Why Q must not be enabled

Figure 3 is used to isolate numerical/source/free-surface error. Enabling any Q response changes amplitude and phase and invalidates the baseline comparison.

### 12.3 Follow-on response matrix

After Figure 3 passes:

| Target | Intended response | Caveat |
|---|---|---|
| Elastic baseline, Figure 3 | elastic | Required |
| Constant-Q comparison, Figure 4 | Prefer corrected anelastic-Q8 or corrected constant-Q-8M | Must specify paper Q and verify realized Q(f) |
| Power-law Q comparison, Figure 5 | Corrected frequency-Q-8M | Current f_trans and weight-scaling defects must be fixed first |

Do not use legacy anelastic/low-pass for reproduction. Its weight_exp handling is unsafe outside two narrow cases.

Current frequency-Q-8M is not ready for a paper-faithful test because:

- f_trans is read but unused;
- Q = 1 table lookup is clamped to Q = 15;
- weights are then multiplied by local inverse Q again;
- published coarse-grained weights may be used in conventional storage without division by eight.

Current constant-Q-4M/8M also needs correction because one RHS path dispatches the model twice and target_Q scaling is ambiguous.

## 13. Illustrative WaveQLab3D input skeleton

The following is a specification skeleton, not a guaranteed run-ready file. It uses the current problem_list/block_list/tensor-list schema and omits unrelated output options.

    &problem_list
      name            = 'data/figure3_elastic'
      problem         = 'default'
      response        = 'elastic'
      plastic_model   = 'default'
      nblocks         = 2
      CFL             = 0.34641016
      coupling        = 'locked'
      fd_type         = 'upwind'
      order           = 4
      t_final         = 6.0
      mesh_source     = 'compute'
      type_of_mesh    = 'cartesian'
      material_source = 'hardcode'
      interpol        = F
      w_stride        = 1
      w_fault         = F
      use_topography  = F
      mollify_source  = F
    /

    &block_list
      btp(1)%nqrs       = 501, 1126, 501
      btp(1)%aqrs       = -15.0, -15.0, 0.0
      btp(1)%bqrs       =   5.0,  30.0, 20.0
      btp(1)%rho_s_p    = 2.7, 3.464, 6.0
      btp(1)%lqrs       = 1, 1, 2
      btp(1)%rqrs       = 0, 1, 1
      btp(1)%pml_lqrs   = F, F, F
      btp(1)%pml_rqrs   = F, F, F
      btp(1)%npml       = 0

      btp(2)%nqrs       = 626, 1126, 501
      btp(2)%aqrs       =   5.0, -15.0, 0.0
      btp(2)%bqrs       =  30.0,  30.0, 20.0
      btp(2)%rho_s_p    = 2.7, 3.464, 6.0
      btp(2)%lqrs       = 0, 1, 2
      btp(2)%rqrs       = 1, 1, 1
      btp(2)%pml_lqrs   = F, F, F
      btp(2)%pml_rqrs   = F, F, F
      btp(2)%npml       = 0
    /

    &moment_list
      use_moment_tensor = T
      order = 4
    /

    !---begin:tensor_listU---
    'cosine' 0.2 0.0  0.0 0.0 0.0  0.01 0.0 0.0  0.0 0.0 1.8  0
    !---end:tensor_listU---

    !---begin:tensor_listV---
    !---end:tensor_listV---

    &mms_list
      use_mms = F
    /

    &output_list
      output_exact_moment  = F
      output_seismograms   = T
      output_fault_topo    = F
      output_fields_block1 = F
      output_fields_block2 = F
      output_station_info  = T
      station_xyz_index    = T
      station_list         = 'infile'
      stride_fields        = 1
    /

    !---begin:station_listU---
    !---end:station_listU---

    !---begin:station_listV---
    12.0 9.0 0.0
    !---end:station_listV---

Before running, compare this skeleton with a known-good current input because several older example files use inconsistent namelist terminators and defaults.

## 14. Reference f–k solution

The FD trace alone cannot reproduce Figure 3; a reference trace is required.

The f–k model must use:

- the same homogeneous Vp, Vs, and density;
- a traction-free half-space;
- the same double-couple tensor and sign convention;
- source depth 1.8 km;
- receiver horizontal range 15 km and azimuth 53.13 degrees;
- identical source-time function and normalization;
- velocity output;
- the same final filtering and sampling.

Export reference traces at dt = 0.002 s or resample both solutions onto a common time grid before comparison. Preserve unfiltered reference traces.

## 15. Post-processing

### 15.1 Component rotation

For azimuth theta = 53.13 degrees from north and x east/y north:

    sin(theta) = 0.8
    cos(theta) = 0.6

One standard rotation is:

    radial     = 0.8 vx + 0.6 vy
    transverse = 0.6 vx - 0.8 vy

The transverse sign depends on convention. Select the convention used by the f–k output and state it explicitly.

If z is positive downward but the reference vertical is positive upward:

    vertical_up = -vz

### 15.2 Filtering

1. Remove any insignificant mean offset.
2. Apply the same 0.2–10 Hz fourth-order bandpass to all FD and reference components.
3. Do not normalize individual traces.
4. Plot a common physical velocity scale in cm/s.
5. Convert km/s to cm/s by multiplying by 100,000.

### 15.3 Fourier spectra

- Use identical time windows for FD and f–k.
- Apply the same taper.
- Use the same zero padding and one-sided amplitude normalization.
- Plot 0.2–10 Hz on a logarithmic frequency axis.
- Record whether spectra use filtered or raw time series; the paper’s visual comparison should be reproduced consistently.

## 16. Verification and acceptance criteria

### 16.1 Pre-run checks

- Grid spacing equals 0.040 km in all directions.
- Startup dt equals 0.002 s.
- Material min/max values are Vp = 6, Vs = 3.464, rho = 2.7.
- Source maps to (0,0,1.8).
- Receiver maps to (12,9,0).
- response is elastic and every attenuation flag is false.
- The welded interface joins identical materials.
- Output cadence is every step.

### 16.2 Primary waveform metrics

For each component:

- P- and S-arrival time error;
- peak velocity ratio;
- normalized L2 waveform error;
- maximum cross-correlation and lag;
- Fourier-amplitude ratio over 0.2–10 Hz;
- phase difference or group delay over the resolved band.

Suggested initial acceptance targets:

| Metric | Target |
|---|---:|
| Arrival-time error | <= one output sample or justified discretization error |
| Cross-correlation | >= 0.98 over principal arrivals |
| Peak amplitude difference | <= 5% |
| Band-limited L2 error | <= 5% |
| Median spectral-amplitude ratio | 0.95–1.05 |

These are engineering targets, not values stated by the paper. If the differing FD formulation cannot meet them, perform grid refinement and report convergence rather than loosening criteria silently.

### 16.3 Sensitivity runs

1. dx = 0.08, 0.04, and 0.02 km where feasible.
2. dt halved at fixed dx.
3. upwind order 4 versus traditional operator.
4. One-block corrected implementation versus two-block locked workaround.
5. Large domain versus reduced domain with absorbing boundaries.
6. Grid-aligned versus deliberately off-grid source/receiver.

## 17. Expected plots and artifacts

Produce:

1. Figure-3-style time series: radial, transverse, vertical; FD and f–k overlaid.
2. Figure-3-style Fourier amplitudes for all components.
3. Difference traces.
4. Spectral amplitude ratio FD/f–k.
5. A metadata file containing source, receiver, material, grid, dt, response, compiler, MPI layout, git revision, filter, and moment normalization.
6. Raw native-component seismograms before rotation/filtering.
7. A machine-readable metric summary.

## 18. Known blockers in current WaveQLab3D

- One-block execution has unsafe block-2 references.
- Moment-source dispatch reads nonlocal/uninitialized block objects on distributed ranks.
- The source convention and physical moment normalization are not documented sufficiently for direct SI amplitude reproduction.
- The WaveQLab3D operator/time integrator differs from the paper’s staggered-grid solver.
- No current CTest covers the elastic half-space source/receiver experiment.
- Existing frequency-Q and configurable constant-Q defects prevent a trustworthy continuation to Figures 4 and 5 without code changes.

Figure 3 can still serve as a valuable design target, but a production run should follow fixes to block ownership/source dispatch and should include explicit moment calibration.

## 19. Minimal staged execution plan

1. Fix or guard nonlocal block accesses in domain:set_rates.
2. Run a tiny two-block elastic source smoke test with bounds/FPE checks.
3. Calibrate source sign and moment normalization against f–k at low resolution.
4. Verify welded-interface transparency.
5. Run a reduced-domain 40 m test with absorbing boundaries.
6. Run the full reflection-free 40 m domain.
7. Apply the common post-processing pipeline.
8. Record quantitative acceptance metrics.
9. Only after Figure 3 passes, repair and test Q responses for Figures 4–5.

## 20. Bottom line

Figure 3 requires response = elastic. Its purpose is to validate everything except attenuation: homogeneous material, double-couple source, free surface, propagation, receiver geometry, rotation, and filtering.

The paper provides material, source, grid, time-step, receiver, and filter values but not domain extents or a complete input file. The specification above fills those gaps transparently. A paper-faithful result also requires an f–k reference, physical moment calibration, and a domain demonstrably free of artificial reflections during the comparison window.
