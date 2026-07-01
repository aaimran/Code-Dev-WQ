# Claude Summary: Figure 6 (Withers et al. 2015) Test Setup + WaveQLab3D `response` Mapping

## Source

- Built from: `Knowledge-base/Claude/figure_3.md`–`figure_5.md`, `response_Claude.md`
- Detailed spec: `Knowledge-base/Claude/figure_6.md`

## What Figure 6 is

Same source/receiver pattern as Figures 3–5, but a **two-layer medium** (paper's Table 3) instead of a uniform half-space: shallow layer (Vp=5196/Vs=3000/ρ=2550, 1000 m thick, `Qp0=Qs0=20`) over a half-space (Vp=6000/Vs=3464/ρ=2700, `Qp0=Qs0=210`), both `γ=0.6`. Tests the coarse-grained method against a sharp Q/velocity discontinuity and Love-wave propagation. Reported accuracy: EM 5–10%, PM 1–2% (worse than Fig. 5's uniform case, attributed to the known coarse-grained-scheme limitation at discontinuities).

## `response` setup — two compounding gaps

1. **Same bulk-interior attenuation gap as Figure 5** (`figure_5_Claude.md`): `response='frequency-Q-8M'` is structurally correct but non-functional outside a thin near-boundary shell in the current code — this figure cannot be validly reproduced until that's fixed.
2. **New gap specific to this figure:** `&anelastic_Qf8_list`'s `c` parameter is a single scalar per block; `Qs(x)=c·Vs(x)` only varies with the material's `Vs` field, and the velocity ratio between the two layers (3000/3464≈0.87) doesn't come close to reproducing the required Q ratio (20/210≈0.10). **A single global `c` cannot deliver Table 3's two different `Qs0` values** — this is independent of gap (1) and would need a source-level change (spatially-varying `c`/`Qs0`) to fix.
3. **Material setup:** no built-in `problem=` case matches Table 3's exact velocities. The closest analog, `problem='LOH1'` (`material.f90:596-639`, the classic SCEC layer-over-halfspace benchmark), uses different Vp/Vs/ρ values. An exact reproduction needs `material_source='file'` with a custom-generated two-layer profile (offline step, not a namelist setting).
4. The universal `Qp0=2·Qs0` hardcoding (`figure_4_Claude.md`) applies on top of all of the above.

## Everything else

Source (moment tensor, `'cosine'` time function), receiver offset, and external post-processing unchanged from Figures 3–5.

## Flag for cross-AI comparison

- **Confidence:** high on gaps (1) and (4) (directly reused from verified prior findings); high on gap (2) (straightforward arithmetic on the code's own `Qs=c·Vs` formula vs. Table 3's stated values); medium-high on gap (3) (`LOH1`'s parameter mismatch is directly read from source, but this pass didn't verify whether `LOH1`'s coordinate-1 layering axis is actually depth in this codebase's convention).
- **This is the most heavily-blocked figure in the 3–6 series** — reproducing it validly requires fixing the bulk-interior attenuation gap *and* adding spatially-varying Q parameterization *and* generating a custom material file.
