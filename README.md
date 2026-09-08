
<p align='left'>
  <a href='https://carbonplan.org/#gh-light-mode-only'>
    <img
      src='https://carbonplan-assets.s3.amazonaws.com/monogram/dark-small.png'
      height='48px'
    />
  </a>
  <a href='https://carbonplan.org/#gh-dark-mode-only'>
    <img
      src='https://carbonplan-assets.s3.amazonaws.com/monogram/light-small.png'
      height='48px'
    />
  </a>
</p>

# srm-downscaling-data-utils

This repository shares utilities for accessing and analyzing output from the [srm-downscaling project](https://carbonplan.github.io/srm-downscaling/). You'll probably be primarily interested in [`notebooks/subsetting-and-exporting.ipynb`](notebooks/subsetting-and-exporting.ipynb), which provides tools for accessing, subsetting, transforming, and exporting the downscaled data from the cloud to your local environment.

To get started, we recommend following the steps below:

**01 — [Set up your environment](#installation)**
Install Git and Pixi, then clone the repository and install dependencies.

**02 — [Run the notebook](#running-the-notebook)**
Launch JupyterLab and open the notebook to start working with the data.

## data

> [!CAUTION]
> **Preliminary Data**: The data used throughout this repository is a preliminary release. We welcome feedback on both the dataset and its access utilities to help guide continued development.

> [!IMPORTANT]
> Data associated with this repository are subject to additional [terms of data access](https://carbonplan.github.io/srm-downscaling/terms-of-data-access.html).

## installation

All installation steps are run from a terminal. Once you have a terminal open, follow the steps below.

### git

1. Verify Git is installed:

```bash
git --version
```

If not installed, follow the [installation instructions](https://git-scm.com/downloads).

1. Clone the repository:

```bash
git clone https://github.com/carbonplan/srm-downscaling-data-utils
cd srm-downscaling-data-utils
```

### pixi

This project uses [Pixi](https://pixi.sh) for environment and dependency management.

1. Verify Pixi is installed:

```bash
pixi --version
```

If not installed, follow the [installation instructions](https://pixi.sh/latest/#installation).

1. Install dependencies:

```bash
pixi install
```

## running the notebook

The `notebooks/subsetting-and-exporting.ipynb` notebook demonstrates how to subset and export the downscaled SRM data for a region of interest.

Launch JupyterLab with:

```bash
pixi run jupyter lab
```

Then open `notebooks/subsetting-and-exporting.ipynb`. The notebook walks through:

- Loading the dataset from cloud storage
- Selecting a region of interest using a vector boundary (Natural Earth or your own file)
- Subsetting by scenario, GCM, and variable
- Exporting to a local file

To execute the notebook non-interactively (e.g. for testing):

```bash
pixi run jupyter nbconvert --to notebook --execute --inplace notebooks/subsetting-and-exporting.ipynb
```

## downloading from the command line

If you want a file rather than an interactive session, `scripts/download.sh` is a
command-line counterpart to the notebook. It takes the same choices — scenario,
variable, region, date range — as arguments.

Check what a request costs before downloading anything:

```bash
./scripts/download.sh --scenario ssp245 --start 2050-01-01 --end 2059-12-31 \
    --bbox 68 6 98 38 --dry-run
```

Download a single-point time series:

```bash
./scripts/download.sh --scenario historical --variable tas \
    --point 28.6 77.2 --start 1990-01-01 --end 1999-12-31 --output delhi.nc
```

Download a region as Zarr:

```bash
./scripts/download.sh --scenario g6_1p5k --variable pr \
    --bbox 68 6 98 38 --start 2050-01-01 --end 2059-12-31 \
    --format zarr --output india_pr.zarr
```

See `./scripts/download.sh --help` for the full list of options.

Two things it does for you:

- **Validates dates against the scenario.** Coverage differs — `g6_1p5k` begins in
  2035, and on `ssp245` the `tasmax`/`tasmin` variables stop in 2069. Asking
  outside those ranges would otherwise write an empty file without complaint.
- **Warns before a large download.** The data is stored in chunks spanning 8,000
  days, so a request touching a wide area reads far more than it returns. Anything
  over 5 GB prompts for confirmation; pass `--yes` to skip the prompt, or
  `--dry-run` to see the estimate and stop.

## license

All the code in this repository is [MIT](https://choosealicense.com/licenses/mit/) licensed.

## about us

CarbonPlan is a non-profit organization that uses data and science for climate action. We aim to improve the transparency and scientific integrity of carbon removal and climate solutions through open data and tools. Find out more at [carbonplan.org](https://carbonplan.org/) or get in touch by [opening an issue](https://github.com/carbonplan/srm-downscaling-data-utils/issues/new) or [sending us an email](mailto:hello@carbonplan.org).
