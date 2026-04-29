# ベンチマーク: test_compare_with_baseline_20260429135559
実行時刻: 2026-04-29 13:55:59
総時間: 922ms (0.9s)

## フェーズ別時間

| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |
|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|
| db_bulk_upsert | 35 | 0 | 1 | 6,488 | 11,415 | 0 | 16/16 | 100.0% |
| sync_plan | 126 | 0 | 1 | 43 | 13,574 | 0 | 0/0 | 100.0% |
| sync_apply | 370 | 0 | 1 | 111 | 2,666 | 0 | 16/16 | 100.0% |
| get_actors_verify | 296 | 0 | 0 | 0 | 0 | 0 | 16/16 | 100.0% |
| p7_commands | 11 | 3 | 0 | 625 | 655 | 0 | 0/0 | 100.0% |
| cleanup | 84 | 0 | 2 | 153 | 14,145 | 0 | 0/0 | 100.0% |

## TCP通信内訳

### p7_commands
| Command | Time (ms) | Bytes Sent | Bytes Recv | Retries | Error |
|---------|-----------|------------|------------|---------|-------|
| create_nav_mesh_volume | 9.1 | 148 | 258 | 0 |  |
| create_patrol_route | 1.3 | 275 | 320 | 0 |  |
| set_ai_behavior | 0.5 | 202 | 77 | 0 |  |

## 追加メトリクス

```json
{
  "plan_create_count": 16,
  "apply_result_summary": {
    "total": 16,
    "succeeded": 16,
    "failed": 0,
    "skipped": 0,
    "creates": 16,
    "update_transforms": 0,
    "update_visuals": 0,
    "deletes": 0,
    "noops": 0
  },
  "missing_actors_after_retry": []
}
```
