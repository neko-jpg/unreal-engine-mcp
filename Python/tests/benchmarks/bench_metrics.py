"""Benchmark metrics collection and reporting utilities."""

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TcpCallRecord:
    command: str
    elapsed_ms: float
    bytes_sent: int
    bytes_recv: int
    retries: int = 0
    error_type: Optional[str] = None


@dataclass
class PhaseRecord:
    name: str
    start_time: float
    end_time: float = 0.0
    tcp_calls: list = field(default_factory=list)
    http_calls: list = field(default_factory=list)
    error_types: list = field(default_factory=list)
    # Phase-specific counters
    actors_created: int = 0
    actors_attempted: int = 0

    @property
    def elapsed_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time > 0 else 0.0

    @property
    def total_bytes_sent(self) -> int:
        return sum(c.bytes_sent for c in self.tcp_calls) + sum(c.bytes_sent for c in self.http_calls)

    @property
    def total_bytes_recv(self) -> int:
        return sum(c.bytes_recv for c in self.tcp_calls) + sum(c.bytes_recv for c in self.http_calls)

    @property
    def total_tcp_roundtrips(self) -> int:
        return len(self.tcp_calls)

    @property
    def total_http_calls(self) -> int:
        return len(self.http_calls)

    @property
    def total_retries(self) -> int:
        return sum(c.retries for c in self.tcp_calls) + sum(c.retries for c in self.http_calls)

    @property
    def success_rate(self) -> float:
        if self.actors_attempted == 0:
            return 1.0
        return self.actors_created / self.actors_attempted


@dataclass
class BenchmarkReport:
    run_id: str
    timestamp: str
    phases: list = field(default_factory=list)
    extra_metrics: dict = field(default_factory=dict)

    @property
    def total_elapsed_ms(self) -> float:
        return sum(p.elapsed_ms for p in self.phases)

    @property
    def total_tcp_roundtrips(self) -> int:
        return sum(p.total_tcp_roundtrips for p in self.phases)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_elapsed_ms": self.total_elapsed_ms,
            "total_tcp_roundtrips": self.total_tcp_roundtrips,
            "phases": [
                {
                    "name": p.name,
                    "elapsed_ms": p.elapsed_ms,
                    "tcp_roundtrips": p.total_tcp_roundtrips,
                    "http_calls": p.total_http_calls,
                    "retries": p.total_retries,
                    "bytes_sent": p.total_bytes_sent,
                    "bytes_recv": p.total_bytes_recv,
                    "actors_created": p.actors_created,
                    "actors_attempted": p.actors_attempted,
                    "success_rate": p.success_rate,
                    "error_types": p.error_types,
                    "tcp_commands": [{"cmd": c.command, "ms": c.elapsed_ms, "bytes_sent": c.bytes_sent, "bytes_recv": c.bytes_recv, "retries": c.retries, "error": c.error_type} for c in p.tcp_calls],
                }
                for p in self.phases
            ],
            "extra_metrics": self.extra_metrics,
        }


class MetricsCollector:
    def __init__(self, run_id: str, timestamp: str):
        self.run_id = run_id
        self.timestamp = timestamp
        self._phases: dict[str, PhaseRecord] = {}
        self._current_phase: Optional[str] = None
        self._extra: dict = {}

    # --- Phase management ---

    def start_phase(self, name: str) -> None:
        self._current_phase = name
        self._phases[name] = PhaseRecord(name=name, start_time=time.perf_counter())

    def end_phase(self, name: str) -> PhaseRecord:
        phase = self._phases[name]
        phase.end_time = time.perf_counter()
        if self._current_phase == name:
            self._current_phase = None
        return phase

    def _active_phase(self) -> Optional[PhaseRecord]:
        if self._current_phase is None:
            return None
        return self._phases.get(self._current_phase)

    # --- Recording ---

    def record_tcp_call(self, command: str, elapsed_ms: float, bytes_sent: int, bytes_recv: int, retries: int = 0, error_type: Optional[str] = None) -> None:
        phase = self._active_phase()
        if phase is None:
            return
        call = TcpCallRecord(command=command, elapsed_ms=elapsed_ms, bytes_sent=bytes_sent, bytes_recv=bytes_recv, retries=retries, error_type=error_type)
        phase.tcp_calls.append(call)
        if error_type:
            phase.error_types.append(error_type)

    def record_http_call(self, endpoint: str, elapsed_ms: float, bytes_sent: int, bytes_recv: int, retries: int = 0) -> None:
        phase = self._active_phase()
        if phase is None:
            return
        call = TcpCallRecord(command=endpoint, elapsed_ms=elapsed_ms, bytes_sent=bytes_sent, bytes_recv=bytes_recv, retries=retries)
        phase.http_calls.append(call)

    def record_actors(self, created: int, attempted: int) -> None:
        phase = self._active_phase()
        if phase is None:
            return
        phase.actors_created += created
        phase.actors_attempted += attempted

    def record_error(self, error_type: str) -> None:
        phase = self._active_phase()
        if phase is None:
            return
        phase.error_types.append(error_type)

    def set_extra(self, key: str, value) -> None:
        self._extra[key] = value

    # --- Output ---

    def summary(self) -> BenchmarkReport:
        return BenchmarkReport(
            run_id=self.run_id,
            timestamp=self.timestamp,
            phases=[self._phases[key] for key in self._phase_order()],
            extra_metrics=self._extra,
        )

    def _phase_order(self) -> list[str]:
        preferred = ["db_bulk_upsert", "sync_plan", "sync_apply", "get_actors_verify", "p7_commands", "cleanup"]
        ordered = []
        for name in preferred:
            if name in self._phases:
                ordered.append(name)
        for name in self._phases:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def save(self, output_dir: Path) -> BenchmarkReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = self.summary()
        metrics_path = output_dir / "metrics.json"
        metrics_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        summary_path = output_dir / "summary.md"
        summary_path.write_text(self._build_markdown(report), encoding="utf-8")
        return report

    def _build_markdown(self, report: BenchmarkReport) -> str:
        lines = [
            f"# ベンチマーク: {report.run_id}",
            f"実行時刻: {report.timestamp}",
            f"総時間: {report.total_elapsed_ms:.0f}ms ({report.total_elapsed_ms / 1000:.1f}s)",
            "",
            "## フェーズ別時間",
            "",
            "| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |",
            "|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|",
        ]
        for p in report.phases:
            lines.append(f"| {p.name} | {p.elapsed_ms:.0f} | {p.total_tcp_roundtrips} | {p.total_http_calls} | {p.total_bytes_sent:,} | {p.total_bytes_recv:,} | {p.total_retries} | {p.actors_created}/{p.actors_attempted} | {p.success_rate:.1%} |")

        lines.append("")
        lines.append("## TCP通信内訳")
        lines.append("")
        for p in report.phases:
            if p.tcp_calls:
                lines.append(f"### {p.name}")
                lines.append("| Command | Time (ms) | Bytes Sent | Bytes Recv | Retries | Error |")
                lines.append("|---------|-----------|------------|------------|---------|-------|")
                for c in p.tcp_calls:
                    error_str = c.error_type or ""
                    lines.append(f"| {c.command} | {c.elapsed_ms:.1f} | {c.bytes_sent:,} | {c.bytes_recv:,} | {c.retries} | {error_str} |")
                lines.append("")

        if report.extra_metrics:
            lines.append("## 追加メトリクス")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(report.extra_metrics, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)


def build_comparison_markdown(before: BenchmarkReport, after: BenchmarkReport, output_dir: Path) -> str:
    """Build a comparison markdown showing improvement ratios."""
    output_dir.mkdir(parents=True, exist_ok=True)

    before_dict = {p.name: p for p in before.phases}
    after_dict = {p.name: p for p in after.phases}
    all_phase_names = sorted(set(list(before_dict.keys()) + list(after_dict.keys())))

    lines = [
        "# 最適化 前後比較",
        "",
        f"## 概要",
        f"- 最適化前: {before.run_id} (総時間: {before.total_elapsed_ms:.0f}ms = {before.total_elapsed_ms / 1000:.1f}s)",
        f"- 最適化後: {after.run_id} (総時間: {after.total_elapsed_ms:.0f}ms = {after.total_elapsed_ms / 1000:.1f}s)",
        f"- 総改善率: **{(1 - after.total_elapsed_ms / max(before.total_elapsed_ms, 1)) * 100:.1f}%** (速度比: {before.total_elapsed_ms / max(after.total_elapsed_ms, 1):.1f}x)",
        "",
        "## フェーズ別比較",
        "",
        "| Phase | Before (ms) | After (ms) | Delta (ms) | Speedup | TCP Before | TCP After | Retry Before | Retry After |",
        "|-------|-------------|------------|------------|---------|------------|-----------|-------------|------------|",
    ]

    for name in all_phase_names:
        b = before_dict.get(name)
        a = after_dict.get(name)
        before_ms = b.elapsed_ms if b else float("nan")
        after_ms = a.elapsed_ms if a else float("nan")
        delta = before_ms - after_ms
        speedup = before_ms / max(after_ms, 1) if b and a and after_ms > 0 else float("nan")

        before_tcp = b.total_tcp_roundtrips if b else 0
        after_tcp = a.total_tcp_roundtrips if a else 0
        before_retries = b.total_retries if b else 0
        after_retries = a.total_retries if a else 0

        def _fmt(v):
            return f"{v:.0f}" if not math.isnan(v) else "-"

        speedup_str = f"{speedup:.1f}x" if not math.isnan(speedup) else "-"
        lines.append(f"| {name} | {_fmt(before_ms)} | {_fmt(after_ms)} | {_fmt(delta)} | {speedup_str} | {before_tcp} | {after_tcp} | {before_retries} | {after_retries} |")

    lines.append("")
    lines.append("## 通信効率比較")
    lines.append("")
    lines.append(f"| Metric | Before | After | Improvement |")
    lines.append(f"|--------|--------|-------|-------------|")
    total_tcp_before = before.total_tcp_roundtrips
    total_tcp_after = after.total_tcp_roundtrips
    lines.append(f"| TCP Round-trips | {total_tcp_before} | {total_tcp_after} | {(1 - total_tcp_after / max(total_tcp_before, 1)) * 100:.1f}% |")

    lines.append("")

    # Add before/after full details
    lines.append("## 最適化前 全指標")
    lines.append("")
    lines.append(format_full_metrics(before))
    lines.append("")
    lines.append("## 最適化後 全指標")
    lines.append("")
    lines.append(format_full_metrics(after))

    result = "\n".join(lines)
    (output_dir / "comparison.md").write_text(result, encoding="utf-8")
    return result


def format_full_metrics(report: BenchmarkReport) -> str:
    lines = [
        f"- 総時間: {report.total_elapsed_ms:.0f}ms ({report.total_elapsed_ms / 1000:.1f}s)",
        f"- TCP通信回数: {report.total_tcp_roundtrips}",
        f"- 全フェーズ成功/試行: {sum(p.actors_created for p in report.phases)}/{sum(p.actors_attempted for p in report.phases)}",
        f"- 総リトライ数: {sum(p.total_retries for p in report.phases)}",
        f"- 転送バイト数(送信/受信): {sum(p.total_bytes_sent for p in report.phases):,}/{sum(p.total_bytes_recv for p in report.phases):,}",
    ]
    return "\n".join(lines)
