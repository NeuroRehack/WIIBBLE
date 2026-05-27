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
