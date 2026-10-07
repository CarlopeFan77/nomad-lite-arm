# NOMAD State Builder

Developer tooling for building offline map packages
used by NOMAD Lite ARM.

This directory is not part of the normal NOMAD
installation process.

The state builder generates:

- Basic vector map MBTiles
- Terrarium terrain MBTiles
- Elevation GeoTIFF working data
- Contour source data
- Final contour MBTiles
- SHA-256 package manifest

Build products are stored outside the repository by
default in:

    ~/nomad-build/

## Requirements

- Python 3
- GDAL
- Python GDAL bindings
- curl
- Tippecanoe
- tile-join

## Usage

From the repository root:

    python3 tools/state-builder/build-state.py rhode-island

An alternate workspace can be selected with:

    python3 tools/state-builder/build-state.py \
        rhode-island \
        --build-root /path/to/builds

Terrain download concurrency can be changed with:

    python3 tools/state-builder/build-state.py \
        rhode-island \
        --workers 8

This tooling is intended for NOMAD developers and
contributors. Normal users should install maps through
the NOMAD installer instead.

## Preparing a New State

New states are first created as WIP configurations.
WIP states are not visible to the normal NOMAD
installer or dashboard.

Example:

    python3 tools/state-builder/prepare-state.py \
        maine \
        --state-code ME

This downloads the state's Basic Shortbread map,
reads its bounds and center metadata, and creates:

    config/maps/wip/maine.json

After reviewing the configuration, build the state:

    python3 tools/state-builder/build-state.py maine

Once the packages have been released and verified,
the state configuration can be moved from `wip/`
into the active `config/maps/` catalog.
