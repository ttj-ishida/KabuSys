# Phase 2 Group U — market_calendar 修正 + S2+T4 複合検証 設計仕様

**作成**: 2026-06-03  
**関連 Issue**: #380（新規）  
**前提**: Phase2_Backtest_Strategy.md Section 50（Group T）の分析結果

---

## 背景

Group T バックテスト（2026-06-02）で T4（quality_score_min=-0.30）および T5/T6 の MaxDD が 33〜95% と異常に過大計上された。原因調査の結果、`market_calendar` で `is_trading_day=True` となっている 2020-10-01（東証システム障害・全日取引停止）に対して `prices_daily` のデータが完全欠損しており、バックテストエンジンがポジション時価をゼロと評価する擬似ドローダウンを生じさせていることが判明した。

また、Group T 結果からセクターフィルター（T1〜T3）は 2018 年モメンタム相場を構造的に取りこぼすため不採択と判断。クオリティフィルター（T4）は修正 MaxDD で 20.47% と有望であり、Group S 採択パラメータ（S2: 3 値レジーム）との複合効果を検証する必要がある。

---

## 目標

1. `market_calendar` の 2020-10-01 を `is_trading_day=False` に修正し、バックテストの擬似 MaxDD を解消する
2. 修正後の環境で T4（クオリティフィルター単体）・S2（3 値レジーム単体）・S2+T4 複合の効果を 1 回のバックテストで比較検証する
3. Phase 2 採択基準（CAGR>8%、Sharpe>0.5、MaxDD<25%、PF>1.1）を達成するシナリオを特定する

---

## 設計

### Step 1: market_calendar 修正スクリプト

`backtest/backtest_improvement_plan/fix_market_calendar_20201001.py` として実装。

- 対象 DB: `.env` の `DUCKDB_PATH` から取得
- 実行内容: `UPDATE market_calendar SET is_trading_day=false WHERE date='2020-10-01'`
- 冪等: 既に False の場合も安全に実行可能
- 確認: 修正前後の状態を標準出力に表示

### Step 2: run_phase2_group_u.py

`backtest/backtest_improvement_plan/run_phase2_group_u.py` として実装。  
`run_phase2_group_t.py` のパターンに準拠（並列実行・decision.json 出力）。

#### シナリオ定義

| シナリオ | 施策A モード | vol_low | vol_high | thr_hi | thr_lo | quality_min | 目的 |
|---------|------------|---------|---------|--------|--------|-------------|------|
| U0_ref | 2 値現行 | 0.12 | None | 0.62 | — | None | 修正後ベースライン |
| U1_t4 | 2 値現行 | 0.12 | None | 0.62 | — | −0.30 | クオリティ単体効果（T4 修正版） |
| U2_s2 | 3 値 S2 | 0.10 | 0.20 | 0.63 | 0.55 | None | S2 単体の再確認 |
| U3_s2t4 | 3 値 S2 | 0.10 | 0.20 | 0.63 | 0.55 | −0.30 | S2 + クオリティ複合（最終候補） |

#### 固定ベース設定（R3 + 施策B）

| パラメータ | 値 |
|-----------|---|
| max_positions | 7 |
| max_utilization | 40% |
| max_position_pct | 22% |
| risk_pct | 0.5% |
| stop_loss_pct | 9% |
| trailing_stop_atr | 2.0 |
| dd_stop | 12%（30 日タイムアウト） |
| dynamic_trailing_stop | ON（gate=1.5, s2=1.8, s3=1.5） |
| ma200_filter | ON |
| period | 2017-01-01 〜 2025-12-31 |

#### 採択基準

| 指標 | 基準 | 根拠 |
|------|------|------|
| CAGR | > 8% | Phase 2 最低ライン |
| Sharpe | > **0.5** | Phase 2 主目標 |
| MaxDD | < 25% | Phase 1 実績内 |
| PF | > 1.1 | Phase 1 基準維持 |

#### 採択判断ロジック

```
いずれかのシナリオで 4 指標同時達成 → ADOPTED（Phase2_Backtest_Strategy.md Section 51 に記録）
Sharpe が U0 を上回るが Sharpe 0.5 未達 → IMPROVED（最良シナリオを Phase 2 ベースとして採用）
全シナリオで U0 以下 → NO_IMPROVEMENT
```

### Phase2_Backtest_Strategy.md への反映

- market_calendar 修正の説明を Section 50（8.7.7）に追記
- Group U の設計・結果を新規 Section 51（`## 9. Section 51 — Group U`）として追加
- 既存 Section 9〜10 の番号を繰り下げ

---

## ファイルマップ

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `backtest/backtest_improvement_plan/fix_market_calendar_20201001.py` | 新規 | market_calendar 修正スクリプト |
| `backtest/backtest_improvement_plan/run_phase2_group_u.py` | 新規 | 4 シナリオ並列バックテストスクリプト |
| `documents/07_Research/Phase2_Backtest_Strategy.md` | 修正 | Section 51 追加・既存 Section 9〜10 番号繰り下げ |

---

## 自己レビュー

- シナリオ数（4）は適切。単体効果の分離と複合効果の確認が 1 ランで完結する。
- `topix_vol_high_threshold=None` の 2 値モード後方互換は既実装済み（Issue #376）。
- `quality_score_min` / `--quality-score-min` は既実装済み（Issue #379）。
- 追加実装は修正スクリプト 1 本 + バックテストスクリプト 1 本のみ。実装コスト低。
- IS 参照値として R3 単体（CAGR 9.01%、Sharpe 0.445、MaxDD 26.87%、PF 1.402）を使用。
