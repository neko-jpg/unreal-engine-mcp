# ベンチマーク: test_compare_with_baseline_20260429135232
実行時刻: 2026-04-29 13:52:32
総時間: 1309ms (1.3s)

## フェーズ別時間

| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |
|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|
| db_bulk_upsert | 33 | 0 | 1 | 6,488 | 11,418 | 0 | 16/16 | 100.0% |
| sync_plan | 229 | 0 | 1 | 43 | 49,933 | 0 | 0/0 | 100.0% |
| sync_apply | 455 | 0 | 1 | 111 | 13,668 | 0 | 16/16 | 100.0% |
| get_actors_verify | 214 | 0 | 0 | 0 | 0 | 0 | 16/16 | 100.0% |
| p7_commands | 40 | 3 | 0 | 625 | 655 | 0 | 0/0 | 100.0% |
| cleanup | 338 | 0 | 2 | 153 | 25,150 | 0 | 0/0 | 100.0% |

## TCP通信内訳

### p7_commands
| Command | Time (ms) | Bytes Sent | Bytes Recv | Retries | Error |
|---------|-----------|------------|------------|---------|-------|
| create_nav_mesh_volume | 19.9 | 148 | 258 | 0 |  |
| create_patrol_route | 3.2 | 275 | 320 | 0 |  |
| set_ai_behavior | 16.2 | 202 | 77 | 0 |  |

## 追加メトリクス

```json
{
  "plan_create_count": 16,
  "apply_result_summary": {
    "total": 101,
    "succeeded": 16,
    "failed": 0,
    "skipped": 85,
    "creates": 16,
    "update_transforms": 0,
    "update_visuals": 0,
    "deletes": 0,
    "noops": 0
  },
  "missing_actors_after_retry": []
}
```
