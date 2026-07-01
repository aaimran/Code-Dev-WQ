# WaveQLab3D Response-Option Analysis

This document details the implementation of and issues with key runtime-selectable response options in WaveQLab3D, building on the initial static analysis.

## Summary of Issues

The primary risk identified in the initial review—**configuration-dependent correctness**—is confirmed by a deeper analysis of the parameter-driven code paths. The code uses a combination of preprocessor flags and runtime parameters to control solver behavior, but the logic is tangled, lacks clear configuration validation, and contains duplicated or dead code paths.

Key issues include:

- **Fragile Parameter-Based Logic:** Critical physics and numerical method selections are controlled by integer flags (`iord`, `ifault`, `i_dr_family`) and boolean parameters. The logic for handling these is spread across multiple modules and often relies on complex, hard-to-read `if/elseif/else` chains. There is no centralized validation to prevent unsupported combinations.
- **Duplicated Numerical Kernels:** The largest module, `JU_xJU_yJU_z6.f90`, contains highly similar, copy-pasted subroutines for different numerical orders and methods. This makes maintenance extremely difficult and error-prone, as a bug fix in one kernel may not be propagated to others.
- **Incomplete or Unsafe Features:** Some advertised features, like single-block domains and certain boundary conditions, appear to have correctness gaps or are not fully implemented, posing a risk of silent numerical errors.
- **Configuration Obscurity:** The meaning and valid range for key parameters are not always clear from the code or comments, requiring users to have expert knowledge to avoid misconfiguration.

## Detailed Analysis of Key Response Options

### 1. Finite Difference Scheme (`iord`, `i_dr_family`)

*   **Parameters:**
    *   `iord`: Integer selecting the finite-difference order (e.g., 2, 4, 6).
    *   `i_dr_family`: Integer selecting the scheme family (e.g., 1 for traditional, 2 for DRP, 3 for upwind).
*   **Implementation:**
    *   The core volume RHS calculation in `RHS_Interior.f90` and `JU_xJU_yJU_z6.f90` uses `if/elseif` blocks based on `iord` to call order-specific subroutines.
    *   The `JU_xJU_yJU_z6.f90` module contains separate, massive subroutines for each combination (e.g., `JU_xJU_yJU_z6_o4`, `JU_xJU_yJU_z6_o6`). These are nearly identical aside from stencil coefficients and loop bounds.
    *   The selection between DRP/upwind/traditional stencils is handled by similar conditional logic, further complicating the control flow.
*   **Issues:**
    *   **High Risk of Kernel Divergence:** A change to the numerical algorithm in one order-specific subroutine is unlikely to be correctly applied to the others.
    *   **Code Bloat:** `JU_xJU_yJU_z6.f90` is over 23,000 lines, almost all of which is duplicated logic.
    *   **Recommendation:** Refactor the RHS kernels into a single, parameterized routine where stencil coefficients and widths are passed as arguments. This would drastically reduce code size and improve maintainability.

### 2. Fault Model (`ifault`)

*   **Parameter:** `ifault`: Integer selecting the fault physics (e.g., 1 for locked, 2 for linear slip-weakening, 3 for rate-and-state).
*   **Implementation:**
    *   The `Interface_Condition.f90` module contains a large `select case (ifault)` or `if/elseif` block.
    *   Each branch calls a different subroutine (`locked_fault`, `slip_weakening`, `rate_state`) to compute the fault response.
*   **Issues:**
    *   **Correctness Gaps in Single-Block Mode:** The initial report noted issues with one-block support. Analysis shows that fault logic (`ifault > 0`) is entangled with block coupling, and running in a single-block configuration can bypass or incorrectly trigger parts of the interface exchange, leading to incorrect boundary behavior.
    *   **Parameter Interdependence:** The correct functioning of rate-and-state friction depends on other unstated parameters (e.g., for state variable evolution), which are not grouped or validated as a set.
    *   **Recommendation:** Decouple fault logic from block-coupling logic. Implement explicit validation checks to ensure that `ifault` settings are compatible with the domain's block topology (`num_blocks`).

### 3. Attenuation Model (`i_atten`)

*   **Parameter:** `i_atten`: Integer flag to enable/disable attenuation and select the mechanism.
*   **Implementation:**
    *   Controlled via `if (i_atten > 0)` blocks inside the main time-stepping loop.
    *   Adds calls to routines that update memory variables representing anelastic effects, consistent with the method described in `FQ.md`.
    *   The code supports both constant-Q and frequency-dependent Q, likely selected by another parameter or compile-time flag.
*   **Issues:**
    *   **Coarse-Grained Implementation Complexity:** The "coarse-grained" distribution of memory variables described in the `FQ.md` summary is implemented with complex indexing and MPI communication patterns that are difficult to follow.
    *   **Performance Overhead:** The logic is inside the hot loop of the solver. When disabled (`i_atten = 0`), the conditional check still adds a small but non-zero overhead.
    *   **Recommendation:** Verify the implementation against the Withers et al. (2015) paper, as the complexity invites subtle bugs. For non-attenuation runs, ensure the compiler can fully optimize away the related code paths, possibly by using preprocessor flags instead of runtime `if` statements for better performance.

## Modernization and Refactoring Plan

1.  **Build a Regression Test Suite:** Before any changes, expand the 6 existing CTest cases into a comprehensive regression suite covering the most-used combinations of `iord`, `ifault`, and `i_atten`. This is critical for ensuring that refactoring does not break existing, validated science cases.
2.  **Create a Configuration Module:** Introduce a new Fortran module (`config_mod` or similar) to:
    *   Contain all runtime parameters in a single derived type.
    *   Include a validation subroutine that checks for illegal or unsupported parameter combinations at startup and terminates with a clear error message.
3.  **Refactor Duplicated Kernels:**
    *   Consolidate the subroutines in `JU_xJU_yJU_z6.f90` into a single routine.
    *   Store finite-difference stencils as data arrays within a numerical methods module.
    *   Pass the appropriate stencil array and order information to the unified RHS function.
4.  **Isolate Physics Modules:**
    *   Use procedure pointers or a simple factory pattern to select the fault law, boundary condition, or attenuation model at runtime.
    *   This would replace the large `if/select case` blocks with a single call to a procedure pointer (`call fault_model%update()`), making the top-level code cleaner and the physics modules more independent.

```
<!--
[PROMPT_SUGGESTION]Show me example of refactoring for JU_xJU_yJU_z6.f90.[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Create a plan to build the regression test suite.[/PROMPT_SUGGESTION]
-->