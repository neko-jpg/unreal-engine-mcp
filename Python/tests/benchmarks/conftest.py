"""Benchmark fixtures.

All benchmarks REQUIRE all three services:
    - SurrealDB on ws://127.0.0.1:8000
    - scene-syncd on http://127.0.0.1:8787
    - Unreal Editor with MCP Bridge on 127.0.0.1:55557

If any service is unavailable, benchmarks are SKIPPED.
"""

import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from .bench_metrics import MetricsCollector, BenchmarkReport, build_comparison_markdown

SCENE_SYNCD_URL = "http://127.0.0.1:8787"
UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557
RESULTS_DIR = Path(__file__).parent / "results"


# --- Persistent TCP connection for unreal_command ---
_unreal_socket: socket.socket | None = None


def unreal_command(command: str, params: dict | None = None) -> dict:
    """Send command to Unreal via persistent TCP connection.

    Reuses the module-level socket across calls for benchmark accuracy.
    Falls back to new connection on failure.
    """
    global _unreal_socket
    payload = json.dumps({"command": command, "params": params or {}}).encode("utf-8") + b"\n"
    last_error = None

    for attempt in range(3):
        try:
            if _unreal_socket is None:
                _unreal_socket = socket.create_connection((UNREAL_HOST, UNREAL_PORT), timeout=10)
                _unreal_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                _unreal_socket.settimeout(30)

            _unreal_socket.sendall(payload)
            data = bytearray()
            while b"\n" not in data:
                chunk = _unreal_socket.recv(262144)
                if not chunk:
                    raise ConnectionError("Unreal connection closed")
                data.extend(chunk)
            return json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, ConnectionError, OSError, socket.timeout) as exc:
            last_error = exc
            # Close and reconnect
            try:
                _unreal_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                _unreal_socket.close()
            except OSError:
                pass
            _unreal_socket = None
            if attempt == 2:
                break
            time.sleep(0.5 * (attempt + 1))

    if last_error is None:
        last_error = RuntimeError(f"Unreal command '{command}' failed after 3 attempts")
    raise last_error


def unreal_command_timed(metrics: MetricsCollector, command: str, params: dict | None = None, expected_retries: int = 0) -> dict:
    """Send a timed unreal command, recording metrics."""
    payload_bytes = json.dumps({"command": command, "params": params or {}}).encode("utf-8") + b"\n"
    t0 = time.perf_counter()
    retries = 0
    last_error = None

    for attempt in range(3):
        retries = attempt
        try:
            result = unreal_command(command, params)
            elapsed = (time.perf_counter() - t0) * 1000
            resp_str = json.dumps(result)
            metrics.record_tcp_call(
                command, elapsed,
                len(payload_bytes), len(resp_str.encode("utf-8")),
                retries=retries
            )
            return result
        except Exception as e:
            last_error = e
            # unreal_command already handles reconnect internally
            pass

    elapsed = (time.perf_counter() - t0) * 1000
    error_type = type(last_error).__name__ if last_error else "unknown"
    metrics.record_tcp_call(command, elapsed, len(payload_bytes), 0, retries=retries, error_type=error_type)
    raise last_error or RuntimeError(f"Timed command '{command}' failed")


def close_unreal_connection():
    """Explicitly close the persistent Unreal connection."""
    global _unreal_socket
    if _unreal_socket is not None:
        try:
            _unreal_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            _unreal_socket.close()
        except OSError:
            pass
        _unreal_socket = None


# --- HTTP helpers (timed versions) ---

def api_post(metrics: MetricsCollector | None, path: str, payload: dict) -> dict:
    url = f"{SCENE_SYNCD_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            if metrics:
                elapsed = (time.perf_counter() - t0) * 1000
                metrics.record_http_call(path, elapsed, len(data), len(json.dumps(resp_data).encode("utf-8")))
            return resp_data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if metrics:
            metrics.record_http_call(path, (time.perf_counter() - t0) * 1000, len(data), 0)
        raise RuntimeError(f"HTTP {e.code} on {path}: {body}") from e


def api_get(metrics: MetricsCollector | None, path: str) -> dict:
    url = f"{SCENE_SYNCD_URL}{path}"
    t0 = time.perf_counter()
    with urllib.request.urlopen(url, timeout=10) as resp:
        resp_bytes = resp.read().decode("utf-8")
        result = json.loads(resp_bytes)
        if metrics:
            elapsed = (time.perf_counter() - t0) * 1000
            metrics.record_http_call(path, elapsed, 0, len(resp_bytes.encode("utf-8")))
        return result


def api_post_simple(path: str, payload: dict) -> dict:
    """Non-timed POST for setup/teardown."""
    return api_post(None, path, payload)


def api_get_simple(path: str) -> dict:
    """Non-timed GET for setup/teardown."""
    return api_get(None, path)


def assert_success(response: dict, context: str) -> dict:
    if not response.get("success"):
        raise AssertionError(f"{context} failed: {response.get('error', response)}")
    return response.get("data", {})


# --- Fixtures ---

@pytest.fixture(scope="session")
def all_services_available():
    """Verify all three services are reachable. Cache for session."""
    issues = []
    # scene-syncd health
    try:
        api_get_simple("/health")
    except Exception as e:
        issues.append(f"scene-syncd: {e}")

    # Unreal TCP bridge
    try:
        s = socket.create_connection((UNREAL_HOST, UNREAL_PORT), timeout=5)
        s.close()
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        issues.append(f"Unreal bridge: {e}")

    if issues:
        return False, issues
    return True, []


@pytest.fixture(scope="session")
def benchmark_dir():
    """Create and return the benchmark results directory for this session."""
    ts = time.strftime("%Y-%m-%d_%H%M%S")
    d = RESULTS_DIR / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def metrics(benchmark_dir, request):
    """Create a MetricsCollector for a single benchmark run.

    The collector is automatically saved to the results directory after the test,
    regardless of pass/fail.
    """
    suffix = time.strftime("%Y%m%d%H%M%S")
    run_id = f"{request.node.name}_{suffix}"
    collector = MetricsCollector(run_id=run_id, timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))
    yield collector
    try:
        collector.save(benchmark_dir)
    except Exception:
        pass


def load_previous_report(exclude_run_id: str | None = None) -> BenchmarkReport | None:
    """Load the most recent benchmark report, optionally excluding a specific run_id."""
    return load_latest_report(exclude_run_id)


def load_latest_report(exclude_run_id: str | None = None) -> BenchmarkReport | None:
    """Load the most recent benchmark report from results directory."""
    if not RESULTS_DIR.exists():
        return None
    dirs = sorted(RESULTS_DIR.iterdir(), reverse=True)
    for d in dirs:
        metrics_file = d / "metrics.json"
        if metrics_file.exists():
            data = json.loads(metrics_file.read_text(encoding="utf-8"))
            if exclude_run_id and data.get("run_id") == exclude_run_id:
                continue
            report = BenchmarkReport(run_id=data["run_id"], timestamp=data["timestamp"])
            from .bench_metrics import PhaseRecord, TcpCallRecord
            for pdata in data.get("phases", []):
                phase = PhaseRecord(name=pdata["name"], start_time=0.0, end_time=pdata["elapsed_ms"] / 1000.0)
                phase.actors_created = pdata.get("actors_created", 0)
                phase.actors_attempted = pdata.get("actors_attempted", 0)
                phase.error_types = pdata.get("error_types", [])
                for tc in pdata.get("tcp_commands", []):
                    phase.tcp_calls.append(TcpCallRecord(
                        command=tc["cmd"], elapsed_ms=tc["ms"],
                        bytes_sent=tc.get("bytes_sent", 0), bytes_recv=tc.get("bytes_recv", 0),
                        retries=tc.get("retries", 0), error_type=tc.get("error"),
                    ))
                report.phases.append(phase)
            return report
    return None
