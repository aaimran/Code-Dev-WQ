# Codex Figure 5 Test Specification Summary

## Purpose

Reproduce Figure 5 of Withers et al. (2015): f–k versus FD for a frequency-dependent-Q homogeneous half-space.

Detailed specification: Knowledge-base/Codex/figure_5.md

## Setup

Reuse Figure 3 completely, then enable:

    Qp0 = Qs0 = 50
    gamma = 0.6
    fT = 1 Hz
    fref = 1 Hz

Target:

    Q(f) = 50                  below 1 Hz
    Q(f) = 50 f^0.6            above 1 Hz, with f in Hz

| Frequency | Q target |
|---:|---:|
| 1 Hz | 50.0 |
| 2 Hz | 75.8 |
| 5 Hz | 131.3 |
| 10 Hz | 199.1 |

Grid, source, receiver, and filter remain:

- dx = 0.04 km;
- dt = 0.002 s;
- source (0,0,1.8) km;
- receiver (12,9,0) km;
- 0.2–10 Hz fourth-order zero-phase filter.

## Response

Required corrected setup:

    response = 'frequency-Q-8M'
    Qs0 = 50
    Qp0 = 50
    gamma = 0.6
    f_trans = 1
    fref = 1

## Current blockers

- f_trans is ignored.
- Qp is forced to 2 Qs.
- Q = 1 table request is clamped to 15, then inverse-Q scaling is applied again.
- Coarse-grained Withers weights are used with conventional storage.
- Eight-mechanism dispatch relies on a four-mechanism flag and allocation.

c = 14.43418 gives Qs = 50 but Qp = 100 and is only a non-faithful diagnostic.

## Required verification

Before wave propagation:

- realized Q error <= 5% over 0.1–10 Hz;
- phase velocity matches input at 1 Hz;
- weights are nonnegative/passive;
- Q rises smoothly above 1 Hz.

The paper reports envelope misfit below 2% and phase misfit below 1%.

Figure 5 must retain more energy than Figure 4 above 1 Hz while remaining similar below 1 Hz.
