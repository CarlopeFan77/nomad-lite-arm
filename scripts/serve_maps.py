#!/usr/bin/env python3

import json
import os
import sqlite3

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

from pathlib import Path
from urllib.parse import urlparse


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

CONFIG_DIR = (
    PROJECT_DIR
    / "config"
    / "maps"
)


# --------------------------------------------------
# Selected state
# --------------------------------------------------

STATE_ID = os.environ.get(
    "NOMAD_MAPS_STATE",
    "wyoming",
).strip().lower()


CONFIG_FILE = (
    CONFIG_DIR
    / f"{STATE_ID}.json"
)


def load_state_config():

    if not CONFIG_FILE.exists():

        raise SystemExit(
            "ERROR: Map state configuration "
            f"not found:\n  {CONFIG_FILE}"
        )


    try:

        config = json.loads(
            CONFIG_FILE.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:

        raise SystemExit(
            "ERROR: Invalid map configuration "
            f"{CONFIG_FILE}:\n  {error}"
        ) from error


    required = (
        "id",
        "name",
        "packages",
    )


    for key in required:

        if key not in config:

            raise SystemExit(
                "ERROR: Missing map configuration "
                f"field: {key}"
            )


    return config


STATE_CONFIG = load_state_config()

STATE_NAME = STATE_CONFIG["name"]

PACKAGES = STATE_CONFIG["packages"]


# --------------------------------------------------
# State package files
# --------------------------------------------------

MAP_FILE = (
    PROJECT_DIR
    / PACKAGES["basic"]["file"]
)

TERRAIN_FILE = (
    PROJECT_DIR
    / PACKAGES["terrain"]["file"]
)

CONTOUR_FILE = (
    PROJECT_DIR
    / PACKAGES["contours"]["file"]
)

PACKAGE_FILES = {
    "basic": MAP_FILE,
    "terrain": TERRAIN_FILE,
    "contours": CONTOUR_FILE,
}

# --------------------------------------------------
# Viewer + MapLibre
# --------------------------------------------------

VIEWER_FILE = (
    PROJECT_DIR
    / "web"
    / "maps"
    / "map.html"
)

MAPLIBRE_MJS = (
    PROJECT_DIR
    / "web"
    / "vendor"
    / "maplibre"
    / "maplibre-gl.mjs"
)

MAPLIBRE_WORKER = (
    PROJECT_DIR
    / "web"
    / "vendor"
    / "maplibre"
    / "maplibre-gl-worker.mjs"
)

MAPLIBRE_SHARED = (
    PROJECT_DIR
    / "web"
    / "vendor"
    / "maplibre"
    / "maplibre-gl-shared.mjs"
)

MAPLIBRE_CSS = (
    PROJECT_DIR
    / "web"
    / "vendor"
    / "maplibre"
    / "maplibre-gl.css"
)


# --------------------------------------------------
# Server
# --------------------------------------------------

HOST = os.environ.get(
    "NOMAD_MAPS_HOST",
    "127.0.0.1",
)

PORT = int(
    os.environ.get(
        "NOMAD_MAPS_PORT",
        "8083",
    )
)


def get_mbtiles_tile(
    file_path,
    z,
    x,
    y,
):

    if not file_path.is_file():
        return None

    # Browser map libraries use XYZ rows.
    # MBTiles stores tile rows using TMS.
    tms_y = (2 ** z - 1) - y


    connection = sqlite3.connect(
        file_path
    )


    tile = connection.execute(
        """
        SELECT tile_data
        FROM tiles
        WHERE zoom_level = ?
          AND tile_column = ?
          AND tile_row = ?
        """,
        (
            z,
            x,
            tms_y,
        ),
    ).fetchone()


    connection.close()


    if tile is None:
        return None


    return tile[0]


def get_tile(
    z,
    x,
    y,
):

    return get_mbtiles_tile(
        MAP_FILE,
        z,
        x,
        y,
    )


def get_terrain_tile(
    z,
    x,
    y,
):

    return get_mbtiles_tile(
        TERRAIN_FILE,
        z,
        x,
        y,
    )


def get_contour_tile(
    z,
    x,
    y,
):

    return get_mbtiles_tile(
        CONTOUR_FILE,
        z,
        x,
        y,
    )


class MapHandler(
    BaseHTTPRequestHandler
):

    def send_local_file(
        self,
        file_path,
        content_type,
    ):

        if not file_path.exists():

            self.send_error(
                404,
                f"Missing file: {file_path}",
            )

            return

        data = file_path.read_bytes()

        self.send_response(200)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(data)),
        )

        self.end_headers()

        self.wfile.write(data)


    def send_json(
        self,
        data,
        status=200,
    ):

        body = json.dumps(
            data
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)


    def do_GET(self):

        path = urlparse(
            self.path
        ).path


        # ----------------------------------------
        # Status page
        # ----------------------------------------

        if path == "/":

            body = (
                "NOMAD Maps\n"
                "==========\n"
                "\n"
                f"State: {STATE_NAME}\n"
                f"State ID: {STATE_ID}\n"
                "\n"
                "Viewer:\n"
                f"http://{HOST}:{PORT}/map\n"
                "\n"
                "Basic map:\n"
                f"{MAP_FILE}\n"
                "\n"
                "Terrain:\n"
                f"{TERRAIN_FILE}\n"
                "\n"
                "Contours:\n"
                f"{CONTOUR_FILE}\n"
                "\n"
                "Endpoints:\n"
                "/tiles/{z}/{x}/{y}.pbf\n"
                "/terrain/{z}/{x}/{y}.png\n"
                "/contours/{z}/{x}/{y}.pbf\n"
            ).encode(
                "utf-8"
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(body)),
            )

            self.end_headers()

            self.wfile.write(body)

            return


        # ----------------------------------------
        # Public map configuration
        # ----------------------------------------

        if path == "/api/config":

            public_config = {
                "id":
                    STATE_CONFIG["id"],

                "name":
                    STATE_CONFIG["name"],

                "center":
                    STATE_CONFIG["center"],

                "zoom":
                    STATE_CONFIG["zoom"],

                "bounds":
                    STATE_CONFIG["bounds"],

                "max_bounds":
                    STATE_CONFIG["max_bounds"],

                "packages": {
                    name: {
                        "minzoom":
                            package["minzoom"],

                        "maxzoom":
                            package["maxzoom"],

                        "installed":
                            PACKAGE_FILES[
                                name
                            ].is_file(),
                    }
                    for name, package
                    in PACKAGES.items()
                },

                "contour_interval_ft":
                    STATE_CONFIG[
                        "contour_interval_ft"
                    ],

                "index_contour_interval_ft":
                    STATE_CONFIG[
                        "index_contour_interval_ft"
                    ],

                "attribution":
                    STATE_CONFIG["attribution"],
            }

            self.send_json(
                public_config
            )

            return


        # ----------------------------------------
        # Map viewer
        # ----------------------------------------

        if path in (
            "/map",
            "/map/",
        ):

            self.send_local_file(
                VIEWER_FILE,
                "text/html; charset=utf-8",
            )

            return


        # ----------------------------------------
        # Local MapLibre ES module
        # ----------------------------------------

        if path == (
            "/static/maplibre-gl.mjs"
        ):

            self.send_local_file(
                MAPLIBRE_MJS,
                "text/javascript; charset=utf-8",
            )

            return


        # ----------------------------------------
        # MapLibre worker module
        # ----------------------------------------

        if path == (
            "/static/maplibre-gl-worker.mjs"
        ):

            self.send_local_file(
                MAPLIBRE_WORKER,
                "text/javascript; charset=utf-8",
            )

            return


        # ----------------------------------------
        # MapLibre shared module
        # ----------------------------------------

        if path == (
            "/static/maplibre-gl-shared.mjs"
        ):

            self.send_local_file(
                MAPLIBRE_SHARED,
                "text/javascript; charset=utf-8",
            )

            return


        # ----------------------------------------
        # Local MapLibre CSS
        # ----------------------------------------

        if path == (
            "/static/maplibre-gl.css"
        ):

            self.send_local_file(
                MAPLIBRE_CSS,
                "text/css; charset=utf-8",
            )

            return


        # ----------------------------------------
        # Vector tile endpoint
        # ----------------------------------------

        if (
            path.startswith("/tiles/")
            and
            path.endswith(".pbf")
        ):

            try:

                parts = path.split("/")

                z = int(
                    parts[2]
                )

                x = int(
                    parts[3]
                )

                y = int(
                    parts[4].removesuffix(
                        ".pbf"
                    )
                )

            except (
                ValueError,
                IndexError,
            ):

                self.send_error(
                    400,
                    "Invalid tile path",
                )

                return


            tile_data = get_tile(
                z,
                x,
                y,
            )


            if tile_data is None:

                self.send_error(
                    404,
                    "Tile not found",
                )

                return


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/vnd.mapbox-vector-tile",
            )

            self.send_header(
                "Content-Encoding",
                "gzip",
            )

            self.send_header(
                "Content-Length",
                str(len(tile_data)),
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )

            self.end_headers()

            self.wfile.write(
                tile_data
            )

            return

        # ----------------------------------------
        # Terrain DEM endpoint
        # ----------------------------------------

        if (
            path.startswith("/terrain/")
            and
            path.endswith(".png")
        ):

            try:

                parts = path.split("/")

                z = int(
                    parts[2]
                )

                x = int(
                    parts[3]
                )

                y = int(
                    parts[4].removesuffix(
                        ".png"
                    )
                )

            except (
                ValueError,
                IndexError,
            ):

                self.send_error(
                    400,
                    "Invalid terrain tile path",
                )

                return


            terrain_data = get_terrain_tile(
                z,
                x,
                y,
            )


            if terrain_data is None:

                self.send_error(
                    404,
                    "Terrain tile not found",
                )

                return


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "image/png",
            )

            self.send_header(
                "Content-Length",
                str(len(terrain_data)),
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )

            self.end_headers()

            self.wfile.write(
                terrain_data
            )

            return

        # ----------------------------------------
        # Contour vector tile endpoint
        # ----------------------------------------

        if (
            path.startswith("/contours/")
            and
            path.endswith(".pbf")
        ):

            try:

                parts = path.split("/")

                z = int(
                    parts[2]
                )

                x = int(
                    parts[3]
                )

                y = int(
                    parts[4].removesuffix(
                        ".pbf"
                    )
                )

            except (
                ValueError,
                IndexError,
            ):

                self.send_error(
                    400,
                    "Invalid contour tile path",
                )

                return


            contour_data = get_contour_tile(
                z,
                x,
                y,
            )


            if contour_data is None:

                self.send_error(
                    404,
                    "Contour tile not found",
                )

                return


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/vnd.mapbox-vector-tile",
            )

            self.send_header(
                "Content-Encoding",
                "gzip",
            )

            self.send_header(
                "Content-Length",
                str(len(contour_data)),
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )

            self.end_headers()

            self.wfile.write(
                contour_data
            )

            return

        # ----------------------------------------
        # Anything else
        # ----------------------------------------

        self.send_error(
            404,
            "Not found",
        )


    def log_message(
        self,
        format,
        *args,
    ):

        print(
            f"{self.client_address[0]} "
            f"- {format % args}"
        )


def main():

    required_files = [

        CONFIG_FILE,

        MAP_FILE,

        VIEWER_FILE,

        MAPLIBRE_MJS,

        MAPLIBRE_WORKER,

        MAPLIBRE_SHARED,

        MAPLIBRE_CSS,

    ]


    for file_path in required_files:

        if not file_path.exists():

            print(
                "ERROR: Required file "
                "not found:"
            )

            print(
                f"  {file_path}"
            )

            return


    server = ThreadingHTTPServer(
        (
            HOST,
            PORT,
        ),
        MapHandler,
    )


    print(
        "NOMAD Maps"
    )

    print(
        "=========="
    )

    print()

    print(
        f"State:   "
        f"{STATE_NAME}"
    )

    print(
        f"Config:  "
        f"{CONFIG_FILE}"
    )

    print()

    print(
        f"Basic:   "
        f"{MAP_FILE}"
    )

    print(
        f"Terrain: "
        f"{TERRAIN_FILE}"
    )

    print(
        f"Contours:"
        f" {CONTOUR_FILE}"
    )

    print()

    print(
        f"Viewer:  "
        f"http://{HOST}:{PORT}/map"
    )

    print()

    print(
        "Press Ctrl+C to stop."
    )

    print()


    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print()

        print(
            "Stopping map server..."
        )


    finally:

        server.server_close()


if __name__ == "__main__":

    main()
