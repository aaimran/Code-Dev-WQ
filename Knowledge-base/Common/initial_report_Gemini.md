# Gemini Initial Analysis Summary: WaveQLab3D

## Repository area

- Analyzed path: `Gemini/WQ/src/`
- Product: WaveQLab3D
- Language/runtime: Fortran with MPI; CMake build
- Analysis type: static source review
- Build verification: not performed because CMake and Fortran/MPI compilers are unavailable in the current environment
- Detailed report: `Knowledge-base/Gemini/initial_report.md`

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