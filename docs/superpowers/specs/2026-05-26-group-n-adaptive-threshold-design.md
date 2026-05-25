# Group N 施策A: ボラティリティレジーム連動 動的シグナル閾値 設計書

**目的:** I1 の Sharpe 改善。2017年など低ボラ・弱モメンタム局面で発生するノイズ約定を削減し、年次リターンの標準偏差を低下させる。

**背景:**
- 既存の `adaptive_threshold`（TOPIX > MA200+5% で threshold 引き上げ）は K6 で MaxDD 悪化・Sharpe 低下と判明
- I1 の不良年（2017: -6.51%）は TOPIX 強気年（+19%）。多くの銘柄が threshold=0.58 を超え、ノイズシグナルが多発した
- I1 の優良年（2018: +64%）は TOPIX 高ボラ年。シグナル数は少ないが品質が高い
- 既存の K6 との違い: K6 は「TOPIX が MA200 を上回る強気局面」で閾値を上げる。本施策は「TOPIX の実現ボラティリティが低い局面」で閾値を上げる

---

## 1. アーキテクチャ

### 1.1 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `src/kabusys/strategy/signal_generator.py` | 変更 | `_calc_topix_vol()` 追加、`generate_signals()` に新パラメータ追加 |
| `src/kabusys/backtest/engine.py` | 変更 | `run_backtest()` に新パラメータ追加、`generate_signals()` 呼び出しに転送 |
| `src/kabusys/backtest/run.py` | 変更 | CLI フラグ 3 本追加 |
| `backtest/backtest_improvement_plan/run_phase1_group_n.py` | 新規 | Group N（施策A単体）バックテスト実行スクリプト |

### 1.2 レジーム判定ロジック

```
毎日:
  1. topix_daily から直近 topix_vol_window 日（デフォルト 20）の close を取得
  2. 日次リターン系列を計算
  3. 標準偏差 × √252 で年次換算ボラティリティを計算
  4. topix_vol < topix_vol_low_threshold なら "低ボラ局面" → threshold を adaptive_threshold_hi に引き上げ
  5. それ以外は threshold を変更しない
```

### 1.3 ヘルパー関数（signal_generator.py モジュールレベル）

```python
def _calc_topix_vol(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    window: int = 20,
) -> float | None:
    """直近 window 日の TOPIX 日次リターン標準偏差を年次換算して返す。
    データ不足（< window+1 本）の場合は None。
    """
    rows = conn.execute(
        "SELECT close FROM topix_daily WHERE date <= ? ORDER BY date DESC LIMIT ?",
        [target_date, window + 1],
    ).fetchall()
    if len(rows) < window + 1:
        return None
    closes = [float(r[0]) for r in rows]
    rets = [(closes[i] - closes[i + 1]) / closes[i + 1] for i in range(window)]
    mean_r = sum(rets) / window
    var = sum((r - mean_r) ** 2 for r in rets) / (window - 1)
    return math.sqrt(var) * math.sqrt(252)
```

### 1.4 generate_signals() への追加パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `adaptive_threshold_vol_regime` | `bool` | `False` | 有効化フラグ |
| `topix_vol_window` | `int` | `20` | ボラティリティ計算ウィンドウ（営業日） |
| `topix_vol_low_threshold` | `float` | `0.15` | 低ボラ判定の年次換算ボラ閾値（例: 0.15 = 15%）|

`adaptive_threshold_hi`（既存, デフォルト 0.62）を共用する。

### 1.5 既存コードへの影響

- `adaptive_threshold_vol_regime=False`（デフォルト）のとき完全に無効。既存 A〜M グループへの影響ゼロ
- 既存の `adaptive_threshold`（MA200乖離ベース）と独立して動作。両方 True の場合は OR 条件で閾値が上がる

---

## 2. Group N シナリオ定義（施策A 単体検証）

**共通ベース設定（全シナリオ I1 固定）:**
```
allocation_method=equal, max_positions=3,
base_util=30%, MA200=ON, threshold=0.58,
max_holding=60d, atr=2.0, stop_loss=9%, dd_stop=12%
期間: 2017-01-01〜2025-12-31
```

| シナリオ | vol_window | vol_low_thr | adaptive_hi | 目的 |
|---|---|---|---|---|
| N0_i1_ref | — | — | — | I1 完全再現（参照・ベースライン） |
| N1a_vol15_hi62 | 20 | 0.15 | 0.62 | メイン候補：低ボラ(< 15%)で0.62に引き上げ |
| N1b_vol12_hi62 | 20 | 0.12 | 0.62 | より厳格な低ボラ判定（12%未満） |
| N1c_vol15_hi60 | 20 | 0.15 | 0.60 | 閾値を控えめ（0.60）に引き上げ |

**採択基準:**
```
Sharpe > 0.5 → 採用
0.382 < Sharpe ≤ 0.5 → I1 超え・参考記録 → I1 継続採用
Sharpe ≤ 0.382 → 施策A 効果なし → 施策B へ
```

---

## 3. CLI フラグ（run.py）

```
--adaptive-threshold-vol-regime   (store_true, default=False)
--topix-vol-window                (type=int,   default=20)
--topix-vol-low-threshold         (type=float, default=0.15)
```

---

## 4. 実行コマンド

```powershell
python backtest/backtest_improvement_plan/run_phase1_group_n.py --workers 4
```

出力先: `artifacts/backtest/backtest_phase1_group_n/{timestamp}/`
