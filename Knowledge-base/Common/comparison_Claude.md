# Claude Summary: Claude vs Codex vs Gemini `src/` Comparison

## Source

- Method: direct `diff` across the three `src/` trees (not independent re-analysis — the three share an almost byte-identical baseline)
- Detailed version: `Knowledge-base/Claude/comparison.md`
- Related: `Knowledge-base/Claude/response.md`, `figure_4.md` (the `anelastic-Q8` `Qp0`/`Qs0` issue this comparison centers on)

## Headline finding

All three `src/` trees are nearly identical (same `response` system, same 11 options, even identical code comments) — the only real differences are each AI's attempt at fixing the same one bug: `anelastic-Q8` hardcoding `Qp = 2·Qs`. None of the three touched the larger issues from `response.md` (bulk-interior attenuation gap, duplicate-dispatch bug, `target_Q` double-scaling bug).

## Ranked comparison

| Rank | AI | What was delivered |
|---|---|---|
| 1 | **Codex** | Real fix in `material.f90`/`datatypes.f90`: exposes `Qs0`/`Qp0` directly, adds input validation (rejects invalid `Qs0`/`Qp0`/`mu`/`rho`/`fref`, catches an unhandled `val_S`/`val_P ≥ 1` modulus-correction failure mode), **re-fits the 8 weight values for the Q≈50 regime** (rather than trusting the inherited high-Q-oriented weights), and adds a runtime self-check (`q8_max_relative_error`) that warns if realized Q error exceeds 5%. |
| 2 | **Claude** (this session) | Real, minimal fix: adds `cp` parameter (`Qp=cp·Vp`), sentinel-default backward compatible. Verified via isolated syntax/logic check (full build not achievable in this environment). No input validation, no runtime accuracy check. |
| 3 | **Gemini** | **No working fix.** `material.f90` unchanged. Instead added 3 new files (`config_mod.f90`, `attenuation_mod.f90`, `main.f90.new`) that are not in `CMakeLists.txt`'s build list and would not compile if added (`USE datatypes, ONLY: real_wp` — `real_wp` is undefined in this codebase; the real kind parameter is `wp`). The actual "update" subroutines are empty stubs with `! Actual implementation ... goes here` comments. This matches a "Create a Configuration Module" item in Gemini's own `response.md` refactor proposal — an architectural sketch, not an attempt at the actual bug. |

## Why Codex's fix is notably better, not just "more code"

The key technical point: the shared baseline's `anelastic-Q8` weights are commented as a "Q0*=1 reference, linearly rescaled by 1/Q at runtime" — but the paper this feature implements (`FQ.md` §2) states that linear rescaling from a Q0*=1 reference is only accurate for **Q > 200**. Figure 4 (and this project's actual test decks) target **Q=50** — squarely in the regime the paper says needs the nonlinear low-Q correction instead. Codex appears to have caught this and re-fit weights specifically for Q≈50, with a runtime check that would flag it if used outside that range. Claude's fix (and the original code) did not catch or address this at all — it inherited and reused the existing weight table without re-verifying its claimed accuracy at the Q value actually in use.

## Flag for cross-AI comparison

- **Confidence:** high — based on direct `diff` output and reading of the actual changed code (not self-reported summaries). Gemini's non-compiling claim (`real_wp` undefined) was independently verified by grepping `datatypes.f90`/`common.f90` for the symbol.
- **Not independently build-verified:** Codex's and Gemini's changes were assessed by source reading only, not compiled, in this pass (a full project build was not achievable in this session's environment for unrelated toolchain reasons — see `comparison.md` §5).
- **Scope note:** this comparison is narrow by construction — it reflects only the one bug all three happened to touch (`anelastic-Q8` `Qp0`/`Qs0`), not a full comparative code-quality audit of all ~50K lines in each tree.
