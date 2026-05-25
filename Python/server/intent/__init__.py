"""React for UE v3.0 - Intent layer.

SceneContextPack assembly, intent + target resolution.
"""

from server.intent.scene_context import (  # noqa: F401
    SceneContextPack,
    SceneObjectBrief,
    EntityBrief,
    ComponentBrief,
    AssetBrief,
    SnapshotBrief,
    OperationBrief,
)
from server.intent.scene_summarizer import (  # noqa: F401
    SceneSummarizer,
    estimate_tokens,
    summarize_scene,
)
from server.intent.intent_types import Intent, RiskLevel  # noqa: F401
from server.intent.intent_resolver import (  # noqa: F401
    IntentResolution,
    IntentResolver,
    resolve_intent,
)
from server.intent.target_resolver import (  # noqa: F401
    TargetResolution,
    TargetResolver,
    resolve_target,
)
