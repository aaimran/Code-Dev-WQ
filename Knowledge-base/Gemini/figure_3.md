# Test Setup for Figure 3 from Withers et al. (2015)

This document specifies how to configure a WaveQLab3D simulation to replicate the elastic verification case presented in Figure 3 of the Withers, Olsen, and Day (2015) paper on frequency-dependent Q.

## 1. Purpose of the Test Case

Figure 3 serves as a baseline validation of the underlying finite-difference code. It compares the code's output for a purely **elastic (infinite Q)** half-space against a semi-analytic solution from a frequency-wavenumber (f-k) code. The goal is to demonstrate that the numerical method accurately reproduces wave propagation before any attenuation physics is added.

## 2. Physical and Numerical Setup

The parameters for the simulation are described in the "Numerical Implementation" section of the paper.

- **Domain:** Uniform half-space.
- **Physics:** Purely elastic (infinite Q).
- **Source:** Buried double-couple point source.
  - **Moment:** 10¹⁶ N·m (Mw ≈ 4.6)
  - **Mechanism:** Strike 90°, Dip 90°, Rake 0°
  - **Time Function:** Cosine bell with a duration of 0.2 s.
- **Discretization:**
  - **Grid Spacing:** 40 m
  - **Time Step:** 0.002 s

## 3. WaveQLab3D Configuration

To run this scenario in WaveQLab3D, the key namelist parameters must be set as follows. This configuration deactivates all attenuation and plasticity models, running the solver in its base elastic mode.

### `&problem_list` Namelist

The most critical parameter is `response`, which must be set to `'elastic'`.

```fortran
&problem_list
  response = 'elastic'  ! Selects pure elastic physics, disabling all attenuation models.
  ! Other parameters for time step, grid dimensions, etc.
/
```

### Other Namelists

- **`&anelastic_list`, `&constant_Q_4M_list`, etc.:** These namelists for attenuation parameters are ignored when `response` is set to `'elastic'`.
- **`&plastic_list`:** The plasticity model is also disabled.
- **Source and Grid:** The moment tensor source parameters and grid parameters must be set to match the physical setup described above. This involves configuring the appropriate source type in the `&moment_list` and setting the grid dimensions and spacing in the `&block_list`.