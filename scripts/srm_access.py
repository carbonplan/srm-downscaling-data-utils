"""Shared access helpers for the CarbonPlan SRM downscaling dataset.

This module is the canonical home for the details that change when the
dataset is republished: the store location, the pinned branch, and the
ensemble-member lookup. Keeping them in one place matters -- the notebook
in this repository once sat broken for a whole release because a dead
store path was hard-coded in a second location.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

__all__ = [
    "STORE",
    "STORE_BRANCH",
    "SCENARIOS",
    "VARIABLES",
    "coverage",
    "ensemble_member",
    "check_members",
    "load_downscaling_store",
    "describe_request",
]

STORE = {
    "bucket": "us-west-2.opendata.source.coop",
    "prefix": "carbonplan/srm-downscaling/output/production/CESM2-WACCM-ERA5-global.icechunk",
    "region": "us-west-2",
}

# There are zero tags on the store, so pinning a branch is the only way to
# get reproducible reads.
STORE_BRANCH = "v0.13.0"

VARIABLES = ["tas", "tasmax", "tasmin", "dtr", "pr", "rsds", "hurs"]
SCENARIOS = ["historical", "ssp245", "g6_1p5k"]

# tasmax/tasmin/dtr come from a separate "bridge" job and carry a different
# ensemble member than tas/pr/rsds/hurs within the same scenario.
_BRIDGE_VARS = {"tasmax", "tasmin", "dtr"}
_MEMBERS = {
    "historical": {"main": "r3i1p1f1", "bridge": "001"},
    "ssp245": {"main": "003", "bridge": "008"},
    "g6_1p5k": {"main": "003", "bridge": "003"},
}

# Coverage is not uniform: g6_1p5k starts late, and on ssp245 the bridge
# variables stop 30 years earlier than the rest. Selecting outside these
# ranges yields an empty result rather than an error, so validate first.
_COVERAGE = {
    "historical": {"main": ("1978-01-01", "2014-12-31"), "bridge": ("1978-01-01", "2014-12-31")},
    "ssp245": {"main": ("2015-01-01", "2099-12-31"), "bridge": ("2015-01-01", "2069-12-31")},
    "g6_1p5k": {"main": ("2035-01-01", "2084-12-31"), "bridge": ("2035-01-01", "2084-12-31")},
}


def _kind(variable: str) -> str:
    return "bridge" if variable in _BRIDGE_VARS else "main"


def ensemble_member(scenario: str, variable: str) -> str:
    """Report which ensemble member a (scenario, variable) pair resolves to."""
    return _MEMBERS[scenario][_kind(variable)]


def coverage(scenario: str, variable: str) -> tuple[str, str]:
    """Return the (first, last) date available for a scenario/variable pair."""
    return _COVERAGE[scenario][_kind(variable)]


def check_members(scenario: str, variables) -> dict:
    """Map each variable to its member, warning when a set spans the split."""
    members = {v: ensemble_member(scenario, v) for v in variables}
    if len(set(members.values())) > 1:
        print(f"WARNING: on '{scenario}' these variables span multiple ensemble members:")
        for v, m in members.items():
            print(f"    {v:8s} -> {m}")
        print("  Combining them mixes members, which is rarely intended.")
    return members


def load_downscaling_store(scenario: str, variable: str = "tas") -> xr.Dataset:
    """Open one scenario/variable group from the published store, lazily.

    chunks={} adopts the store's own chunk grid, (8000, 8, 16). Passing
    chunks="auto" instead fuses those into ~115 MB dask tasks -- 28x more
    memory per task for exactly the same bytes read.
    """
    import icechunk

    if scenario not in _MEMBERS:
        raise ValueError(f"scenario must be one of {SCENARIOS}, got {scenario!r}")
    if variable not in VARIABLES:
        raise ValueError(f"variable must be one of {VARIABLES}, got {variable!r}")

    storage = icechunk.s3_storage(anonymous=True, **STORE)
    session = icechunk.Repository.open(storage).readonly_session(branch=STORE_BRANCH)
    return xr.open_dataset(
        session.store,
        group=f"{scenario}/{variable}/{ensemble_member(scenario, variable)}",
        engine="zarr",
        consolidated=False,
        zarr_format=3,
        chunks={},
    )


def describe_request(da: xr.DataArray, label: str = "selection", quiet: bool = False) -> int:
    """Estimate what a selection costs before you load it.

    Returns the number of bytes that will actually be read, which is what
    matters: a chunk is the unit of decompression, so a request touching one
    cell of a chunk still reads the whole thing.
    """
    native = da.encoding.get("chunks") or da.encoding.get("preferred_chunks")
    if isinstance(native, dict):
        native = tuple(native[d] for d in da.dims)

    if native:
        source = "store chunks"
    elif da.chunks:
        native = tuple(c[0] for c in da.chunks)
        source = "dask chunks, store encoding dropped"
    else:
        native, source = da.shape, "already in memory"

    chunk_bytes = int(np.prod(native)) * da.dtype.itemsize
    n_chunks = getattr(getattr(da, "data", None), "npartitions", 1)
    read = n_chunks * chunk_bytes

    if not quiet:
        print(f"{label}:")
        print(f"  shape          {dict(zip(da.dims, da.shape))}")
        print(f"  logical size   {da.nbytes / 1e9:8.3f} GB")
        print(f"  chunks touched {n_chunks:8d}  ({chunk_bytes / 1e6:.1f} MB each, {source})")
        print(f"  data read      {read / 1e9:8.3f} GB")
    return read
