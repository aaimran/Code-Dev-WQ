# WaveQLab3D Response Options: Parameters, Implementation, and Issues

## 1. Scope

This report traces the response option in Codex/WQ/src from input parsing through initialization, constitutive state allocation, right-hand-side evaluation, Runge–Kutta updates, PML treatment, and plastic correction.

The accepted response strings are:

1. elastic
2. plastic
3. anelastic
4. low-pass
5. anelastic-Q
6. anelastic-Q8
7. anelastic-Qf
8. constant-Q-4M
9. constant-Q-8M
10. frequency-Q-4M
11. frequency-Q-8M

The review is static. The environment does not provide CMake or a Fortran/MPI compiler, so the findings have not been confirmed by executing the solver.

## 2. Executive findings

The response system consists of three real behaviors:

- Elastic propagation with no additional constitutive state.
- Elastic propagation followed by an end-of-step plastic correction.
- Elastic propagation coupled to four- or eight-mechanism generalized standard-linear-solid memory variables.

Several response names are aliases:

- low-pass and anelastic use the same initializer and state.
- frequency-Q-4M and anelastic-Qf use the same four-mechanism implementation and namelist.
- frequency-Q-8M is implemented by setting the four-mechanism activation flag and routing through a dispatcher that detects eight-mechanism allocation.
- constant-Q-8M similarly sets the four-mechanism flag and relies on allocation-based dispatch.

The most serious confirmed source issues are:

1. f_trans is read and stored for frequency-dependent Q but never used to scale relaxation times, so changing it has no effect on the attenuation spectrum.
2. The frequency-Q initializers request Withers weights at Q = 1, but the table routine clamps Q below 15 to Q = 15. The RHS then multiplies those already Q-dependent weights by local inverse Q again.
3. constant-Q-4M is dispatched twice at one RHS site, doubling its stress-memory contribution and rate update for that subset of points.
4. Constant-Q weight methods mix target_Q-dependent fitted weights with a second local inverse-Q scaling in the RHS; the intended normalization is therefore ambiguous and likely inconsistent.
5. The lookup method scales weights proportional to target_Q, the opposite direction from the usual inverse-Q attenuation scaling.
6. The withers method computes but never uses its requested-band scale factor; fmin, fmax, and target_Q do not meaningfully control its returned weights.
7. The legacy anelastic/low-pass option initializes tau and weights only for weight_exp near 0 or 0.6. Other accepted values leave zero relaxation times and can cause division by zero.
8. Plastic parameters mu_beta_eta are initialized only for problem = rate-weakening. Other problem/default combinations can use undefined values in the default plastic model.
9. The example response test files use namelist groups not consumed by the current main/domain input path, and none of these response examples are registered as CTest cases.

## 3. Global selection and lifecycle

### 3.1 Input location

response and plastic_model belong to problem_list in domain.f90:

    &problem_list
      response = 'elastic'
      plastic_model = 'default'
      ...
    /

Defaults:

| Parameter | Default |
|---|---|
| response | elastic |
| plastic_model | default |

The master rank trims and left-adjusts response, validates it against the eleven exact strings, then broadcasts the normalized value and invalid flag. Matching is case-sensitive.

An invalid response triggers MPI_Finalize followed by a C exit with status 1. This is better than a rank-local stop, though other response parameter failures still use stop.

### 3.2 Initialization dispatch

block:init_block uses a chain of independent if statements. Exactly one initializer should run for a valid response, except aliases route to the same initializer.

After material initialization:

- attenuation responses allocate Q arrays and six memory-variable families;
- plastic allocates plastic strain/rate state;
- elastic allocates neither.

All blocks remain physically elastic in block physics. Response changes constitutive behavior layered onto the same nine-field elastic velocity–stress system.

### 3.3 Per-stage execution

For every low-storage Runge–Kutta stage:

1. fields:scale_rates_interior scales field and active memory-variable rates by RK coefficient A.
2. RHS_Interior computes elastic velocity/stress rates.
3. Active attenuation kernels subtract memory stress from stress rates and accumulate memory-variable derivatives.
4. PML-specific attenuation kernels replace ordinary strain terms inside PML points.
5. fields:update_fields_interior advances wavefield, memory variables, and PML state by the RK B-stage increment.

Plasticity is different: domain:update_fields calls update_fields_plastic only after the last RK stage, using the full D%dt. This is an operator-split correction rather than a stage-coupled constitutive evolution.

## 4. Common attenuation data model

Every attenuation family stores:

- a logical activation flag;
- mechanism count and model parameters;
- Qp inverse and Qs inverse three-dimensional arrays;
- relaxation times tau;
- weights;
- six memory arrays eta4 through eta9, corresponding to six stress components;
- six memory-rate arrays Deta4 through Deta9.

The four-mechanism families allocate 48 extra real values per grid point:

    6 stress components x 4 mechanisms x (state + rate)

The eight-mechanism families allocate 96 extra real values per grid point. Two inverse-Q arrays add another two values per point. Ghost nodes are included.

This is a conventional all-mechanisms-per-point layout, not the coarse-grained one-mechanism-per-point layout described by Withers et al. Published coarse-grained weights therefore require normalization conversion before direct use.

## 5. Elastic

### Purpose

Pure elastic wave propagation with no intrinsic attenuation or plastic correction.

### Parameters

No response-specific namelist.

### Implementation

- Material stores lambda, mu, and density in M(:,:,:,1:3).
- The wavefield has nine components: three velocities and six stresses.
- RHS_Interior calculates elastic stress and velocity rates.
- No memory variables are allocated.
- update_fields_plastic immediately returns because response is not plastic.

### Issues

Elastic is the clean baseline and the best control case for every attenuation test. There is no centralized post-initialization assertion proving all attenuation flags are false, although derived-type defaults make that the expected state.

## 6. Plastic

### Purpose

Elastic wave propagation with off-fault plastic/viscoplastic stress correction.

### Parameters

Top-level:

| Parameter | Meaning | Default |
|---|---|---|
| plastic_model | Selects scec or default plastic algorithm | default |

Per block, block_list supplies:

| btp field | Meaning |
|---|---|
| mu_beta_eta(1) | Internal friction parameter mu |
| mu_beta_eta(2) | Dilatancy parameter beta |
| mu_beta_eta(3) | Viscosity/relaxation parameter eta |

### Initialization

init_plastic_material allocates two scalars per interior point:

- P(:,:,:,1): plastic strain
- P(:,:,:,2): plastic strain rate

For problem = rate-weakening, it copies mu_beta_eta into the block plastic structure. For TPV31 the copy is commented out. For all other problems, the state arrays are zeroed but the three parameters are not initialized.

### Update

Plasticity runs once after the final RK stage:

- PML zones are excluded to prevent artificial PML stresses from triggering yield.
- Initial stress is reconstructed from problem and coordinates.
- plastic_model = scec calls plastic_flow2, a hard-coded Drucker–Prager-like viscoplastic return.
- Other plastic_model values call plastic_flow using mu, beta, eta and elastic bulk/shear moduli.

The scec branch hard-codes cohesion, bulk friction, and relaxation time, with alternate values for TPV30.

### Issues

- Critical: mu_beta_eta is undefined for default problem combinations and TPV31 when plastic_model is not scec.
- plastic_model is not validated. Any misspelling silently selects the default branch.
- Parameters are problem-dependent in two places: plastic_material and plastic_flow2.
- The full-step correction after RK is undocumented operator splitting and needs temporal-convergence tests.
- Plastic state is not part of RK stage scaling/update.
- PML exclusion bounds are hand-coded per face and need decomposition-edge tests.
- The response cannot combine plasticity with attenuation because response is a single exclusive string.

## 7. Legacy anelastic and low-pass

### Relationship

Both strings call init_anelastic_properties and activate M%anelastic. There is no implementation difference.

### Namelist

    &anelastic_list
      c = 1.0
      weight_exp = 0.0
      fref = 1.0
    /

| Parameter | Code meaning | Default |
|---|---|---:|
| c | Qs = c times Vs, because Qs_inverse = 1/(c Vs) | 1.0 |
| weight_exp | Selects one of two hard-coded spectra | 0.0 |
| fref | Reference frequency for modulus correction | 1.0 Hz |

Qp is hard-coded as 2 Qs because Qp_inverse = 0.5 Qs_inverse.

### Spectrum

- N = 4.
- tau uses a denominator of 16 even though only four mechanisms exist.
- weight_exp < 0.01 selects one hard-coded weight set.
- 0.59 < weight_exp < 0.61 selects another.
- Both use fixed limits derived from 15 Hz and 0.08 Hz with an additional factor of 200 in taumax.

### Implementation

The initializer:

1. allocates Q inverse and six four-mechanism state/rate families;
2. calculates Qs and Qp from c and local Vs;
3. assigns hard-coded tau/weights for two narrow weight_exp cases;
4. adjusts lambda and mu to unrelaxed values at fref.

The RHS has ordinary and PML versions, and fields scales/updates this family at every RK stage.

### Issues

- Critical: most weight_exp values match neither branch. tau and weights retain their zero defaults; RHS kernels divide by tau.
- low-pass is undocumented as an exact alias.
- c semantics are not obvious and differ from some comments elsewhere.
- The tau denominator is explicitly described in newer code as a bug for N = 4.
- No validation exists for c > 0, fref > 0, positive tau, nonnegative weights, or 1 - modulus correction > 0.
- Only two exponent neighborhoods are supported despite weight_exp being a free real input.

This option should be treated as legacy until bounded parameter validation and spectrum tests exist.

## 8. anelastic-Q

### Purpose

Four-mechanism constant-Q GSLS model intended to fix the legacy tau spacing.

### Namelist

    &anelastic_Q_list
      c = 1.0
      fref = 1.0
    /

| Parameter | Meaning | Default |
|---|---|---:|
| c | Qs = c times Vs | 1.0 |
| fref | Modulus-correction reference frequency | 1.0 Hz |

Qp = 2 Qs.

### Spectrum

- N = 4.
- Nominal band: 0.05–20 Hz.
- tau is log-spaced using denominator 2N = 8.
- Four fixed NNLS weights are stored for a normalized constant-Q spectrum.
- Source comments say fit range 0.08–15 Hz, maximum Q error below 18%, and mean below 0.3%.

### Implementation

The fixed normalized weights are multiplied by local inverse Q in the RHS. The initializer uses the same scaling in its fref modulus correction. Ordinary/PML kernels and RK memory-state handling are complete.

### Issues

- c and fref are not validated.
- Q is tied to local Vs through Qs = c Vs; users cannot independently prescribe Qp/Qs fields.
- The stated nominal band and stated fit band differ.
- A maximum error near 18% is materially larger than the 5% often associated with eight-mechanism fits.
- No runtime output reports actual Q range, tau, weights, or modulus-correction denominator.

## 9. anelastic-Q8

### Purpose

Eight-mechanism constant-Q model with improved broadband fit.

### Namelist

    &anelastic_Q8_list
      c = 1.0
      fref = 1.0
    /

Parameters and Qp/Qs relation match anelastic-Q.

### Spectrum

- N = 8.
- Band: 0.05–20 Hz.
- tau uses denominator 2N = 16.
- Eight hard-coded normalized NNLS weights.
- Comments claim maximum Q error below 5% and mean below 0.1%.

### Implementation

This family has dedicated Q arrays, state/rate arrays, ordinary/PML RHS kernels, and RK scaling/update branches.

### Issues

- c meaning is stated inconsistently in comments: one location says Qs = c times Vs while other response comments say c divided by Vs. The executable formula is Qs = c times Vs.
- Same validation and observability gaps as anelastic-Q.
- Roughly twice the attenuation-state memory and arithmetic of the four-mechanism option.

## 10. anelastic-Qf and frequency-Q-4M

### Relationship

Both strings call init_anelastic_Qf_properties and use anelastic_Qf_list. They are exact implementation aliases.

### Namelist

    &anelastic_Qf_list
      c = 1.0
      gamma = 0.0
      f_trans = 1.0
      fref = 1.0
    /

| Parameter | Intended meaning | Default | Actual behavior |
|---|---|---:|---|
| c | Qs scaling, Qs = c times Vs | 1.0 | Used |
| gamma | Power-law exponent | 0.0 | Clamped to 0.0–0.9 and used for table interpolation |
| f_trans | Transition frequency | 1.0 Hz | Stored but never used |
| fref | Modulus-correction reference frequency | 1.0 Hz | Used |

### Spectrum

- N = 4.
- The first four mechanisms are extracted from the eight-mechanism Withers tables.
- gamma interpolates tabulated tau limits and weights.
- Q below 15 is clamped to 15 inside get_withers_weights.

### Implementation

The initializer calls:

    get_relaxation_times_Qf(gamma, tau)
    get_withers_weights_Qf(gamma, 1.0, weights)

It then computes local Qs inverse from c and Vs, adjusts moduli at fref, and the RHS multiplies each weight by local Q inverse.

### Issues

- Critical: f_trans never affects tau. The model remains tied to the tables’ original transition/band regardless of input.
- Critical/semantic: requesting weights at Q = 1 does not return unscaled Q = 1 weights. withers_tables clamps Q < 15 to Q = 15, after which the RHS multiplies by inverse Q again.
- Taking the first four entries from an eight-mechanism optimized spectrum is not equivalent to fitting an optimized four-mechanism model. The comment claiming those four are optimized for this case is not substantiated in the table code.
- The paper’s coarse-grained weights appear to be used in a conventional all-mechanism layout without a visible division by eight.
- gamma is silently clamped instead of rejected or reported.
- c, f_trans, and fref are not validated for positivity.
- Alias names are redundant and may mislead users into expecting distinct models.

## 11. frequency-Q-8M

### Namelist

    &anelastic_Qf8_list
      c = 1.0
      gamma = 0.0
      f_trans = 1.0
      fref = 1.0
    /

Semantics mirror the four-mechanism frequency-dependent option.

### Implementation

- Allocates eight-mechanism Qf8 state.
- Sets both anelastic_Qf8 and anelastic_Qf true.
- The top-level RHS checks anelastic_Qf, then apply_anelastic_Qf_point_dispatch detects allocated Qf8 arrays and calls the eight-mechanism kernel.
- fields similarly checks allocation before choosing the eight- or four-mechanism state.

### Issues

- f_trans is stored but unused.
- Q = 1 weight request is clamped to Q = 15, then locally inverse-Q scaled again.
- The Qf flag is overloaded to mean either four- or eight-mechanism frequency Q; the dedicated Qf8 flag is not used by the RHS or field update.
- Dispatch depends on allocation status rather than an explicit model enum.
- Published coarse-grained versus conventional normalization needs verification.
- The comment says tau is independent of gamma, but get_relaxation_times interpolates gamma-dependent tau_min and tau_max.

## 12. constant-Q-4M

### Namelist

    &constant_Q_4M_list
      c = 1.0
      fmin = 0.05
      fmax = 20.0
      target_Q = 50.0
      weight_method = 'nnls'
      manual_weights = 0, 0, 0, 0
      fref = 1.0
    /

| Parameter | Intended meaning | Default |
|---|---|---:|
| c | Local Qs scale: Qs = c times Vs | 1.0 |
| fmin | Lower design frequency | 0.05 Hz |
| fmax | Upper design frequency | 20 Hz |
| target_Q | Constant-Q target used by fitting | 50 |
| weight_method | nnls, withers, or lookup | nnls |
| manual_weights | Full override if every entry is positive | all zero |
| fref | Modulus-correction frequency | 1 Hz |

Qp = 2 Qs.

### Relaxation times

Four tau values are log-spaced between:

    tau_min = 1/(2 pi fmax)
    tau_max = 1/(2 pi fmin)

### Weight methods

nnls:

- Runs a custom projected iterative routine at 30 log-spaced frequencies.
- Uses compute_Q_response and an approximate Hessian/gradient.
- Stops at 100 iterations or a small direction norm.

withers:

- Loads gamma = 0 Withers eight-mechanism weights.
- Returns the first four.
- Computes a band scale factor but does not use it.

lookup:

- Calls the withers path.
- Multiplies returned weights by target_Q/50.

manual:

- Used only if all four entries are strictly positive.

### Implementation

The RHS uses local inverse Q based on c and Vs in addition to the chosen weights. A dispatcher selects the four- or eight-mechanism kernel based on whether eight-mechanism arrays are allocated.

### Issues

- Critical: at RHS_Interior lines 257–258, the dispatcher is called twice consecutively. This doubles both memory-stress subtraction and Deta accumulation for points handled by that code path.
- target_Q influences fitted weights, while c independently defines a spatial Q that multiplies those weights again in the RHS. The intended effective Q is unclear.
- lookup scaling increases weights as target_Q increases; weaker attenuation normally requires smaller weights.
- withers ignores target_Q and does not use the calculated fmin/fmax scale factor.
- lookup therefore also does not genuinely adapt the spectral band.
- manual weights cannot contain a deliberate zero because override requires all entries > 0.
- Sanitized fmin/fmax/target_Q values are not written back to the corresponding M metadata fields after correction.
- No post-fit error, convergence status, weight-sum check, or nonfinite check is reported.
- The routine named NNLS is an approximate custom optimizer, not a standard verified NNLS implementation.
- Invalid weight_method falls back to nnls with a warning from every participating rank.

## 13. constant-Q-8M

### Namelist

constant_Q_8M_list has the same parameters as the four-mechanism list, with eight manual weights.

### Implementation

- Allocates eight-mechanism constant-Q state.
- Sets both anelastic_const_Q_8M and anelastic_const_Q_4M.
- The top-level RHS only tests the 4M flag.
- apply_const_Q_4M_point_dispatch detects allocated eta4_8M and routes to the 8M kernel.
- fields uses allocation detection to scale and update 8M state.

### Issues

- The 8M activation flag is effectively unused outside initialization.
- Model selection relies on allocation state and a misleading 4M dispatcher name.
- The same target_Q/local-Q double-scaling ambiguity applies.
- The withers and lookup method issues apply.
- The duplicate dispatcher call at the first RHS site also invokes the 8M kernel twice for that code path.
- Eight mechanisms double the principal memory-state footprint versus 4M.

## 14. RHS and PML implementation

Each attenuation kernel:

1. subtracts the sum of the relevant memory stresses from DU(4:9);
2. computes six Deta families from strain-rate components;
3. divides each mechanism update by tau.

Ordinary kernels use Ux, Uy, and Uz directly. PML variants form corrected strain terms from spatial derivatives and PML auxiliary fields before applying the same constitutive form.

point_in_pml selects the PML variant for all modern attenuation families.

Issues:

- Response calls are copied into many stencil-region loops, creating consistency risk. The duplicate call proves this risk is already realized.
- The top-level repeated blocks test flags independently rather than dispatching one model once.
- PML and ordinary formulas are manually duplicated for every family.
- No assertion guarantees exactly one attenuation family is active.
- Allocation-based dispatch hides invalid flag combinations.

## 15. Parameter consistency problems

### c has two roles in configurable constant-Q options

The executable formula is:

    Qs_inverse = 1/(c Vs)
    Qp_inverse = 0.5 Qs_inverse

Therefore:

    Qs = c Vs
    Qp = 2 Qs

Some comments incorrectly describe Qs as c divided by Vs. target_Q is a second Q control in constant-Q-4M/8M. The code does not document how target_Q and c are meant to combine.

### fref

fref is used in modulus correction but is not validated. Zero or negative values are accepted. There is no output confirming phase velocity at fref.

### f_trans

f_trans is wholly ineffective in both frequency-dependent implementations. It is read, stored, and never referenced again.

### gamma

gamma is clamped to 0–0.9. The user receives no warning that input was changed.

### Qp/Qs relation

Every attenuation option hard-codes Qp = 2 Qs. Independent Qp and Qs input fields are not supported by these initializers.

### Spatial behavior

Q is derived from local Vs and a global c, so Q varies with material velocity. target_Q is global. This distinction is not surfaced in the input documentation.

## 16. Input examples and testing status

Files named test_const_Q_4M.in, test_const_Q_8M.in, test_freq_Q_4M.in, and test_freq_Q_8M.in exist. However, they use domain_list and parameters_list, whereas the current main/domain path reads problem_list and block_list. They appear to target another input schema and are not usable evidence that current response parsing works.

The active CMake file registers rupture tests only. It does not register:

- any attenuation response;
- plastic response;
- response validation failures;
- PML plus attenuation;
- four-versus-eight mechanism comparisons;
- fref, gamma, f_trans, or weight-method behavior.

## 17. Response matrix

| Response | Mechanisms | Spectrum | Extra parameters | RHS/PML | Status |
|---|---:|---|---|---|---|
| elastic | 0 | None | None | Elastic only | Baseline |
| plastic | 0 | None | plastic_model, mu_beta_eta | End-step plastic correction | Parameter initialization risk |
| anelastic | 4 | Two hard-coded legacy spectra | c, weight_exp, fref | Dedicated ordinary/PML | Unsafe for most weight_exp |
| low-pass | 4 | Same as anelastic | Same | Same | Undocumented alias |
| anelastic-Q | 4 | Fixed constant-Q NNLS | c, fref | Dedicated ordinary/PML | Operational but untested |
| anelastic-Q8 | 8 | Fixed constant-Q NNLS | c, fref | Dedicated ordinary/PML | Operational but untested |
| anelastic-Qf | 4 | First four Withers mechanisms | c, gamma, f_trans, fref | Qf dispatcher | f_trans and scaling defects |
| frequency-Q-4M | 4 | Same as anelastic-Qf | Same | Same | Alias with same defects |
| constant-Q-4M | 4 | Configurable band/weights | c, fmin, fmax, target_Q, method, manual, fref | Shared const-Q dispatcher | Duplicate call and scaling ambiguity |
| constant-Q-8M | 8 | Configurable band/weights | Same, 8 manual weights | Allocation-routed 8M | Same issues |
| frequency-Q-8M | 8 | Full Withers table | c, gamma, f_trans, fref | Allocation-routed Qf8 | f_trans and scaling defects |

## 18. Recommended fixes

### Priority 0: correctness

1. Remove the duplicate constant-Q dispatcher call.
2. Make f_trans scale tau explicitly and test at multiple transition frequencies.
3. Define one weight convention:
   - normalized shape multiplied by local inverse Q in RHS, or
   - fully Q-scaled weights with no second Q multiplication.
4. Correct Withers conventional/coarse-grained normalization.
5. Do not request Q = 1 through a routine that clamps to Q = 15.
6. Initialize mu_beta_eta for every plastic path or reject unsupported combinations.
7. Reject unsupported legacy weight_exp values before tau is used.

### Priority 1: explicit model dispatch

1. Replace eleven strings plus overlapping flags with a response enum.
2. Use one select case in init_block.
3. Use one attenuation dispatch call at each RHS point.
4. Dispatch explicitly on model, not allocated arrays.
5. Assert exactly one constitutive response is active.
6. Either remove aliases or document them as deprecated names.

### Priority 2: parameter validation

Validate collectively:

- c > 0;
- fref > 0;
- f_trans > 0;
- 0 <= gamma <= 0.9;
- 0 < fmin < fmax;
- target_Q > 0;
- all tau > 0 and finite;
- weights nonnegative and finite;
- modulus-correction denominators positive;
- plastic_model in an explicit allowed set;
- plastic coefficients initialized and physically valid.

Report normalized parameters, tau, weights, local Q range, and fitted error on the master rank.

### Priority 3: testing

1. Material-point Q(f) and phase-velocity tests for every attenuation response.
2. Alias-equivalence tests.
3. f_trans sensitivity test.
4. Four/eight mechanism accuracy and memory comparison.
5. PML versus ordinary kernel consistency.
6. Constant-Q method comparison for nnls, withers, lookup, and manual.
7. Plastic yield/no-yield and temporal-convergence tests.
8. MPI partition invariance.
9. Debug build with bounds, NaN initialization, and floating-point traps.

## 19. Bottom line

The response architecture contains a useful range of elastic, plastic, constant-Q, and frequency-dependent-Q models, and its RK/PML memory-state plumbing is substantial. However, the option surface is ahead of its verification and input semantics.

Elastic is the reliable baseline. The fixed four- and eight-mechanism constant-Q options are structurally complete but lack tests. Plasticity has uninitialized-parameter combinations. The legacy anelastic aliases accept unsafe exponent values. The configurable constant/frequency-Q families contain confirmed dispatch and parameter-effect defects.

Before scientific use of the newer response options, the code needs a single explicit model dispatch, one documented weight/Q convention, repaired f_trans behavior, and response-specific numerical regression tests.
