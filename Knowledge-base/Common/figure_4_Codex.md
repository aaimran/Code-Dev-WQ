# Codex Figure 4 Test Specification Summary

## Purpose

Reproduce Figure 4 of Withers et al. (2015): f–k versus FD for a constant-Q homogeneous half-space.

Detailed specification: Knowledge-base/Codex/figure_4.md

## Setup

Use the complete Figure 3 geometry, source, receiver, grid, time step, boundaries, and processing unchanged.

| Parameter | Value |
|---|---:|
| Vp | 6.000 km/s |
| Vs | 3.464 km/s |
| Density | 2.700 g/cm³ |
| Qp0 | 50 |
| Qs0 | 50 |
| gamma | 0.0 |
| Reference/transition frequency | 1 Hz |
| Grid spacing | 0.040 km |
| Time step | 0.002 s |
| Source | 90/90/0 double couple at (0,0,1.8) km |
| Receiver | (12,9,0) km |
| Filter | Fourth-order zero-phase 0.2–10 Hz Butterworth |

## Response

Required corrected setup:

    response = 'frequency-Q-8M'
    Qs0 = 50
    Qp0 = 50
    gamma = 0
    f_trans = 1 Hz
    fref = 1 Hz

The current namelist lacks independent Qs0/Qp0 inputs.

## Current blocker

WaveQLab3D computes Qs = c Vs and forces Qp = 2 Qs. Setting c = 50/3.464 = 14.43418 gives Qs = 50 but Qp = 100, not the paper model.

Additional blockers:

- Q = 1 Withers request is clamped to 15 and then inverse-Q scaled again;
- coarse-grained table weights are used with conventional storage;
- configurable constant-Q has duplicate dispatch and ambiguous target_Q scaling.

## Required implementation

1. Support independent Qp and Qs.
2. Establish one weight normalization.
3. Use conventional fitted weights or implement paper-faithful coarse graining.
4. Correct unrelaxed moduli at 1 Hz.
5. Remove duplicate dispatch.
6. Verify realized Q and dispersion before the wave test.

## Acceptance

The paper reports:

- envelope misfit below 6%;
- phase misfit below 2%.

Also require Qp(f), Qs(f), phase velocity, waveform, Fourier amplitude, MPI invariance, and boundary independence checks.
