# Codex Initial Analysis Summary: WaveQLab3D

## Repository area

- Analyzed path: `Codex/WQ/src/`
- Product: WaveQLab3D
- Language/runtime: Fortran with MPI; CMake build
- Analysis type: static source review
- Build verification: not performed because CMake and Fortran/MPI compilers are unavailable in the current environment
- Detailed report: `Knowledge-base/Codex/initial_report.md`

## Purpose

WaveQLab3D is an MPI-parallel three-dimensional seismic wave and earthquake-rupture solver. It advances a nine-component elastic velocity-stress state on Cartesian or curvilinear structured grids, coupling blocks through a fault/interface and applying high-order boundary/interface penalties.

## Size and composition

| Metric | Value |
|---|---:|
| Fortran files inspected | 43 |
| Approximate total source lines | 53,268 |
| Largest module | `JU_xJU_yJU_z6.f90` (23,392 lines) |
| Main executable | `waveqlab3d` |
| Secondary executable | `pre_wql3d` |
| Registered CTest cases | 6 |

The source directory also contains inactive alternatives/backups (`BoundaryConditions2/3`, `original_RHS_interior`, `RHS_Interior.f90.bak`) and dormant HDF5 support.

## Architectural outline

| Concern | Main modules |
|---|---|
| Program/lifecycle | `main`, `domain`, `time_step`, `block` |
| Data model | `datatypes`, `common` |
| Numerical RHS | `elastic`, `RHS_Interior`, `JU_xJU_yJU_z6`, `metrics` |
| Grid/material | `grid`, `material`, `inter_material`, `unit_normals` |
| Boundary/fault | `BoundaryConditions`, `Interface_Condition`, `CouplingForcing`, `iface`, `boundary` |
| Extra physics | `plastic`, `pml`, `moment_tensor`, `mms` |
| Parallel/I/O | `mpi3dbasic`, `mpi3dcomm`, `mpi3d_interface`, `mpi3dio`, output modules |

Execution follows this stage loop:

`MPI halo exchange → scale RK rates → volume RHS → interface exchange → boundary/fault SAT forcing → output → state update`

Time integration is a fixed five-stage, fourth-order low-storage Runge-Kutta method.

## Supported feature set

- Cartesian and curvilinear meshes; computed or file-sourced.
- One or two blocks in the current domain interface, though one-block support has correctness gaps.
- Traditional, upwind, and DRP finite-difference families over multiple orders.
- Locked, linear, slip-weakening, and rate-and-state fault coupling.
- PML, spatial material variation, off-fault plasticity, and moment-tensor sources.
- Manufactured solutions.
- Four- and eight-mechanism constant/frequency-dependent attenuation variants.
- Fault, seismogram, slice, plane, and distributed binary output.

## Key strengths

- Broad, mature scientific functionality.
- Clear top-level separation between domain orchestration, volume RHS, and SAT/interface physics.
- Explicit derived types for grids, blocks, faults, and distributed output.
- MPI Cartesian decomposition and interface-specific communication.
- Existing CTest scenarios, MMS support, and aggressive GNU debug flags.
- Multiple standard earthquake benchmark configurations already encoded.

## Highest-priority findings

| Priority | Finding | Impact |
|---|---|---|
| Critical | `domain:set_rates` and MMS reporting access block 2 without a one-block guard | Out-of-bounds/undefined behavior in `nblocks=1` runs |
| Critical | Two-block MPI membership formulas overlap for odd rank counts greater than one | A rank can operate on an uninitialized block |
| High | `nblocks` is used against a fixed two-element temporary array before validation | Out-of-bounds or undefined input-derived state |
| Critical | Moment-source dispatch reads block 1 and block 2 on every rank without ownership/extent guards | Reads uninitialized nonlocal blocks and goes out of bounds in one-block mode |
| High | CFL time step ignores actual curved/file mesh metrics and spatial material fields | Potentially non-conservative stability limit |
| Medium | `fault_output.f90` occurs twice in the CMake source list | Build hygiene/portability problem |
| Medium | Unsupported FD/order combinations lack centralized validation and can do no useful RHS work | Silent incorrect simulation |
| Medium | Plain `stop` is used widely in MPI code | Non-collective failure/hanging peers risk |

## Maintainability profile

The main maintainability concern is duplication. Nearly half of the source is one expanded finite-difference module. Attenuation adds separate arrays, scaling, updates, and point/PML kernels for each response and mechanism count. Benchmark-specific logic is spread across grid, material, initial stress, friction, and source modules.

This makes cross-cutting changes risky: a new attenuation mode or benchmark can require synchronized edits in many files, while the current registered tests exercise only a small subset of the configuration matrix.

## Test coverage assessment

Current registered scenarios cover serial/MPI, Cartesian/curvilinear, and premeshed frictional rupture. Important missing coverage includes:

- One-block mode.
- Odd MPI rank counts.
- Each finite-difference order/family.
- Each attenuation response and Q curve.
- PML effectiveness.
- Plasticity and moment tensors.
- Individual friction/nonlinear solves.
- Input validation and collective failure behavior.
- Metric identities, convergence rates, and MPI-invariant results.

## Recommended order of work

1. Correct one-block indexing, MPI membership, and early `nblocks` validation.
2. Replace attenuation setup conditionals with one exclusive response dispatch.
3. Add one-block, odd-rank, response-matrix, and MMS convergence tests.
4. Remove duplicate/backup source artifacts and fix the CMake source list.
5. Compute the stability step from initialized mesh metrics and materials.
6. Centralize input validation and MPI-fatal error handling.
7. Refactor hard-coded two-block branches into loops/connectivity data.
8. Parameterize or generate repetitive attenuation and FD kernels behind numerical tests.
9. Add checkpoint/restart and continuously build a modern parallel output path.

## Comparative-review tags

For later comparison with other implementations, classify this code as:

- **Domain:** computational seismology / dynamic rupture
- **Parallel model:** distributed-memory MPI with Cartesian decomposition
- **Numerics:** structured-grid high-order finite differences with SAT coupling
- **Architecture maturity:** research-grade, modular at a coarse level, highly specialized internally
- **Primary risk class:** configuration-dependent correctness and duplicated numerical kernels
- **Modernization priority:** correctness tests first, architectural reduction second

## Bottom line

WaveQLab3D contains valuable and extensive scientific capability. Its top-level flow is understandable, but safe operation is narrower than the advertised configuration surface. The immediate goal should be to make topology and response selection impossible to misconfigure, then build a numerical regression envelope before attempting major refactoring.
