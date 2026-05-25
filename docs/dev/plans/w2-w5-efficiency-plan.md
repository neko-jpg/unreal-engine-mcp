# W2-W5 Efficiency Plan

> Created: 2026-05-23
> Context: W1 wave-close PR #113 is CI-green, awaiting user merge

---

## Phase 0: W1 Close-Out (今すぐ並行実行可能)

### 手動アクション (ユーザ依頼)
- [ ] PR #113 を merge

### 自動アクション (merge 後、即座に実行)
1. `gh issue comment 78 --body "Done"` + `gh issue close 78`
   - 内容: merged PRs (#106, #107, #111, #112, #113), handler count (51/51), live smoke result path
2. `gh issue edit 69` — umbrella body table の W1 行を tick
3. W2 part1 ブランチを即座に立ち上げ (次節参照)

---

## Phase 1: W2 Execution (目標: 2026-07-04)

### PR 分割計画 (54 stubs, 4 カテゴリ)

| PR | ブランチ名 | カテゴリ | Stubs | spike 要否 |
|---|---|---|---:|---|
| W2-1 | `codex/stubs-w2-datatable-part1` | DataTable #85 | 9 | 不要 (Engine only) |
| W2-2 | `codex/stubs-w2-sequencer-part1` | Sequencer #87 | 6 | 不要 |
| W2-3 | `codex/stubs-w2-gas-part1` | GAS #86 | 8 of 16 | 不要 |
| W2-4 | `codex/stubs-w2-gas-part2` | GAS #86 | 8 of 16 | 不要 |
| W2-5 | `codex/stubs-w2-ai-nav-part1` | AI/Nav #84 | 8 of 23 | **必須** |
| W2-6 | `codex/stubs-w2-ai-nav-part2` | AI/Nav #84 | 8 of 23 | (spike 継続) |
| W2-7 | `codex/stubs-w2-ai-nav-part3` | AI/Nav #84 | 7 of 23 | (spike 継続) |
| W2-close | `codex/wave2-close` | wave close | — | — |

### 並行戦略

```
Week 1 (5/24 - 5/30):
  Worker A: DataTable #85 (9 stubs) → 1 PR
  Worker B: Sequencer #87 (6 stubs) → 1 PR
  spike:    AI/Nav #84 spike doc (docs/spike/ai-nav-ue57.md)

Week 2 (5/31 - 6/6):
  Worker A: GAS #86 part1 (8 stubs)
  Worker B: GAS #86 part2 (8 stubs)
  spike:    AI/Nav spike 完了確認

Week 3-4 (6/7 - 6/20):
  Worker A: AI/Nav #84 part1 (8 stubs)
  Worker B: AI/Nav #84 part2 (8 stubs)
  Worker A: AI/Nav #84 part3 (7 stubs)

Week 5 (6/21 - 7/4):
  buffer + wave-close PR
```

### 効率化ポイント
- DataTable + Sequencer は spike 不要、week 1 から即着手
- GAS は spike 不要だが 16 stubs なので 2 PR 分割
- AI/Nav は spike 必須 → spike 完了を待ってから part1 着手
- part1 はすべて base=main 直 (stacked PR は避ける)

---

## Phase 2: W3 Execution (目標: 2026-07-18, 74 stubs)

| PR | カテゴリ | Stubs | spike |
|---|---|---:|---|
| W3-1 | Foliage #90 | 8 of 20 | 不要 |
| W3-2 | Foliage #90 | 8 of 20 | — |
| W3-3 | Foliage #90 | 4 of 20 | — |
| W3-4 | Water #92 | 8 of 15 | 不要 |
| W3-5 | Water #92 | 7 of 15 | — |
| W3-6 | Chaos #89 | 8 of 19 | **必須** |
| W3-7 | Chaos #89 | 8 of 19 | — |
| W3-8 | Chaos #89 | 3 of 19 | — |
| W3-9 | PCG #91 | 8 of 20 | **必須** |
| W3-10 | PCG #91 | 8 of 20 | — |
| W3-11 | PCG #91 | 4 of 20 | — |

spike 並行: W2 実装中に Chaos + PCG の spike doc を先行着手

---

## Phase 3: W4 Execution (目標: 2026-08-01, 65 stubs)

| PR | カテゴリ | Stubs | spike |
|---|---|---:|---|
| W4-1 | Localization #94 | 8 of 10 | 不要 |
| W4-2 | Localization #94 | 2 of 10 | — |
| W4-3 | Source Control #97 | 8 of 13 | 不要 |
| W4-4 | Source Control #97 | 5 of 13 | — |
| W4-5 | MRQ #95 | 8 of 21 | **必須** |
| W4-6 | MRQ #95 | 8 of 21 | — |
| W4-7 | MRQ #95 | 5 of 21 | — |
| W4-8 | Networking #96 | 8 of 21 | **必須** |
| W4-9 | Networking #96 | 8 of 21 | — |
| W4-10 | Networking #96 | 5 of 21 | — |

---

## Phase 4: W5 Execution (目標: 2026-08-08, 31 stubs)

| PR | カテゴリ | Stubs | spike |
|---|---|---:|---|
| W5-1 | MetaSound #99 | 7 | **必須** |
| W5-2 | Mobile/XR #100 | 8 of 14 | 不要 |
| W5-3 | Mobile/XR #100 | 6 of 14 | — |
| W5-4 | Testing/Validation #101 | 8 of 10 | 不要 |
| W5-5 | Testing/Validation #101 | 2 of 10 | — |

---

## Spike Doc 先行スケジュール

spike は実装 PR より **最低 2 週間前** に着手。

| spike doc | 着手時期 | 対応 wave |
|---|---|---|
| `ai-nav-ue57.md` | W2 Week 1 (5/24) | W2 |
| `chaos-ue57.md` | W2 Week 2 (5/31) | W3 |
| `pcg-ue57.md` | W2 Week 3 (6/7) | W3 |
| `movie-render-queue-ue57.md` | W3 Week 1 (6/21) | W4 |
| `networking-iris-ue57.md` | W3 Week 1 (6/21) | W4 |
| `metasound-ue57.md` | W4 Week 1 (7/5) | W5 |

---

## 全体タイムライン

```
5/23  PR #113 merge → W1 close-out → W2 part1 立ち上げ
5/24  DataTable + Sequencer 着手 (spike 不要カテゴリ)
5/31  GAS part1+part2 着手、AI/Nav spike 継続
6/7   AI/Nav part1 着手 (spike 完了前提)
6/21  W2 wave-close PR、W3 part1 着手 (Foliage + Water)
7/4   W2 merge deadline、Chaos/PCG spike 完了
7/18  W3 merge deadline、W4 part1 着手
8/1   W4 merge deadline、W5 part1 着手
8/8   W5 merge deadline
8/10  umbrella #69 close
```

---

## 効率化のコツ (W1 からの教訓)

1. **spike 不要カテゴリから着手** — 即座にコードを書ける (DataTable, Sequencer, Foliage, Water, Localization, Source Control, Mobile/XR, Testing)
2. **PR は最大 8 handlers** — レビュー負荷とコンフリクトリスクのバランス
3. **base=main 直** — stacked PR は squash-merge 後のコンフリクトが面倒
4. **shared files は触らない** — Router.cpp, Bridge.cpp, CHANGELOG.md, queued_baseline.json は wave-close PR でまとめて更新
5. **spike は先行** — 実装開始前に `docs/spike/` に UE 5.7 調査結果を書く
6. **ローカル検証は毎 PR** — `pytest`, `audit_route_contracts.py --strict`, `audit_no_new_queued.py` を PR 前に必ず実行
7. **CHANGELOG fragment** — 各カテゴリ PR は `CHANGELOG.d/` に fragment を書き、wave-close で集約
