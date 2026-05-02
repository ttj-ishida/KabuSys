# トレーリングストップ実装設計 (Issue #182)

## 概要

`_generate_sell_signals()` に ATR×2 ベースのトレーリングストップを追加する。
直近最高値から 2×ATR を超えて下落した場合に `reason=trailing_stop` の SELL シグナルを発動し、含み益を保護する。

## 設計方針

### 発動条件

```
close < peak_close − trailing_stop_atr × ATR_20d
```

| 変数 | 定義 |
|------|------|
| `peak_close` | エントリー日〜target_date の `MAX(close)`（`position_entries` + `prices_daily` から都度計算） |
| `ATR_20d` | 直近20日の Average True Range（`prices_daily` の high/low/close から算出） |
| `trailing_stop_atr` | ATR 乗数。デフォルト `2.0`（`--trailing-stop-atr` CLI 引数で変更可） |

### ATR 計算式

True Range (TR) = `MAX(high − low, |high − prev_close|, |low − prev_close|)`

ATR_20d = 直近20日分の TR の単純平均（先頭行は prev_close が NULL のため除外）

### 適用条件（含み益ありのときのみ）

`peak_close > avg_price` のときのみ発動する。
未入益のポジションはストップロス（-8%）に委ねるため、trailing_stop は発動しない。

ATR や peak_close が算出不能（データ不足）の場合はスキップする。

### SELL 優先順序

既存の優先順序を維持し、trailing_stop を time_exit の前に挿入する。

```
1. stop_loss          （最優先、即時 SELL）
2. earnings_avoidance （決算前強制 SELL）
3. trailing_stop      （含み益保護、今回追加）
4. time_exit          （最大保有期間）
5. min_holding_days   （最低保有日数チェック、上記4件はバイパス）
6. score_drop         （スコア低下）
```

trailing_stop は time_exit と同様に `min_holding_days` チェックをバイパスする（利益保護を最低保有日数より優先）。

Bear レジームでも trailing_stop は発動する。

## StrategyModel.md との整合

StrategyModel.md Section 5.2 では「直近の最高値から -10%（固定）」と記載されていたが、
RiskManagement.md Section 5.2 の「最高値 − ATR×2」を採用する。
ATR ベースのほうが銘柄ボラティリティに適応的であり、高ボラ銘柄の誤発動と低ボラ銘柄の遅延反応を同時に抑制できるため。

StrategyModel.md の記述は本実装後に更新する（別 PR）。

## 変更ファイル

### `src/kabusys/strategy/signal_generator.py`

- `_TRAILING_STOP_ATR_MULT: float = 2.0` 定数を追加
- `_atr_20d(conn, code, target_date) -> float | None` ヘルパーを追加
  - `prices_daily` から直近20日分の ATR を計算して返す
  - データ不足（20日未満）の場合は `None`
- `_peak_close(conn, code, target_date) -> float | None` ヘルパーを追加
  - `position_entries` と `prices_daily` を JOIN し、最も古いオープンエントリー日以降の `MAX(close)` を返す
  - エントリーが存在しない場合は `None`
- `_generate_sell_signals()` に `trailing_stop_atr: float = _TRAILING_STOP_ATR_MULT` パラメータを追加
  - earnings_avoidance ブロックの直後に trailing_stop チェックを追加
- `generate_signals()` に `trailing_stop_atr: float = _TRAILING_STOP_ATR_MULT` パラメータを追加
  - バリデーション: `trailing_stop_atr <= 0` のとき `ValueError`
  - `_generate_sell_signals()` 呼び出しに `trailing_stop_atr=trailing_stop_atr` を追加

### `src/kabusys/backtest/engine.py`

- `run_backtest()` に `trailing_stop_atr: float = 2.0` パラメータを追加
- バリデーション: `trailing_stop_atr <= 0` のとき `ValueError`
- `generate_signals()` 呼び出しに `trailing_stop_atr=trailing_stop_atr` を追加

### `src/kabusys/backtest/run.py`

- `--trailing-stop-atr` CLI 引数を追加（type=float, default=2.0）
- `run_backtest()` 呼び出しに `trailing_stop_atr=args.trailing_stop_atr` を追加
- `build_report()` 呼び出しに `trailing_stop_atr=args.trailing_stop_atr` を追加

### `src/kabusys/backtest/report.py`

- `ReportMeta` に `trailing_stop_atr: float = 2.0` フィールドを追加
- `build_report()` シグネチャに `trailing_stop_atr: float = 2.0` を追加
- `format_markdown()` の設定テーブルに `| Trailing Stop ATR | {m.trailing_stop_atr} |` を追加

### `tests/test_trailing_stop.py`（新規）

- `TestAtr20d`: 既知の価格列で ATR が正しく計算されること
- `TestPeakClose`: エントリー日以降の `MAX(close)` が返ること
- `TestTrailingStopFires`: 発動条件（`close < peak - atr_mult × ATR`）を満たすとき SELL が発生すること
- `TestTrailingStopSuppressed`: 発動条件を満たさないとき SELL が発生しないこと
- `TestTrailingStopNoProfitNoFire`: `peak_close <= avg_price` のとき発動しないこと
- `TestTrailingStopBypassesMinHolding`: `min_holding_days` 未満でも trailing_stop が発動すること
- `TestTrailingStopInBearRegime`: Bear レジームでも発動すること
- `TestTrailingStopValidation`: `trailing_stop_atr <= 0` で `ValueError`
- `TestTrailingStopDefault`: シグネチャ・デフォルト値検証

## パラメータ一覧

| パラメータ | デフォルト | CLI | 説明 |
|-----------|-----------|-----|------|
| `trailing_stop_atr` | `2.0` | `--trailing-stop-atr` | ATR 乗数。`peak_close − N×ATR` を下回ったら SELL |

## 設計上の決定事項

1. **peak_close は都度計算**: `position_entries.entry_date` と `prices_daily` を JOIN して算出。`positions` テーブルへのカラム追加・マイグレーション不要。
2. **含み益フィルタ**: `peak_close > avg_price` のときのみ発動。stop_loss との役割を分離。
3. **ATR×2 採用**: `volatility_20` は Z スコアであり使用不可。`prices_daily` から raw ATR を計算。
4. **スキーマ変更なし**: `positions` テーブルは現状のまま変更しない。
