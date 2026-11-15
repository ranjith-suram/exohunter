# %% [markdown]
# # 01 — Rediscover a known planet, step by step
# Open in Jupyter/VS Code (percent-format script; `pip install jupytext` to convert).
# Target: WASP-126 b (TIC 25155310, TOI-114.01), period ≈ 3.289 days.

# %%
import lightkurve as lk
import numpy as np
from astropy.timeseries import BoxLeastSquares

# %% [markdown]
# ## 1. Find and download the light curve from MAST

# %%
search = lk.search_lightcurve("TIC 25155310", mission="TESS", author="SPOC", exptime=120)
print(search)
lc = search[0].download().remove_nans().normalize()
lc.plot()

# %% [markdown]
# ## 2. Remove slow trends (stellar variability, spacecraft systematics)

# %%
flat = lc.flatten(window_length=721)  # 721 cadences x 2 min ≈ 1 day
flat.plot()

# %% [markdown]
# ## 3. Search for periodic box-shaped dips

# %%
t, f = flat.time.value, np.asarray(flat.flux.value, float)
bls = BoxLeastSquares(t, f)
periods = np.linspace(0.5, 13, 20000)
res = bls.power(periods, 0.1)
best = np.argmax(res.power)
P, t0 = res.period[best], res.transit_time[best]
print(f"Best period: {P:.4f} d   depth: {res.depth[best] * 1e6:.0f} ppm")

# %% [markdown]
# ## 4. Fold on the period and look at the transit

# %%
flat.fold(period=P, epoch_time=t0).scatter()

# %% [markdown]
# ## Exercises
# 1. Try a TOI with a smaller planet — does BLS still find it?
# 2. Change `window_length` to 101. What happens to the transit depth? Why?
# 3. Compare with `exohunter analyze 25155310 -s 1` and the dashboard.
