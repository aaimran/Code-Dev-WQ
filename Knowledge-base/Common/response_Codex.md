# Codex Summary: WaveQLab3D Response Options

## Scope

Analyzed Codex/WQ/src response selection, parameters, constitutive initialization, RHS/PML kernels, Runge–Kutta state handling, plastic correction, and tests.

Detailed report: Knowledge-base/Codex/response.md

## Accepted values

| Response | Meaning |
|---|---|
| elastic | Pure elastic velocity–stress propagation |
| plastic | Elastic propagation plus end-of-step plastic correction |
| anelastic | Legacy four-mechanism attenuation |
| low-pass | Exact alias of anelastic |
| anelastic-Q | Fixed four-mechanism constant-Q model |
| anelastic-Q8 | Fixed eight-mechanism constant-Q model |
| anelastic-Qf | Four-mechanism frequency-dependent model |
| frequency-Q-4M | Exact alias of anelastic-Qf |
| constant-Q-4M | Configurable four-mechanism constant-Q model |
| constant-Q-8M | Configurable eight-mechanism constant-Q model |
| frequency-Q-8M | Eight-mechanism frequency-dependent model |

## Common attenuation behavior

Attenuation options add six memory-variable families, one per stress component. Four-mechanism models add 48 state/rate reals per point; eight-mechanism models add 96, plus two inverse-Q fields. State is advanced with every Runge–Kutta stage, with separate ordinary and PML kernels.

The storage is conventional—all mechanisms at every point—not Withers coarse graining.

## Main parameters

| Parameter | Used by | Meaning/actual behavior |
|---|---|---|
| c | All attenuation models | Qs = c times Vs; Qp = 2 Qs |
| fref | All attenuation models | Reference frequency for unrelaxed-modulus correction |
| weight_exp | anelastic/low-pass | Selects only hard-coded exponent neighborhoods near 0 or 0.6 |
| gamma | Frequency-Q | Withers table interpolation, clamped to 0–0.9 |
| f_trans | Frequency-Q | Intended transition frequency; currently unused |
| fmin/fmax | Configurable constant-Q | Relaxation design band |
| target_Q | Configurable constant-Q | Weight-fitting target, separate from c-derived local Q |
| weight_method | Configurable constant-Q | nnls, withers, or lookup |
| manual_weights | Configurable constant-Q | Override only when every entry is positive |
| plastic_model | plastic | scec or implicit default branch |
| mu_beta_eta | plastic | Friction, dilatancy, viscosity parameters |

## Critical findings

1. f_trans has no effect: it is read and stored but never used.
2. Frequency-Q asks the Withers table for Q = 1, which is clamped to Q = 15, then multiplies weights by local inverse Q again.
3. One RHS site calls the constant-Q dispatcher twice, doubling attenuation work/contribution for those points.
4. Configurable constant-Q mixes target_Q-dependent weights with separate c-derived inverse-Q scaling.
5. lookup weight scaling grows with target_Q rather than inverse target_Q.
6. withers computes but ignores its band scale factor and does not honor target_Q.
7. Legacy anelastic accepts unsupported weight_exp values that leave zero tau and risk division by zero.
8. Plastic mu_beta_eta is undefined for several problem/default-model combinations.
9. Current response examples use a different namelist schema and no response test is registered in CMake.

## Design concerns

- Eight-mechanism modes set four-mechanism flags and rely on allocated-array detection.
- Dedicated 8M flags are largely unused by RHS/update dispatch.
- Alias names imply distinctions that do not exist.
- Qp = 2 Qs is hard-coded.
- gamma is silently clamped.
- c semantics are inconsistent in comments.
- Attenuation calls and ordinary/PML formulas are heavily duplicated.
- A single response string prevents combined attenuation plus plasticity.

## Recommended order

1. Remove duplicate dispatch.
2. Repair f_trans scaling.
3. Establish one normalized-weight/local-Q convention.
4. Convert Withers coarse weights correctly for conventional storage.
5. Fix plastic and legacy parameter initialization.
6. Replace overlapping flags/allocation dispatch with an enum and one select case.
7. Add centralized parameter validation and master-rank parameter reporting.
8. Add Q spectrum, dispersion, PML, plastic, and MPI regression tests.

## Bottom line

The fixed elastic and memory-variable plumbing is substantial, but several advertised response parameters and newer Q options are not scientifically trustworthy without repair and verification. The immediate priorities are dispatch correctness, Q/weight normalization, transition-frequency behavior, and response-specific tests.
