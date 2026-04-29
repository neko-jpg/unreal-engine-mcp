# ベンチマーク: test_compare_with_baseline_20260429143426
実行時刻: 2026-04-29 14:34:26
総時間: 1147ms (1.1s)

## フェーズ別時間

| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |
|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|
| db_bulk_upsert | 26 | 0 | 1 | 6,488 | 11,415 | 0 | 16/16 | 100.0% |
| sync_plan | 120 | 0 | 1 | 43 | 13,574 | 0 | 0/0 | 100.0% |
| sync_apply | 368 | 0 | 1 | 111 | 2,666 | 0 | 16/16 | 100.0% |
| get_actors_verify | 298 | 0 | 0 | 0 | 0 | 0 | 16/16 | 100.0% |
| p7_commands | 20 | 3 | 0 | 625 | 655 | 0 | 0/0 | 100.0% |
| cleanup | 315 | 0 | 2 | 153 | 14,145 | 0 | 0/0 | 100.0% |

## TCP通信内訳

### p7_commands
| Command | Time (ms) | Bytes Sent | Bytes Recv | Retries | Error |
|---------|-----------|------------|------------|---------|-------|
| create_nav_mesh_volume | 9.8 | 148 | 258 | 0 |  |
| create_patrol_route | 1.0 | 275 | 320 | 0 |  |
| set_ai_behavior | 9.1 | 202 | 77 | 0 |  |

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
