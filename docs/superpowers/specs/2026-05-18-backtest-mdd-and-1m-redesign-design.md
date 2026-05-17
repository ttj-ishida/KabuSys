# 設計仕様書: 10m MDD対策 & 1m スコアリングアブレーション分析

作成日: 2026-05-18  
対象ブランチ: feature/issue-342-backfill-features

---

## 背景・問題

### 10m スケール（1,000万円）

OOS検証（2023・2024・2025）の結果、2024年のMaxDDが41.35%に達した。  
主因は2024年8月のブラックマンデー（TOPIX急落）期間中に新規エントリーが止まらなかったこと。  
既存のTOPIXベアガード（`topix_drawdown_threshold=-0.15`）では発動が遅すぎた。

### 1m スケール（100万円）

OOS検証で2023年CAGR -9.71%・2024年CAGR -3.70%・2025年CAGR +53.11%という強いオーバーフィットが確認された。  
2025年固有の相場構造（継続的上昇トレンド）に過適合している可能性が高い。  
スコアリングの重み（momentum=0.40が最大）がどの年度でも安定して機能しているか不明であり、  
まずアブレーション分析でどのファクターが2023/2024の損失を引き起こしているかを特定する。

---

## 1. 10m MDD対策

### 1-1. アーキテクチャ

2つの独立したガードを二段構えで実装する。

```
毎日の処理ループ（engine.py）
  ├─ ① TOPIXベアガード（既存パラメータ強化）
  │     topix_drawdown_threshold: -0.15 → -0.10（早めに発動）
  │     topix_size_multiplier_bear: 0.50 → 0.25（ベア時は75%削減）
  │
  └─ ② ポートフォリオドローダウンストップ（新規実装）
        ピーク資産比 -portfolio_drawdown_stop_pct 超のドローダウン
        → その日の全BUYシグナルをスキップ
        → ポートフォリオが回復すれば翌日から自動解除
```

### 1-2. 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `src/kabusys/backtest/engine.py` | `run_backtest()` に `portfolio_drawdown_stop_pct: float \| None = None` パラメータを追加。ピーク資産追跡変数 `peak_value` を初期化し、毎日更新。BUY処理前にドローダウン計算・エントリーブロック判定を挿入。 |
| `src/kabusys/backtest/run.py` | `--portfolio-drawdown-stop` CLI引数を追加（type=float, default=None）。`run_backtest()` に転送。 |

### 1-3. engine.py 実装詳細

```python
def run_backtest(
    ...,
    portfolio_drawdown_stop_pct: float | None = None,  # 追加
) -> BacktestResult:

    peak_value: float = initial_cash  # ピーク追跡

    for date in trading_dates:
        # ポートフォリオ時価を計算
        portfolio_value = cash + sum(pos.shares * prices[pos.code] for pos in positions)
        peak_value = max(peak_value, portfolio_value)

        # ② ポートフォリオドローダウンチェック
        entry_blocked = (
            portfolio_drawdown_stop_pct is not None
            and (portfolio_value / peak_value - 1) < -portfolio_drawdown_stop_pct
        )

        # BUYシグナル処理
        for signal in buy_signals_today:
            if entry_blocked:
                continue  # スキップ（SELLは影響しない）
            # 既存エントリー処理
```

**重要な制約:**
- SELL処理（ストップロス・タイムイグジット・トレーリングストップ）はブロックしない
- `entry_blocked` はBUYのみに適用
- ピーク値のリセットは行わない（一度下落したピークは保持し続ける）

### 1-4. 検証スクリプト

**ファイル**: `backtest/backtest_improvement_plan/run_backtest_improvement_10m_mdd.py`  
**出力先**: `artifacts/backtest/backtest_improvement_10m_mdd/`  
**シナリオ数**: 6シナリオ × 3年（2023/2024/2025）= 18ラン

| シナリオ名 | topix_thr | topix_mult | dd_stop | 検証目的 |
|---|---|---|---|---|
| `base` | -0.15 | 0.50 | なし | OOS2ベースラインの再現（内部一貫性確認） |
| `bear_stronger` | **-0.10** | **0.25** | なし | TOPIXガード強化のみの効果を分離 |
| `dd_stop15` | -0.15 | 0.50 | **0.15** | ポートフォリオストップのみの効果を分離 |
| `dd_stop12` | -0.15 | 0.50 | **0.12** | ポートフォリオストップ厳しめ |
| `combined15` | **-0.10** | **0.25** | **0.15** | 両者の組み合わせ（標準） |
| `combined12` | **-0.10** | **0.25** | **0.12** | 両者の組み合わせ（厳格） |

**results.csv 列**: `name`, `year`, `topix_drawdown_threshold`, `topix_size_multiplier_bear`, `portfolio_drawdown_stop_pct`, `cagr`, `sharpe`, `max_drawdown`, `win_rate`, `payoff_ratio`, `profit_factor`, `avg_holding_days`, `total_trades`, `trades_csv`

### 1-5. 成功指標

- 2024年MaxDDを41.35% → **25%以下**に削減
- 2024年CAGRが base比でプラス方向に改善、またはマイナス幅が縮小
- 2025年CAGRへの影響が -5pp 以内（過度な機会損失を避ける）

---

## 2. 1m スコアリングアブレーション分析

### 2-1. 概要

各ファクターのウェイトを1つずつ0にして3年間のOOS検証を行い、どのファクターが  
2023/2024の損失に寄与しているかを特定する。特定後は重みを調整した再検証スクリプトを別途作成する。

### 2-2. ファクター重みの操作方法

`strategy_config.yaml` の `weights` セクションを書き換える（既存スクリプトと同パターン）。  
残りの重みは `generate_signals()` 内で自動正規化されるため、合計が1.0でなくても動作する。

```yaml
# 例: no_momentum シナリオ
strategy:
  weights:
    momentum: 0.00   # ← 0 に設定
    value: 0.20
    volatility: 0.15
    liquidity: 0.15
    news: 0.10
```

### 2-3. 検証スクリプト

**ファイル**: `backtest/backtest_improvement_plan/run_backtest_improvement_1m_ablation.py`  
**出力先**: `artifacts/backtest/backtest_improvement_1m_ablation/`  
**シナリオ数**: 6シナリオ × 3年 = 18ラン

| シナリオ名 | momentum | value | volatility | liquidity | news |
|---|---|---|---|---|---|
| `base` | 0.40 | 0.20 | 0.15 | 0.15 | 0.10 |
| `no_momentum` | **0** | 0.20 | 0.15 | 0.15 | 0.10 |
| `no_value` | 0.40 | **0** | 0.15 | 0.15 | 0.10 |
| `no_volatility` | 0.40 | 0.20 | **0** | 0.15 | 0.10 |
| `no_liquidity` | 0.40 | 0.20 | 0.15 | **0** | 0.10 |
| `no_news` | 0.40 | 0.20 | 0.15 | 0.15 | **0** |

**ベースパラメータ** (1m_equal_4slots v2 最良設定):

```python
cash=1_000_000, allocation_method="equal", max_positions=4,
max_position_pct=0.22, max_utilization=0.80, stop_loss_pct=0.09,
threshold=0.58, topix_drawdown_threshold=-0.15,
topix_size_multiplier_bear=0.50, trailing_stop_atr_mult=2.0,
max_holding_days=60
```

**results.csv 列**: `name`, `year`, `w_momentum`, `w_value`, `w_volatility`, `w_liquidity`, `w_news`, `cagr`, `sharpe`, `max_drawdown`, `win_rate`, `payoff_ratio`, `profit_factor`, `avg_holding_days`, `total_trades`, `trades_csv`

### 2-4. 分析方法

結果を受け取ったら以下のマトリクスを作成して判定する:

```
シナリオ        | 2023 Sharpe | 2024 Sharpe | 2025 Sharpe | 判定
base           |    -0.340   |   -0.021    |    1.946    | ベースライン
no_momentum    |     ?       |     ?       |     ?       | 改善→momentumが問題
no_value       |     ?       |     ?       |     ?       | 改善→valueが問題
...
```

判定基準:
- 除外で **2023/2024 Sharpe が改善** → そのファクターが悪化の原因
- 除外で **2025 Sharpe が大幅低下** → そのファクターは2025年に有効（外せない）
- 次フェーズ: 問題ファクターの重みを下げ、有効ファクターの重みを上げた設定でOOS再検証

### 2-5. 成功指標

- アブレーション結果から「原因ファクター」を1〜2個特定できること
- 原因ファクターを下げた設定で2023/2024 Sharpeが `base` 比で改善すること（次フェーズ確認）

---

## 実装順序

1. **engine.py 改修**（`portfolio_drawdown_stop_pct` 追加）+ TDD
2. **run.py 改修**（CLI引数追加）
3. **`run_backtest_improvement_10m_mdd.py`** 作成・実行
4. **`run_backtest_improvement_1m_ablation.py`** 作成・実行（engine.py改修不要）
5. 結果分析 → 次フェーズ設計

ステップ3と4は engine.py 改修後に並行実行可能。
