#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CATALOG="$PROJECT_DIR/config/education-catalog.txt"

STATE_DIR="$PROJECT_DIR/data/education"
OUTPUT="$STATE_DIR/sizes.txt"

mkdir -p "$STATE_DIR"

CATALOG_PATH="$CATALOG" \
OUTPUT_PATH="$OUTPUT" \
kolibri shell <<'PYTHON'

import os
from pathlib import Path

from kolibri.core.content.models import ContentNode


catalog_path = Path(
    os.environ["CATALOG_PATH"]
)

output_path = Path(
    os.environ["OUTPUT_PATH"]
)

rows = []


for raw_line in catalog_path.read_text().splitlines():

    line = raw_line.strip()

    if not line or line.startswith("#"):
        continue

    parts = line.split("|", 4)

    if len(parts) != 5:
        continue

    (
        course_id,
        category,
        name,
        description,
        node_id,
    ) = parts

    try:
        node = ContentNode.objects.get(
            id=node_id
        )

    except ContentNode.DoesNotExist:
        rows.append(
            f"{course_id}|0|0|0"
        )
        continue

    descendants = (
        ContentNode.objects.filter(
            channel_id=node.channel_id,
            tree_id=node.tree_id,
            lft__gte=node.lft,
            rght__lte=node.rght,
        )
        .prefetch_related(
            "files__local_file"
        )
    )

    seen_files = set()

    total_bytes = 0
    remaining_bytes = 0
    resources = 0

    for content in descendants:

        if content.kind != "topic":
            resources += 1

        for file_obj in content.files.all():

            local_file = file_obj.local_file

            if local_file is None:
                continue

            if local_file.id in seen_files:
                continue

            seen_files.add(
                local_file.id
            )

            size = (
                local_file.file_size
                or 0
            )

            total_bytes += size

            if not local_file.available:
                remaining_bytes += size

    rows.append(
        "|".join(
            [
                course_id,
                str(total_bytes),
                str(remaining_bytes),
                str(resources),
            ]
        )
    )


output_path.write_text(
    "\n".join(rows) + "\n"
)

print()
print(
    f"Education sizes written to:"
)
print(output_path)

PYTHON
