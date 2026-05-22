# BB逆張り戦略 バックテスト設計書

**作成日**: 2026-05-22
**スコープ**: スタンドアロン調査スクリプト（既存生産コードへの変更なし）

---

## 概要

ボリンジャーバンド（BB）逆張り戦略の有効性を検証するスタンドアロンバックテストスクリプトを実装する。
既存のマルチファクター・モメンタム戦略（Group I/J）とは独立した調査として実施し、
`generate_signals()` には一切手を加えない。

---

## 1. ファイル構成

| 操作 | パス | 役割 |
|------|------|------|
| 新規作成 | `backtest/backtest_improvement_plan/run_bb_reversal.py` | メイン調査スクリプト |

既存コードへの変更: **なし**

---

## 2. 実行フロー

```
1. DuckDB 接続（既存 DB をそのまま使用）
2. トレーディング日を market_calendar から取得
3. 各シナリオ × 各日付をループ:
   a. DuckDB SQL ウィンドウ関数で全銘柄のBB値を一括計算
   b. BUY/SELL 条件を評価してシグナルを生成
   c. signals テーブルへ書き込み（日付単位で冪等）
4. 既存 Simulator クラスをインポートして実行
5. BacktestMetrics で結果を集計
6. コンソール出力 + CSV 保存
```

---

## 3. BB計算仕様

DuckDB SQLウィンドウ関数で計算（ルックアヘッドバイアスなし）:

```sql
middle_band = AVG(close) OVER (PARTITION BY code ORDER BY date ROWS (N-1) PRECEDING)
std         = STDDEV_POP(close) OVER (PARTITION BY code ORDER BY date ROWS (N-1) PRECEDING)
lower_band  = middle_band - k * std
upper_band  = middle_band + k * std
```

- N日分の履歴が不足する銘柄・日付はスキップ
- `std = 0`（価格変動なし）の銘柄はスキップ

---

## 4. シグナルロジック

### エントリー（BUY）
| 条件 | 詳細 |
|------|------|
| BB下抜け | `close < lower_band` |
| 未保有 | 同銘柄のポジションを保有していない |
| Regimeフィルター（optional） | `bear` レジームまたは `breadth_stop=True` の日は BUY 抑制 |

### エグジット（SELL） — 優先順位順
| 優先度 | 条件 | トリガー |
|--------|------|---------|
| 1 | 損切り | `pnl_rate <= -8%` |
| 2 | 時間決済 | 保有営業日数 >= `max_holding_days`（デフォルト20日） |
| 3 | 利確 | `close >= middle_band`（中心線回帰） |

---

## 5. 検証シナリオ

全シナリオ共通設定:
- `stop_loss = -8%`
- `max_holding_days = 20`
- バックテスト期間: 2017-01-01 〜 2025-12-31（Group I/J と同期間）
- 初期資金: 10,000,000 円

| シナリオID | period | sigma | regime_filter | 目的 |
|-----------|--------|-------|---------------|------|
| BB1_base | 20 | 2.0 | OFF | ベースライン |
| BB2_tight | 20 | 1.5 | OFF | タイトバンド（シグナル増） |
| BB3_wide | 20 | 2.5 | OFF | ワイドバンド（シグナル減） |
| BB4_base_regime | 20 | 2.0 | ON | Regimeフィルターの有無比較 |
| BB5_tight_regime | 20 | 1.5 | ON | タイト + Regime複合 |

---

## 6. ポジション管理・資金管理

| パラメータ | 値 | 理由 |
|-----------|-----|------|
| `max_positions` | 5 | BB逆張りはシグナル頻度が高いため分散 |
| `allocation_method` | `equal` | BBにはスコアランクがなく均等配分が自然 |
| `max_position_pct` | 0.20 | 1銘柄あたり資産の20%上限 |
| `max_utilization` | 0.70 | 既存戦略と統一 |
| `commission` | 0.00055 | 既存戦略と統一 |
| `slippage` | 0.001 | 既存戦略と統一 |

---

## 7. ユニバース

既存の `features` テーブルに登録されている銘柄を使用（株価 ≥ 300円・売買代金 ≥ 5億円フィルター済み）。
BB計算に必要な history（N日分）が不足する銘柄は自動除外。

---

## 8. 出力

### コンソール（テーブル形式）
```
scenario              CAGR    Sharpe   MaxDD   WinRate  Trades
BB1_base             +5.2%    0.41   -18.3%    52.1%     312
BB2_tight            +6.8%    0.48   -21.0%    49.8%     487
BB3_wide             +3.1%    0.29   -14.2%    55.3%     198
BB4_base_regime      +4.8%    0.51   -13.7%    53.6%     245
BB5_tight_regime     +6.1%    0.55   -16.8%    51.2%     381
```

### CSVファイル
`artifacts/bb_reversal_YYYYMMDD_HHMMSS.csv`（全シナリオの全指標を列として保存）

---

## 9. 採択基準

以下をすべて満たすシナリオが存在する場合 → BB戦略の本格設計（Approach B）へ移行を検討:
- `CAGR > 5%`
- `Max DD < 25%`
- `Sharpe > 0.40`
- `WinRate > 48%`

いずれも満たさない場合 → BB逆張りは現時点での採用を見送り、結果を記録して終了。

---

## 10. 制約・注意事項

- **ルックアヘッドバイアス禁止**: BB計算は `date <= target_date` のデータのみ使用（ウィンドウ関数で自動保証）
- **冪等性**: `signals` テーブルへの書き込みは日付単位の DELETE → INSERT で冪等
- **Regime判定**: `market_breadth.breadth_stop` と `ai_scores` テーブルの既存データを参照
- **生産コード非改変**: `generate_signals()` / `feature_engineering.py` に変更を加えない
