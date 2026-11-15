"""Streamlit dashboard. Run with `exohunter app` or `streamlit run src/exohunter/dashboard.py`."""

from __future__ import annotations

import argparse

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from exohunter.config import get_settings
from exohunter.search import phase_fold
from exohunter.storage import Store

parser = argparse.ArgumentParser()
parser.add_argument("--data-dir", default=None)
args, _ = parser.parse_known_args()

st.set_page_config(page_title="ExoHunter", page_icon="🔭", layout="wide")
st.title("🔭 ExoHunter")

store = Store(get_settings(args.data_dir))
df = store.results()
if df.empty:
    st.info("No results yet. Try: `exohunter analyze 25155310` or `exohunter sector 1 --limit 20`.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    statuses = st.multiselect("Status", sorted(df.status.unique()), default=None)
    labels = st.multiselect("Catalog match", sorted(df.match_label.unique()), default=None)
    min_sde = st.slider("Minimum SDE", 0.0, float(max(df.sde.max(), 10)), 0.0, 0.5)

view = df[df.sde >= min_sde]
if statuses:
    view = view[view.status.isin(statuses)]
if labels:
    view = view[view.match_label.isin(labels)]

st.subheader(f"Results ({len(view)} of {len(df)})")
st.dataframe(
    view.assign(depth_ppm=(view.depth * 1e6).round(0))[
        ["tic_id", "status", "match_label", "toi", "period", "depth_ppm", "sde", "depth_snr",
         "n_transits", "odd_even_sigma", "secondary_sigma", "flags", "sectors"]
    ],
    hide_index=True,
    use_container_width=True,
)
if view.empty:
    st.stop()

tic = st.selectbox("Inspect target", view.tic_id.tolist(), format_func=lambda t: f"TIC {t}")
row = view[view.tic_id == tic].iloc[0]

c = st.columns(5)
c[0].metric("Period", f"{row.period:.4f} d")
c[1].metric("Depth", f"{row.depth * 1e6:.0f} ppm")
c[2].metric("Duration", f"{row.duration * 24:.2f} h")
c[3].metric("SDE", f"{row.sde:.1f}")
c[4].metric("SNR", f"{row.depth_snr:.1f}")
st.caption(
    f"Status **{row.status}** · match **{row.match_label}**"
    + (f" · TOI {row.toi} ({row.toi_disposition})" if row.toi else "")
    + (f" · flags: {row['flags']}" if row["flags"] else "")
    + f" · [ExoFOP](https://exofop.ipac.caltech.edu/tess/target.php?id={tic})"
)

lc = store.load_series(tic, "lc")
pg = store.load_series(tic, "bls")
if lc is None:
    st.warning("Light curve file missing; re-run the analysis.")
    st.stop()

PLOT = dict(height=320, margin=dict(l=10, r=10, t=40, b=10))

fig = go.Figure()
fig.add_scattergl(x=lc.time, y=lc.flux_raw, mode="markers", name="normalized",
                  marker=dict(size=3, opacity=0.35, color="#9aa0a6"))
fig.add_scattergl(x=lc.time, y=lc.flux, mode="markers", name="detrended",
                  marker=dict(size=3, color="#1f77b4"))
n0 = np.ceil((lc.time.min() - row.t0) / row.period)
for t in row.t0 + row.period * np.arange(n0, n0 + 200):
    if t > lc.time.max():
        break
    fig.add_vline(x=t, line=dict(width=1, dash="dot", color="gray"))
fig.update_layout(title="Light curve", xaxis_title="Time (BTJD days)", yaxis_title="Rel. flux",
                  **PLOT)
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
if pg is not None:
    f2 = go.Figure(go.Scatter(x=pg.period, y=pg.power, mode="lines", line=dict(width=1)))
    f2.add_vline(x=row.period, line=dict(color="red", dash="dash"))
    f2.update_layout(title="BLS periodogram", xaxis_title="Period (d)", xaxis_type="log",
                     yaxis_title="Power", **PLOT)
    left.plotly_chart(f2, use_container_width=True)


def fold_plot(center_t0: float, title: str) -> go.Figure:
    ph = phase_fold(lc.time.values, row.period, center_t0) * 24
    win = max(3 * row.duration * 24, 3)
    m = np.abs(ph) < win
    order = np.argsort(ph[m])
    x, y = ph[m][order], lc.flux.values[m][order]
    edges = np.linspace(-win, win, 61)
    idx = np.digitize(x, edges)
    bx = [x[idx == i].mean() for i in range(1, len(edges)) if np.any(idx == i)]
    by = [y[idx == i].mean() for i in range(1, len(edges)) if np.any(idx == i)]
    f = go.Figure()
    f.add_scattergl(x=x, y=y, mode="markers", name="data",
                    marker=dict(size=3, opacity=0.4, color="#9aa0a6"))
    f.add_scatter(x=bx, y=by, mode="lines+markers", name="binned",
                  marker=dict(size=5, color="#d62728"), line=dict(color="#d62728"))
    f.update_layout(title=title, xaxis_title="Hours from centre", yaxis_title="Rel. flux", **PLOT)
    return f


right.plotly_chart(fold_plot(row.t0, "Phase-folded transit"), use_container_width=True)
st.plotly_chart(fold_plot(row.t0 + row.period / 2, "Phase 0.5 (secondary eclipse check)"),
                use_container_width=True)
