import importlib.util
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SCENECTL_PATH = REPO_ROOT / "scripts" / "scenectl.py"


spec = importlib.util.spec_from_file_location("scenectl", SCENECTL_PATH)
scenectl = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(scenectl)


def sample_object(**overrides):
    obj = {
        "mcp_id": "castle_wall_001",
        "desired_name": "Castle Wall 001",
        "actor_type": "StaticMeshActor",
        "group": "scene_group:walls",
        "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
        "transform": {
            "location": {"x": 1, "y": 2, "z": 3},
            "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
            "scale": {"x": 1, "y": 1, "z": 1},
        },
        "visual": {},
        "physics": {},
        "tags": ["castle", "defensive"],
        "desired_hash": "new",
        "last_applied_hash": "old",
    }
    obj.update(overrides)
    return obj


def args(**overrides):
    defaults = {
        "mcp_id": None,
        "group": None,
        "tag": None,
        "name_contains": None,
        "changed": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_filter_objects_requires_all_requested_tags():
    objects = [
        sample_object(mcp_id="a", tags=["castle", "defensive"]),
        sample_object(mcp_id="b", tags=["castle"]),
    ]

    filtered = scenectl.filter_objects(objects, args(tag=["castle", "defensive"]))

    assert [obj["mcp_id"] for obj in filtered] == ["a"]


def test_filter_objects_can_find_changed_objects():
    objects = [
        sample_object(mcp_id="changed", desired_hash="new", last_applied_hash="old"),
        sample_object(mcp_id="synced", desired_hash="same", last_applied_hash="same"),
    ]

    filtered = scenectl.filter_objects(objects, args(changed=True))

    assert [obj["mcp_id"] for obj in filtered] == ["changed"]


def test_object_to_upsert_payload_preserves_editable_state():
    payload = scenectl.object_to_upsert_payload("main", sample_object())

    assert payload["scene_id"] == "main"
    assert payload["mcp_id"] == "castle_wall_001"
    assert payload["group_id"] == "walls"
    assert payload["asset_ref"] == {"path": "/Engine/BasicShapes/Cube.Cube"}
    assert payload["tags"] == ["castle", "defensive"]
    assert payload["visual"] == {}
    assert payload["physics"] == {}


def test_summarize_object_is_table_safe():
    row = scenectl.summarize_object(sample_object())

    assert row["mcp_id"] == "castle_wall_001"
    assert row["group"] == "walls"
    assert row["location"] == "1,2,3"
    assert "castle" in row["tags"]


def test_split_interactive_line_preserves_quoted_arguments():
    argv = scenectl.split_interactive_line('scene create demo --name "Demo Scene"')

    assert argv == ["scene", "create", "demo", "--name", "Demo Scene"]


def test_slash_commands_include_common_entries():
    assert "/help" in scenectl.SLASH_COMMANDS
    assert "/doctor" in scenectl.SLASH_COMMANDS
    assert "/object list" in scenectl.SLASH_COMMANDS
