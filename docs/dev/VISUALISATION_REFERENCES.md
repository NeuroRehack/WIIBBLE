# Visualisation References & Interpretation Guide

**Applies to:** `report.py` v1.x
**Last reviewed:** 2026-07
**Maintainer:** Update this document whenever a figure is added, removed, or changed in `report.py`.

This document serves two purposes:

1. **Interpretation** — what each report figure shows, how it is derived (in general and mathematical terms), and how to read it clinically.
2. **Literature** — the published basis for including each visualisation.

It is written for clinicians, researchers, and reviewers. It does **not** describe implementation details or source code.

---

## Shared signal pipeline (all report figures)

Every plot in the HTML report is built from the same processed **stabilogram** — a time series of centre-of-pressure (CoP) position in centimetres.

### Step 1 — From board forces to CoP (cm)

During recording, WIIBBLE stores raw force **deviations** at each corner (in kg). These are converted to CoP using the lever-arm model validated for the Wii Balance Board (Leach et al. 2014):

$$
\text{CoP}_{ML}\;[\text{cm}] = 21.65 \times \frac{x_{kg}}{W_{total}}
$$

$$
\text{CoP}_{AP}\;[\text{cm}] = 11.90 \times \frac{y_{kg}}{W_{total}}
$$

where:

- $x_{kg} = (F_{top\_right} + F_{bottom\_right}) - (F_{top\_left} + F_{bottom\_left})$ — net left–right force imbalance
- $y_{kg} = (F_{top\_left} + F_{top\_right}) - (F_{bottom\_left} + F_{bottom\_right})$ — net front–back force imbalance
- $W_{total}$ is the calibrated body weight (kg) stored in the recording metadata

**Axis convention (report plots):**

| Axis | Positive direction |
|------|-------------------|
| Mediolateral (ML) | Right |
| Anteroposterior (AP) | Forward (toward the top of the board) |

### Step 2 — Mean centring (critical for interpretation)

Before any further processing, the **session mean** is subtracted from both ML and AP:

$$
\text{CoP}_{ML,centred}(t) = \text{CoP}_{ML}(t) - \overline{\text{CoP}}_{ML}
$$

$$
\text{CoP}_{AP,centred}(t) = \text{CoP}_{AP}(t) - \overline{\text{CoP}}_{AP}
$$

This is standard in posturographic analysis: spatial plots and most derived features describe **sway variability around the average stance**, not absolute position on the board.

The original (uncentred) means are preserved numerically as **Mean position — ML** and **Mean position — AP** in the feature summary table.

### Step 3 — Resampling and filtering

The centred signal is then:

1. **Resampled** to a uniform 25 Hz time grid (SWARII method).
2. **Low-pass filtered** at 10 Hz (4th-order Butterworth, zero-phase).

All report figures use this final processed stabilogram unless noted otherwise.

---

## Live canvas vs HTML report — reference frames

A common source of confusion is comparing the **live WIIBBLE canvas** during a session with the **offline HTML report**. They use different reference frames.

### Live canvas (during recording)

| Element | Reference frame |
|---------|----------------|
| **Global crosshairs** (solid grey) | Board geometric centre — neutral, symmetric loading |
| **Cursor / sway trail** | Instantaneous absolute CoP relative to board centre |
| **Local crosshairs** (dotted, optional) | Centre of the sway bounding box — *not* the board centre |

When the cursor sits on the global crosshairs, the patient’s CoP is approximately at the board centre **at that instant**. The display may apply a smoothing filter; recorded data is always raw.

The canvas shows **absolute** position. It does **not** subtract the session mean.

### HTML report (spatial plots: sway path, density)

| Element | Reference frame |
|---------|----------------|
| **Origin (0, 0) and dashed crosshairs** | Session **average** stance (after mean centring) |
| **Sway path, ellipse, density contours** | Variability **around** that average |

After mean centring, the statistical centre of the sway cloud is at the origin by design. The plots answer: *“How much and in what pattern did the patient move relative to where they stood on average?”*

They do **not** directly answer: *“How far from the board centre was the patient throughout the test?”* — that is reported numerically as **Mean position — ML/AP** in the feature table.

### Practical comparison guide

| Observation | Likely explanation |
|-------------|-------------------|
| Cursor on global crosshairs during test, sway path centred in report | Expected — average stance was near board centre and variability is shown around that mean |
| Cursor on global crosshairs, but **Mean position** in table is non-zero (e.g. 0.3 cm ML) | Small sustained bias (foot placement, sensor asymmetry, calibration). Spatial plots still centre at origin; check the table for absolute offset |
| Sway path looks shifted to one side but ML/AP time series oscillate around **y = 0** | Visual asymmetry in sway **shape** (more excursions one way), not a DC offset. Origin is correct |
| ML/AP time series oscillate around a **non-zero** value | Unusual — contact the development team with the CSV |

### What the report is not

- **Not** a pixel-for-pixel replay of the live canvas.
- **Not** an absolute board-centre plot (unless you read **Mean position** from the table).
- **Not** affected by the display smoothing filter (recordings are always raw).

---

## 1 · CoP Sway Path & 95% Confidence Ellipse

### What it shows

A bird’s-eye view of the CoP trajectory in the ML–AP plane: where the pressure point moved throughout the recording, plus a 95% confidence ellipse summarising sway extent and direction.

### How it is derived

1. Each processed sample is a point $(\text{ML}, \text{AP})$ in cm (mean-centred).
2. Points are connected in **time order** to form the sway path.
3. The 95% confidence ellipse is computed from the covariance matrix of ML and AP:

$$
\mathbf{\Sigma} = \text{cov}\begin{pmatrix} \text{ML} \\ \text{AP} \end{pmatrix}
$$

The ellipse boundary satisfies:

$$
(\mathbf{x} - \boldsymbol{\mu})^T \mathbf{\Sigma}^{-1} (\mathbf{x} - \boldsymbol{\mu}) = \chi^2_{2,\,0.95} \approx 5.991
$$

where $\boldsymbol{\mu}$ is the mean position (≈ $(0, 0)$ after centring). The ellipse **area** (cm²) is reported in the title when features are available.

Green dot = first sample after processing; red × = last sample.

### How to interpret

| Feature | Meaning |
|---------|---------|
| **Path length / tortuosity** | Overall dynamic activity; longer, more tangled paths suggest greater postural activity |
| **Ellipse size** | Overall sway magnitude; larger ellipse = more displacement |
| **Ellipse orientation** | Dominant direction of sway (e.g. more ML than AP) |
| **Start vs end markers** | Where the processed trace begins and ends; need not coincide — drift during the trial is normal |
| **Origin (0, 0)** | Average stance during the session — **not** the board centre |

**Do not** expect this plot to match the live canvas pixel-for-pixel. A patient can stand on the global crosshairs on average and still show a characteristic sway pattern spread around the origin here.

### Literature justification

The stabilogram scatter plot overlaid with a confidence ellipse is arguably the most widely reproduced posturographic figure in the literature. Prieto et al. (1996) formally defined ellipse area as the primary measure of overall sway magnitude and popularised the 95% chi-squared ellipse.

**Key references:**

- Prieto, T. E., Myklebust, J. B., Hoffmann, R. G., Lovett, E. G., & Myklebust, B. M. (1996). Measures of postural steadiness: differences between healthy young and elderly adults. *IEEE Transactions on Biomedical Engineering*, 43(9), 956–966.
- Winter, D. A., Patla, A. E., Prince, F., Ishac, M., & Gielo-Perczak, K. (1998). Stiffness control of balance in quiet standing. *Journal of Neurophysiology*, 80(3), 1211–1221.

---

## 2 · ML / AP Time Series

### What it shows

CoP displacement in each axis as a function of time — the classical **stabilogram** in the time domain.

### How it is derived

For each resampled, filtered sample at time $t$ (seconds from start):

- **Top panel:** $\text{ML}(t)$ in cm
- **Bottom panel:** $\text{AP}(t)$ in cm

Both channels are mean-centred. The horizontal dashed line at $y = 0$ is the session average for that axis.

### How to interpret

| Pattern | Possible reading |
|---------|-----------------|
| Small, irregular oscillations around zero | Typical quiet standing |
| Slow drift away from and back to zero | Weight shift, fatigue, attention changes |
| Large isolated spikes | Brief perturbation or correction |
| One channel much larger than the other | Directional bias in control strategy (ML vs AP) |
| Signal centred on **y = 0** | Confirms mean centring; spatial plots should be centred on average |

Amplitude here is **relative to average stance**, not absolute board position. For absolute offset, see **Mean position — ML/AP** in the feature table.

### Literature justification

The time-domain stabilogram is the foundational representation of postural sway. Collins & De Luca (1993) established the framework of analysing ML and AP channels independently.

**Key references:**

- Collins, J. J., & De Luca, C. J. (1993). Open-loop and closed-loop control of posture: a random-walk analysis of center-of-pressure trajectories. *Experimental Brain Research*, 95(2), 308–318.
- Shumway-Cook, A., & Woollacott, M. H. (2007). *Motor Control: Translating Research into Clinical Practice* (3rd ed.). Lippincott Williams & Wilkins.

---

## 3 · CoP Velocity Time Series

### What it shows

How fast the CoP is moving in each direction over time — the **speed of postural corrections**.

### How it is derived

Velocity is obtained by differentiating the position stabilogram (Savitzky–Golay method), giving:

$$
v_{ML}(t) = \frac{d\,\text{CoP}_{ML}}{dt}, \qquad v_{AP}(t) = \frac{d\,\text{CoP}_{AP}}{dt}
$$

Units: cm/s. Positive velocity means movement in the positive axis direction (right for ML, forward for AP).

### How to interpret

| Feature | Meaning |
|---------|---------|
| **Higher velocity** | Faster, more active postural adjustments |
| **Bursts of velocity** | Corrective movements in response to sway |
| **Sustained high velocity** | Greater overall postural activity than quiet standing |
| **ML vs AP velocity** | Which direction drives more corrective action |

Velocity is partially independent of displacement magnitude: a patient with small sway amplitude but rapid corrections can show high velocity. Mean velocity values are in the feature table.

### Literature justification

Instantaneous velocity discriminates between populations where displacement-based measures fail and is among the more reproducible force-platform measures (Rocchi et al. 2002).

**Key references:**

- Rocchi, L., Chiari, L., & Horak, F. B. (2002). Effects of deep brain stimulation and levodopa on postural sway in Parkinson's disease. *Journal of Neurosurgery & Psychiatry*, 73(3), 267–274.
- Chiari, L., Rocchi, L., & Cappello, A. (2002). Stabilometric parameters are affected by anthropometry and foot placement. *Clinical Biomechanics*, 17(9–10), 666–677.

---

## 4 · Power Spectral Density (PSD)

### What it shows

How sway **energy** is distributed across frequencies — which rhythmic components dominate postural control.

### How it is derived

The Welch method estimates the power spectral density of the ML and AP stabilograms:

$$
\text{PSD}(f) \quad [\text{cm}^2 / \text{Hz}]
$$

The plot displays 0–5 Hz. Shaded bands mark:

| Band | Clinical context |
|------|------------------|
| **0–1 Hz** (green) | Normal quiet-standing sway |
| **1–3 Hz** (red) | Elevated concern; more active or pathological control |

When available, dashed vertical lines mark the **95% power frequency** ($f_{95}$) — the frequency below which 95% of total spectral power lies.

### How to interpret

| Pattern | Possible reading |
|---------|-----------------|
| Most power below 1 Hz | Typical healthy quiet standing |
| Increased 1–3 Hz energy | Faster, less smooth control — age, pathology, or anxiety |
| AP vs ML differences | Axis-specific control strategies |
| Higher overall PSD | Greater sway energy (related to, but not identical to, ellipse area) |

PSD describes **oscillatory content** of mean-centred sway, not absolute position.

### Literature justification

Frequency-domain analysis reveals the control bandwidth of the postural system. Diener et al. (1984) established that healthy quiet standing is dominated by sway below 1 Hz.

**Key references:**

- Diener, H. C., Dichgans, J., Bacher, M., & Gompf, B. (1984). Quantification of postural sway in normals and patients with cerebellar diseases. *Electroencephalography and Clinical Neurophysiology*, 57(2), 134–142.
- Maki, B. E., Holliday, P. J., & Fernie, G. R. (1990). Aging and postural control. *Journal of the American Geriatrics Society*, 38(1), 1–9.
- Donker, S. F., Ledebt, A., Roerdink, M., Savelsbergh, G. J., & Beek, P. J. (2008). Children with cerebral palsy exhibit greater and more regular postural sway than typically developing children. *Experimental Brain Research*, 184(3), 363–370.

---

## 5 · Diffusion Plot (log–log MSD)

### What it shows

How far the CoP wanders over increasing time intervals — a **random-walk** characterisation of postural control (Stabilogram Diffusion Analysis, SDA).

### How it is derived

For each time lag $\Delta t$, the **mean square displacement** (MSD) is computed:

$$
\text{MSD}(\Delta t) = \left\langle \left[\text{CoP}(t + \Delta t) - \text{CoP}(t)\right]^2 \right\rangle
$$

Both axes use logarithmic scales. Separate curves are shown for ML and AP. Dashed vertical lines mark the **critical time** $t^*$ when the slope changes — the transition between short-term (more persistent) and long-term (more constrained) behaviour.

### How to interpret

| Region | Meaning |
|--------|---------|
| **Short lags (left)** | Immediate sway behaviour; steeper slope ≈ more persistent (less damped) motion |
| **Long lags (right)** | Sway constrained by feedback; shallower or declining slope ≈ closed-loop control |
| **Critical time $t^*$** | Estimated crossover between open-loop and closed-loop regimes |
| **Higher MSD overall** | Greater displacement over time — less stable control |

This plot describes **stochastic dynamics** of sway, not where the patient stood on the board.

### Literature justification

Collins & De Luca (1993, 1994) showed MSD follows a power law with a characteristic crossover; Collins et al. (1995) demonstrated disturbance of this crossover in neurological conditions.

**Key references:**

- Collins, J. J., & De Luca, C. J. (1993). Open-loop and closed-loop control of posture: a random-walk analysis. *Experimental Brain Research*, 95(2), 308–318.
- Collins, J. J., & De Luca, C. J. (1994). Random walking during quiet standing. *Physical Review Letters*, 73(5), 764–767.
- Collins, J. J., De Luca, C. J., Burrows, A., & Lipsitz, L. A. (1995). Age-related changes in open-loop and closed-loop postural control mechanisms. *Experimental Brain Research*, 104(3), 480–492.

---

## 6 · CoP Spatial Density (2D Histogram Contour)

### What it shows

Where the CoP **spent the most time** during the test — a spatial map of stance preference, independent of the order in which positions were visited.

### How it is derived

1. The ML–AP plane is divided into bins.
2. Each mean-centred sample increments the bin count for its $(\text{ML}, \text{AP})$ location.
3. Contour lines connect regions of equal **sample density** (darker blue = more time spent).
4. The full sway path is overlaid faintly for context.

The dashed crosshairs mark $(0, 0)$ — the session average stance.

### How to interpret

| Feature | Meaning |
|---------|---------|
| **Tight, centred contours** | Consistent stance; low spatial variability |
| **Offset densest region from origin** | Asymmetric sway distribution — more time spent on one side of average (can occur even when mean is at origin) |
| **Multiple peaks** | Distinct preferred loading zones (e.g. weight shifting between two positions) |
| **Elongated contours** | Directional preference in where time is spent |

Like the sway path, this uses mean-centred coordinates. A dense region away from the crosshairs means the patient spent more time on one side of their **average** position, not necessarily away from the board centre.

### Literature justification

Spatial density complements the sway path by revealing preferred loading zones. Baratto et al. (2002) introduced sway density analysis in the clinical context.

**Key references:**

- Baratto, L., Morasso, P. G., Re, C., & Spada, G. (2002). A new look at posturographic analysis in the clinical context. *Motor Control*, 6(3), 246–270.
- Morasso, P. G., & Schieppati, M. (1999). Can muscle stiffness alone stabilize upright standing? *Journal of Neurophysiology*, 82(3), 1622–1626.

---

## 7 · Feature Summary Table

### What it shows

A structured list of numerical descriptors computed from the processed stabilogram, grouped by domain (positional, dynamic, frequency, diffusion, etc.).

### How it is derived

Each value is a standard posturographic feature from the `code_descriptors_postural_control` library, computed on the same mean-centred, resampled, filtered stabilogram used for the plots.

### How to interpret — key fields for canvas comparison

| Feature | Meaning | Relation to live canvas |
|---------|---------|------------------------|
| **Mean position — ML / AP** | Average absolute CoP during the session (cm), **before** mean centring | Closest report equivalent to “where did they stand relative to board centre?” Small non-zero values (e.g. 0.2–0.5 cm) can occur even when the cursor appeared on the crosshairs |
| **RMS, range, ellipse area** | Magnitude of sway **variability** | No direct canvas equivalent |
| **Mean velocity** | Average speed of CoP movement | Related to how actively the cursor moved |
| **Frequency / diffusion features** | Spectral and stochastic properties | No canvas equivalent |

Most table values describe **variability**, not absolute stance. For “was the patient centred on the board?”, use **Mean position — ML/AP**.

### Literature justification

Leach et al. (2014) validated ellipse area, path length, RMS, and velocity as the most reliable Wii Balance Board features at the session-to-session level.

**Key references:**

- Leach, J. M., Mancini, M., Peterka, R. J., Hayes, T. L., & Horak, F. B. (2014). Validating and calibrating the Nintendo Wii balance board to derive reliable center of pressure measures. *Sensors*, 14(10), 18244–18267.

---

## General background

For a comprehensive review of force-platform posturography methodology — signal processing, feature selection, test–retest reliability, and clinical validity — see:

- Ruhe, A., Fejer, R., & Walker, B. (2010). The test–retest reliability of centre of pressure measures in bipedal static task conditions. *Gait & Posture*, 32(4), 436–445.
- Chiari, L., Della Croce, U., Leardini, A., & Cappozzo, A. (2005). Human movement analysis using stereophotogrammetry. Part 2: Instrumental errors. *Gait & Posture*, 21(2), 197–211.
- Doyle, R. J., Ragan, B. G., Rajaram, G., Rosengren, K. S., & Hsiao-Wecksler, E. T. (2007). Generalizability of stabilogram diffusion analysis of center of pressure measures. *Gait & Posture*, 25(3), 381–386.

---

## Document history

| Change | Notes |
|--------|-------|
| 2025-01 | Initial literature references |
| 2026-07 | Added interpretation guide, shared pipeline, canvas vs report reference-frame section |
