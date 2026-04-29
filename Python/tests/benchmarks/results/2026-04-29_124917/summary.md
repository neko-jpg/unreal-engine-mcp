# ベンチマーク: test_compare_with_baseline_20260429125051
実行時刻: 2026-04-29 12:50:51
総時間: 482ms (0.5s)

## フェーズ別時間

| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |
|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|
| db_bulk_upsert | 25 | 0 | 1 | 6,488 | 11,418 | 0 | 16/16 | 100.0% |
| sync_plan | 93 | 0 | 1 | 43 | 20,150 | 0 | 0/0 | 100.0% |
| sync_apply | 364 | 0 | 1 | 111 | 4,739 | 0 | 16/16 | 100.0% |
| get_actors_verify | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 100.0% |

## TCP通信内訳

## 追加メトリクス

```json
{
  "plan_create_count": 16,
  "apply_result_summary": {
    "total": 32,
    "succeeded": 16,
    "failed": 0,
    "skipped": 16,
    "creates": 16,
    "update_transforms": 0,
    "update_visuals": 0,
    "deletes": 0,
    "noops": 0
  }
}
```
