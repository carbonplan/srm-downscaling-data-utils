
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

Utilities for accessing and analysing output from the srm-downscaling project

## data

> [!CAUTION]
> **Preliminary Data**: This dataset includes multiple variables, scenarios, and GCMs at the daily timestep with global coverage, downscaled to the 0.25° resolution. The version currently released is a preliminary subset containing mean daily temperature (`tasmean`) for one historical scenario, one GCM, and two future scenarios (the G6-1.5 SAI scenario and SSP2-4.5). We welcome feedback on both the preliminary dataset and its access utilities to help guide continued development.

> [!IMPORTANT]
> Data associated with this repository are subject to additional [terms of data access](https://carbonplan.github.io/srm-downscaling/terms-of-data-access.html).

## installation

This project uses [Pixi](https://pixi.sh) for environment and dependency management.

1. Install Pixi: follow the [installation instructions](https://pixi.sh/latest/#installation)

2. Clone and set up:

```bash
git clone https://github.com/carbonplan/srm-downscaling-data-utils
cd srm-downscaling-data-utils
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

## license

All the code in this repository is [MIT](https://choosealicense.com/licenses/mit/) licensed.

## about us

CarbonPlan is a non-profit organization that uses data and science for climate action. We aim to improve the transparency and scientific integrity of carbon removal and climate solutions through open data and tools. Find out more at [carbonplan.org](https://carbonplan.org/) or get in touch by [opening an issue](https://github.com/carbonplan/srm-downscaling-data-utils/issues/new) or [sending us an email](mailto:hello@carbonplan.org).
