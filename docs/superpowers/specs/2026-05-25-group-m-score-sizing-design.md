# Group M: シグナル強度ベースサイジング 設計書

**目的:** I1 戦略の Sharpe 改善。スコア比例配分と銘柄集中の効果を検証し、均等配分（equal）を上回るリスク調整後リターンを狙う。

**背景:**
- I1 の Sharpe 0.382 は年次リターンの構造的偏り（2018/2024 に集中）が原因
- Group L（動的 utilization）では全シナリオで Sharpe が I1 以下と判明
- シグナルの `score` は既にバックテストエンジンに渡されており、`allocation_method="score"` で線形スコア比例配分が利用可能
- `max_positions` パラメータも既存サポート済み

---

## 1. アーキテクチャ

### 1.1 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `backtest/backtest_improvement_plan/run_phase1_group_m.py` | 新規 | Group M バックテスト実行スクリプト |

engine.py・run.py・portfolio_builder.py への変更なし。

### 1.2 スコア重み付け計算（既存実装）

`src/kabusys/portfolio/portfolio_builder.py::calc_score_weights()` が担当：

```python
weight_i = score_i / Σ(score_j)
```

I1 候補（スコア ≥ 0.58）の例：
```
スコア 0.58, 0.70, 0.90 → 重み 26.6%, 32.1%, 41.3%
（最高スコアが最低スコアの約 1.6 倍）
```

---

## 2. Group M シナリオ定義

**共通ベース設定（全シナリオ I1 固定）:**

```
base_util=30%, MA200=ON, threshold=0.58,
max_holding=60d, atr=2.0, stop_loss=9%, dd_stop=12%
期間: 2017-01-01〜2025-12-31
```

| シナリオ | allocation | max_positions | 目的 |
|---|---|---|---|
| M0_i1_ref | equal | 3 | I1 完全再現（参照・ベースライン） |
| M1_score | score | 3 | スコア重み付けの効果を分離 |
| M2_equal_pos2 | equal | 2 | 銘柄集中の効果を分離 |
| M3_score_pos2 | score | 2 | スコア重み × 集中の相乗効果 |

**設計の意図:**
- M1 と M0 の差 → スコア重み付けの純粋な効果
- M2 と M0 の差 → 銘柄集中（pos=2）の純粋な効果
- M3 と M0 の差 → 両者の組み合わせ効果

---

## 3. 実装ファイル

### 3.1 run_phase1_group_m.py

`run_phase1_group_k.py` を参考に作成。主な差分：

- `_COM["allocation_method"]` は各シナリオで個別指定（共通値なし）
- `_COM["max_positions"]` も各シナリオで個別指定
- `_build_command()` でシナリオの `allocation_method` と `max_positions` を CLI に渡す

```python
# シナリオ固有パラメータの反映
cmd += ["--allocation-method", scenario["allocation_method"]]
cmd += ["--max-positions", str(scenario["max_positions"])]
```

出力先: `artifacts/backtest/backtest_phase1_group_m/{timestamp}/`

---

## 4. 検証と採択判断

### 4.1 実行コマンド

```powershell
python backtest/backtest_improvement_plan/run_phase1_group_m.py --workers 4
```

### 4.2 サマリー出力形式

```
シナリオ      allocation  max_pos  CAGR    Sharpe  MaxDD    PF    Trades
M0_i1_ref    equal       3        7.72%   0.382   24.96%  1.297   697
M1_score     score       3        x.xx%   x.xxx   xx.xx%  x.xxx   xxx
M2_equal_pos2 equal      2        x.xx%   x.xxx   xx.xx%  x.xxx   xxx
M3_score_pos2 score      2        x.xx%   x.xxx   xx.xx%  x.xxx   xxx
```

### 4.3 採択判断ロジック

```
Sharpe > 0.5 を達成したシナリオがある
  → 当該設定を Phase 1 改良版として採用（CAGR>5%, MaxDD<25%, PF>1.1 も確認）

Sharpe > 0.382（I1 超え）かつ Sharpe ≤ 0.5
  → 最良シナリオを Phase 2 設計の参考として記録 → I1 継続採用

全シナリオで Sharpe ≤ 0.382
  → スコア重み付け・銘柄集中いずれも効果なし → Group N へ進む
```

---

## 5. 採択後の適用

採択された場合、`allocation_method` と `max_positions` を I1 の正式パラメータとして `Phase1_Backtest_Strategy.md` に追記し、`config/strategy.toml`（既存）に保存する。
