# Frequency-Dependent Q: Technical Notes

## Source

Kyle B. Withers, Kim B. Olsen, and Steven M. Day, “Memory-Efficient Simulation of Frequency-Dependent Q,” *Bulletin of the Seismological Society of America*, 105(6), 3129–3142, December 2015. DOI: 10.1785/0120150020.

This report summarizes the supplied PDF and translates its results into implementation guidance for time-domain wave-propagation codes, particularly WaveQLab3D.

## 1. Executive summary

The paper develops a memory-variable representation of seismic attenuation whose quality factor is constant below a transition frequency and increases as a power law above it. Eight relaxation mechanisms reproduce the target Q spectrum and its causal velocity dispersion generally within 5% across 0.1–10 Hz.

The method supports two implementations:

- Conventional: all relaxation mechanisms are stored and updated at every applicable stress point.
- Coarse-grained: mechanisms are spatially distributed over a repeating cell, reducing attenuation-state memory and arithmetic.

For weak attenuation, the weights are found with nonnegative linear least squares and scale inversely with the desired reference Q. For stronger attenuation, especially in a coarse-grained medium, the authors fit effective Q nonlinearly and use a compact interpolation in 1/Q and 1/Q².

Finite-difference results agree closely with frequency–wavenumber solutions for uniform and layered models. In simulations of the 2008 Mw 5.4 Chino Hills earthquake, frequency-dependent Q better preserves observed high-frequency energy at regional distance; constant Q becomes too attenuating above 1 Hz.

## 2. Motivation

The quality factor Q is inversely related to intrinsic seismic attenuation. Low Q produces strong loss; high Q produces weak loss. Anelasticity changes both amplitude and phase velocity.

Constant Q is often an acceptable approximation below roughly 1 Hz. At higher frequencies, regional observations commonly show Q increasing with frequency. Extending a low-frequency constant Q to several hertz consequently removes too much high-frequency energy, particularly after waves propagate many wavelengths.

This matters as 3-D simulations approach 10 Hz:

- intrinsic losses accumulate over more wavelengths;
- source roughness and material heterogeneity generate broadband motion;
- regional amplitude prediction becomes sensitive to the assumed Q spectrum;
- incorrect Q also produces incorrect dispersion and arrival phase.

## 3. Target Q model

The general power-law model is:

    Q(f) = Q0 (f/f0)^gamma

The paper uses a piecewise target:

    Q(f) = Q0                         for 0 < f < fT
    Q(f) = Q0 (f/fT)^gamma            for f > fT

where:

- Q0 is the low-frequency quality factor;
- fT is the transition frequency;
- gamma is between 0 and 1;
- gamma = 0 recovers constant Q.

Larger gamma means Q rises faster, so less high-frequency energy is removed. The examples use fT = 1 Hz and smooth the transition over approximately 0.8–1.2 Hz. A finite sum of smooth relaxation peaks cannot exactly fit a sharp change in slope.

## 4. Memory-variable formulation

### 4.1 Constitutive approximation

Direct evaluation of a viscoelastic stress–strain convolution requires strain history and is prohibitively expensive for large 3-D simulations. The memory-variable method replaces the history with N local first-order state variables.

In schematic scalar form:

    sigma(t) = Mu [epsilon(t) - sum_k xi_k(t)]

Each memory variable obeys:

    tau_k d(xi_k)/dt + xi_k = lambda_k epsilon

Here Mu is the unrelaxed modulus, tau_k is a relaxation time, and lambda_k is its weight. Each mechanism contributes a Debye-shaped attenuation peak centered near the inverse relaxation time. Their weighted sum approximates the target Q(f).

This converts a nonlocal constitutive law into ordinary differential equations advanced alongside the wavefield.

### 4.2 Discrete evolution

The decay over a time increment dt can be integrated with an exponential recurrence:

    xi_k(new) = exp(-dt/tau_k) xi_k(old)
                + lambda_k [1 - exp(-dt/tau_k)] epsilon

Exact indexing depends on the solver’s stress/strain staggering. Retaining the exponential relaxation factor is preferable to an unnecessarily crude explicit decay approximation.

### 4.3 Three-dimensional isotropic form

For isotropic elasticity, memory stresses are evolved for the stress tensor with separate bulk and shear forcing. The total stress is the unrelaxed elastic stress minus the memory-stress sum.

The paper assumes bulk and shear Q have the same frequency dependence while allowing different Q0 values. At high Q, one normalized spectral shape can therefore be scaled separately for bulk and shear attenuation. At low Q, or when bulk and shear spectra differ in shape, separate weight sets are required.

### 4.4 Modulus and reference-frequency correction

Input seismic velocities normally describe phase velocity at a finite reference frequency, not the unrelaxed infinite-frequency velocity. Anelastic dispersion therefore requires correction of the unrelaxed bulk and shear moduli so the modeled phase velocity matches the requested velocity at the reference frequency.

This correction is essential. Adding loss terms without it may produce plausible amplitude decay but incorrect phase velocity and arrival times.

## 5. Relaxation times

The authors use eight relaxation times distributed uniformly in logarithmic time:

    ln(tau_k) = ln(tau_m)
                + (2k - 1)/16 [ln(tau_M) - ln(tau_m)],
    k = 1,...,8

The relaxation band extends beyond the simulation band to improve accuracy near its edges.

For the paper’s 0.1–10 Hz band and fT = 1 Hz:

| gamma | tau_m (s) | tau_M (s) |
|---:|---:|---:|
| 0.0–0.6 | 0.0032 | 15.9155 |
| 0.7–0.8 | 0.0066 | 3.9789 |
| 0.9 | 0.0085 | 3.9789 |

The lower relaxation limit is adjusted for high gamma to improve the fit. Mechanism placement is therefore part of the calibrated model, not a universal constant.

To move the transition from 1 Hz to another fT, divide all relaxation times by the desired frequency-shift factor. The normalized weights remain unchanged.

## 6. Weight fitting

### 6.1 High-Q regime

For weak loss, nominally Q > 200, a low-loss approximation makes inverse Q linear in the weights. The authors use constrained nonnegative least squares.

Nonnegative weights are physically important: negative weights would introduce gain rather than dissipation. The fit is normalized at Q0* = 1, then scaled:

    lambda_k(Q0) = lambda_k(Q0*) Q0*/Q0

One fitted shape for each gamma can therefore support arbitrary sufficiently high Q0. Relaxation times determine the spectral position of the loss peaks, while inverse-Q0 scaling determines their magnitude.

The cited formulation also requires the scaled weight sum to remain below one for stability.

### 6.2 Low-Q coarse-grained regime

The low-loss approximation becomes inaccurate as attenuation increases. Coarse graining also changes the effective response; the harmonic average of the moduli is more accurate than directly averaging Q.

For approximately 15 <= Q < 200, the authors:

1. fit effective Q through constrained nonlinear least squares;
2. solve weights for every integer Q from 15 through 220;
3. fit two coefficients per mechanism to:

       lambda_k(Q) = a_k/Q² + b_k/Q

Table 2 in the paper provides a_k and b_k for gamma from 0.0 through 0.9. This compact formula replaces a large lookup table.

Low-Q, high-gamma cases are hardest to fit near the transition. The reported errors are generally within 5%, though the most difficult combinations approach that limit.

## 7. Conventional versus coarse-grained storage

### Conventional form

Every stress point carries all eight mechanisms. Storage and work scale directly with the mechanism count. This is simple and locally homogeneous.

### Coarse-grained form

The eight mechanisms are distributed over a period-two 3-D cell. Because 2³ = 8, each stress point carries one mechanism instead of eight. The cell’s effective response approximates the target medium.

For this pattern:

    w_k = 8 lambda_k

This normalization distinction is critical. A table of coarse-grained w_k values cannot be inserted unchanged into a conventional all-mechanisms-per-point implementation.

Benefits:

- approximately one-eighth of the attenuation-state storage for eight mechanisms;
- fewer relaxation updates at each point;
- suitability for large memory-bound 3-D calculations.

Costs:

- microscopic periodic heterogeneity;
- the need to fit effective Q, especially at low Q;
- additional care at material discontinuities;
- deterministic mechanism assignment across MPI partitions;
- possible interactions with grid, source, or output periodicity.

The spectral-fitting method itself is not restricted to coarse graining; the same relaxation spectrum can be used conventionally.

## 8. Published coefficient tables

Table 1 supplies coarse-grained weights w_k = 8 lambda_k for Q0 = 1 and gamma = 0.0–0.9. These are normalized spectral shapes and must be scaled to the requested Q0. Table 2 supplies the low-Q interpolation coefficients.

Implementation rules:

1. Select the gamma model.
2. Construct eight log-spaced relaxation times from tau_m and tau_M.
3. Scale the relaxation times if fT differs from 1 Hz.
4. Scale high-Q weights by inverse Q0.
5. Use the nonlinear interpolation coefficients in the low-Q regime.
6. Divide coarse-grained w_k by eight for conventional storage.
7. Verify nonnegativity, the weight-sum bound, and realized Q(f).

Several fitted weights are nearly zero, particularly for high gamma. This suggests that another relaxation placement could cover a wider band, but any altered layout requires refitting and verification.

For gamma values between published columns, interpolation may be tempting but was not established by the paper’s tests. Refitting the exact target is safer.

## 9. Numerical implementation used in the paper

The authors used:

- a scalable staggered-grid velocity–stress finite-difference solver;
- fourth-order spatial accuracy;
- second-order temporal accuracy;
- eight relaxation mechanisms;
- period-two coarse-grained placement;
- one mechanism per stress node.

The reference frequency–wavenumber solver used the same complex frequency-dependent modulus. This is important because the comparison tests amplitude loss and causal dispersion together.

## 10. Verification experiments

The point source was a buried right-lateral double couple at 1.8 km depth with a 0.2 s cosine-bell moment-rate function and moment 10^16 N·m, approximately Mw 4.6. The finite-difference grid used 40 m spacing and a 0.002 s step.

Finite-difference and frequency–wavenumber solutions were compared for:

- an elastic half-space;
- a constant-Q half-space;
- a frequency-dependent half-space with gamma = 0.6;
- a layered frequency-dependent model with a shallow low-velocity layer.

The reported time histories and spectra agree closely in amplitude and phase for body and surface waves. The target Q and fitted Q are generally within 5% across 0.1–10 Hz.

Fitting Q(f) alone would not be sufficient verification. The waveform comparisons demonstrate that the implementation also reproduces the required dispersion.

## 11. Chino Hills application

The authors modeled the 29 July 2008 Mw 5.4 Chino Hills, California, earthquake and compared synthetics with 110 strong-motion stations. They contrasted constant Q (gamma = 0) with a frequency-dependent model (gamma = 0.8).

Key observations:

- Below about 1 Hz, results are similar by construction.
- Differences grow with frequency and propagation distance.
- Near the fault, source and structural uncertainty can dominate.
- In the 1–4 Hz band, the power-law model retains more energy.
- Beyond roughly 25 km, the power-law model better follows observed amplitude decay.
- Near 3.5 Hz, constant Q predicts amplitudes approximately three to five times smaller than observations and the gamma = 0.8 model.
- At a 0.4 s period, power-law Q better matches distance decay; at a 3 s period, both models are nearly identical.

The comparison supports frequency-dependent intrinsic attenuation but cannot uniquely separate it from elastic scattering, site effects, source uncertainty, velocity-model error, and topography.

## 12. Accuracy and validity limits

- Fits are generally within 5% over two decades and often two to three decades.
- Fixed relaxation times limit accuracy near sharp spectrum features.
- Low Q and high gamma are the hardest combination.
- Better spectral fit does not automatically guarantee better coarse-grained time-domain behavior.
- Coefficients cover gamma = 0.0–0.9.
- The paper argues gamma > 1 is incompatible with the high-frequency shape of the Debye spectrum.
- The coarse-grained low-Q fit extends to approximately Q = 15.
- Extrapolation outside the fitted Q, gamma, or frequency ranges requires independent validation.

## 13. Implementation recipe

1. Specify Qp0, Qs0, gamma, fT, reference frequency, and simulation bandwidth.
2. Choose conventional or coarse-grained storage.
3. Choose or refit relaxation times extending beyond the working band.
4. Obtain nonnegative weights with the appropriate high- or low-Q procedure.
5. Convert coarse-grained and conventional weight normalization correctly.
6. Correct the unrelaxed bulk and shear moduli for the reference-frequency velocities.
7. Allocate memory stresses and their temporal rates.
8. Add memory forcing consistently to every stress-rate kernel, including PML and curvilinear paths.
9. Advance memory state consistently with the elastic time integrator.
10. Validate complex modulus, Q(f), phase velocity, waveform amplitude, and phase.

## 14. Recommended tests

### Material-point tests

- Target versus realized Q(f) over and outside the working band.
- Phase velocity relative to the requested reference-frequency velocity.
- Weight nonnegativity and sum constraint.
- Inverse-Q0 scaling in the high-Q regime.
- Low-Q interpolation versus directly optimized weights.

### Wave tests

- Homogeneous plane-wave amplitude and phase decay.
- Half-space point source versus a frequency-domain solution.
- Layered body- and surface-wave comparison.
- Grid and time-step convergence.
- Conventional versus coarse-grained equivalence.
- Discontinuous-Q material interface.
- PML tests separating attenuation from boundary absorption.

### Parallel tests

- Mechanism placement independent of MPI decomposition.
- One-rank and multi-rank waveform/energy agreement.
- Restart reproducibility including every memory variable.

## 15. Relevance to WaveQLab3D

The paper maps directly to the existing attenuation implementation:

- datatypes.f90 stores relaxation parameters, inverse-Q fields, and stress memory variables.
- material.f90 initializes attenuation models and weights.
- RHS_Interior.f90 applies ordinary and PML attenuation kernels.
- fields.f90 scales and updates memory-variable rates during Runge–Kutta stages.
- withers_tables.f90 is the natural home for the published coefficient data.

WaveQLab3D appears to store every mechanism at every point, which is the conventional form. Published coarse-grained weights therefore require division by eight unless the source table or loading code has already converted them. That convention should be documented beside the data and checked with a computed-Q test.

Three checks are especially important:

1. ordinary and PML paths must use identical constitutive parameters;
2. input velocities need the reference-frequency modulus correction;
3. tests must verify both attenuation and dispersion, not merely reproduce a coefficient table.

## 16. Conclusions

Eight memory-variable relaxations can approximate a Q spectrum that is constant at low frequency and increases as a power law at high frequency to about 5% across a broad band. High-Q weights scale simply with inverse Q0. Low-Q coarse-grained models require nonlinear effective-medium fitting and interpolation.

The approach is compact and practical, but it is not merely an amplitude damping term. Relaxation placement, weights, modulus correction, coefficient normalization, temporal integration, stability, and causal dispersion form one constitutive model and must be implemented and tested together.

For regional high-frequency simulation, constant Q can substantially underpredict amplitudes. The Chino Hills example shows that frequency-dependent Q retains high-frequency energy in a manner more consistent with observations, while also emphasizing that intrinsic attenuation cannot be interpreted independently of scattering and structural uncertainty.
