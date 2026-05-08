# Strategy Parameter Externalization (Remaining 4 Constants) Design

## Goal

`signal_generator.py` に残るハードコード定数 4 件を `config/strategy_config.yaml` の `sector:` / `regime:` セクションから runtime 読み込みに変更し、再起動不要でパラメータを変更できるようにする。

## Background

`_load_strategy_config()` と `strategy_config.yaml` はすでに実装済みで、`weights` / `threshold` / `stop_loss_rate` など主要パラメータはすでに外出し済み。残るハードコードは 4 定数のみ。

| 定数 | 値 | 用途 |
|------|----|------|
| `_SECTOR_BOOST` | 0.03 | 上位セクター銘柄への final_score 加算量 |
| `_SECTOR_QUARTILE` | 0.25 | セクター上位・下位の区切り割合 |
| `_TOPIX_DRAWDOWN_THRESHOLD` | -0.15 | TOPIX 200MA 乖離率の地合い悪化判定閾値 |
| `_TOPIX_SIZE_MULTIPLIER_BEAR` | 0.5 | 地合い悪化時の size_multiplier |

## Architecture

既存の `_load_strategy_config()` パターンを踏襲する。YAML に `sector:` / `regime:` セクションを追加し、返却 dict は既存の flat 構造に 4 キーを追加する。ヘルパー関数には明示的パラメータとして渡す。

## Changes

### 1. `config/strategy_config.yaml`

```yaml
sector:
  boost: 0.03       # 上位セクター銘柄への final_score 加算量（≥ 0）
  quartile: 0.25    # 上位・下位の区切り割合（0 < x < 1）

regime:
  topix_drawdown_threshold: -0.15   # TOPIX 200MA 乖離率の地合い悪化判定閾値（< 0）
  topix_size_multiplier_bear: 0.5   # 地合い悪化時の size_multiplier（0 < x ≤ 1）
```

### 2. `src/kabusys/strategy/signal_generator.py`

**`_STRATEGY_CONFIG_DEFAULTS` に 4 キー追加：**

```python
_STRATEGY_CONFIG_DEFAULTS: dict = {
    # 既存キー（変更なし）
    "weights": {k: v for k, v in _DEFAULT_WEIGHTS.items()},
    "threshold": _DEFAULT_THRESHOLD,
    "stop_loss_rate": _STOP_LOSS_RATE,
    "gap_up_threshold": _GAP_UP_THRESHOLD,
    "gap_down_threshold": _GAP_DOWN_THRESHOLD,
    "min_holding_days": _MIN_HOLDING_DAYS,
    "max_holding_days": _MAX_HOLDING_DAYS,
    "trailing_stop_atr_mult": _TRAILING_STOP_ATR_MULT,
    "reentry_cooldown_days": _REENTRY_COOLDOWN_DAYS,
    # 追加
    "sector_boost": _SECTOR_BOOST,
    "sector_quartile": _SECTOR_QUARTILE,
    "topix_drawdown_threshold": _TOPIX_DRAWDOWN_THRESHOLD,
    "topix_size_multiplier_bear": _TOPIX_SIZE_MULTIPLIER_BEAR,
}
```

**`_load_strategy_config()` に `sector:` / `regime:` セクション解析を追加：**

```python
# sector セクション
sec = data.get("sector")
if isinstance(sec, dict):
    v = sec.get("boost")
    if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool) \
            and math.isfinite(float(v)) and float(v) >= 0:
        result["sector_boost"] = float(v)

    v = sec.get("quartile")
    if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool) \
            and math.isfinite(float(v)) and 0.0 < float(v) < 1.0:
        result["sector_quartile"] = float(v)

# regime セクション
reg = data.get("regime")
if isinstance(reg, dict):
    v = reg.get("topix_drawdown_threshold")
    if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool) \
            and math.isfinite(float(v)) and float(v) < 0:
        result["topix_drawdown_threshold"] = float(v)

    v = reg.get("topix_size_multiplier_bear")
    if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool) \
            and math.isfinite(float(v)) and 0.0 < float(v) <= 1.0:
        result["topix_size_multiplier_bear"] = float(v)
```

**`_calc_sector_strengths()` シグネチャ変更：**

```python
def _calc_sector_strengths(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    sector_quartile: float = _SECTOR_QUARTILE,
) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
    ...
    top_n = max(1, math.ceil(n * sector_quartile))
    bottom_n = max(1, math.ceil(n * sector_quartile))
```

**`_get_topix_size_multiplier()` シグネチャ変更：**

```python
def _get_topix_size_multiplier(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    drawdown_threshold: float = _TOPIX_DRAWDOWN_THRESHOLD,
    size_multiplier_bear: float = _TOPIX_SIZE_MULTIPLIER_BEAR,
) -> float:
    ...
    if ma200 > 0 and (close / ma200 - 1.0) < drawdown_threshold:
        return size_multiplier_bear
```

**`generate_signals()` 内での渡し方：**

```python
_cfg = _load_strategy_config()
# 既存（変更なし）
threshold = _cfg["threshold"]
weights = _cfg["weights"]
...
# 追加
sector_boost = _cfg["sector_boost"]

top_sectors, bottom_sectors, sector_map = _calc_sector_strengths(
    conn, target_date, sector_quartile=_cfg["sector_quartile"]
)

topix_multiplier = _get_topix_size_multiplier(
    conn, target_date,
    drawdown_threshold=_cfg["topix_drawdown_threshold"],
    size_multiplier_bear=_cfg["topix_size_multiplier_bear"],
)

# final_score 補正箇所
final_score += sector_boost  # _SECTOR_BOOST → sector_boost
```

### 3. テスト — `tests/test_signal_generator.py`

既存の `_load_strategy_config` テストパターンを踏襲し、以下を追加する。

**設定読み込みテスト：**
- `sector:` / `regime:` セクション正常値 → 各キーが設定値で返る
- `sector.boost = -0.01`（負値）→ デフォルト `0.03` にフォールバック
- `sector.quartile = 0.0`（境界値 = 0）→ デフォルト `0.25` にフォールバック
- `sector.quartile = 1.0`（境界値 = 1）→ デフォルト `0.25` にフォールバック
- `regime.topix_drawdown_threshold = 0.10`（正値）→ デフォルト `-0.15` にフォールバック
- `regime.topix_size_multiplier_bear = 1.5`（> 1）→ デフォルト `0.5` にフォールバック
- `sector:` セクション欠落 → デフォルト値が使われる
- `regime:` セクション欠落 → デフォルト値が使われる

**ヘルパー関数テスト：**
- `_calc_sector_strengths(conn, date, sector_quartile=0.5)` → top/bottom セクター数が増える
- `_get_topix_size_multiplier(conn, date, drawdown_threshold=-0.01, size_multiplier_bear=0.3)` → TOPIX データがあれば `0.3` を返す

## Validation Rules

| キー | 有効範囲 | 不正時の挙動 |
|------|---------|------------|
| `sector_boost` | float ≥ 0、finite | デフォルト `0.03` |
| `sector_quartile` | float、0 < x < 1、finite | デフォルト `0.25` |
| `topix_drawdown_threshold` | float < 0、finite | デフォルト `-0.15` |
| `topix_size_multiplier_bear` | float、0 < x ≤ 1、finite | デフォルト `0.5` |

## Files

- Modify: `config/strategy_config.yaml`
- Modify: `src/kabusys/strategy/signal_generator.py`
- Modify: `tests/test_signal_generator.py`

## Out of Scope

- breadth_stop の 35% 閾値（DB の `market_breadth.breadth_stop` フラグとして管理されており、本 Issue では変更しない）
- `value_score:` セクションの変更（既存の `_load_value_config()` で対応済み）
- UI / Streamlit からのパラメータ変更機能（Issue #233 の範囲）
