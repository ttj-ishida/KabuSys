# Group O 施策B: 多段階・時間減衰型トレーリングストップ 設計書

**目的:** I1 の Sharpe 改善。トレンド初期は利益を伸ばしつつ、含み益が一定水準に達した後や保有が長期化した局面ではストップをタイトにして利益吐き出しと含み損塩漬けを防ぐ。

**背景:**
- I1 の Sharpe 0.382 の主因は年次リターンの偏り（2018/2024 集中）と他年のフラット/マイナス
- 現行のトレーリングストップは ATR 乗数 2.0 固定。保有 30 日超の停滞ポジションにも同じ基準が適用される
- Group N 施策A（N1b_vol12_hi62）は Sharpe +0.038 にとどまり採用基準（>0.5）未達
- 施策B では利益吐き出しの防止（Stage 2）と長期塩漬けの防止（Stage 3）を段階的に実現する

---

## 1. アーキテクチャ

### 1.1 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `src/kabusys/strategy/signal_generator.py` | 変更 | `_generate_sell_signals()` の trailing stop ブロックを拡張 |
| `src/kabusys/backtest/engine.py` | 変更 | `run_backtest()` に新パラメータ追加、`generate_signals()` 呼び出しに転送 |
| `src/kabusys/backtest/run.py` | 変更 | CLI フラグ 4 本追加 |
| `backtest/backtest_improvement_plan/run_phase1_group_o.py` | 新規 | Group O バックテスト実行スクリプト |

### 1.2 3段階トレーリングストップ ロジック

```
毎日（SELL シグナル判定時）:
  1. held_days を position_entries テーブルから取得（既存ロジック）
  2. peak_close を取得（既存ロジック）
  3. peak > avg_price のとき（含み益あり）:
      atr = _atr_20d()
      effective_mult = trailing_stop_atr  ← Stage 1 デフォルト (2.0)
      if dynamic_trailing_stop:
          if held_days >= 21:               ← Stage 3: 時間減衰（無条件）
              effective_mult = trail_stage3_mult
          elif held_days >= 6:              ← Stage 2: 含み益条件付き
              if (close - avg_price) >= trail_profit_gate_atr × atr:
                  effective_mult = trail_stage2_mult
      if close < peak - effective_mult × atr:
          SELL（trailing_stop）
```

Stage 2 の含み益条件 `(close - avg_price) >= trail_profit_gate_atr × ATR` は、「エントリー値から現在値が ATR の N 倍以上上昇している」ことを意味する。ATR は Stage 判定と停止判定で1回だけ計算して共用する。

### 1.3 新規パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `dynamic_trailing_stop` | `bool` | `False` | 有効化フラグ |
| `trail_profit_gate_atr` | `float` | `1.5` | Stage 2 移行の含み益閾値（ATR 単位）|
| `trail_stage2_mult` | `float` | `1.5` | Stage 2 の ATR 乗数 |
| `trail_stage3_mult` | `float` | `1.0` | Stage 3 の ATR 乗数 |

Stage 日数閾値（Stage 2 開始=6日目、Stage 3 開始=21日目）は全シナリオ固定とし、パラメータ化しない。

### 1.4 既存コードへの影響

- `dynamic_trailing_stop=False`（デフォルト）のとき完全に無効。既存 A〜N グループへの影響ゼロ
- `_atr_20d()` と `_peak_close()` の呼び出し順・ロジックは変更しない。trailing stop ブロック内部の乗数計算のみ変更

---

## 2. Group O シナリオ定義（施策B 単体検証）

**共通ベース設定（全シナリオ I1 固定）:**
```
allocation_method=equal, max_positions=3,
base_util=30%, MA200=ON, threshold=0.58,
max_holding=60d, atr=2.0, stop_loss=9%, dd_stop=12%
trail_profit_gate_atr=1.5（固定）
Stage 2 開始=6日目、Stage 3 開始=21日目（固定）
期間: 2017-01-01〜2025-12-31
```

| シナリオ | dynamic | stage2_mult | stage3_mult | 目的 |
|---|---|---|---|---|
| O0_i1_ref | OFF | — | — | I1 完全再現（参照・ベースライン）|
| O1_s15_s10 | ON | 1.5 | 1.0 | メイン候補: 段階的縮小 |
| O2_s18_s15 | ON | 1.8 | 1.5 | 控えめな縮小 |
| O3_s12_s10 | ON | 1.2 | 1.0 | 積極的なタイト化 |

**採択基準:**
```
Sharpe > 0.5           → 採用
0.382 < Sharpe ≤ 0.5   → 参考記録・I1 継続採用 → Step 3（施策A+B 複合）へ
全シナリオ Sharpe ≤ 0.382 → 施策B 単体効果なし → Step 3 で施策A と合わせて検証
```

---

## 3. CLI フラグ（run.py）

```
--dynamic-trailing-stop      (store_true, default=False)
--trail-profit-gate-atr      (type=float, default=1.5)
--trail-stage2-mult          (type=float, default=1.5)
--trail-stage3-mult          (type=float, default=1.0)
```

---

## 4. 実行コマンド

```powershell
python backtest/backtest_improvement_plan/run_phase1_group_o.py --workers 4
```

出力先: `artifacts/backtest/backtest_phase1_group_o/{timestamp}/`
