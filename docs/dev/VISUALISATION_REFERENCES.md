# Visualisation References & Justifications

**Applies to:** `report.py` v1.x
**Last reviewed:** 2025-01
**Maintainer:** Update this document whenever a figure is added, removed, or changed in `report.py`.

This document provides the literature basis for each visualisation included in the WIIBBLE posturographic report. Where a visualisation has been revised or added relative to the original `VISUALISATION_IDEAS.md`, the rationale is noted.

---

## 1. CoP Sway Path + 95% Confidence Ellipse

**Justification**: The stabilogram scatter plot overlaid with a confidence ellipse is arguably the most widely reproduced posturographic figure in the literature. Prieto et al. (1996) formally defined ellipse area as the primary measure of overall sway magnitude and popularised the 95% chi-squared ellipse. It captures both the extent and directionality of sway in a single glance.

**Key references**:
- Prieto, T. E., Myklebust, J. B., Hoffmann, R. G., Lovett, E. G., & Myklebust, B. M. (1996). Measures of postural steadiness: differences between healthy young and elderly adults. *IEEE Transactions on Biomedical Engineering*, 43(9), 956–966.
- Winter, D. A., Patla, A. E., Prince, F., Ishac, M., & Gielo-Perczak, K. (1998). Stiffness control of balance in quiet standing. *Journal of Neurophysiology*, 80(3), 1211–1221.

---

## 2. ML / AP Time Series

**Justification**: The time-domain stabilogram is the foundational representation of postural sway. Collins & De Luca (1993) established the framework of analysing ML and AP channels independently, demonstrating that each axis reflects partially distinct neuromuscular control mechanisms. The time series is also the most intuitive representation for clinicians — slow drift, perturbation responses, and fatigue effects are immediately visible.

**Key references**:
- Collins, J. J., & De Luca, C. J. (1993). Open-loop and closed-loop control of posture: a random-walk analysis of center-of-pressure trajectories. *Experimental Brain Research*, 95(2), 308–318.
- Shumway-Cook, A., & Woollacott, M. H. (2007). *Motor Control: Translating Research into Clinical Practice* (3rd ed.). Lippincott Williams & Wilkins.

---

## 3. CoP Velocity Time Series *(added in report v1)*

**Justification**: Instantaneous velocity of the CoP trajectory provides information about the speed and intensity of postural corrections, which is partially independent of displacement magnitude. Rocchi et al. (2002) demonstrated that mean velocity discriminates between populations where displacement-based measures fail, and noted that velocity is among the most reproducible measures on force platforms. The `Stabilogram.speed` property (Savitzky–Golay differentiation) is already computed within `code_descriptors_postural_control`, making this trivial to include.

This visualisation was **not** in the original `VISUALISATION_IDEAS.md` but was added because it adds clinical interpretive value beyond the time-series position trace.

**Key references**:
- Rocchi, L., Chiari, L., & Horak, F. B. (2002). Effects of deep brain stimulation and levodopa on postural sway in Parkinson's disease. *Journal of Neurology, Neurosurgery & Psychiatry*, 73(3), 267–274.
- Chiari, L., Rocchi, L., & Cappello, A. (2002). Stabilometric parameters are affected by anthropometry and foot placement. *Clinical Biomechanics*, 17(9–10), 666–677.

---

## 4. Power Spectral Density

**Justification**: Frequency-domain analysis reveals the control bandwidth of the postural system. Diener et al. (1984) established that healthy quiet standing is dominated by sway frequencies below 1 Hz. Pathological states — peripheral neuropathy, cerebellar ataxia, vestibular dysfunction — systematically shift spectral energy toward the 1–3 Hz band. The Welch method (used internally by `Stabilogram`) is preferred over simple FFT because it provides a more stable PSD estimate for short, non-stationary signals.

The shaded frequency bands (0–1 Hz and 1–3 Hz) are clinically standard.

**Key references**:
- Diener, H. C., Dichgans, J., Bacher, M., & Gompf, B. (1984). Quantification of postural sway in normals and patients with cerebellar diseases. *Electroencephalography and Clinical Neurophysiology*, 57(2), 134–142.
- Maki, B. E., Holliday, P. J., & Fernie, G. R. (1990). Aging and postural control. *Journal of the American Geriatrics Society*, 38(1), 1–9.
- Donker, S. F., Ledebt, A., Roerdink, M., Savelsbergh, G. J., & Beek, P. J. (2008). Children with cerebral palsy exhibit greater and more regular postural sway than typically developing children. *Experimental Brain Research*, 184(3), 363–370.

---

## 5. Diffusion Plot (Stabilogram Diffusion Analysis — SDA)

**Justification**: SDA characterises the stochastic dynamics of CoP movement as a random process. Collins & De Luca (1993, 1994) showed that the mean square displacement (MSD) follows a power law with a characteristic crossover from short-lag (persistent, open-loop) to long-lag (anti-persistent, closed-loop) behaviour. This crossover — the critical point (t\*, Δr\*) — is a mechanistic marker of the sensorimotor feedback loop. Collins et al. (1995) further showed that this crossover is disturbed in neurological conditions. The log-log presentation is the standard in the SDA literature.

**Key references**:
- Collins, J. J., & De Luca, C. J. (1993). Open-loop and closed-loop control of posture: a random-walk analysis. *Experimental Brain Research*, 95(2), 308–318.
- Collins, J. J., & De Luca, C. J. (1994). Random walking during quiet standing. *Physical Review Letters*, 73(5), 764–767.
- Collins, J. J., De Luca, C. J., Burrows, A., & Lipsitz, L. A. (1995). Age-related changes in open-loop and closed-loop postural control mechanisms. *Experimental Brain Research*, 104(3), 480–492.

---

## 6. CoP Spatial Density (2D Histogram Contour)

**Justification**: Spatial density maps show where the CoP spends most time, independently of the temporal order of samples. This complements the sway path (which shows trajectory) by revealing preferred loading zones. Baratto et al. (2002) introduced the sway density curve as a 1D analogue; a 2D spatial version extends this to show asymmetric loading patterns that are particularly informative in post-stroke, unilateral pain, and prosthetic gait populations.

A contour representation (`go.Histogram2dContour`) is used in preference to a raw 2D histogram because the smooth isocontours are less noisy for the short recording durations typical in clinical assessments.

**Key references**:
- Baratto, L., Morasso, P. G., Re, C., & Spada, G. (2002). A new look at posturographic analysis in the clinical context. *Motor Control*, 6(3), 246–270.
- Morasso, P. G., & Schieppati, M. (1999). Can muscle stiffness alone stabilize upright standing? *Journal of Neurophysiology*, 82(3), 1622–1626.

---

## 7. Feature Radar / Spider Chart

**Justification**: A normalised polar chart summarising 6–8 key features in a single glyph has become standard in clinical performance profiling (e.g., sports science, rehabilitation). No single paper defines this as a posturographic standard, but it is consistent with the composite score approach advocated by Visser et al. (2008) for making multidimensional posturographic data interpretable by non-specialist clinicians.

The features selected for the radar (`confidence_ellipse_area`, `mean_velocity`, `mean_distance_Radius`, `rms_ML`, `rms_AP`, `mean_frequency`, `fractal_dimension`, `LFS`) represent the major posturographic domains: area, velocity, displacement, frequency, and complexity.

Reference ranges used for normalisation are approximate, drawn from:
- Prieto et al. (1996) — area, displacement, velocity
- Goldie et al. (1989) — typical healthy adult ranges
- Expert consensus in the WIIBBLE team

**Key references**:
- Visser, J. E., Carpenter, M. G., van der Kooij, H., & Bloem, B. R. (2008). The clinical utility of posturography. *Clinical Neurophysiology*, 119(11), 2424–2436.
- Goldie, P. A., Bach, T. M., & Evans, O. M. (1989). Force platform measures for evaluating postural control. *Archives of Physical Medicine and Rehabilitation*, 70(7), 510–517.

---

## 8. Feature Summary Table

**Justification**: A plain-language table of key numerical values is essential for clinical record-keeping and handover. Leach et al. (2014) specifically validated ellipse area, path length, RMS, and velocity as the most reliable features on the Wii Balance Board at the session-to-session level. The table groups these alongside frequency and diffusion features with explicit units and human-readable names.

**Key references**:
- Leach, J. M., Mancini, M., Peterka, R. J., Hayes, T. L., & Horak, F. B. (2014). Validating and calibrating the Nintendo Wii balance board to derive reliable center of pressure measures. *Sensors*, 14(10), 18244–18267.

---

## General Background

For a comprehensive review of force-platform posturography methodology — covering signal processing choices, feature selection, test–retest reliability, and clinical validity — see:

- Ruhe, A., Fejer, R., & Walker, B. (2010). The test–retest reliability of centre of pressure measures in bipedal static task conditions. *Gait & Posture*, 32(4), 436–445.
- Chiari, L., Della Croce, U., Leardini, A., & Cappozzo, A. (2005). Human movement analysis using stereophotogrammetry. Part 2: Instrumental errors. *Gait & Posture*, 21(2), 197–211.
- Doyle, R. J., Ragan, B. G., Rajaram, G., Rosengren, K. S., & Hsiao-Wecksler, E. T. (2007). Generalizability of stabilogram diffusion analysis of center of pressure measures. *Gait & Posture*, 25(3), 381–386.
