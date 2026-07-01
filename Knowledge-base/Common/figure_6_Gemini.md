# Test Setup for Figure 6 from Withers et al. (2015)

This document specifies how to configure WaveQLab3D to replicate the layered, frequency-dependent Q verification case (Figure 6) from the Withers, Olsen, and Day (2015) paper.

## 1. Purpose of the Test Case

Figure 6 validates the attenuation implementation in a more complex, heterogeneous scenario. It models a low-velocity layer over a half-space, with different frequency-dependent Q properties in each layer. This tests the code's ability to handle sharp contrasts in both velocity and attenuation.

## 2. Physical and Numerical Setup

This test introduces a layered material model.

- **Source, Receiver, Grid, Time Step:** Same as Figure 3.
- **Material Model:**
  - **Layer 1 (Top):** 0-1 km depth. Vp=4.0 km/s, Vs=2.3 km/s, ρ=2.3 g/cm³, Q₀s=50, Q₀p=100, γ=0.6.
  - **Layer 2 (Bottom):** >1 km depth. Vp=6.0 km/s, Vs=3.464 km/s, ρ=2.7 g/cm³, Q₀s=100, Q₀p=200, γ=0.6.
- **Physics:** Anelastic with frequency-dependent Q, varying by layer.

## 3. WaveQLab3D Configuration

This requires a material file instead of hardcoded values.

### `&problem_list` Namelist

```fortran
&problem_list
  response        = 'frequency-Q-8M'
  material_source = 'file'
  mesh_source     = 'file' ! To read material file
  ...
/
```

### Material File

A material file must be created that defines the two layers with their respective elastic and anelastic properties (Vp, Vs, rho, Qp_inv, Qs_inv). The `Q_op_gamma` and `Q_op_f_trans` from the `&anelastic_list` namelist would apply globally.