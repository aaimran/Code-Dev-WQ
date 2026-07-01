# WaveQLab3D Codebase Analysis (Claude/WQ/src)

**Analysis date:** 2026-06-30
**Scope:** `/gpfs/scratch/aimran/Code-Dev-WQ/Claude/WQ/src/` — 41 files, ~53,100 lines of Fortran (90/03/2008-ish, free-form), plus `CMakeLists.txt` and one stray backup file.

---

## 1. Overview

WaveQLab3D is a 3D, MPI-parallel, curvilinear, summation-by-parts (SBP) finite-difference solver for the elastodynamic wave equation, purpose-built for **dynamic earthquake rupture simulation**. It originates from Eric Dunham's group at Stanford (header credits: Eric Dunham, Kenneth Duru, Hari Radhakrishnan — `main.f90:5-8`), and is a 3D evolution of an earlier 2D code referred to internally as "KD3D" (mentioned in `datatypes.f90`'s header comment).

**Numerical method.** The solver discretizes the velocity-stress (first-order hyperbolic) form of the 3D elastodynamic wave equation:

- 9 field unknowns per grid point: 3 particle-velocity components (`F(:,:,:,1:3)`) and 6 independent stress-tensor components (`F(:,:,:,4:9)` = σxx, σyy, σzz, σxy, σxz, σyz).
- Spatial discretization uses SBP-style finite-difference stencils (traditional centered 6th-order, or upwind-biased schemes of order 2–9, plus "DRP" — dispersion-relation-preserving — variants) on a **logical unit-cube (q,r,s) coordinate system** mapped to physical (x,y,z) space via a curvilinear coordinate transformation (Jacobian `G%J`, metric arrays `G%metricx/y/z`).
- Boundary and inter-block coupling conditions are enforced weakly via **SAT (Simultaneous Approximation Term) penalty terms**, characteristic/Riemann-type formulations that subtract `tau0/h * (field − hat-field)` from the rate array (confirmed exact pattern at `RHS_Interior.f90:1637`: `B%F%DF(mx,y,z,1:n) = B%F%DF(mx,y,z,1:n) - tau0/hx*U_x(1:n)`), where `tau0` is a scheme-dependent penalty parameter hardcoded per (fd_type, order) combination in `block.f90:231-296`.
- Time integration uses a 5-stage, 4th-order, **low-storage Runge-Kutta scheme** (Carpenter-Kennedy RK4(3)5[2R+]C, see Section 4).

**Physics modeled:**
- Linear isotropic elastodynamics (Lamé parameters λ, μ, density ρ) — no anisotropic stiffness tensor support.
- Up to two curvilinear blocks ("minus"/"plus" sides) coupled across a single fault interface, with several friction laws: locked (welded), linear friction, linear slip-weakening, and rate-and-state friction (regularized aging-law style via `asinh`), implemented in `Interface_Condition.f90`.
- Off-fault bulk **plasticity** (Drucker-Prager, rate-dependent/Perzyna viscoplastic return-map) in `plastic.f90`.
- **PML** (Perfectly Matched Layer) absorbing boundaries (`pml.f90` for allocation; actual CFS-PML damping equations live in `RHS_Interior.f90`).
- Seven parallel **viscoelastic attenuation (Q) models** (generalized standard linear solid / generalized Maxwell body formulations) of increasing sophistication: `anelastic`, `anelastic-Q`, `anelastic-Q8`, `anelastic-Qf` (frequency-dependent), `anelastic-Qf8`, `constant-Q-4M`, `constant-Q-8M`.
- Point/finite seismic **moment-tensor sources** (double-couple-style earthquake sources) via regularized discrete delta functions or continuous Gaussian-smoothed body forces (`moment_tensor.f90`).
- **Method of Manufactured Solutions (MMS)** verification infrastructure (`mms.f90`) for convergence-order testing.

**Intended use case:** SCEC-style (Southern California Earthquake Center) dynamic rupture benchmark problems — the code contains extensive hardcoded parameter tables for named benchmarks: TPV5, TPV10, TPV26–TPV37, TPV101/102, LOH1, MG01/mg_a1/mg_b1a, SCITS2016, wasatch100, OKLAHOMA, and others, scattered through `material.f90`, `Interface_Condition.f90`, and `initial_stress_condition.f90`. This strongly indicates the code's primary purpose is reproducing/extending SCEC benchmark rupture simulations (and presumably real-event simulations, e.g. Oklahoma induced seismicity).

---

## 2. Build system

**`CMakeLists.txt`** (`Claude/WQ/src/CMakeLists.txt`, 182 lines) builds **two executables** from a shared pool of modules:

### Compiler flags (`CMakeLists.txt:20-36`)
Three compiler branches, selected by matching the Fortran compiler executable name:
- **gfortran**: Release = `-fdefault-real-8 -fdefault-double-8 -O5 -Wuninitialized`; Debug = adds `-Og -g -Wall -Wextra -Wconversion -fbounds-check -fbacktrace -finit-real=nan -ffpe-trap=invalid,zero,overflow -fimplicit-none -fall-intrinsics -std=f2008ts`. Note `-fdefault-real-8 -fdefault-double-8` promotes default `real` to 8 bytes — this is how `wp` (selected via `selected_real_kind(15,99)` in `common.f90`) ends up as true double precision at the compiler-flag level too (belt-and-suspenders precision control).
- **ifort**: Release = `-m64 -xHost -r8 -i4 -std08 -g -O2 -heap-arrays`; Debug = adds extensive runtime checks (`-check all,noarg_temp_created -warn all -traceback -ftrapuv -fpe0 -fp-stack-check -fltconsistency`).
- **Cray (`ftn`)**: Release = `-O2 -Oipa0 -v -V`; Debug = `-O0 -g`. Notably the Cray branch's `if`/`elseif` chain is malformed: it's written as `if (gfortran) ... elseif (ifort) ... else (ftn) ...` (`CMakeLists.txt:23,27,31`) — the final `else` branch is unconditionally taken for "anything that isn't gfortran or ifort," with a misleading trailing `(Fortran_COMPILER_NAME MATCHES "ftn.*")` annotation on the `else` that has no actual effect (cosmetic/comment-like but written as if it were a condition).
- HDF5 support is explicitly disabled: `FIND_PACKAGE(HDF5 ...)`, `HDF5_DEFINITIONS`, `HDF5_INCLUDE_DIRS` are all commented out (`CMakeLists.txt:12-15`), and `target_link_libraries(waveqlab3d ${HDF5_LIBRARIES})` is commented out (line 101). `hdf5_output.f90` is excluded from the source list (line 79, `#hdf5_output.f90`).

### Two executables
1. **`waveqlab3d`** (`WQL3D_SRC`, ~37 files) — the main solver. Source list (`CMakeLists.txt:50-83`) includes `fault_output.f90` **twice** (lines 50 and 76 — harmless CMake duplicate, not a functional issue but a list-hygiene wart).
2. **`pre_wql3d`** (`PRE_WQL3D_SRC`, 9 files: `common, datatypes, grid, preprocessor, metrics, mpi3dbasic, mpi3dcomm, mpi3dio, mpi3d_interface`) — a standalone mesh-generation preprocessor that writes binary grid files (`block_grid_<id>.X/.Y/.Z`) later consumed by `waveqlab3d` via `grid.f90:init_grid_from_file` when `mesh_source='file'`. This is a clean separation of (potentially expensive) curvilinear mesh generation from the time-stepping solver.

Both executables link only `MPI_Fortran_LIBRARIES` (no HDF5, no other external numerical libraries — the codebase has zero third-party dependencies beyond MPI).

### Testing (`CMakeLists.txt:103-164`)
`enable_testing()` defines 6 CTest cases run against `test_problems/` input files (`test_rup_cart_fric.in`, `test_rup_curv_fric.in`) with both `_premesh` (uses `pre_wql3d` output) and direct-compute mesh variants, each at 4-way MPI parallelism and serial (`n=1`). Tests invoke `cmake/run_mpi_test.cmake`/`run_test.cmake`, which `mpirun`s `waveqlab3d`, then calls a Python script `python/read_binary.py` to diff the output binary against checked-in "truth" data in `test_problems/truth/<n>/` — i.e., regression testing via binary-output comparison, not unit tests of individual subroutines.

### Documentation
`find_package(Doxygen)` conditionally adds a `docs` target using `conf/Doxyfile.in` (`CMakeLists.txt:172-181`). Consistent with this, many subroutines carry Doxygen-style `!>`/`!@brief`/`!@param` comments (quality varies significantly by file — `withers_tables.f90` and `mms.f90` are the most thoroughly documented; `metrics.f90`'s stencil coefficients have none).

---

## 3. Module map

| File | LOC | Primary purpose | Key public types / routines |
|---|---|---|---|
| `common.f90` | 9 | Floating-point kind parameters | `wp` (working precision, double), `sp`, `lp` |
| `datatypes.f90` | 344 | Central derived-type definitions (avoids circular deps) | `block_type`, `block_grid_t`, `block_material`, `block_fields`, `block_boundary`, `block_plastic`, `block_pml`, `iface_type`, `fault_type`, `domain_type`, `moment_tensor`, `mms_type`, `seismogram_type`, `slice_type`, `plane_output_type`, `block_temp_parameters` |
| `block.f90` | 526 | Per-block lifecycle: init, RHS dispatch, RK scale/update, exchange | `init_block`, `partition_block`, `set_rates_block`, `update_fields_block`, `block_time_step` |
| `boundary.f90` | 156 | `block_boundary` allocation, unit-normal setup, cross-interface exchange | `init_boundary`, `exchange_fields_across_interface`, `exchange_materials_across_interface` |
| `iface.f90` | 80 | `iface_type` allocation, RK scale/update for interface (slip/state) vars | `init_iface`, `scale_rates_iface`, `update_fields_iface` |
| `domain.f90` | 808 | Top-level domain orchestration: init, BC/interface enforcement, exchange, output dispatch | `init_domain`, `enforce_bound_iface_conditions`, `exchange_fields`, `scale_rates`, `set_rates`, `update_fields`, `write_output` |
| `main.f90` | 136 | Program entry point / time loop driver | `program main` |
| `time_step.f90` | 153 | Low-storage RK coefficients and one-step driver | `RK_type`, `init_RK`, `time_step_RK` |
| `grid.f90` | 2740 | Curvilinear/Cartesian mesh generation, metric/Jacobian computation, file I/O of meshes | `init_grid_cartesian`, `init_grid_curve`, `init_grid_from_file`, `Curve_Grid_3D3`, `derivatives` |
| `metrics.f90` | 1284 | 6th-order FD stencil library (boundary-closed + interior) for metric derivatives | `D6x/D6y/D6z`, `Dfx6/Dfy6/Dfz6`, `Dbx6/Dby6/Dbz6` |
| `material.f90` | 1820 | Isotropic elastic material model + 7 attenuation (Q) model initializers | `init_material`, `init_material_from_file`, `init_anelastic*_properties` (×7) |
| `inter_material.f90` | 315 | Lagrange interpolation of material props between grids | `interpolatematerials` |
| `plastic.f90` | 356 | Off-fault Drucker-Prager viscoplasticity | `update_fields_plastic`, `plastic_flow`, `plastic_flow2`, `yield` |
| `plastic_material.f90` | 62 | Plastic state-array allocation/init | `init_plastic_material` |
| `elastic.f90` | 32 | Thin RHS dispatcher for elastic physics | `set_rates_elastic` |
| `pml.f90` | 170 | PML auxiliary-array allocation per block face | `init_pml` |
| `unit_normals.f90` | 285 | Local orthonormal (normal, tangent) triad per boundary face | `local_orth_vectors_q/r/s`, `gen_orth_vectors`, `Gram_Schmidt` |
| `fields.f90` | 354 | `block_fields` allocation, RK scale/update (incl. all attenuation/PML state), norms | `init_fields`, `scale_rates_interior`, `update_fields_interior`, `norm_fields` |
| `RHS_Interior.f90` | 3478 | RHS assembly: interior dispatch, near-boundary stencils, BC imposition, PML physics, anelastic point-update kernels | `RHS_Center`, `RHS_near_boundaries`, `impose_boundary_condition`, `PML`, ~20 `apply_anelastic_*_point*` routines |
| `original_RHS_interior.f90` | 767 | Older/smaller version of the above (no anelastic-Q8/Qf8/4M/8M kernels) | same top-level names, narrower scope |
| `RHS_Interior.f90.bak` | 3221 | Stray backup of an intermediate `RHS_Interior.f90` (missing `Qf8`/`const_Q_8M` routines vs. current) | n/a — dead file, not referenced by CMake |
| `JU_xJU_yJU_z6.f90` | 23392 | Auto/hand-expanded SBP differentiation kernels (per-direction, per-order, per-scheme) — the actual finite-difference engine | ~30 subroutines `JJU_x{2..9}[_upwind][_drp][_interior]` |
| `BoundaryConditions.f90` | 921 | **Active** far-field boundary SAT conditions (absorbing/free-surface/clamped) | `init_boundaries`, `BC_Lx/Rx/Ly/Ry/Lz/Rz`, `BCp`, `BCm` |
| `BoundaryConditions2.f90` | 935 | **Orphaned** — older characteristic-decomposition BC implementation, not in CMakeLists | same module name `BoundaryConditions` (collides if both compiled) |
| `BoundaryConditions3.f90` | 903 | **Orphaned** — near-identical to file 1 but with the *general* (non-simplified) SAT formula active | same module name `BoundaryConditions` |
| `CouplingForcing.f90` | 607 | Geometric rotation + SAT penalty assembly for block-block fault coupling | `Couple_Interface_x`, `Rotate_in_Local_Cordinates`, `rupture_front` |
| `Interface_Condition.f90` | 2889 | Fault physics core: friction laws, prestress, nucleation, ~25 benchmark problem configs | `Interface_RHS`, `Welded_Interface`, `Linear_Friction`, `Slip_Weakening_Friction`, `rate_state_friction`, `prestress`, `Tau_strength` |
| `initial_stress_condition.f90` | 256 | Background/initial stress tensor per benchmark problem | `initial_stress_tensor` |
| `fault_output.f90` | 138 | Fault-plane time-series output (8 MPI-IO channels) | `init_fault_output`, `write_fault`, `write_hats`, `destroy_fault` |
| `seismogram.f90` | 634 | Point-receiver time-series output (ASCII) | `init_seismogram`, `write_seismogram`, `Find_Coordinates[_moment]` |
| `plane_output.f90` | 660 | 2D plane-slice output (velocity only), modern/actively maintained | `init_plane_output`, `write_plane_output`, `end_plane_output` |
| `slice_output.f90` | 103 | Older full-field (9 components) 2D slice output via distributed MPI-IO | `init_slice_output`, `write_slice`, `end_slice_output` — **dead code, never called from `domain.f90`** |
| `hdf5_output.f90` | 102 | Incomplete parallel-HDF5 scaffolding | `start_hdf_output`, `create_dataset` — **excluded from build** |
| `parallel_write.f90` | 45 | Single nearest-grid-point lookup utility | `init_seismogram_parallel` — **dead code, zero callers** |
| `moment_tensor.f90` | 1329 | Point/finite moment-tensor source injection (3 competing implementations) | `init_moment_tensor`, `set_moment_tensor`, `moment_tensor_body_force`, `set_moment_tensor_smooth`, `singular_source` |
| `withers_tables.f90` | 355 | Withers et al. (2015) GMB attenuation coefficient tables | `get_relaxation_times`, `get_withers_weights` |
| `mms.f90` | 235 | Trigonometric manufactured-solution forcing/exact-solution evaluation | `init_mms`, `eval_mms`, `mms_forcing`, `evaluate_mms[_dt/dx/dy/dz]` |
| `mpi3dbasic.f90` | 490 | MPI bootstrap, 1D load balancing, messaging/error utilities | `start_mpi`, `decompose1d`, `new_communicator`, `error`, `warning` |
| `mpi3dcomm.f90` | 781 | 3D Cartesian decomposition descriptor + intra-block halo exchange | `cartesian3d_t`, `decompose3d`, `exchange_all_neighbors`, `allocate_array_body/boundary` |
| `mpi3d_interface.f90` | 576 | Block-block interface communicator + cross-interface halo exchange | `interface3d`, `new_interface3d`, `exchange_interface_neighbors[3d]` |
| `mpi3dio.f90` | 516 | Collective MPI-IO parallel binary file I/O | `file_distributed`, `subarray`, `open/write/read/close_file_distributed` |
| `preprocessor.f90` | 124 | `pre_wql3d` standalone mesh-generation executable | `program pre_wql3d` (implicit), `write_mesh_serial`, `read_mesh_serial` (dead) |

---

## 4. Architecture / data flow

### Type hierarchy and `domain_type`
`datatypes.f90` is the single source of truth for derived types (consolidated explicitly to avoid circular `use` dependencies — see header comment, `datatypes.f90:2-6`). The hierarchy is:

```
domain_type
 ├─ B(:) : block_type        (up to 2 blocks; nblocks clamped to {1,2} — domain.f90:208-214)
 │   ├─ G  : block_grid_t    (coordinates x, metricx/y/z, Jacobian J, cartesian3d_t C)
 │   ├─ M  : block_material  (λ,μ,ρ + 7 parallel attenuation-state sub-blocks)
 │   ├─ F  : block_fields    (F = 9-component state, DF = rates)
 │   ├─ P  : block_plastic   (plastic strain/strain-rate, mu_beta_eta)
 │   ├─ MT : moment_tensor   (source params)
 │   ├─ B(6) : block_boundary (per-face: normals n_l/n_m/n_n, F/DF/Fopp/Mopp slices)
 │   ├─ PMLB(6) : block_pml  (per-face PML aux fields Q/DQ)
 │   ├─ boundary_vars : boundary_type (Lx/Rx/Ly/Ry/Lz/Rz flags — is this face a true domain boundary?)
 │   └─ tau0, rho_s_p, order, fd_type, nb  (scalar scheme parameters)
 ├─ I(:) : iface_type         (0 or 1 interfaces; direction='q' only is implemented)
 │   ├─ T, V/DV, S/DS, W/DW, Svel, trup   (traction, slip-rate, slip, state, rupture time)
 │   └─ II : interface3d     (MPI interface communicator/geometry, from mpi3d_interface)
 ├─ fault   : fault_type      (8 MPI-IO file handles + slip/Uhat/Vhat/state output buffers)
 ├─ mms_vars, seismometers(:), slicer, plane_outputs(:)  (verification/output config)
 └─ dt, t, t_final, CFL, nt, w_stride, coupling, fd_type, response, ...
```

The architecture is explicitly designed (per comments in `domain.f90:5-11`) to generalize to an arbitrary number of blocks/interfaces with unstructured connectivity, but the **current implementation hardcodes a 2-block, 1-interface, q-direction-only topology** at multiple layers: `domain.f90`'s module-level `in_block_comm(2)` etc. (sized 2), `mpi3dbasic.f90`'s requirement that `nprocs` be even or 1 (`mpi3dbasic.f90:38-42`, tied to a fixed 50/50 rank split between the two blocks), `block.f90`'s commented-out r/s-direction boundary copies (only q-direction sides 1,2 are wired up), and `mpi3d_interface.f90`'s `exchange_interface_neighbors` (2D-array variant) implicitly supporting only `normal=(±1,0,0)`.

### Time loop and RK integration
`main.f90`'s `program main` calls `init_RK` (builds a 5-stage Carpenter-Kennedy low-storage RK4 — `RK%A/B/C` rational coefficients, `time_step.f90:53-62`) and `init_domain`, then loops `do n = 1, D%nt` calling `time_step_RK(D, D%dt, RK, n)` once per full time step. Each call to `time_step_RK` (`time_step.f90:68-150`) loops over the RK stages and per stage:
1. `exchange_fields(D)` — intra-block ghost/halo exchange (one MPI `SendRecv` per field component per face, via `mpi3dcomm::exchange_all_neighbors`, called once per component from `fields::exchange_all_fields`).
2. `scale_rates(D, RK%A(stage))` — multiply existing `DF` (and interface `DS/DW`) by stage coefficient `A` (low-storage convention).
3. `set_rates(D)` — evaluate the PDE RHS: `block::set_rates_block` → `elastic::set_rates_elastic` → `RHS_Interior::RHS_Center` (dispatches to the appropriate `JJU_x{order}_interior[_upwind][_drp]` kernel in `JU_xJU_yJU_z6.f90` based on `F%fd_type`/`F%order`) + `RHS_Interior::RHS_near_boundaries` (one-sided stencils near block edges, also computes PML contributions). Moment-tensor source terms are then optionally added.
4. `exchange_fields_interface(D)` — exchange fields across the block-block interface (`mpi3d_interface::exchange_interface_neighbors`).
5. `enforce_bound_iface_conditions(D, stage)` — `block::enforce_bound_conditions` (→ `RHS_Interior::impose_boundary_condition` → `BoundaryConditions::BC_Lx/Rx/...` for true domain boundaries) and, if an interface exists, `domain::enforce_iface_conditions` (→ `RHS_Interior::Impose_Interface_Condition` / `CouplingForcing::Couple_Interface_x` → `Interface_Condition::Interface_RHS`, the friction-law solve). Both paths subtract SAT penalty terms (`tau0/h * (field − hat-field)`) directly into `DF`.
6. On `stage==1` (and every `w_stride`-th step): `write_output(D)` — fault, seismogram, and plane output. Output is deliberately tied to stage 1 because fault slip-rate/traction "rates" are only meaningful there (documented in `time_step.f90:131-136`).
7. `update_fields(D, RK%B(stage)*dt, stage, RK%nstage)` — `F = F + dt*DF` for all blocks/interfaces/PML/attenuation state; on the final stage, plasticity (`plastic::update_fields_plastic`) is applied.

### Fault rupture coupling
The fault/rupture subsystem spans three files with a clear separation of concerns: `Interface_Condition.f90` implements the **physics** — for each fault-plane grid point it computes outgoing/incoming characteristics `p = Z1*v - T`, `q = Z2*v + T` (impedance-weighted, `Z1/Z2` from local P/S wave speeds and density of the two adjacent blocks), forms the impedance-weighted stress-transfer function `phi`, and solves the friction-law constraint (`Welded_Interface` for locked, `Linear_Friction`, `Slip_Weakening_Friction` via a closed-form linear solve, or `rate_state_friction` via a `Regula_Falsi` nonlinear root find on an `asinh`-regularized rate-and-state law) to produce "hat" variables (the boundary values that exactly satisfy the interface condition). `CouplingForcing.f90` handles the **mechanics**: rotates 9-component fields into local fault-normal/strike/dip coordinates (`Rotate_in_Local_Cordinates`), calls `Interface_RHS`, rotates back, and assembles the SAT penalty forcing using full characteristic projection matrices. `fault_output.f90` is the **I/O consumer**, writing slip, slip-rate, state, rupture-time, and hat-variable time series to 8 separate MPI-IO binary channels. Rupture nucleation is forced via expanding-front time-ramps (`Time_of_Forced_Rupture`) or smooth spatio-temporal bump functions (TPV101/102-style), both in `Interface_Condition.f90`.

### MPI domain decomposition and SBP operators
`mpi3dbasic.f90` provides the foundational `decompose1d` load-balancing algorithm (handles 4 parity cases for maximally even index-range splitting) and communicator utilities (`new_communicator`, `error`/`MPI_Abort`). `mpi3dcomm.f90` builds on this with `cartesian3d_t` (per-block 3D Cartesian decomposition: global/local index ranges, ghost widths, neighbor ranks via `MPI_Cart_shift`, and a hierarchy of MPI derived datatypes for halo exchange) and `decompose3d`. `mpi3d_interface.f90` layers block-to-block interface geometry on top (finding which ranks sit on the shared fault plane and their "mirror" rank on the opposite block). The SBP differentiation operators themselves live in `JU_xJU_yJU_z6.f90` — each `JJU_x{order}[_variant]` subroutine computes the 9-component spatial derivative contribution at one (or a swath of) grid point(s), using the precomputed metric/Jacobian arrays from `grid.f90`/`metrics.f90` to apply the chain rule from logical (q,r,s) to physical (x,y,z) derivatives; `RHS_Interior.f90`'s `RHS_Center`/`RHS_near_boundaries` select the correct kernel via `F%fd_type`/`F%order` and assemble the final velocity/stress rate equations (e.g. `DU(1) = (Ux(4)+Uy(7)+Uz(8))*rhoJ_inv` for the x-velocity rate — confirmed at `RHS_Interior.f90:241`).

---

## 5. Notable design patterns and observations

- **Per-block derived-type aggregation.** Nearly every physics/numerics concern (grid, material, fields, plasticity, PML, boundary, moment-tensor source) is a sub-type nested inside `block_type`, with parallel "block-level" (`block.f90`) and "module-level" (`fields.f90`, `boundary.f90`, etc.) operational routines that mostly thin-wrap the underlying per-component routine. This produces a very regular, if verbose, call structure (`block::scale_rates_block` → `fields::scale_rates_interior`, `block::update_fields_block` → `fields::update_fields_interior`, etc.).

- **Hand-expanded/generated stencil code for performance.** `JU_xJU_yJU_z6.f90` (23,392 lines) contains ~30 large, nearly-mechanically-derived subroutines, one per (differentiation order × upwind/traditional/DRP variant × interior/near-boundary). This is the classic SBP-FD performance pattern of fully unrolling boundary-closure stencils rather than using a generic banded-operator abstraction, traded against enormous code size and duplication. `RHS_Interior.f90` (3478 lines) and its predecessor `original_RHS_interior.f90` (767 lines, only the `'traditional'`+order-6-upwind subset) follow the same pattern at a coarser grain (whole-RHS-assembly subroutines per anelastic model variant).

- **Stray backup file.** `RHS_Interior.f90.bak` (3221 lines) is a near-complete duplicate of `RHS_Interior.f90`, differing only in that it lacks 4 subroutines present in the current file (`apply_anelastic_Qf8_point`, `apply_anelastic_Qf8_point_pml`, `apply_const_Q_8M_point`, `apply_const_Q_8M_point_pml`) — i.e., it's a pre-Qf8/const-Q-8M-feature snapshot left in the source tree. Not referenced by `CMakeLists.txt`; should be removed or moved to version-control history only.

- **Three competing `BoundaryConditions*.f90` files, one active.** Only `BoundaryConditions.f90` is compiled (confirmed via `CMakeLists.txt` grep — files 2 and 3 do not appear). All three declare the same Fortran module name `BoundaryConditions`, so they are mutually exclusive at build time. `BoundaryConditions2.f90` is a structurally distinct, older-generation implementation using raw saved characteristic work arrays (`w1_p,w2_p,...,save`) without local-basis rotation, and supports only 2 of the 3 `type_of_bc` values (no clamped-wall). `BoundaryConditions3.f90` is line-for-line identical to the active `BoundaryConditions.f90` except that its `BCp`/`BCm` kernels keep the **general** `alpha`/`theta`-driven SAT formula active, whereas the compiled `BoundaryConditions.f90` has that general formula commented out in favor of a simplified version that no longer differentiates absorbing/free-surface/clamped-wall behavior by anything other than face sign. This is a substantive finding: **the boundary condition code that actually ships may implement a regressed/incomplete version of the intended physics**, with the "more correct" version sitting unused in `BoundaryConditions3.f90`.

- **Preprocessing/solver separation.** `pre_wql3d` (built from `preprocessor.f90` + the grid/MPI infrastructure modules) is a clean architectural separation allowing expensive curvilinear mesh generation (including fault-surface geometry baked in via `Curve_Grid_3D3`'s TFI) to be done once and reused across multiple solver runs via `grid.f90:init_grid_from_file`.

- **MMS verification code is real and wired up**, not vestigial: `mms.f90` is clean, well-commented, and actively invoked from `main.f90` (`if (D%mms_vars%use_mms) call eval_mms(D); call norm_fields(D)`) and `block.f90`/`domain.f90`. It implements a single trigonometric manufactured solution (`cos(nt·π·t)·sin/cos(nx·π·x)·sin/cos(ny·π·y)·sin/cos(nz·π·z)`) with an analytically exact forcing term subtracted from the rate array — the textbook MMS pattern, used to verify convergence order of the SBP-SAT discretization.

- **Attenuation/Q-model proliferation.** Seven near-duplicate viscoelastic attenuation implementations exist in `material.f90`/`datatypes.f90`/`fields.f90` (`anelastic`, `anelastic_Q`, `anelastic_Q8`, `anelastic_Qf`, `anelastic_Qf8`, `constant-Q-4M`, `constant-Q-8M`), each with its own ~100-line near-identical init routine and its own 6×N memory-variable array set in `block_material`. This is clearly the area of most active recent feature development (confirmed by `withers_tables.f90`'s comparatively polished Doxygen documentation and explicit "fixes a tau formula bug" comment in `material.f90`'s `init_anelastic_Q_properties` referring to the older `init_anelastic_properties`).

- **Sentinel/poison-value convention.** Rate and "not yet computed" arrays are frequently initialized to large sentinel values rather than zero — `DF` to `1.0e40_wp` (`fields.f90:38`), `I%DS`/`I%DW` to `1.0e40_wp` (`iface.f90:38,40`), `I%trup` to `1.0e9_wp` (`iface.f90:41`, "not yet ruptured"), generic array allocation default `1.0e20_wp` (`mpi3dcomm.f90`), and PML rates `B%DQ` to `1.0e40_wp` (`pml.f90:46`). This is a deliberate "loud failure" debugging convention, but it is not paired with systematic runtime assertions — the one NaN/Inf checker that exists (`fields.f90::check_block_fields_for_invalid_values`) does not appear to be called from the active code path.

---

## 6. Potential concerns / code quality notes

1. **Flagged-incorrect unit-normal formula.** `boundary.f90:56` contains the explicit author comment "(formulas below are incorrect, but illustrate use of metric derivative arrays)" directly above the call to `local_orth_vectors_q/r/s`. Unit normals are physically load-bearing for every SAT boundary/interface condition (traction projection, friction-law geometry). It is unclear from `boundary.f90` alone whether `unit_normals.f90`'s actual implementation resolves this caveat or whether the comment is stale — this is worth dedicated verification before relying on curvilinear-mesh boundary results.

2. **`BoundaryConditions.f90` (the compiled file) uses a simplified SAT formula that ignores `alpha`/`theta`.** As detailed in Section 5, the active boundary-condition kernel may not differentiate absorbing/free-surface/clamped-wall physics as intended, while a "more complete" version sits unused in `BoundaryConditions3.f90`. This is the single highest-priority code-quality finding in the review.

3. **Hardcoded 2-block / even-`nprocs` architecture vs. generic-looking types.** `domain_type`/`block_type`/`iface_type` use `allocatable` arrays suggesting N-block generality, but `nblocks` is hard-clamped to `{1,2}` (`domain.f90:208-211`), `mpi3dbasic::start_mpi` requires even `nprocs` (or exactly 1) tied to a fixed 50/50 rank split, and only `direction=='q'` interfaces are implemented (`'r'`/`'s'` hit `stop 'interfaces in r and s direction not implemented'` in `domain.f90`). The header comments in `domain.f90:5-11` and a TODO in `iface.f90:30` acknowledge this is a deliberate simplification, but it means the codebase is materially less general than its type system implies — a maintenance trap for anyone assuming N-block support exists.

4. **Computed-but-unused work-distribution logic.** `domain.f90:223-234` computes mesh-volume ratios (`ratio1, ratio2, nprocs_1, nprocs_2`) intended for proportional rank allocation between two differently-sized blocks, then discards them in favor of a flat 50/50 split (lines 240-241), with an explicit comment acknowledging the dead code ("Can be generalized by using ratio1, ratio2 instead").

5. **Latent bug: `Dbz6` boundary check uses wrong loop variable.** `metrics.f90:1266`'s interior-bound test reads `if ((z .ge. 7) .and. (y .le. mz-6))` — using `y` where every other directional variant (and the analogous `z`-loop logic) uses the matching loop variable (`z`). This is a copy-paste typo that could silently misapply the interior vs. boundary stencil selection when `y` and `z` extents differ.

6. **Latent bug: uninitialized arguments in `preprocessor.f90`.** `use_topography`, `topography_type`, `topography_path`, `ny`, `nz` are declared in `preprocessor.f90` but never set from any namelist before being passed into `Curve_Grid_3D3` (`preprocessor.f90:68-69`) — any curvilinear preprocessing run that exercises topography or fractal-fault array sizing would read garbage/undefined values.

7. **Precision mismatch in dead code.** `preprocessor.f90::read_mesh_serial` (never called) reads with `MPI_REAL` (single precision) into `real(G%X,4)`, while the corresponding `write_mesh_serial` writes `MPI_DOUBLE_PRECISION` — if this routine were ever wired up, it would silently misread its own output files.

8. **Dead/unused output mechanisms shipped alongside active ones.** `slice_output.f90` is fully compiled but never invoked (`init_slice_output` imported, never called, in `domain.f90`); `hdf5_output.f90` is excluded from the build entirely and is incomplete scaffolding (no actual dataset-write subroutine, `info` MPI handle used uninitialized, hardcoded `MPI_COMM_WORLD`); `parallel_write.f90` has zero callers anywhere in the codebase. None of these are large risks individually, but together they represent meaningful dead-code mass (≈250 lines) a new contributor would have to rule out before trusting the live `seismogram.f90`/`plane_output.f90` outputs as the actual I/O surface.

9. **Three independent, unreconciled moment-tensor forcing implementations.** `moment_tensor.f90` contains `set_moment_tensor` (discrete regularized delta function), `moment_tensor_body_force` (continuous isotropic Gaussian), and `set_moment_tensor_smooth` (continuous anisotropic per-axis Gaussian) — `domain.f90:set_rates` dispatches between the first and third based on `D%mollify_source`, while `moment_tensor_body_force`'s call sites are commented out (`domain.f90:749,766`). `moment_tensor_body_force` also has a likely copy-paste index bug at `moment_tensor.f90:1201` (`B%G%X(i,ms,1,3)` instead of an indexed `k`, inconsistent with the adjacent `hx`/`hy` computations). A ~500-line fully-commented-out analytic Green's-function exact-solution routine (`exact_moment_tensor`) also exists, unused.

10. **Pervasive bare-`stop` error handling outside the MPI-IO layer.** `mpi3dio.f90` and `mpi3dbasic.f90` consistently route fatal errors through `mpi3dbasic::error` (clean `MPI_Abort`), but `block.f90`, `fields.f90`, `boundary.f90`, `material.f90`, `Interface_Condition.f90`, and `grid.f90` instead use bare Fortran `stop '<message>'` in `select case default` branches — on some MPI implementations a `stop` on one rank can hang rather than cleanly abort the whole job. There is no consistent error-handling policy across the codebase.

11. **Heavy code duplication.** The `lagrange` Lagrange-interpolation function is duplicated verbatim between `grid.f90` and `inter_material.f90`. The 7 anelastic-Q initializer subroutines in `material.f90` are ~80% structurally identical. `mpi3dio.f90`'s 4 rank-variants (0d/1d/2d/3d) of `write_file_distributed`/`read_file_distributed` are near-identical boilerplate. `unit_normals.f90::local_orth_vectors` is an exact duplicate of `local_orth_vectors_q`. `boundary.f90::init_boundary`'s `'elastic'` and `'acoustic'` cases are byte-for-byte identical despite acoustic physics being unimplemented everywhere else (`block.f90::set_rates_block` stops on `'acoustic'`), meaning this duplication currently has no effect but would mask a real allocation-size bug if acoustic physics were ever finished (acoustic should have 4 components, not 9).

12. **Mixed real-literal precision suffixes.** Most files consistently use the `_wp` kind suffix, but `plastic.f90` (`plastic_flow2`), `Interface_Condition.f90`, and `initial_stress_condition.f90` intermix bare `d0`/`0_wp`/undecorated literals (e.g. `1.36d0`, `1d10`, `1d-9`) — functionally fine only because `wp` happens to equal double precision, but a portability/consistency smell, and `moment_tensor.f90` separately redefines `pi` with two different literal precisions in different subroutines (`3.141592653589793_wp` vs `3.14159265359_wp`).

13. **`main.f90` has substantial dead/commented debug code.** Lines 25 (`!use hdf5_output`), 64 (`!call start_hdf_output()`), 77-78 (commented `create_dataset` calls), 106-127 (a large commented-out `else` branch referencing variables — `handles`, `Theta`, `my_id` — that aren't even declared in the current file, confirming it's stale residue from an earlier version that would not compile if uncommented), and 132 (`!call finish_hdf_output()`). The MMS-error print at lines 107-108 also hardcodes references to `D%B(1)` and `D%B(2)`, which would be invalid/out-of-bounds if `D%mms_vars%use_mms` were combined with `nblocks=1`.

14. **Magic numbers without named constants or provenance comments.** `metrics.f90`'s ~15-significant-digit boundary-closure stencil coefficients have no citation or derivation comment; `material.f90`'s benchmark velocity-model layers (TPV31/32/33, OKLAHOMA) hardcode dozens of literal Vp/Vs/ρ values inline; `block.f90`'s `tau0` SAT-penalty table is hardcoded per (fd_type, order) with no comment explaining the derivation (these are legitimate, scheme-specific SBP-SAT theory values, but their lack of a reference/derivation comment makes the table hard to extend or audit); `initial_stress_condition.f90` repeats the literal `32.03812032_wp` "reference shear modulus" 4 times rather than as a module parameter.

15. **Naming inconsistencies.** `Prestress`/`prestress` (Interface_Condition.f90, Fortran case-insensitivity masks this), `local_orth_vectors` vs `local_orth_vectors_q` (an exact duplicate with inconsistent naming), `MaterialProps` array literally named `LambdaMu` in `mms.f90` despite its 3rd component being density (not a λ/μ quantity), order values `66`/`679` used as DRP-scheme sentinel/encoding integers rather than true accuracy orders in `block.f90`/`RHS_Interior.f90`/`JU_xJU_yJU_z6.f90`, and two types (`block_indices`, `boundary_type`) explicitly marked in their own doc comments as redundant/should-be-deleted (`datatypes.f90:16-17,160-161`).

---

## 7. Summary

WaveQLab3D is a mature, physics-rich, single-purpose research solver for 3D curvilinear SBP-SAT earthquake rupture simulation, built around a consistent derived-type-per-block architecture (`block_type` aggregating grid, material, fields, plasticity, PML, and boundary sub-types, all defined centrally in `datatypes.f90` to avoid circular module dependencies) and a 5-stage low-storage RK4 (Carpenter-Kennedy) time integrator that threads ghost exchange, RHS evaluation, and SAT-penalty boundary/interface enforcement through every stage. Its numerical core — the SBP differentiation kernels in `JU_xJU_yJU_z6.f90` and `metrics.f90`, and the RHS assembly in `RHS_Interior.f90` — favors fully unrolled, per-order/per-scheme stencil code over generic operator abstractions, trading code size (the `JU_xJU_yJU_z6.f90` file alone is 23,000+ lines) for performance, a common and defensible pattern in production SBP-FD codes. The fault-rupture subsystem (`Interface_Condition.f90`, `CouplingForcing.f90`, `fault_output.f90`) implements a textbook characteristic/impedance-weighted Riemann coupling with pluggable friction laws (locked, linear, slip-weakening, rate-and-state) and extensive hardcoded configuration for ~25 named SCEC benchmark problems, confirming the code's purpose as a benchmark-validated dynamic rupture research tool. Architecturally, the codebase is significantly less general than its type system suggests: it is hardcoded throughout (MPI bootstrap, domain init, interface exchange) to exactly 1–2 blocks coupled along a single q-direction interface, a limitation the developers explicitly acknowledge in comments rather than hide. Code-quality-wise, the most actionable findings are (a) an author-flagged-incorrect unit-normal formula in `boundary.f90` that is physically load-bearing for every boundary/interface condition, (b) the discovery that the actively-compiled `BoundaryConditions.f90` uses a simplified SAT formula while a more complete version sits unused in the orphaned `BoundaryConditions3.f90`, (c) a stray `RHS_Interior.f90.bak` backup file and several genuinely dead modules (`slice_output.f90`, `hdf5_output.f90`, `parallel_write.f90`) that should be pruned or clearly marked, and (d) heavy duplication in the attenuation-model and MPI-IO rank-variant code that would benefit from refactoring before further Q-model or output-format features are added.
