# Vendored: code_descriptors_postural_control

This directory contains a vendored copy of
[`Jythen/code_descriptors_postural_control`](https://github.com/Jythen/code_descriptors_postural_control),
a Python library for computing posturographic descriptors (stabilogram features) from
Centre of Pressure data.

## Attribution

**Original author:** Jythen
**Upstream repository:** https://github.com/Jythen/code_descriptors_postural_control
**Upstream commit pinned:** `c66a0e4` ("correct filtering option")
**License:** MIT — see [LICENSE](LICENSE)

The original `LICENSE` file is preserved unchanged, as required by the MIT license terms.

## Why vendored

The library is not published on PyPI and has no `pyproject.toml`, so it cannot be
installed as a normal package dependency. Vendoring also pins the exact revision used
and allows the local patches below to be tracked in version control.

## Local patches

All changes from the upstream pinned commit are described here.

### 1. `stabilogram/stato.py` — fix `from_array` with 3-column input

**File:** `stabilogram/stato.py`
**Problem:** When `from_array` was called with a `(N, 3)` array (time, ML, AP), the
`else` branch reshaped `time` to `(N, 1)` via `time = time[:,None]` and then attempted
to assign it back into `signal[:,0]` (shape `(N,)`), raising:

```
ValueError: could not broadcast input array from shape (2436,1) into shape (2436,)
```

The `[:,None]` reshape was only needed in the `if n_columns == 2` branch for
`np.concatenate`. In the `else` branch it is not needed.

**Fix:** Removed the `time = time[:,None]` line in the `else` branch.

### 2. `stabilogram/stato.py` — fix `mean_value` shape in `else` branch

**File:** `stabilogram/stato.py`
**Problem:** In the same `else` branch, `self.mean_value` was assigned the result of
`np.mean(..., keepdims=True)`, giving shape `(1, 2)`. The `if n_columns == 2` branch
correctly stores `mean[0]` (shape `(2,)`). Downstream code in
`descriptors/positional.py` indexes `signal.mean_value[0]` and `signal.mean_value[1]`,
which raised:

```
IndexError: index 1 is out of bounds for axis 0 with size 1
```

**Fix:** Changed `self.mean_value = mean` to `self.mean_value = mean[0]` to match the
shape expected by the rest of the library.

### 3. `descriptors/stochastic.py` — replace statsmodels OLS with NumPy

**File:** `descriptors/stochastic.py`
**Problem:** `statsmodels` is a heavy dependency (slow import, poor Nuitka compile time)
used only for ordinary least-squares fits in the SDA (Stabilogram Diffusion Analysis)
descriptor.

**Fix:** Added `_ols_fit()` using `numpy.linalg.lstsq` with the same design matrix
(`sm.add_constant` equivalent). Numerical output is unchanged (verified against a
golden-features fixture).

### 4. `descriptors/positional.py` — replace sklearn PCA with NumPy

**File:** `descriptors/positional.py`
**Problem:** `sklearn` is only used for `PCA(n_components=2)` in
`principal_sway_direction`.

**Fix:** Replaced with `numpy.linalg.eigh` on the 2×2 covariance matrix. The feature
uses `np.abs` on the direction component, so eigenvector sign is immaterial.

### 5. `stabilogram/swarii.py` — replace scipy.interpolate with NumPy

**File:** `stabilogram/swarii.py`
**Problem:** `scipy.interpolate.interp1d` is only used for linear gap-filling after
SWARII resampling when empty windows occur.

**Fix:** Replaced with column-wise `numpy.interp` (WIIBBLE always uses linear
interpolation). Reduces scipy surface area to `scipy.signal` and `scipy.stats` only.
