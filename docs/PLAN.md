# ExoHunter — Roadmap

Each phase lists what to build, what you'll learn, and how you know it's done.
Checkboxes are meant to become GitHub issues / milestones.

## Phase 0 — Foundations (1–2 weeks)
**Learn:** what a light curve is, BTJD time, PDCSAP vs SAP flux, how a transit looks, ADQL.
- [ ] Work through the lightkurve tutorials (search, download, flatten, fold)
- [ ] Recover a known planet by hand in a notebook (`notebooks/01_rediscover_a_planet.py`)
- [ ] Run one ADQL query against the Exoplanet Archive TOI table
- [ ] Read: Kovács+2002 (BLS), Hippke & Heller 2019 (TLS) — skim is fine

## Phase 1 — MVP pipeline ✅ scaffolded (v0.1)
**Learn:** detrending, periodograms, SNR/SDE, packaging, testing.
- [x] MAST adapter (single star, sector target list)
- [x] Detrend, clip, bin
- [x] BLS search
- [x] Vetting: odd/even, secondary eclipse, TESS-orbit, SNR/SDE
- [x] TOI cross-match with harmonics
- [x] DuckDB/Parquet storage, CLI, Streamlit dashboard
- [x] Offline tests with injected transits, CI
- [ ] Batch-run one full sector (≈ 20k stars) and record runtime
- [ ] Measure recall on known planets → tune thresholds (acceptance criteria in SPEC §8)

## Phase 2 — Better vetting & ranking (≈ 4 weeks)
**Learn:** false-positive astrophysics, injection–recovery testing.
- [ ] Injection–recovery: inject fake planets into real light curves, map completeness vs depth/period
- [ ] Transit Least Squares as a second search method
- [ ] Multi-planet search: mask the best signal, search again (up to 3 signals per star)
- [ ] Transit-shape tests (V vs U shape), duration vs stellar density (TIC radius/mass)
- [ ] Contamination check: nearby bright stars from Gaia within 21″ (one TESS pixel)
- [ ] Human labels in the dashboard (`real?/EB/systematic/unsure`), stored in DuckDB
- [ ] Ranking score combining tests

## Phase 3 — Scale & more data (6–8 weeks)
**Learn:** cloud data access, parallel processing, big-data plotting.
- [ ] Read FITS straight from the free AWS bucket (`s3://stpubdata/tess`) instead of HTTP
- [ ] Full-frame-image light curves (QLP / TESS-SPOC HLSPs) — ~10× more stars
- [ ] Multi-sector stitching per star
- [ ] Kepler/K2 adapter (same pipeline, different source)
- [ ] Workflow orchestrator (Prefect) with retries and resumable runs
- [ ] Datashader/HoloViews views for sector-wide plots
- [ ] General anomaly detection: feature extraction + Isolation Forest (find Boyajian-star-like oddities)

## Phase 4 — New science cases (6–8 weeks)
**Learn:** astrometry, high-energy astrophysics, cross-mission matching.
- [ ] Gaia adapter (ESA TAP): DR3 now, **DR4 epoch astrometry when released** (planned ~Dec 2026)
- [ ] Dark-companion search: large RUWE / orbital solutions with high mass function, normal-looking star
- [ ] Fermi-LAT unassociated sources → pulsar-likeness ranking (curvature, variability)
- [ ] Sky view with Aladin Lite; HEALPix-indexed positional cross-match
- [ ] Plug-in interface: each science case = adapter + detector + vetter + view

## Phase 5 — Share & collaborate (ongoing)
- [ ] Export candidates in ExoFOP CTOI format; variable stars to AAVSO VSX
- [ ] Public read-only dashboard (Streamlit Community Cloud or a small VM)
- [ ] Write up one result as a notebook/blog post
- [ ] Optional: FastAPI + React frontend if Streamlit becomes limiting

## Risks to keep in mind
1. **False positives dominate.** Expect > 95 % of raw detections to be noise, binaries or systematics.
2. **"New" is hard.** Always cross-match; check ExoFOP and the literature before believing anything.
3. **Data volume.** Don't scale until vetting is good; 1 sector first.
4. **Real discoveries need follow-up.** Plan to hand candidates to professionals (ExoFOP / TFOP).
