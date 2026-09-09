"""Shared access helpers for the CarbonPlan SRM downscaling dataset.

This module is the canonical home for the details that change when the
dataset is republished: which store to open, the pinned branch, the group
layout, and the ensemble-member lookup. Keeping them in one place matters --
the notebook in this repository once sat broken for a whole release because a
dead store path was hard-coded in a second location.

Group layout as of v0.14.1::

    {method}/{scenario}/{variable}/{member}

The method level (bcsd, qdmsd) is new in v0.14.1; earlier versions had no
such level and lived in a differently named store.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

__all__ = [
    "BUCKET",
    "REGION",
    "STORE_BRANCH",
    "GCMS",
    "METHODS",
    "SCENARIOS",
    "VARIABLES",
    "scenarios_for",
    "coverage",
    "ensemble_member",
    "check_members",
    "load_downscaling_store",
    "describe_request",
]

BUCKET = "us-west-2.opendata.source.coop"
REGION = "us-west-2"
_PREFIX = "carbonplan/srm-downscaling/output/production"

# There are zero tags on these stores, so pinning a branch is the only way to
# get reproducible reads.
STORE_BRANCH = "v0.14.1"

# One store per GCM. Only these two publish v0.14.1; MIROC-ES2H exists but is
# still at v0.13.0, which has a different group layout, so it is not offered.
_STORES = {
    "CESM2-WACCM6": "CESM2-WACCM6-ERA5-global",
    "UKESM1-1-LL": "UKESM1-1-LL-ERA5-global",
}
GCMS = list(_STORES)

# Downscaling method. Both are published for every scenario and variable.
METHODS = ["bcsd", "qdmsd"]

VARIABLES = ["tas", "tasmax", "tasmin", "pr", "rsds"]

# tasmax/tasmin were produced by a separate "bridge" job for CESM2-WACCM6 and
# carry a different ensemble member there. UKESM1-1-LL has no such split.
_BRIDGE_VARS = {"tasmax", "tasmin"}

# {gcm: {scenario: {kind: (member, first_date, last_date)}}}
# Generated from the published stores rather than transcribed by hand.
_LAYOUT = {
    "CESM2-WACCM6": {
        "historical": {
            "main": ("r3i1p1f1", "1978-01-01", "2014-12-31"),
            "bridge": ("001", "1978-01-01", "2014-12-31"),
        },
        "ssp245": {
            "main": ("003", "2015-01-01", "2099-12-31"),
            "bridge": ("008", "2015-01-01", "2069-12-31"),
        },
        "g6_1p5k": {
            "main": ("003", "2035-01-01", "2084-12-31"),
            "bridge": ("003", "2035-01-01", "2084-12-31"),
        },
        "g6_1p5k_end": {
            "main": ("002", "2085-01-01", "2100-12-31"),
            "bridge": ("002", "2085-01-01", "2100-12-31"),
        },
    },
    "UKESM1-1-LL": {
        "historical": {
            "main": ("u-by791", "1978-01-01", "2014-12-31"),
            "bridge": ("u-by791", "1978-01-01", "2014-12-31"),
        },
        "ssp245": {
            "main": ("r2i1p1f2", "2015-01-01", "2099-12-31"),
            "bridge": ("r2i1p1f2", "2015-01-01", "2099-12-31"),
        },
        "g6_1p5k": {
            "main": ("r2i1p1f2", "2035-01-01", "2084-12-31"),
            "bridge": ("r2i1p1f2", "2035-01-01", "2084-12-31"),
        },
    },
}

# Scenarios common to every GCM. g6_1p5k_end extends g6_1p5k to 2100 but is
# published for CESM2-WACCM6 only, so use scenarios_for() when it matters.
SCENARIOS = sorted(set.intersection(*(set(v) for v in _LAYOUT.values())))


def scenarios_for(gcm: str) -> list[str]:
    """Scenarios published for a given GCM."""
    _check_gcm(gcm)
    return sorted(_LAYOUT[gcm])


def _check_gcm(gcm: str) -> None:
    if gcm not in _LAYOUT:
        raise ValueError(f"gcm must be one of {GCMS}, got {gcm!r}")


def _entry(gcm: str, scenario: str, variable: str):
    _check_gcm(gcm)
    if scenario not in _LAYOUT[gcm]:
        raise ValueError(
            f"scenario must be one of {scenarios_for(gcm)} for {gcm}, got {scenario!r}"
        )
    if variable not in VARIABLES:
        raise ValueError(f"variable must be one of {VARIABLES}, got {variable!r}")
    kind = "bridge" if variable in _BRIDGE_VARS else "main"
    return _LAYOUT[gcm][scenario][kind]


def ensemble_member(scenario: str, variable: str, gcm: str = "CESM2-WACCM6") -> str:
    """Report which ensemble member a (gcm, scenario, variable) triple resolves to."""
    return _entry(gcm, scenario, variable)[0]


def coverage(scenario: str, variable: str, gcm: str = "CESM2-WACCM6") -> tuple[str, str]:
    """Return the (first, last) date available for a scenario/variable pair."""
    _, first, last = _entry(gcm, scenario, variable)
    return first, last


def check_members(scenario: str, variables, gcm: str = "CESM2-WACCM6") -> dict:
    """Map each variable to its member, warning when a set spans the split.

    On CESM2-WACCM6, tasmax/tasmin come from a separate bridge job, so on
    historical and ssp245 they carry a different member than tas/pr/rsds.
    Combining across that split mixes ensemble members, which is rarely
    intended. UKESM1-1-LL uses one member per scenario and never warns.
    """
    members = {v: ensemble_member(scenario, v, gcm) for v in variables}
    if len(set(members.values())) > 1:
        print(f"WARNING: on {gcm}/{scenario} these variables span multiple ensemble members:")
        for v, m in members.items():
            print(f"    {v:8s} -> {m}")
        print("  Combining them mixes members, which is rarely intended.")
    return members


def load_downscaling_store(
    scenario: str,
    variable: str = "tas",
    gcm: str = "CESM2-WACCM6",
    method: str = "bcsd",
) -> xr.Dataset:
    """Open one group from the published store, lazily.

    chunks={} adopts the store's own chunk grid. Passing chunks="auto" instead
    fuses native chunks into much larger dask tasks -- more memory per task for
    exactly the same bytes read.
    """
    import icechunk

    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    member = ensemble_member(scenario, variable, gcm)  # also validates gcm/scenario/variable

    storage = icechunk.s3_storage(
        bucket=BUCKET,
        prefix=f"{_PREFIX}/{_STORES[gcm]}.icechunk",
        anonymous=True,
        region=REGION,
    )
    session = icechunk.Repository.open(storage).readonly_session(branch=STORE_BRANCH)
    return xr.open_dataset(
        session.store,
        group=f"{method}/{scenario}/{variable}/{member}",
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
