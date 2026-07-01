# Codex Figure 6 Test Specification Summary

## Purpose

Reproduce Figure 6 of Withers et al. (2015): f–k versus FD for a frequency-dependent-Q shallow layer over a half-space.

Detailed specification: Knowledge-base/Codex/figure_6.md

## Published model

| Layer | Thickness | Vp | Vs | Density | Qp0 | Qs0 | gamma |
|---|---:|---:|---:|---:|---:|---:|---:|
| Shallow | 1 km | 5.196 km/s | 3.000 km/s | 2.550 g/cm³ | 20 | 20 | 0.6 |
| Half-space | Infinite | 6.000 km/s | 3.464 km/s | 2.700 g/cm³ | 210 | 210 | 0.6 |

Use fT = fref = 1 Hz.

Reuse the Figure 3 source and receiver:

    source = (0,0,1.8) km
    receiver = (12,9,0) km
    dx = 0.04 km
    dt = 0.002 s

Use a 7 s window. A conservative inferred domain is x,y = -20 to 35 km and z = 0 to 25 km; verify all artificial reflected paths lie outside the retained window.

## Required response

Corrected:

    response = 'frequency-Q-8M'
    Qp0 = Qs0 = 20 for z < 1 km
    Qp0 = Qs0 = 210 for z >= 1 km
    gamma = 0.6
    f_trans = 1
    fref = 1

The model requires spatial Q fields or explicit layer parameters.

## Current blocker

WaveQLab3D uses Qs = c Vs with one global c and Qp = 2 Qs.

Required c values would be:

    top:    20/3.0 = 6.6667
    bottom: 210/3.464 = 60.6236

One c cannot match both, and Qp would still be wrong. f_trans and weight normalization are also defective.

## Material setup

Do not use existing LOH1; its values and interface direction differ.

Add a dedicated z-layer material initializer or provide distributed lambda/mu/rho volumes. Q fields need a separate implementation.

## Paper-specific numerical detail

The paper uses coarse-grained effective Q:

- harmonic treatment in the low-Q shallow layer;
- arithmetic treatment in the underlying half-space.

A conventional all-mechanisms-per-point implementation should refit each layer and validate against the same f–k complex modulus.

## Acceptance

Paper reports:

| Interval | Envelope misfit | Phase misfit |
|---|---:|---:|
| First 5 s | <= 5% | <= 2% |
| Later surface waves | 8–10% | about 2% |

Also verify:

- exact Table 3 profile;
- grid-aligned 1 km interface;
- Q error <= 5% in both layers;
- correct Love/Rayleigh waves;
- no Q smoothing unless declared;
- MPI and boundary independence.
