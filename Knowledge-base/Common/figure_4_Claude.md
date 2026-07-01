# Claude Summary: Figure 4 (Withers et al. 2015) Test Setup + WaveQLab3D `response` Mapping

## Source

- Built from: `Knowledge-base/Claude/figure_3.md`, `FQ_Claude.md`, `response_Claude.md`
- Detailed spec: `Knowledge-base/Claude/figure_4.md`

## What Figure 4 is

Same half-space, source, and receiver as Figure 3, but now **viscoelastic with constant Q** (`γ=0.0`, `Qs0=Qp0=50`) — the first figure that exercises the paper's memory-variable weight-fitting. Expected accuracy: EM<6%, PM<2%.

## `response` setup

**`response = 'anelastic-Q8'`** — per `response_Claude.md`, this is one of the three fully-functional (bulk + near-boundary) anelastic modes, uses `N=8` mechanisms matching the paper, and its built-in NNLS-fitted weight table is explicitly a `γ=0` (constant-Q) fit — the natural, already-working match for this figure.

```fortran
response = 'anelastic-Q8'
&anelastic_Q8_list
  c = 0.014434   ! Qs = c*Vs = 50  (Vs=3464 m/s)
/
```

## New finding (not in earlier reports): this code cannot set `Qp0 = Qs0`

`material.f90` hardcodes `Qp = 2·Qs` (`Qp_inv = 0.5·Qs_inv`) identically across **all seven** anelastic `response` variants — verified at 7 separate call sites. The paper's Fig. 4/5/6 tests all specify `Qp0 = Qs0` (equal, not 2:1). Tuning `c` to hit the paper's `Qs=50` will give `Qp=100` in this code, not `Qp0=50`. There's no namelist path around this — it would require a source change to expose `Qp0` independently. **This should be added to `response.md` as a known limitation**, since it affects reproduction of all three of Figures 4–6.

## Everything else

Domain, grid, moment-tensor source, `'cosine'` source-time function, receiver location, and external f-k/filtering comparison are unchanged from `figure_3_Claude.md` — only `response` and the new `&anelastic_Q8_list` block are added.

## Flag for cross-AI comparison

- **Confidence:** high — `response='anelastic-Q8'` recommendation and the `Qp=2·Qs` hardcoding are both directly verified in `material.f90`. The exact numeric misfit reproduction depends on the unresolved `Qp0` discrepancy above.
