#!/bin/bash

CHANNEL_ID="c9d7f950ab6b5a1199e3d6c10d7f0103"

kolibri shell <<PYTHON
from kolibri.core.content.models import ContentNode

channel_id = "$CHANNEL_ID"

roots = ContentNode.objects.filter(
    channel_id=channel_id,
    kind="topic",
    level__lte=2
).order_by("lft")

print()
print("Khan Academy topics")
print("===================")

for node in roots:
    indent = "  " * node.level
    print(f"{indent}{node.title} | {node.id}")
PYTHON
