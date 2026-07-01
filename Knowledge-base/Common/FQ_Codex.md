# Codex Summary: Memory-Efficient Frequency-Dependent Q

## Source

Withers, K. B., K. B. Olsen, and S. M. Day (2015), “Memory-Efficient Simulation of Frequency-Dependent Q,” *Bulletin of the Seismological Society of America*, 105(6), 3129–3142. DOI: 10.1785/0120150020.

Source PDF: Knowledge-base/Common/FQ.pdf  
Detailed notes: Knowledge-base/Codex/FQ.md

## Problem

Constant Q is often adequate below about 1 Hz but can over-attenuate regional motion at higher frequencies. The paper models:

    Q(f) = Q0                         for f < fT
    Q(f) = Q0 (f/fT)^gamma            for f > fT

Q0 controls loss, fT is the transition frequency, and gamma controls the high-frequency increase in Q.

## Core method

The viscoelastic history integral is replaced with first-order memory variables:

    tau_k d(xi_k)/dt + xi_k = lambda_k epsilon

Each of eight relaxation mechanisms contributes a Debye attenuation peak. Nonnegative fitted weights superpose to approximate target Q(f) and its causal dispersion.

| Regime | Weight strategy |
|---|---|
| High Q, approximately Q > 200 | Nonnegative linear least squares; normalized weights scale as 1/Q0 |
| Low Q, approximately 15 <= Q < 200 | Nonlinear effective-Q fit and lambda_k = a_k/Q² + b_k/Q interpolation |

Changing transition frequency scales the relaxation times, not the normalized weights.

## Conventional versus coarse-grained

- Conventional: all eight mechanisms are evaluated at every stress point.
- Coarse-grained: the mechanisms are distributed over a period-two 3-D cell, leaving one mechanism per point.

For the eight-cell coarse pattern:

    w_k = 8 lambda_k

Confusing coarse-grained w_k with conventional lambda_k changes the attenuation strength by a factor of eight.

## Principal results

- Eight mechanisms generally fit the target within 5% over 0.1–10 Hz.
- Half-space and layered finite-difference solutions closely match frequency–wavenumber solutions in amplitude and phase.
- Body and surface waves are both reproduced.
- Low-Q, high-gamma models are hardest near the transition frequency.
- Weights must be nonnegative and satisfy the formulation’s stability bound.
- Unrelaxed moduli must be corrected to preserve input velocities at their reference frequency.

## Chino Hills result

For the 2008 Mw 5.4 Chino Hills earthquake:

- constant-Q and power-law-Q results are similar below 1 Hz;
- differences increase with frequency and distance;
- beyond roughly 25 km, frequency-dependent Q better follows observed high-frequency amplitude decay;
- near 3.5 Hz, constant Q underpredicts amplitude by about a factor of three to five relative to observations and the gamma = 0.8 model.

This supports frequency-dependent intrinsic attenuation but does not uniquely separate it from scattering, source, site, topographic, and structural effects.

## Implementation checklist

1. Specify Qp0, Qs0, gamma, fT, reference frequency, and simulation band.
2. Choose conventional or coarse-grained storage.
3. Select or refit relaxation times extending beyond the working band.
4. Fit nonnegative weights using the appropriate Q regime.
5. Convert coarse and conventional normalization correctly.
6. Correct unrelaxed moduli for reference-frequency velocity.
7. Integrate memory variables consistently with wavefield and PML updates.
8. Verify Q(f), phase velocity, amplitude decay, stability, and MPI invariance.

## WaveQLab3D relevance

WaveQLab3D has corresponding state and kernels in datatypes.f90, material.f90, RHS_Interior.f90, fields.f90, and withers_tables.f90. Its apparent all-mechanisms-per-point layout is conventional, so published coarse-grained weights require normalization review before use.

Highest-value tests:

- realized versus target Q spectrum;
- reference-frequency phase velocity;
- half-space waveform comparison with a frequency-domain solution;
- ordinary versus PML kernel consistency;
- four- versus eight-mechanism accuracy;
- MPI-partition invariance.

## Bottom line

The paper provides a compact way to model Q that is constant at low frequency and rises at high frequency. It is a complete constitutive model, not an amplitude-only correction: weights, relaxation times, modulus correction, dispersion, integration, and normalization must remain consistent.
