# WaveQLab3D (`Codex/WQ/src`) Initial Technical Report

## 1. Executive summary

`Codex/WQ/src` implements WaveQLab3D, an MPI-parallel Fortran solver for three-dimensional seismic wave propagation and dynamic earthquake rupture. The code advances a first-order velocity-stress elastic system on Cartesian or curvilinear multiblock grids. Its principal numerical ingredients are high-order finite differences, summation-by-parts/simultaneous-approximation-term (SBP-SAT) style boundary and interface treatment, low-storage Runge-Kutta time integration, frictional fault laws, perfectly matched layers (PML), optional viscoplasticity, moment-tensor sources, and several attenuation/Q models.

The source is scientifically substantial: 43 Fortran source files plus one CMake file, approximately 53,000 lines in total. Its strongest qualities are broad physical capability, explicit data structures for blocks/interfaces, distributed-memory decomposition, multiple verification/output facilities, and a large library of high-order spatial operators. Its main engineering liabilities are extreme concentration of generated/repetitive kernels, two-block assumptions that survive inside recently generalized one-block code, weak input validation and error propagation, substantial problem-specific branching, limited automated coverage, and build/source hygiene issues.

The highest-priority correctness findings from static inspection are:

1. One-block execution can access `D%B(2)` unconditionally in `domain:set_rates`; MMS reporting in `main` also assumes two blocks.
2. The MPI rank split overlaps block memberships for odd process counts greater than one, leaving a rank marked as belonging to block 2 even though block 2 initialization is skipped on that rank.
3. `nblocks` is used to loop over a fixed two-element temporary block array before it is validated as 1 or 2.
4. Moment-source dispatch reads both block entries unconditionally on every rank, including ranks that own only one initialized block and one-block domains where block 2 does not exist.
5. The CMake source list contains `fault_output.f90` twice.

This report is a static source analysis. A configure/build/test run was attempted, but this environment does not provide `cmake`, `mpifort`, or `gfortran`; therefore buildability and numerical results were not independently verified.

## 2. Scope and inventory

### 2.1 Source scale

- Fortran implementation files: 43, including active, alternative, and backup files.
- CMake build definition: `src/CMakeLists.txt`.
- Approximate total source size: 53,268 lines.
- Largest files:
  - `JU_xJU_yJU_z6.f90`: 23,392 lines.
  - `RHS_Interior.f90`: 3,478 lines.
  - `RHS_Interior.f90.bak`: 3,221 lines.
  - `Interface_Condition.f90`: 2,889 lines.
  - `grid.f90`: 2,740 lines.
  - `material.f90`: 1,820 lines.

`JU_xJU_yJU_z6.f90` alone is about 44% of the inspected source. It contains many expanded traditional, upwind, and dispersion-relation-preserving finite-difference kernels and their interior variants.

### 2.2 Build products

The CMake file defines two executables:

- `waveqlab3d`: the simulation executable, with `main.f90` as its program unit.
- `pre_wql3d`: a mesh/preprocessing executable, with `preprocessor.f90` as its program unit.

MPI is required. HDF5 support exists in `hdf5_output.f90`, but its discovery, source inclusion, initialization, and linkage are commented out. Compiler-specific flags are supplied for GNU, Intel `ifort`, and Cray-style `ftn` compilers. Debug GNU flags are appropriately aggressive (`implicit-none`, bounds checks, floating-point traps, NaN initialization, and backtraces), although the ability to use them depends on the compiler and current source conformance.

The CMake configuration registers six tests: two four-rank MPI tests, two premesh tests, and two serial tests. They cover Cartesian and curvilinear frictional rupture scenarios but do not directly cover plasticity, PML, attenuation variants, moment tensors, one-block mode, odd MPI process counts, or most friction laws.

### 2.3 Active versus inactive/alternative files

The active build uses `BoundaryConditions.f90` and `RHS_Interior.f90`. These nearby files are not in the active target:

- `BoundaryConditions2.f90` and `BoundaryConditions3.f90`, both defining the same module name `BoundaryConditions`.
- `original_RHS_interior.f90`.
- `RHS_Interior.f90.bak`.
- `hdf5_output.f90`.

Keeping same-module alternatives and backups in `src` makes accidental glob-based builds unsafe and obscures which implementation is authoritative.

## 3. System purpose and supported capabilities

The solver models elastic seismic waves and rupture across a fault represented by a block interface. Based on the README and implementation, supported features include:

- Three-dimensional elastic velocity-stress propagation.
- Cartesian, stretched, computed curvilinear, and file-supplied grids.
- One or two blocks, with the two-block interface currently fixed to the computational `q` direction.
- Traditional high-order finite differences and several upwind/DRP orders.
- External boundary conditions enforced through characteristic/SAT terms.
- Locked, linear-friction, slip-weakening, and rate-and-state fault coupling.
- Spatially varying or file-provided material properties.
- Drucker-Prager-style off-fault plasticity.
- PML absorbing layers on six block faces.
- Moment-tensor sources with several temporal source functions.
- Manufactured-solution evaluation.
- Attenuation responses named `anelastic`, `anelastic-Q`, `anelastic-Q8`, `anelastic-Qf`, `constant-Q-4M`, `constant-Q-8M`, `frequency-Q-4M`, and `frequency-Q-8M`.
- Fault, seismogram, slice, plane, and distributed binary output paths; HDF5 is presently dormant.

The implementation remains fundamentally specialized to elastic physics. Although a `physics` field and an acoustic branch exist, blocks are initialized as `elastic`, and the acoustic branch explicitly stops as unimplemented.

## 4. Architecture

### 4.1 Architectural layers

| Layer | Primary files | Responsibility |
|---|---|---|
| Programs/build | `main.f90`, `preprocessor.f90`, `CMakeLists.txt` | Startup, input selection, executable definitions, test registration |
| Domain orchestration | `domain.f90`, `time_step.f90`, `block.f90` | Global lifecycle, block/interface ownership, RK staging, high-level updates |
| Shared data model | `datatypes.f90`, `common.f90` | Kind selection and derived types for grids, fields, materials, blocks, interfaces, output |
| Spatial discretization | `elastic.f90`, `RHS_Interior.f90`, `JU_xJU_yJU_z6.f90`, `metrics.f90` | PDE RHS, finite-difference operators, metric transformations |
| Geometry/materials | `grid.f90`, `material.f90`, `inter_material.f90`, `plastic_material.f90`, `unit_normals.f90` | Mesh construction/read, material setup/interpolation, normals |
| Boundaries/interfaces | `boundary.f90`, `BoundaryConditions.f90`, `Interface_Condition.f90`, `CouplingForcing.f90`, `iface.f90` | Halo-facing boundary storage, characteristic boundary conditions, fault/interface physics, SAT forcing |
| Additional physics | `plastic.f90`, `pml.f90`, `moment_tensor.f90`, `initial_stress_condition.f90`, `mms.f90` | Plasticity, absorbing layers, sources, initial stress, verification |
| Parallel runtime/I/O | `mpi3dbasic.f90`, `mpi3dcomm.f90`, `mpi3d_interface.f90`, `mpi3dio.f90`, output modules | MPI lifecycle/topologies/halo exchange/interface exchange and output |

### 4.2 Central data model

`datatypes.f90` is the dependency hub. Its key types are:

- `block_grid_t`: Cartesian communicator/decomposition metadata, coordinates, metric derivatives, Jacobian, and spacing.
- `block_material`: elastic material array plus configuration and memory variables for every attenuation model.
- `block_fields`: four-dimensional state and derivative arrays.
- `block_boundary`: face-local coordinates, material, normals, local/opposite fields, rates, and displacement.
- `block_pml`: per-face PML state and rates.
- `block_type`: aggregates grid, material, fields, six boundaries, six PML regions, plastic state, moment source, discretization choice, and diagnostics.
- `iface_type`: two-block connectivity, fault velocity/traction/slip/state variables, and interface communicator.
- `domain_type`: global time/configuration, blocks, interfaces, fault output, MMS settings, and output managers.

This aggregation makes the main execution flow legible and avoids earlier circular module dependencies, as the file comment explains. The tradeoff is a large, mutable object graph with weak encapsulation: most types and fields are public, and many routines accept whole block/domain objects even when they need only a subset.

### 4.3 Initialization flow

`main` performs the following:

1. Initialize MPI.
2. Read the first command-line argument as the input file.
3. Initialize fixed fourth-order, five-stage low-storage RK coefficients.
4. Call `init_domain`.
5. Advance `D%nt` steps.
6. Optionally report manufactured-solution errors.
7. Close output resources and finalize MPI.

`init_domain` reads the `problem_list` and `block_list` namelists, validates the response string, computes a scalar CFL time step, constructs block communicators, initializes each local block, establishes the one permitted interface, initializes fault state and output, then creates MMS, seismogram, and plane-output state.

`init_block` performs decomposition, grid generation/read, material generation/read, optional interpolation and attenuation setup, plastic/source/PML initialization, field allocation, halo exchange, boundary allocation, and SAT constants.

### 4.4 Time-step data flow

Every RK stage executes:

1. Exchange block field halos.
2. Scale accumulated rates by the RK `A` coefficient.
3. Evaluate the elastic interior and near-boundary RHS.
4. Copy/exchange interface face fields.
5. Add external-boundary and interface/fault SAT forcing.
6. At stage one and the configured stride, write output.
7. Set stage time and update block fields, interface state, attenuation memory, PML state, and (at the last stage) plastic state.

The division between volume physics and SAT forcing is conceptually sound. Output during stage one is deliberate because fault rate-like quantities are computed while enforcing interface conditions.

## 5. Numerical and physical implementation

### 5.1 State convention

The field allocation uses nine components, consistent with three velocities and six independent stress components. Boundary/interface calculations rotate the relevant velocity and traction components into a local orthonormal frame, solve characteristic/interface conditions, then rotate corrections back into physical coordinates.

### 5.2 Spatial operators

`RHS_Interior` dispatches by `fd_type` and `order`:

- `traditional`: sixth-order-oriented kernel path (`JJU_x6*`).
- `upwind`: orders 2 through 9.
- `upwind_drp`: orders 3 through 7 plus special identifiers 66 and 679.

The enormous `JU_xJU_yJU_z6` module contains separate fully expanded routines for near-boundary and interior regions. This likely favors performance and compiler optimization, but creates a high verification burden: changes to field equations, attenuation, PML, or metrics must remain consistent across many duplicated kernels.

### 5.3 Curvilinear grids and metrics

`grid.f90` supports Cartesian, stretched, constructed curved, and file-sourced meshes. It includes surface mesh generation and interpolation utilities. `metrics.f90` and the Jacobian/metric arrays in `block_grid_t` map computational derivatives to physical coordinates. Geometry logic includes numerous named problem/profile cases, so its practical behavior is more specialized than the generic API suggests.

### 5.4 Boundary and interface treatment

`BoundaryConditions.f90` builds face conditions for all six sides and characteristic plus/minus states. `RHS_Interior:impose_boundary_condition` applies those conditions through penalties.

For the inter-block fault, `Interface_Condition.f90` supports:

- Welded/locked continuity.
- Linear friction.
- Slip-weakening friction.
- Rate-and-state friction with a Regula Falsi/nonlinear solve.
- Problem-specific prestress, cohesion, forced-rupture timing, and initial state.

Only a `q`-normal interface between blocks 1 and 2 is orchestrated. Interfaces in `r` or `s` stop at runtime. Many SCEC-style benchmark names are embedded directly in interface/material/initial-stress logic; this is useful for benchmark reproduction but couples scenario definition tightly to solver code.

### 5.5 Attenuation and plasticity

Attenuation is represented by six stress-component memory-variable families, with four or eight relaxation mechanisms depending on the response. Initialization lives in `material.f90`; point kernels and PML variants live in `RHS_Interior.f90`; rate scaling and state updates live in `fields.f90`. Constant-Q weights can be obtained by a normal-equation/NNLS-like calculation, Withers tables, lookup, or manual values.

This implementation is feature-rich but structurally repetitive. A new response mode currently requires coordinated edits to the data type, allocation/initialization, RHS dispatch, PML kernel, rate scaling, field update, validation string list, README, and tests. That is a classic consistency-risk surface.

Plastic state is initialized for `response == 'plastic'` and updated only after the last RK stage. The plastic update receives the full-step `D%dt` rather than the stage increment; this may be intentional operator splitting, but should be documented and numerically tested as such.

### 5.6 Parallelization

MPI support consists of:

- World startup/finalization and diagnostics in `mpi3dbasic`.
- Cartesian 3-D domain decomposition, derived datatypes, allocation helpers, and halo exchange in `mpi3dcomm`.
- Cross-block interface communicators and paired exchanges in `mpi3d_interface`.
- Distributed file views/output in `mpi3dio` and higher-level output modules.

Each block receives a subcommunicator, then uses `MPI_Dims_create` and a Cartesian topology. Ghost widths depend on the chosen finite-difference family/order. Interface ranks are selected from the opposing block faces and communicate across the world-level pairing.

## 6. Input and output interfaces

### 6.1 Namelists

The source recognizes these namelist groups:

- `problem_list`: problem identity, response, block count, time/CFL, coupling, discretization, mesh/material source, output and topography switches.
- `block_list`: two `block_temp_parameters` entries containing dimensions, extents, material constants, boundary codes, profiles, PML, and fault dimensions.
- `moment_list` and source configuration read by moment-tensor code.
- `mms_list`.
- `output_list` for seismograms/stations.
- `slice_list`.
- `plane_output_list`.
- Attenuation lists: `anelastic_list`, `anelastic_Q_list`, `anelastic_Q8_list`, `anelastic_Qf_list`, `constant_Q_4M_list`, `constant_Q_8M_list`, and `anelastic_Qf8_list`.

Most readers rewind the same input unit and search for their group. Missing groups (`iostat < 0`) are usually treated as defaults; malformed groups (`iostat > 0`) stop.

### 6.2 Output

Output facilities include fault-plane distributed data, hat variables, rupture time, seismograms, horizontal/vertical slices, and arbitrary configured planes. Binary distributed I/O is the active path. The HDF5 module has only start/finish/dataset scaffolding and is disabled in the build.

There is no checkpoint/restart facility visible in `src`, which is a major operational gap for long HPC runs.

## 7. Detailed findings and risks

### 7.1 Critical/high correctness risks

#### A. One-block mode dereferences block 2

`domain:set_rates` correctly guards the volume call with `in_block_comm(2)`, but later evaluates `D%B(2)%MT%use_moment_tensor` without checking `D%nblocks` or membership. With `nblocks=1`, `D%B` has extent one, so bounds-checking builds should fail and unchecked builds have undefined behavior. `main` similarly prints MMS errors for `D%B(1)` and `D%B(2)` unconditionally.

Recommendation: iterate `i=1,D%nblocks` for block-local source and MMS work. Avoid hard-coded block indices in all lifecycle routines.

#### B. Odd MPI process counts produce overlapping block membership

For two-block mode:

```fortran
in_block_comm(1) = (rank < (nprocs + 1)/2)
in_block_comm(2) = (rank >= nprocs/2)
```

With three ranks, rank 1 belongs to both groups. The initialization loop skips block 2 on that rank only because `init_iface` and related calls often include `.not.in_block_comm(1)`, but later routines see `in_block_comm(2)` and operate on an uninitialized `D%B(2)`. The intentional one-rank serial special case is mixed into a formula that is unsafe for other odd sizes.

Recommendation: create disjoint memberships for `nprocs > 1` using one explicit split index; implement serial two-block ownership as a separate branch. Add tests for 1, 2, 3, 4, and 5 ranks.

#### C. `nblocks` validation happens after unsafe use

`btp` is declared with exactly two elements. The time-step loop runs from 1 to `max(1,nblocks)` before `nblocks` is checked and normalized to 1 or 2. An input value above 2 reads beyond `btp`; a value below 1 computes from `btp(1)` and is then changed to 2, potentially leaving the second block data undefined.

Recommendation: validate immediately after reading `problem_list`, before reading/using block data, and fail clearly rather than silently changing the requested topology.

#### D. Moment-source dispatch is not ownership-safe

After guarded calls to `set_rates_block`, `domain:set_rates` tests `D%B(1)%MT%use_moment_tensor` and `D%B(2)%MT%use_moment_tensor` without communicator-membership guards. In a normal distributed two-block run, each rank initializes only its locally owned block, so a block-2-only rank reads the uninitialized block-1 object and a block-1-only rank reads the uninitialized block-2 object. In one-block mode, the second reference is outside the allocated array. This is unsafe even when no moment tensor was requested because the logical flag itself must be read to decide that.

Recommendation: iterate over owned blocks or guard each source branch with both `in_block_comm(i)` and `i <= D%nblocks`. Initialize all domain/block metadata deterministically if nonlocal placeholders must remain allocated.

#### E. Time step ignores actual mesh metrics and material fields

The code itself emits a warning: `D%dt` is computed from scalar block extents, point counts, and input `rho_s_p`, not from curvilinear metric/Jacobian information, file-supplied meshes, spatially varying materials, attenuation stiffness changes, or PML constraints. Consequently, the CFL estimate can be non-conservative for distorted grids or heterogeneous/file materials.

Recommendation: compute a global stability bound after grid/material initialization from local metric-scaled wave speeds, then use `MPI_Allreduce(MIN)`.

### 7.2 Medium engineering and reliability risks

- CMake lists `fault_output.f90` twice. CMake may deduplicate or reject this depending on generator/version behavior, but it is unambiguously incorrect source-list hygiene.
- `D%nt = floor(t_final/dt)` ends at or before `t_final` and can omit a fractional final step; the actual achieved time should be reported. The input `nt` is read but then overwritten/ignored.
- Many invalid inputs use plain `stop` on a subset of ranks. In MPI runs this can strand peers or yield uneven termination. Prefer a collective error path ending in `MPI_Abort`.
- The response is validated, but mesh source, mesh type, coupling, FD family/order combinations, dimensions, output stride, CFL, final time, and PML widths lack equivalent centralized validation. Unsupported FD choices can silently execute no spatial operator because dispatch lacks a default error.
- `w_stride=0` causes `mod(...,0)`; dimensions of one cause division by zero in spacing; negative or zero physical values can enter square roots/divisions.
- Response initialization is a chain of independent conditionals, and `frequency-Q-4M` aliases the `anelastic-Qf` initializer. Although the current ordering leaves its Qf flag enabled, the design is fragile; one exclusive `select case` plus response postcondition tests would make the active model unambiguous.
- Derived MPI datatypes and Cartesian/subcommunicators are created but no comprehensive teardown/free path is evident. This matters for repeated library-style runs and resource-checking tools.
- `close_domain` is index-specific and assumes the two-element module membership arrays. It does not deallocate the full domain graph explicitly.
- Wall-step reporting uses `cpu_time`, which is process CPU time rather than MPI wall time. `MPI_Wtime` or the existing `time_elapsed` wrapper would produce meaningful performance measurements.
- Large amounts of commented-out debugging/legacy code obscure active logic and raise review cost.
- `block_indices` and `boundary_type` are acknowledged in source comments as redundant but remain active.
- Public/private boundaries are largely absent, increasing accidental coupling between modules.
- Several output routines expose and slice raw internal arrays directly; an output-view API would reduce coupling.

### 7.3 Maintainability risks

- Problem names such as TPV and regional scenarios are encoded in large `select case` blocks across grid, material, stress, source, and friction modules. Adding a problem can require edits in multiple distant files.
- Attenuation models replicate six memory-variable names per model and four/eight mechanism-specific kernels. An array dimension for stress component and mechanism would drastically reduce code paths.
- `Interface_Condition.f90`, `grid.f90`, and `material.f90` mix generic algorithms, parameter databases, parsing, and benchmark-specific policy.
- Module/file naming is inconsistent (`BoundaryConditions`, `Interface_Condition`, `RHS_Interior` versus lowercase modules), and typos persist in identifiers/comments (`Cordinates`, `intial`, `memomry`). Fortran is case-insensitive, but tooling and human navigation suffer.
- Backup and alternative source files are colocated with production source instead of tracked through version control or an explicit experiments directory.

## 8. Testing and verification assessment

### 8.1 Existing strengths

- CTest integration exists for MPI, serial, Cartesian, curvilinear, and premeshed cases.
- Manufactured solutions provide an analytical-error path.
- Debug compiler flags enable bounds, undefined-value, and floating-point checks under GNU.
- Field finite-value checking routines exist in `fields.f90`.
- Several benchmark input decks are present outside `src`.

### 8.2 Gaps

The registered tests are scenario-level and narrow. No source-level unit tests are registered for:

- MPI decomposition and odd-rank block assignment.
- One-block lifecycle.
- Finite-difference operator convergence by order/family.
- Metric identities and Jacobian positivity.
- Boundary reflection/energy behavior.
- Welded/frictional Riemann solves and nonlinear solver convergence.
- PML reflection attenuation.
- Every attenuation mode and its expected Q curve.
- Plastic yield/update behavior.
- Input validation/failure modes.
- Output schema and restart compatibility.

The tests appear to execute simulations, but the supplied CMake scripts should be reviewed to confirm they compare against toleranced reference results rather than merely checking exit status.

### 8.3 Recommended verification ladder

1. Pure unit tests for RK coefficients, `decompose1d`, interpolation, friction solvers, source-time functions, and Q-weight/response calculations.
2. Operator tests for polynomial exactness and convergence of every FD family/order.
3. One-block propagation tests with periodic/free/absorbing boundaries.
4. Two-block welded-interface equivalence to a one-block solution.
5. Friction benchmark regression tests with scalar diagnostics and selected waveform norms.
6. Attenuation tests measuring amplitude/phase and recovered Q over the configured band.
7. MPI invariance tests at 1–5 ranks, including odd counts and multiple Cartesian factorizations.
8. Debug/sanitized CI plus optimized numerical-regression CI.

## 9. Build and portability assessment

- The minimum CMake version (3.5) is old and predates many robust modern Fortran/MPI target features.
- Global compile/link directories and `${MPI_Fortran_*}` variables should be replaced by the imported target `MPI::MPI_Fortran` where available.
- Release uses GNU `-O5`, which is compiler-specific and potentially aggressive for reproducible floating-point behavior.
- The Intel branch only recognizes `ifort`, not the newer `ifx` name.
- Default-real promotion (`-fdefault-real-8`, `-r8`) coexists with an explicit `wp` kind and MPI real-kind abstractions. Relying on both increases ABI and literal-kind risk; the explicit kind should be authoritative.
- HDF5 code uses the legacy `hdf5` module and is not continuously built, so it may have drifted.
- No install rules, package metadata, library target, generated configuration, or explicit Fortran module directory are defined.
- Source order is manually maintained despite CMake's Fortran dependency scanning; the duplicate entry demonstrates the fragility of the list.

## 10. Recommended remediation roadmap

### Phase 0: correctness gates

1. Fix all one-block out-of-bounds references by iterating over `D%nblocks`.
2. Make two-block communicator membership disjoint for all multi-rank cases; special-case serial mode explicitly.
3. Validate `nblocks`, grid dimensions, CFL, `t_final`, stride, mesh/material source, coupling, and FD/order combinations before use.
4. Refactor response initialization to a single dispatch and add one test per response.
5. Remove the duplicate CMake source and move backup/alternative files out of active `src`.
6. Run the full suite in a bounds/FPE/NaN debug build.

### Phase 1: reproducible validation

1. Add one-block and odd-rank CTests.
2. Make tests compare numerical artifacts or norms against versioned tolerances.
3. Add MMS convergence tests across resolutions.
4. Add attenuation response tests and friction solver tests.
5. Centralize collective fatal-error handling.

### Phase 2: safer architecture

1. Split input parsing/validation from allocation and physics initialization.
2. Replace hard-coded block 1/2 branches with loops and explicit connectivity records.
3. Move benchmark-specific parameter logic into configuration/data modules or external data.
4. Encapsulate derived types with `private` defaults and narrow public APIs.
5. Separate generic interface solvers from problem-specific prestress/nucleation policy.

### Phase 3: reduce duplication and improve performance confidence

1. Represent attenuation state as component × mechanism arrays and one parameterized kernel.
2. Generate FD kernels from reviewed coefficient tables/scripts, retaining generator inputs and operator tests.
3. Profile before changing layouts; record MPI scaling, memory per grid point, and output costs.
4. Add checkpoint/restart and modernize parallel I/O, ideally with HDF5 enabled in CI.
5. Compute CFL from actual mesh metrics/materials and document the stability model.

## 11. Suggested ownership map

For safe future work, changes should normally be grouped as follows:

- Time/domain/MPI topology: `main`, `domain`, `time_step`, `block`, `mpi3d*`.
- Core discretization: `elastic`, `RHS_Interior`, `JU_xJU_yJU_z6`, `metrics`.
- Geometry: `grid`, `unit_normals`, `inter_material`.
- Fault physics: `Interface_Condition`, `CouplingForcing`, `initial_stress_condition`, `iface`.
- Constitutive physics: `material`, `plastic_material`, `plastic`, attenuation portions of `fields` and `RHS_Interior`.
- Sources/verification: `moment_tensor`, `mms`.
- I/O: `fault_output`, `seismogram`, `slice_output`, `plane_output`, `parallel_write`, `mpi3dio`, dormant `hdf5_output`.

Any attenuation or FD-operator change crosses more than one ownership group and should require focused numerical regression review.

## 12. Overall assessment

WaveQLab3D is a capable research/HPC codebase with serious numerical breadth and recognizable architecture, not a toy solver. Its scientific mechanisms are visible and reasonably partitioned at the module level. However, its operational safety currently depends on a narrow set of expected configurations—especially two blocks, familiar process counts, known benchmark names, and hand-maintained response/discretization combinations. Recent expansion into one-block execution and multiple attenuation variants appears only partially integrated.

The best near-term investment is not a broad rewrite. It is to establish hard correctness gates around topology, input dispatch, and numerical regression; then remove the highest-risk duplication behind those tests. That sequence preserves the code's scientific value while making future physical-model work materially safer.
