"""Command-line interface: `exohunter --help`."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import typer

from .config import get_settings
from .crossmatch import fetch_toi_table
from .storage import Store

app = typer.Typer(help="Hunt for transit signals in public NASA TESS data.", no_args_is_help=True)

DataDir = typer.Option(None, "--data-dir", envvar="EXOHUNTER_DATA", help="Where data is stored.")


def _save(store: Store, result) -> None:
    store.save_result(result.row)
    tic = result.row["tic_id"]
    store.save_series(tic, "lc", result.lightcurve)
    store.save_series(tic, "bls", result.periodogram)


def _line(row: dict) -> str:
    return (
        f"TIC {row['tic_id']:>11}  P={row['period']:8.4f} d  depth={row['depth'] * 1e6:8.0f} ppm  "
        f"SDE={row['sde']:5.1f}  {row['status']:<18} {row['match_label']}"
        + (f" (TOI {row['toi']})" if row["toi"] else "")
    )


@app.command()
def analyze(
    tic_id: int = typer.Argument(..., help="TESS Input Catalog ID, e.g. 25155310"),
    sector: list[int] = typer.Option(None, "--sector", "-s", help="Sector(s); default latest."),
    data_dir: Path = DataDir,
) -> None:
    """Fetch, search and vet a single star."""
    from .pipeline import analyze_target

    settings = get_settings(data_dir)
    toi = fetch_toi_table(settings.catalog_dir)
    result = analyze_target(tic_id, settings, sector or None, toi)
    _save(Store(settings), result)
    typer.echo(_line(result.row))
    if result.row["flags"]:
        typer.echo(f"  flags: {result.row['flags']}")


def _worker(tic_id: int, data_dir: str, sector: int, toi):
    from .pipeline import analyze_target

    return analyze_target(tic_id, get_settings(data_dir), [sector], toi)


@app.command()
def sector(
    sector: int = typer.Argument(..., help="TESS sector number"),
    limit: int = typer.Option(25, help="Max number of stars to process."),
    workers: int = typer.Option(4, help="Parallel processes."),
    data_dir: Path = DataDir,
) -> None:
    """Batch-process stars observed at 2-min cadence in one sector."""
    from .sources.tess import targets_in_sector

    settings = get_settings(data_dir)
    store = Store(settings)
    toi = fetch_toi_table(settings.catalog_dir)
    tics = targets_in_sector(sector, limit)
    typer.echo(f"Sector {sector}: processing {len(tics)} stars with {workers} workers")
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_worker, t, str(settings.data_dir), sector, toi): t for t in tics
        }
        for fut in as_completed(futures):
            try:
                result = fut.result()
            except Exception as exc:  # one bad star must not stop the batch
                typer.echo(f"TIC {futures[fut]:>11}  ERROR {type(exc).__name__}: {exc}", err=True)
                continue
            _save(store, result)
            typer.echo(_line(result.row))


@app.command("list")
def list_results(
    status: list[str] = typer.Option(None, help="candidate | weak | likely_eb | ..."),
    label: list[str] = typer.Option(None, help="known_toi | no_known_match | ..."),
    min_sde: float = typer.Option(None),
    limit: int = typer.Option(50),
    data_dir: Path = DataDir,
) -> None:
    """Show stored results, strongest first."""
    df = Store(get_settings(data_dir)).results(status or None, label or None, min_sde)
    if df.empty:
        typer.echo("No results.")
        return
    for row in df.head(limit).to_dict("records"):
        typer.echo(_line(row))


@app.command()
def catalogs(force: bool = typer.Option(False, help="Re-download even if cached."),
             data_dir: Path = DataDir) -> None:
    """Download/refresh reference catalogs (TOI table)."""
    df = fetch_toi_table(get_settings(data_dir).catalog_dir, force=force)
    typer.echo(f"TOI table: {len(df)} rows")


@app.command("app")
def run_app(data_dir: Path = DataDir) -> None:
    """Open the Streamlit dashboard."""
    script = Path(__file__).with_name("dashboard.py")
    env_args = ["--", "--data-dir", str(data_dir)] if data_dir else []
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(script), *env_args], check=False)


if __name__ == "__main__":
    app()
