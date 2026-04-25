---
description: Preview scene object tombstones by scenectl filters
---

Preview which scene objects would be tombstoned using the provided filters. Example:

```text
/scene-delete-dry-run --scene castle_crown_064013 --tag white_castle_crown
```

Command output:

!`python scripts/scenectl.py object delete $ARGUMENTS --dry-run`

Summarize the target count. Do not tombstone or apply deletion.
