# Test Setup for Figure 4 from Withers et al. (2015)

This document specifies how to configure WaveQLab3D to replicate the constant-Q verification case (Figure 4) from the Withers, Olsen, and Day (2015) paper.

## 1. Purpose of the Test Case

Figure 4 validates the attenuation implementation for a frequency-independent Q model. It compares the finite-difference solution for a constant-Q half-space against the semi-analytic f-k solution. This test isolates the effect of constant-Q attenuation, using the elastic case from Figure 3 as a baseline.

## 2. Physical and Numerical Setup

The setup is identical to Figure 3, except for the introduction of attenuation.

- **Domain, Source, Grid, Time Step:** Same as Figure 3.
- **Physics:** Anelastic with constant Q.
  - **Q Model:** Qp = 400, Qs = 200.

## 3. WaveQLab3D Configuration

To enable constant-Q attenuation, the `response` parameter must be changed, and the relevant Q namelist must be provided.

### `&problem_list` Namelist

```fortran
&problem_list
  response = 'constant-Q-8M' ! Selects 8-mechanism constant-Q model.
  ...
/
```

### `&constant_Q_8M_list` Namelist

```fortran
&constant_Q_8M_list
  Qp_inv = 0.0025 ! 1/400
  Qs_inv = 0.0050 ! 1/200
/
```