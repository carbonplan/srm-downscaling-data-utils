#!/usr/bin/env python
"""Download a subset of the CarbonPlan SRM downscaling dataset.

A command-line counterpart to notebooks/subsetting-and-exporting.ipynb, for
when you want a file rather than an interactive session.

Examples
--------
Estimate the cost of a request without downloading anything::

    python scripts/download.py --scenario ssp245 --start 2050-01-01 \
        --end 2059-12-31 --bbox 68 6 98 38 --dry-run

Download a single-point time series::

    python scripts/download.py --scenario historical --variable tas \
        --point 28.6 77.2 --start 1990-01-01 --end 1999-12-31 \
        --output delhi.nc
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from srm_access import (  # noqa: E402
    SCENARIOS,
    STORE_BRANCH,
    VARIABLES,
    coverage,
    describe_request,
    ensemble_member,
    load_downscaling_store,
)

# A request reading more than this prompts for confirmation. The store is
# space-fragmented, so global requests reach tens of GB very easily.
PROMPT_ABOVE_GB = 5.0


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="download.py",
        description="Download a spatial/temporal subset of the SRM downscaling dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples")[-1],
    )
    p.add_argument("--scenario", required=True, choices=SCENARIOS)
    p.add_argument("--variable", default="tas", choices=VARIABLES)
    p.add_argument("--start", help="ISO start date, e.g. 2050-01-01")
    p.add_argument("--end", help="ISO end date, e.g. 2059-12-31")

    region = p.add_mutually_exclusive_group()
    region.add_argument(
        "--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX")
    )
    region.add_argument("--point", nargs=2, type=float, metavar=("LAT", "LON"))

    p.add_argument("--output", type=Path, help="output path (default derived from selection)")
    p.add_argument("--format", default="netcdf", choices=["netcdf", "zarr"])
    p.add_argument("--dry-run", action="store_true", help="report cost, download nothing")
    p.add_argument("--yes", "-y", action="store_true", help="skip the confirmation prompt")
    return p.parse_args(argv)


def validate_dates(args, first: str, last: str) -> None:
    """Fail loudly on out-of-range dates instead of writing an empty file."""
    for name, value in (("--start", args.start), ("--end", args.end)):
        if value is None:
            continue
        try:
            stamp = pd.Timestamp(value)
        except ValueError:
            raise SystemExit(f"error: {name} {value!r} is not a valid date")
        if not (pd.Timestamp(first) <= stamp <= pd.Timestamp(last)):
            raise SystemExit(
                f"error: {name} {value} is outside {args.scenario}/{args.variable} "
                f"coverage ({first} to {last}). Selecting outside it yields no data."
            )
    if args.start and args.end and pd.Timestamp(args.start) > pd.Timestamp(args.end):
        raise SystemExit("error: --start is after --end")


def _human(nbytes: int) -> str:
    """Format a byte count without collapsing small files to '0.0 MB'."""
    for unit, scale in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if nbytes >= scale:
            return f"{nbytes / scale:.1f} {unit}"
    return f"{nbytes} B"


def default_output(args) -> Path:
    bits = [args.scenario, args.variable]
    if args.point:
        bits.append(f"pt{args.point[0]:g}_{args.point[1]:g}")
    elif args.bbox:
        bits.append("bbox")
    if args.start:
        bits.append(args.start[:4])
    if args.end:
        bits.append(args.end[:4])
    suffix = ".zarr" if args.format == "zarr" else ".nc"
    return Path("_".join(bits) + suffix)


def main(argv=None) -> int:
    args = parse_args(argv)

    first, last = coverage(args.scenario, args.variable)
    validate_dates(args, first, last)

    member = ensemble_member(args.scenario, args.variable)
    print(f"{args.scenario}/{args.variable} -> member {member} (branch {STORE_BRANCH})")
    print(f"coverage: {first} to {last}")

    ds = load_downscaling_store(args.scenario, args.variable)
    da = ds[args.variable]

    if args.start or args.end:
        da = da.sel(time=slice(args.start, args.end))
    if args.point:
        lat, lon = args.point
        da = da.sel(lat=lat, lon=lon, method="nearest")
    elif args.bbox:
        lon_min, lat_min, lon_max, lat_max = args.bbox
        da = da.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    if da.size == 0:
        raise SystemExit("error: selection is empty; check the dates and region")

    read_bytes = describe_request(da, "requested subset")

    if args.dry_run:
        print("\ndry run - nothing downloaded")
        return 0

    read_gb = read_bytes / 1e9
    if read_gb > PROMPT_ABOVE_GB and not args.yes:
        if not sys.stdin.isatty():
            raise SystemExit(
                f"error: this reads {read_gb:.1f} GB, above the {PROMPT_ABOVE_GB:g} GB "
                "threshold, and stdin is not a terminal. Re-run with --yes to proceed."
            )
        reply = input(f"\nThis will read {read_gb:.1f} GB. Continue? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted")
            return 1

    out = args.output or default_output(args)
    print(f"\nwriting {out} ...")

    out_ds = da.to_dataset(name=args.variable)
    # Drop encoding inherited from the source store. It still describes the
    # full 3-D grid -- chunks (8000, 8, 16) and shards (16000, 72, 144) -- so
    # writing a reduced selection with it raises an arity error in zarr.
    for name in out_ds.variables:
        out_ds[name].encoding = {}

    if args.format == "zarr":
        out_ds.to_zarr(out, mode="w")
    else:
        out_ds.to_netcdf(out)

    size = sum(f.stat().st_size for f in out.rglob("*")) if out.is_dir() else out.stat().st_size
    print(f"wrote {out} ({_human(size)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
