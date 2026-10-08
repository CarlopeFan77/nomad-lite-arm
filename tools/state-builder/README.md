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


## One-Command State Pipeline

Once the development environment is configured, a new
state can be prepared, built, and released with one
command:

    python3 tools/state-builder/state-pipeline.py \
        new-hampshire \
        --state-code NH

The pipeline runs:

    prepare-state.py
    → build-state.py
    → release-state.py

The GitHub release step still asks for confirmation
before publication.

For unattended operation after reviewing the workflow:

    python3 tools/state-builder/state-pipeline.py \
        new-hampshire \
        --state-code NH \
        --yes

To remove local build files after a successful release:

    python3 tools/state-builder/state-pipeline.py \
        new-hampshire \
        --state-code NH \
        --yes \
        --clean

The pipeline is resumable. Existing WIP configurations,
completed builds, and draft releases are reused rather
than starting over.


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

## Publishing a State

After a state has been built and reviewed, publish it
with:

    python3 tools/state-builder/release-state.py maine

The release tool:

1. Verifies local package sizes and SHA-256 hashes.
2. Creates a draft GitHub Release.
3. Uploads Basic, terrain, and contour MBTiles.
4. Verifies the uploaded release assets.
5. Adds release URLs, hashes, and exact package sizes
   to the state configuration.
6. Publishes the GitHub Release.
7. Moves the state from `config/maps/wip/` into the
   active `config/maps/` catalog.

To skip the confirmation prompt:

    python3 tools/state-builder/release-state.py \
        maine \
        --yes

To delete the local build after a successful release:

    python3 tools/state-builder/release-state.py \
        maine \
        --yes \
        --clean

Existing releases can be checked without changing
anything:

    python3 tools/state-builder/release-state.py \
        maine \
        --verify-only

The tool intentionally does not create Git commits or
push repository changes. Review the generated state
configuration before committing it.
