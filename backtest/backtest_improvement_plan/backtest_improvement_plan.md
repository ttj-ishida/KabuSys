# バックテスト改善計画

作成日: 2026-05-16  
対象スクリプト: `work/run_backtest_rsi65_trim_slots7_cash_compare.py`

---

## 1. 現状の問題点サマリー

### 100万円の根本問題：単元株制約

現行の `risk_based` 配分では 1 ポジションあたりの予算が小さすぎる。

```
1ポジション予算 = cash × risk_pct / stop_loss_pct
               = 1,000,000 × 0.005 / 0.09 = 55,556 円
```

- 55,556 円 ÷ 100 株 = **上限株価 555 円**
- 全シグナルのうち実際に執行できたのは **28 / 492 件（約 6%）**
- 特定銘柄（63660）が利益の **67%** を占める過集中状態
- 統計的に意味のある評価が不可能

### 1000万円の問題

| 問題 | 数値 | 影響 |
|---|---|---|
| Profit Factor ギリギリ | 1.037 | 少しの悪化でマイナス転落 |
| 短期保有（≤5日）損失 | **-1,470,750 円** | 30 トレードで全利益を食う |
| 4月の下落 | **-581,823 円** | トランプ関税ショック |
| 11月の下落 | **-479,076 円** | ベア相場対応不足 |
| 手数料が利益と同水準 | 227,437 円 vs 利益 211,860 円 | 短期売買が多すぎる |

---

## 2. 検証パターン

### 2-A. 100万円向けパターン（4本）

**目的**: `allocation_method=equal` に切り替え、ポジション予算を拡大して単元株制約を緩和する。

| シナリオ名 | allocation_method | max_positions | max_position_pct | 1ポジション予算 | アクセス可能上限 |
|---|---|---|---|---|---|
| `1m_base` | risk_based | 7 | 10% | ~55,556 円 | ~500 円/株（現行） |
| `1m_equal_6slots` | **equal** | **6** | **15%** | **150,000 円** | ~1,500 円/株 |
| `1m_equal_5slots` | **equal** | **5** | **18%** | **180,000 円** | ~1,800 円/株 |
| `1m_equal_4slots` | **equal** | **4** | **22%** | **220,000 円** | ~2,200 円/株 |

> **注**: equal allocation では `1ポジション予算 = cash × max_utilization / max_positions`  
> 例: 1,000,000 × 0.75 / 5 = **150,000 円**（`1m_equal_6slots` の場合）

#### 共通の strategy_config 設定（100万円向け）

```yaml
strategy:
  threshold: 0.58
  rsi_overbought_threshold: 65.0
  gap_up_threshold: 0.07
  gap_down_threshold: -0.05
  stop_loss_rate: -0.08
  min_holding_days: 5
  max_holding_days: 60
  trailing_stop_atr_mult: 2.0
  reentry_cooldown_days: 5
sector:
  boost: 0.05
  quartile: 0.30
regime:
  topix_drawdown_threshold: -0.15
  topix_size_multiplier_bear: 0.50
```

#### 各シナリオの backtest パラメータ

```python
# 1m_base（現行・比較ベースライン）
{
    "cash": 1_000_000,
    "allocation_method": "risk_based",
    "max_positions": 7,
    "max_position_pct": 0.10,
    "max_utilization": 0.70,
    "risk_pct": 0.005,
    "stop_loss_pct": 0.09,
}

# 1m_equal_6slots
{
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_positions": 6,
    "max_position_pct": 0.15,
    "max_utilization": 0.75,
    "risk_pct": 0.005,     # equal では参照されないが保持
    "stop_loss_pct": 0.09,
}

# 1m_equal_5slots
{
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_positions": 5,
    "max_position_pct": 0.18,
    "max_utilization": 0.75,
    "risk_pct": 0.005,
    "stop_loss_pct": 0.09,
}

# 1m_equal_4slots
{
    "cash": 1_000_000,
    "allocation_method": "equal",
    "max_positions": 4,
    "max_position_pct": 0.22,
    "max_utilization": 0.80,
    "risk_pct": 0.005,
    "stop_loss_pct": 0.09,
}
```

---

### 2-B. 1000万円向けパターン（4本）

**目的**: 短期損失の抑制、ベア局面フィルタ強化、Winner をより長く保有して Payoff 改善。

| シナリオ名 | threshold | bear_mult | trailing_atr | 主な狙い |
|---|---|---|---|---|
| `10m_base` | 0.58 | 0.50 | 2.0 | 現行比較ベースライン |
| `10m_tighter_entry` | **0.62** | 0.50 | 2.0 | シグナル精度向上・不要エントリー削減 |
| `10m_bear_guard` | **0.62** | **0.30** | 2.0 | 4月・11月の下落局面でポジション抑制 |
| `10m_hold_longer` | **0.62** | **0.30** | **2.5** | Payoff 改善（Winner をより長く保有） |

#### 各シナリオの変更点詳細

```python
# 10m_base（現行・比較ベースライン）
strategy:
  threshold: 0.58
  trailing_stop_atr_mult: 2.0
regime:
  topix_drawdown_threshold: -0.15
  topix_size_multiplier_bear: 0.50

# 10m_tighter_entry
# → threshold のみ変更。1 点の変化の効果を単独で測定する
strategy:
  threshold: 0.62        # ← 変更

# 10m_bear_guard
# → threshold 引き上げ + ベア判定の早期化・ポジション抑制
strategy:
  threshold: 0.62
regime:
  topix_drawdown_threshold: -0.12   # ← 変更（-15%→-12%: 早めにベア判定）
  topix_size_multiplier_bear: 0.30  # ← 変更（0.5→0.3: ベア時は 70%削減）

# 10m_hold_longer
# → bear_guard に加えてトレーリングストップを緩め Winner を引っ張る
strategy:
  threshold: 0.62
  trailing_stop_atr_mult: 2.5       # ← 変更（2.0→2.5）
regime:
  topix_drawdown_threshold: -0.12
  topix_size_multiplier_bear: 0.30
```

#### 共通の backtest パラメータ（1000万円向け）

```python
{
    "cash": 10_000_000,
    "allocation_method": "risk_based",
    "max_positions": 7,
    "max_position_pct": 0.10,
    "max_utilization": 0.70,
    "risk_pct": 0.005,
    "stop_loss_pct": 0.09,
}
```

---

## 3. スクリプト修正内容

対象: `work/run_backtest_rsi65_trim_slots7_cash_compare.py`

### 修正 1：`SCENARIOS` リストを展開

`SCENARIOS` を 100万円 4 本 + 1000万円 4 本の 8 本に差し替える。

```python
SCENARIOS = [
    # --- 100万円：allocation_method 比較 ---
    {"name": "1m_base",         "cash": 1_000_000,  "allocation_method": "risk_based", "max_positions": 7, "max_position_pct": 0.10, "max_utilization": 0.70},
    {"name": "1m_equal_6slots", "cash": 1_000_000,  "allocation_method": "equal",      "max_positions": 6, "max_position_pct": 0.15, "max_utilization": 0.75},
    {"name": "1m_equal_5slots", "cash": 1_000_000,  "allocation_method": "equal",      "max_positions": 5, "max_position_pct": 0.18, "max_utilization": 0.75},
    {"name": "1m_equal_4slots", "cash": 1_000_000,  "allocation_method": "equal",      "max_positions": 4, "max_position_pct": 0.22, "max_utilization": 0.80},
    # --- 1000万円：threshold / bear / hold チューニング ---
    {"name": "10m_base",           "cash": 10_000_000, "allocation_method": "risk_based", "threshold": 0.58, "topix_size_multiplier_bear": 0.50, "topix_drawdown_threshold": -0.15, "trailing_stop_atr_mult": 2.0},
    {"name": "10m_tighter_entry",  "cash": 10_000_000, "allocation_method": "risk_based", "threshold": 0.62, "topix_size_multiplier_bear": 0.50, "topix_drawdown_threshold": -0.15, "trailing_stop_atr_mult": 2.0},
    {"name": "10m_bear_guard",     "cash": 10_000_000, "allocation_method": "risk_based", "threshold": 0.62, "topix_size_multiplier_bear": 0.30, "topix_drawdown_threshold": -0.12, "trailing_stop_atr_mult": 2.0},
    {"name": "10m_hold_longer",    "cash": 10_000_000, "allocation_method": "risk_based", "threshold": 0.62, "topix_size_multiplier_bear": 0.30, "topix_drawdown_threshold": -0.12, "trailing_stop_atr_mult": 2.5},
]
```

---

### 修正 2：`_build_strategy_config()` をシナリオ対応に変更

現在は固定値で上書きしている。シナリオごとに `threshold` / `trailing_stop_atr_mult` / `regime` を切り替えられるよう引数を追加する。

```python
def _build_strategy_config(base: dict, scenario: dict) -> dict:
    strategy_config = deepcopy(base)
    strategy_section = strategy_config.setdefault("strategy", {})
    sector_section   = strategy_config.setdefault("sector", {})
    regime_section   = strategy_config.setdefault("regime", {})
    portfolio_section = strategy_config.setdefault("portfolio", {})

    # 固定値
    strategy_section["rsi_overbought_threshold"] = 65.0
    strategy_section["gap_up_threshold"]         = 0.07
    strategy_section["gap_down_threshold"]       = -0.05
    strategy_section["stop_loss_rate"]           = -0.08
    strategy_section["min_holding_days"]         = 5
    strategy_section["max_holding_days"]         = 60
    strategy_section["reentry_cooldown_days"]    = 5
    sector_section["boost"]    = 0.05
    sector_section["quartile"] = 0.30

    # シナリオで上書き可能な値
    strategy_section["threshold"]              = scenario.get("threshold", 0.58)
    strategy_section["trailing_stop_atr_mult"] = scenario.get("trailing_stop_atr_mult", 2.0)
    regime_section["topix_size_multiplier_bear"]  = scenario.get("topix_size_multiplier_bear", 0.50)
    regime_section["topix_drawdown_threshold"]    = scenario.get("topix_drawdown_threshold", -0.15)

    portfolio_section["max_positions"] = scenario.get("max_positions", 7)
    return strategy_config
```

---

### 修正 3：`_build_backtest_params()` に `allocation_method` / `max_positions` / `max_position_pct` / `max_utilization` を追加

```python
def _build_backtest_params(scenario: dict) -> dict[str, object]:
    return {
        "start":             "2025-01-01",
        "end":               "2025-12-31",
        "cash":              scenario["cash"],
        "allocation_method": scenario.get("allocation_method", "risk_based"),
        "max_positions":     scenario.get("max_positions", 7),
        "max_position_pct":  scenario.get("max_position_pct", 0.10),
        "max_utilization":   scenario.get("max_utilization", 0.70),
        "risk_pct":          scenario.get("risk_pct", 0.005),
        "stop_loss_pct":     scenario.get("stop_loss_pct", 0.09),
        "min_holding_days":  5,
        "max_holding_days":  60,
        "trailing_stop_atr": scenario.get("trailing_stop_atr_mult", 2.0),
    }
```

---

### 修正 4：`_build_command()` に `--allocation-method` を追加

```python
def _build_command(db_path: Path, params: dict[str, object], output_dir: Path) -> list[str]:
    return [
        sys.executable, "-m", "kabusys.backtest.run",
        "--db",                str(db_path),
        "--start",             str(params["start"]),
        "--end",               str(params["end"]),
        "--cash",              str(params["cash"]),
        "--allocation-method", str(params["allocation_method"]),   # ← 追加
        "--max-position-pct",  str(params["max_position_pct"]),
        "--max-utilization",   str(params["max_utilization"]),
        "--max-positions",     str(params["max_positions"]),
        "--risk-pct",          str(params["risk_pct"]),
        "--stop-loss-pct",     str(params["stop_loss_pct"]),
        "--min-holding-days",  str(params["min_holding_days"]),
        "--max-holding-days",  str(params["max_holding_days"]),
        "--trailing-stop-atr", str(params["trailing_stop_atr"]),
        "--output-format",     "all",
        "--output-dir",        str(output_dir),
    ]
```

---

### 修正 5：`fieldnames` と `record` に `allocation_method` を追加

```python
fieldnames = [
    "name", "run_id", "created_at",
    "cash", "allocation_method",          # ← allocation_method 追加
    "threshold",                           # ← 追加（シナリオ差異を記録）
    "topix_size_multiplier_bear",          # ← 追加
    "trailing_stop_atr",                   # ← 追加
    "rsi_overbought_threshold",
    "max_positions", "max_position_pct", "max_utilization",
    "risk_pct", "stop_loss_pct",
    "cagr", "sharpe", "max_drawdown",
    "win_rate", "payoff_ratio", "profit_factor",
    "avg_holding_days", "total_trades",
    "trades_csv",
]
```

```python
record = {
    "name":                       scenario_slug,
    "run_id":                     run_id,
    "created_at":                 metrics["created_at"],
    "cash":                       params["cash"],
    "allocation_method":          params["allocation_method"],
    "threshold":                  scenario.get("threshold", 0.58),
    "topix_size_multiplier_bear": scenario.get("topix_size_multiplier_bear", 0.50),
    "trailing_stop_atr":          scenario.get("trailing_stop_atr_mult", 2.0),
    "rsi_overbought_threshold":   65.0,
    "max_positions":              params["max_positions"],
    "max_position_pct":           params["max_position_pct"],
    "max_utilization":            params["max_utilization"],
    "risk_pct":                   params["risk_pct"],
    "stop_loss_pct":              params["stop_loss_pct"],
    **metrics,
    "trades_csv":                 str(scenario_dir / "trades.csv"),
}
```

---

### 修正 6：`main()` 内のループ呼び出しを更新

`_build_strategy_config` と `_build_backtest_params` の呼び出し箇所を修正する。

```python
# Before
strategy_config = _build_strategy_config(context["strategy_config"])
...
params = _build_backtest_params(int(scenario["cash"]))

# After
strategy_config = _build_strategy_config(context["strategy_config"], scenario)  # ← 引数追加
...
params = _build_backtest_params(scenario)  # ← scenario 全体を渡す
```

> `_build_strategy_config` の呼び出しを `for scenario in SCENARIOS:` ループ**内**に移動すること（現在はループ外で一度だけ呼んでいる）。

---

## 4. 期待される改善効果

### 100万円

| シナリオ | トレード数予測 | PF 目標 | 備考 |
|---|---|---|---|
| `1m_base`（現行） | ~28 | <1.0 | 対照群 |
| `1m_equal_6slots` | **~150 以上** | 未知 | 1,500 円以下の銘柄にアクセス可能 |
| `1m_equal_5slots` | **~200 以上** | 未知 | 1,800 円以下にアクセス可能 |
| `1m_equal_4slots` | **~250 以上** | 未知 | 2,200 円以下にアクセス可能 |

### 1000万円

| シナリオ | 変更点 | 期待効果 |
|---|---|---|
| `10m_base`（現行） | なし | 対照群（PF 1.037） |
| `10m_tighter_entry` | threshold 0.58→0.62 | 勝率向上、PF 改善 |
| `10m_bear_guard` | + bear_mult 0.5→0.3 | 4月・11月損失削減 |
| `10m_hold_longer` | + trailing_atr 2.0→2.5 | Payoff 改善 |

---

## 5. 追加指標の候補（次フェーズ）

上記スウィープで PF > 1.1 程度が安定して出たら、以下の指標追加も検討する。

| 指標 | 計算式 | 狙い | 実装難易度 |
|---|---|---|---|
| `high52w_proximity` | `(close - MAX(high) 252日) / MAX(high) 252日` | ブレイクアウト銘柄の識別 | 低 |
| `mom_accel` | `mom_1m(今日) - mom_1m(20日前)` | モメンタム加速中の銘柄を選別 | 低 |
| `beta_60` | 60日間の TOPIX 共分散 / TOPIX 分散 | ベア相場での高ベータ銘柄除外 | 中 |
| `ma5_dev` | `(close - MA5) / MA5` | 短期過熱エントリーの回避 | 低 |
| `roe_yoy` | `ROE(当期) - ROE(前期)` | 改善中 ROE の識別 | 中 |
