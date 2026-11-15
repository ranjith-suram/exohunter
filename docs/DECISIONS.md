# Architecture Decision Records

Short records of *why* things are the way they are. Add a new entry rather than
editing an old one when a decision changes.

---

## ADR-001 — Python, not Rust (for now)

**Status:** accepted · **Date:** 2026-11

**Context.** This is a learning project in astronomy data analysis. The bottleneck
is understanding the science and the data, not raw CPU speed.

**Decision.** Use Python 3.11+.

| | Python | Rust |
|---|---|---|
| Astronomy libraries | astropy, astroquery, lightkurve, pyvo, TLS, wotan, Gaia/MAST clients — the whole field uses them | Very few; FITS I/O and TAP clients would need writing from scratch |
| Tutorials / papers / notebooks | Nearly all examples are Python | Almost none |
| Interactive exploration | Jupyter, Streamlit | Weak |
| Speed | Hot loops already in C/NumPy (BLS is compiled in astropy) | Excellent |
| Learning value | Learn astronomy + data science | Learn Rust (a different project) |

**Consequences.** If profiling later shows a real hot spot (e.g. a custom search
over millions of light curves), write *that function* in Rust as a Python
extension with [PyO3](https://pyo3.rs) + [maturin](https://www.maturin.rs). Rust as
an accelerator, Python as the glue — this is how Polars, Ruff and pydantic-core work.

---

## ADR-002 — Visualization: Plotly + Streamlit (MVP), Bokeh/Datashader + Aladin Lite later

**Status:** accepted

| Need | Tool | When |
|---|---|---|
| Quick plots in notebooks | matplotlib (lightkurve's `.plot()` uses it) | Phase 0 |
| Interactive charts (zoom, hover) | **Plotly** (`scattergl` handles ~100k points) | MVP |
| Dashboard / candidate review UI | **Streamlit** — pure Python, no frontend skills needed | MVP |
| Millions of points (full sectors, all-sky) | HoloViews + **Datashader**, or Bokeh | Phase 3 |
| Sky maps / images around a target | **Aladin Lite** (embed), `astropy.visualization`, `healpy` | Phase 4 |
| Polished multi-user web app | FastAPI + React + Plotly.js | Phase 5, only if needed |

---

## ADR-003 — Storage: DuckDB + Parquet

**Status:** accepted

Single-file, serverless, fast analytical SQL, reads Parquet natively, zero ops.
Connections are opened per call so the CLI and dashboard can share the file.
Revisit (Postgres + `q3c`) if we need concurrent writers or positional
cross-matching across millions of rows.

---

## ADR-004 — First science case: TESS 2-minute SPOC light curves + BLS

**Status:** accepted

Pre-cleaned (PDCSAP) light curves, a well-understood algorithm, a ground-truth
catalogue (TOIs) for measuring recall, and a real submission path (ExoFOP CTOIs).
Upgrade path: Transit Least Squares (more sensitive to small planets), full-frame
image light curves (QLP / TESS-SPOC HLSPs, ~1M more stars), multi-planet search by
masking and re-searching.
