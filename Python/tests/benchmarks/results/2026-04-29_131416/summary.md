# ベンチマーク: test_compare_with_baseline_20260429131419
実行時刻: 2026-04-29 13:14:19
総時間: 1667ms (1.7s)

## フェーズ別時間

| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |
|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|
| db_bulk_upsert | 34 | 0 | 1 | 6,488 | 11,412 | 0 | 16/16 | 100.0% |
| sync_plan | 279 | 0 | 1 | 43 | 35,385 | 0 | 0/0 | 100.0% |
| sync_apply | 700 | 0 | 1 | 111 | 9,267 | 0 | 16/16 | 100.0% |
| get_actors_verify | 299 | 0 | 0 | 0 | 0 | 0 | 16/16 | 100.0% |
| p7_commands | 17 | 3 | 0 | 625 | 655 | 0 | 0/0 | 100.0% |
| cleanup | 338 | 0 | 2 | 153 | 20,743 | 0 | 0/0 | 100.0% |

## TCP通信内訳

### p7_commands
| Command | Time (ms) | Bytes Sent | Bytes Recv | Retries | Error |
|---------|-----------|------------|------------|---------|-------|
| create_nav_mesh_volume | 8.0 | 148 | 258 | 0 |  |
| create_patrol_route | 1.0 | 275 | 320 | 0 |  |
| set_ai_behavior | 7.6 | 202 | 77 | 0 |  |

## 追加メトリクス

```json
{
  "plan_create_count": 16,
  "apply_result_summary": {
    "total": 67,
    "succeeded": 16,
    "failed": 0,
    "skipped": 51,
    "creates": 16,
    "update_transforms": 0,
    "update_visuals": 0,
    "deletes": 0,
    "noops": 0
  },
  "missing_actors_after_retry": []
}
```
