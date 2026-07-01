# Test Setup for Figure 5 from Withers et al. (2015)

This document specifies how to configure WaveQLab3D to replicate the frequency-dependent Q verification case (Figure 5) from the Withers, Olsen, and Day (2015) paper.

## 1. Purpose of the Test Case

Figure 5 validates the implementation of a frequency-dependent Q model. It compares the finite-difference solution against the f-k solution for a half-space where Q increases with frequency according to a power law.

## 2. Physical and Numerical Setup

The setup is identical to Figure 3, except for the attenuation model.

- **Domain, Source, Grid, Time Step:** Same as Figure 3.
- **Physics:** Anelastic with frequency-dependent Q.
  - **Q Model:** Q(f) = Q₀(f/fT)<sup>γ</sup> for f > fT
  - **Parameters:** Q₀s = 100, Q₀p = 200, γ = 0.6, fT = 1.0 Hz.

## 3. WaveQLab3D Configuration

### `&problem_list` Namelist

```fortran
&problem_list
  response = 'frequency-Q-8M' ! Selects 8-mechanism frequency-dependent Q model.
  ...
/
```

### `&anelastic_list` Namelist

```fortran
&anelastic_list
  Q_op_f_trans = 1.0  ! Transition frequency in Hz
  Q_op_gamma   = 0.6  ! Power-law exponent
  ! Qs_inv and Qp_inv are used for the low-frequency Q0 values
  Qs_inv       = 0.01 ! 1/100
  Qp_inv       = 0.005! 1/200
/
```