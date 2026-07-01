# Frequency-Dependent Attenuation (Q) Modeling

This document summarizes the method for memory-efficient simulation of frequency-dependent seismic attenuation (Q) described by Withers, Olsen, and Day (2015), and its relevance to WaveQLab3D. [1, 2, 3]

## Purpose

Standard seismic simulations often use a frequency-independent (constant) model for the quality factor Q, which describes energy attenuation. However, observations show that Q often increases with frequency, especially above ~1 Hz. [1] Accurately modeling this frequency dependence is computationally expensive. The paper presents a memory-efficient numerical method to simulate frequency-dependent Q, where Q is constant at low frequencies and follows a power-law increase at higher frequencies. [1]

## Key Method

The approach approximates the target Q(f) spectrum by adjusting the weights of several memory variables, each representing a relaxation process.

- A set of relaxation times is chosen to cover the desired frequency bandwidth. [1]
- For high-Q values (>~50-200), a linear least-squares inversion solves for the memory-variable weights that best fit the target Q(f). [1]
- For low-Q values (<~50-200), where the approximation is less accurate, a nonlinear inversion is used, and the resulting weights are fitted to a simple interpolation formula for efficiency. [1]
- The technique is implemented in a "coarse-grained" manner, where memory variables are distributed across grid cells, reducing computational and storage costs. [1]

## Implementation and Validation

The method was implemented in a fourth-order staggered-grid finite-difference code. [1]

Validation was performed by comparing the code's output against semi-analytic solutions (frequency-wavenumber method) for test cases, including:
- A uniform half-space with constant Q.
- A uniform half-space with power-law Q(f). [1]
- A layered model with sharp contrasts in velocity and Q. [1]

The results showed excellent agreement, with misfits in phase and amplitude of only a few percent, validating the method's accuracy even for complex scenarios. [1]

## Key Findings

The method was applied to simulate the 2008 M₩ 5.4 Chino Hills, California, earthquake and compared against real-world seismogram data. [1]

- The frequency-dependent Q(f) model produced significantly more high-frequency energy at larger distances from the fault compared to the constant-Q model. [1]
- The Q(f) model's predictions for ground motion decay with distance were in better agreement with the observed data and established ground-motion prediction equations (GMPEs), particularly at frequencies > 1 Hz. [1]
- The study concludes that including frequency-dependent Q is critical for accurate ground motion prediction, and their method provides a computationally feasible way to do so. [1]

## Relevance to WaveQLab3D

The initial analysis of WaveQLab3D identified "Four- and eight-mechanism constant/frequency-dependent attenuation variants" as a supported feature. The Withers et al. (2015) paper provides the theoretical and numerical basis for such a feature.

- The paper's co-authors (Olsen, Day) are associated with the development of similar codes, suggesting the methods in WaveQLab3D may be based on or related to the techniques described.
- The use of a coarse-grained, memory-variable approach is a highly efficient and validated method for implementing frequency-dependent Q in finite-difference codes like WaveQLab3D.
- The findings underscore the scientific importance of this feature for producing realistic earthquake simulations. Understanding this method is key to verifying, maintaining, and potentially extending the attenuation modeling capabilities within WaveQLab3D.