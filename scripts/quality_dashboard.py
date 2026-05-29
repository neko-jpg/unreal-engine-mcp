"""Print recent cave quality history records with trend analysis."""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_records(history_dir: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not history_dir.exists():
        return records
    for path in sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_path"] = str(path)
            records.append(data)
        except Exception:
            continue
    return records


def _filter_records(
    records: List[Dict[str, Any]],
    scene_id: Optional[str] = None,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filtered = records
    if scene_id:
        filtered = [r for r in filtered if r.get("scene_id") == scene_id]
    if since:
        try:
            cutoff = datetime.fromisoformat(since)
            filtered = [
                r for r in filtered
                if datetime.fromisoformat(r.get("timestamp", "1970-01-01T00:00:00+00:00")) >= cutoff
            ]
        except ValueError:
            pass
    return filtered


SUB_SCORE_KEYS = [
    "semantic_score", "shape_score", "composition_score", "detail_score",
    "material_score", "lighting_score", "topology_score", "technical_score", "performance_score",
]


def _get_sub_scores(record: Dict[str, Any]) -> Dict[str, Any]:
    qv = record.get("quality_vector", {})
    if isinstance(qv, dict):
        return {k: qv.get(k, "") for k in SUB_SCORE_KEYS}
    return {k: "" for k in SUB_SCORE_KEYS}


def _format_table(records: List[Dict[str, Any]], show_subscores: bool = False) -> str:
    lines: List[str] = []
    if show_subscores:
        header = (
            f"{'timestamp':<22} | {'scene_id':<12} | {'overall':>7} | {'passed':>6} | "
            f"{'shape':>5} | {'detail':>6} | {'material':>8} | {'light':>5} | {'blockers'}"
        )
        lines.append(header)
        lines.append("-" * len(header))
        for record in records:
            gate = record.get("gate_results", {})
            blockers = ",".join(gate.get("blockers", [])) if isinstance(gate, dict) else ""
            ss = _get_sub_scores(record)
            lines.append(
                f"{record.get('timestamp', ''):<22} | "
                f"{record.get('scene_id', ''):<12} | "
                f"{record.get('overall', ''):>7} | "
                f"{str(gate.get('passed', '')):>6} | "
                f"{ss.get('shape_score', ''):>5} | "
                f"{ss.get('detail_score', ''):>6} | "
                f"{ss.get('material_score', ''):>8} | "
                f"{ss.get('lighting_score', ''):>5} | "
                f"{blockers}"
            )
    else:
        lines.append("timestamp | scene_id | overall | passed | blockers")
        lines.append("-" * 72)
        for record in records:
            gate = record.get("gate_results", {})
            blockers = ",".join(gate.get("blockers", [])) if isinstance(gate, dict) else ""
            lines.append(
                f"{record.get('timestamp', '')} | "
                f"{record.get('scene_id', '')} | "
                f"{record.get('overall', '')} | "
                f"{gate.get('passed', '') if isinstance(gate, dict) else ''} | "
                f"{blockers}"
            )
    return "\n".join(lines)


def _format_json(records: List[Dict[str, Any]]) -> str:
    return json.dumps(records, indent=2, default=str)


def _format_csv(records: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp", "scene_id", "overall", "passed", "iterations"] + SUB_SCORE_KEYS + ["blockers"])
    for record in records:
        gate = record.get("gate_results", {})
        blockers = ",".join(gate.get("blockers", [])) if isinstance(gate, dict) else ""
        ss = _get_sub_scores(record)
        writer.writerow([
            record.get("timestamp", ""),
            record.get("scene_id", ""),
            record.get("overall", ""),
            gate.get("passed", "") if isinstance(gate, dict) else "",
            record.get("iterations", ""),
        ] + [ss.get(k, "") for k in SUB_SCORE_KEYS] + [blockers])
    return buf.getvalue()


def _format_trend(records: List[Dict[str, Any]]) -> str:
    if len(records) < 2:
        return "Not enough records for trend analysis (need at least 2)."
    lines: List[str] = []
    lines.append("TREND ANALYSIS")
    lines.append("=" * 60)
    scores = [float(r.get("overall", 0)) for r in records if r.get("overall") is not None]
    if not scores:
        return "No scores found."
    lines.append(f"Records: {len(scores)}")
    lines.append(f"Score range: {min(scores):.1f} - {max(scores):.1f}")
    lines.append(f"Mean: {sum(scores)/len(scores):.1f}")
    if len(scores) >= 2:
        delta = scores[-1] - scores[0]
        direction = "UP" if delta > 0 else "DOWN" if delta < 0 else "FLAT"
        lines.append(f"Trend: {direction} ({delta:+.1f} from first to last)")
    # Sub-score trends
    for key in SUB_SCORE_KEYS:
        vals = []
        for r in records:
            qv = r.get("quality_vector", {})
            if isinstance(qv, dict) and qv.get(key) is not None:
                vals.append(float(qv[key]))
        if len(vals) >= 2:
            d = vals[-1] - vals[0]
            lines.append(f"  {key}: {vals[0]:.3f} -> {vals[-1]:.3f} ({d:+.3f})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show recent SQOP quality scores.")
    parser.add_argument("--last-n", type=int, default=10)
    parser.add_argument("--history-dir", default=str(Path(__file__).resolve().parents[1] / "artifacts" / "quality_history"))
    parser.add_argument("--format", choices=["table", "json", "csv", "trend"], default="table")
    parser.add_argument("--sub-scores", action="store_true", help="Show sub-score columns (table mode)")
    parser.add_argument("--scene-id", type=str, default=None, help="Filter by scene_id")
    parser.add_argument("--since", type=str, default=None, help="Filter records since ISO timestamp")
    args = parser.parse_args()

    records = _load_records(Path(args.history_dir))
    records = _filter_records(records, scene_id=args.scene_id, since=args.since)
    records = records[-max(args.last_n, 1):]

    if not records:
        print("No quality history records found.")
        return 0

    if args.format == "json":
        print(_format_json(records))
    elif args.format == "csv":
        print(_format_csv(records))
    elif args.format == "trend":
        print(_format_trend(records))
    else:
        print(_format_table(records, show_subscores=args.sub_scores))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
