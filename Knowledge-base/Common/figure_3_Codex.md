# Codex Figure 3 Test Specification Summary

## Reference assumption

FD.md is absent from the workspace. “Figure 3” is interpreted as Figure 3 of Withers, Olsen, and Day (2015), supplied as Knowledge-base/Common/FQ.pdf.

Detailed specification: Knowledge-base/Codex/figure_3.md

## Test purpose

Compare a three-component finite-difference elastic half-space solution against an f–k reference. This is the no-attenuation baseline required before constant-Q or frequency-dependent-Q tests.

## Published parameters

| Item | Value |
|---|---|
| Medium | Homogeneous isotropic elastic half-space |
| Vp | 6.000 km/s |
| Vs | 3.464 km/s |
| Density | 2.700 g/cm³ |
| Source | Right-lateral double couple |
| Strike/dip/rake | 90/90/0 degrees |
| Source depth | 1.8 km |
| Moment | 10^16 N m, approximately Mw 4.6 |
| Source time | 0.2 s cosine-bell moment rate |
| Grid spacing | 0.040 km |
| Time step | 0.002 s |
| Receiver range | 15 km horizontally |
| Receiver azimuth | 53.13 degrees from north |
| Receiver coordinate | (12, 9, 0) km for x east/y north/z down |
| Filter | Fourth-order 0.2–10 Hz bandpass |
| Components | Radial, transverse, vertical |

Expected direct arrivals:

    tP approximately 2.518 s
    tS approximately 4.361 s

## WaveQLab3D response

Use:

    response = 'elastic'

Do not include an attenuation namelist. Confirm all attenuation flags are false and no memory-variable arrays are allocated.

Figure 3 must not use anelastic, low-pass, constant-Q, or frequency-Q. Those responses alter both amplitude and phase and defeat the elastic-control purpose.

## Recommended WaveQLab3D setup

Current one-block/source ownership defects make a two-block homogeneous workaround safer:

| Block | x extent | Nx | lqrs | rqrs |
|---|---:|---:|---|---|
| 1 | -15 to 5 km | 501 | (1,1,2) | (0,1,1) |
| 2 | 5 to 30 km | 626 | (0,1,2) | (1,1,1) |

Shared:

    y = -15 to 30 km, Ny = 1126
    z = 0 to 20 km, Nz = 501
    rho_s_p = (2.7, 3.464, 6.0)
    coupling = 'locked'
    type_of_mesh = 'cartesian'
    fd_type = 'upwind'
    order = 4
    CFL = 0.34641016
    t_final = 6.0 s

Boundary code 2 gives the z = 0 free surface, code 1 characteristic external boundaries, and code 0 the internal locked interface.

The recommended domain is inferred, not published. It is chosen so non-surface reflected P-wave paths exceed the 6 s comparison window.

## Source and receiver

Use:

    source = (0, 0, 1.8) km
    receiver = (12, 9, 0) km
    output stride = 1

For x east/y north/z down, the ideal tensor has only Mxy nonzero. A dimensional starting value is:

    Mxy = plus or minus 0.01 GPa km³

because 1 GPa km³ = 10^18 N m. The sign and source-time normalization must be calibrated against the f–k reference.

The WaveQLab3D tensor-list candidate is:

    'cosine' 0.2 0.0  0 0 0  0.01 0 0  0 0 1.8  0

The last value is the fourth-order discrete-source alpha selector; zero chooses the centered stencil. It is not the FD order.

## Component processing

For azimuth 53.13 degrees:

    radial     = 0.8 vx + 0.6 vy
    transverse = 0.6 vx - 0.8 vy

Confirm transverse sign against the f–k convention. If WaveQLab3D z is positive down and reference vertical is positive up:

    vertical_up = -vz

Apply identical filtering, tapering, sampling, and FFT normalization to FD and f–k traces. Retain raw traces.

## Acceptance checks

- dx = 0.040 km and reported dt = 0.002 s.
- Uniform Vp, Vs, and density.
- Correct source/receiver grid locations.
- Transparent locked interface.
- No artificial reflection in the comparison window.
- Arrival-time, waveform, amplitude, and spectral agreement quantified.

Suggested engineering targets:

| Metric | Target |
|---|---:|
| Cross-correlation | >= 0.98 |
| Peak amplitude difference | <= 5% |
| Band-limited L2 error | <= 5% |
| Median spectral ratio | 0.95–1.05 |

These tolerances are proposed, not stated by the paper.

## Response follow-up

After the elastic test passes:

- Figure 4 constant-Q work should use a corrected eight-mechanism constant-Q response.
- Figure 5 power-law-Q work should use a corrected frequency-Q-8M response.

Current Q responses require repair first: f_trans is ineffective, Withers Q scaling is inconsistent, coarse/conventional normalization is unresolved, and one constant-Q RHS path dispatches twice.

## Key caveats

- WaveQLab3D does not use the paper’s identical fourth-order staggered-grid/second-order-time scheme.
- Paper domain extents are not reported.
- Physical moment normalization in WaveQLab3D requires calibration.
- One-block and distributed moment-source ownership defects should be fixed before production execution.
