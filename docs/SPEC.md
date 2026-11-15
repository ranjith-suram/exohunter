# ExoHunter — MVP Specification

## 1. Purpose

A learning-oriented tool that downloads public NASA TESS light curves, searches them
for periodic transit-like dips, filters out common false positives, checks results
against known catalogues, and lets a human review candidates visually.

Success means: **it re-discovers known planets reliably, and surfaces a short,
reviewable list of signals that are *not* in the catalogues.**

## 2. Scope

### In scope (MVP, v0.1)
- TESS SPOC 2-minute-cadence light curves from MAST (one or more sectors per star).
- Single-star and whole-sector batch processing.
- Detrending, Box Least Squares search, basic automated vetting.
- Cross-match against the NASA Exoplanet Archive TOI table.
- DuckDB/Parquet storage; CLI; Streamlit dashboard.

### Out of scope (for now)
- Full-frame-image light curves, Kepler/K2, Gaia, Fermi, X-ray missions (see PLAN.md).
- Pixel-level vetting (centroid shifts, difference images).
- Machine-learning classifiers.
- Multi-user accounts, hosting.

## 3. Users & stories

| As a… | I want to… | so that… |
|---|---|---|
| learner | analyse one star by TIC ID and see its plots | I understand each pipeline step |
| hunter | batch-process a sector overnight | I get a ranked list of signals |
| reviewer | filter to "candidate + no_known_match" and inspect plots | I spend time only on plausible new signals |
| maintainer | run tests offline | CI is fast and deterministic |

## 4. Data sources

| Source | Data | Access |
|---|---|---|
| MAST (STScI) | TESS SPOC light-curve FITS (PDCSAP flux) | `lightkurve.search_lightcurve` / `astroquery.mast` |
| NASA Exoplanet Archive | TOI table (`toi`): TIC, period, depth, disposition | TAP `https://exoplanetarchive.ipac.caltech.edu/TAP/sync` |
| ExoFOP-TESS | Per-target follow-up pages (linked, not queried) | web link |

No scraping: only documented APIs. Respect archive rate limits; cache everything.

## 5. Pipeline

```
fetch (MAST) ─▶ normalize + stitch ─▶ flatten (Savitzky–Golay, ~1 d window)
   ─▶ clip bright outliers (flares; never dips) ─▶ bin to 10 min
   ─▶ BLS search ─▶ vet ─▶ cross-match TOIs ─▶ store ─▶ dashboard
```

### 5.1 Search (BLS)
- Period range: 0.5 d to baseline/2 (≥ 2 transits). Grid from `autoperiod`, capped at 200k points.
- Trial durations: 1.0, 1.4, 1.9, 2.9, 3.8, 6.0 h.
- Outputs: period, t0, duration, depth ± err, depth SNR, SDE, number of transits,
  odd/even depths.

### 5.2 Vetting rules (initial thresholds, tune later)

| Test | Flag | Effect on status |
|---|---|---|
| SDE < 7 | `low_sde` | → `weak` |
| depth SNR < 7 | `low_snr` | → `weak` |
| fewer than 2 transits with data | `too_few_transits` | → `weak` |
| odd vs even depth differ > 3σ **and** > 15 % | `odd_even_mismatch` | → `likely_eb` |
| dip at phase 0.5 > 3σ | `secondary_eclipse` | → `likely_eb` |
| period ≈ 13.7 d or 6.85 d (TESS orbit) | `near_tess_orbit` | → `suspect_systematic` |
| depth > 3 % | `deep_transit` | flag only |

Status priority: `weak` > `likely_eb` > `suspect_systematic` > `candidate`.

### 5.3 Cross-match labels
- `known_toi` — same TIC and period within 1 % (incl. 2×, ½×, 3×, ⅓× harmonics).
- `new_signal_on_toi_star` — star is a TOI but the period does not match (possible extra planet!).
- `no_known_match` — star is not a TOI.

## 6. Data model

`results` table (DuckDB), one row per star (latest run wins):
`tic_id, sectors, analyzed_at, n_points, period, t0, duration, depth, depth_snr, sde,
n_transits, odd_even_sigma, secondary_sigma, status, flags, match_label, toi,
toi_disposition, known_period`.

Per star Parquet files in `data/lightcurves/`:
- `TIC<id>_lc.parquet` — `time, flux, flux_err, flux_raw` (binned)
- `TIC<id>_bls.parquet` — `period, power` (decimated periodogram)

## 7. Interfaces

CLI (`exohunter`): `analyze <tic> [-s N]`, `sector <N> --limit --workers`,
`list --status --label --min-sde`, `catalogs [--force]`, `app`.

Dashboard: filter sidebar · results table · light curve with predicted transits ·
periodogram · phase-folded transit · phase-0.5 view · ExoFOP link.

## 8. Acceptance criteria (MVP done when…)

1. `exohunter analyze 25155310 -s 1` recovers WASP-126 b (P ≈ 3.289 d) and labels it `known_toi`.
2. On a 200-star sector batch, ≥ 80 % of known planet TOIs (`KP`/`CP`, SNR-detectable) are recovered.
3. Fewer than 10 % of all processed stars end up as `candidate + no_known_match`.
4. Offline test suite passes in CI in < 2 min.
5. Dashboard shows every plot above for any stored star.

## 9. Non-functional
- Runs on a laptop (8 GB RAM); ~2 MB download per star-sector.
- Reproducible: pinned deps via `uv.lock`; all thresholds in code, not magic numbers in notebooks.
- Every external call cached; a failing star never aborts a batch.
