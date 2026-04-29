# ベンチマーク: test_compare_with_baseline_20260429141718
実行時刻: 2026-04-29 14:17:18
総時間: 67ms (0.1s)

## フェーズ別時間

| Phase | Time (ms) | TCP Calls | HTTP Calls | Bytes Sent | Bytes Recv | Retries | Actors | Success Rate |
|-------|-----------|-----------|------------|------------|------------|---------|--------|-------------|
| db_bulk_upsert | 19 | 0 | 1 | 6,488 | 11,412 | 0 | 16/16 | 100.0% |
| sync_plan | 6 | 0 | 1 | 43 | 13,571 | 0 | 0/0 | 100.0% |
| sync_apply | 41 | 0 | 1 | 111 | 6,225 | 0 | 0/16 | 0.0% |

## TCP通信内訳

## 追加メトリクス

```json
{
  "plan_create_count": 16,
  "apply_result_summary": {
    "total": 16,
    "succeeded": 0,
    "failed": 16,
    "skipped": 0,
    "creates": 0,
    "update_transforms": 0,
    "update_visuals": 0,
    "deletes": 0,
    "noops": 0
  }
}
```
