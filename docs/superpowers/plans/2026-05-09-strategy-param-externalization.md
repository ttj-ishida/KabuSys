# Strategy Parameter Externalization (Remaining 4 Constants) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `signal_generator.py` に残るハードコード定数 4 件（`_SECTOR_BOOST`, `_SECTOR_QUARTILE`, `_TOPIX_DRAWDOWN_THRESHOLD`, `_TOPIX_SIZE_MULTIPLIER_BEAR`）を `config/strategy_config.yaml` の `sector:` / `regime:` セクションから runtime 読み込みに変更し、再起動不要でパラメータを変更できるようにする。

**Architecture:** 既存の `_load_strategy_config()` / `_STRATEGY_CONFIG_DEFAULTS` パターンを踏襲し、YAML の `sector:` / `regime:` セクションを解析して返却 dict に 4 キーを追加する。`_calc_sector_strengths()` と `_get_topix_size_multiplier()` はデフォルト付き明示パラメータを受け取り、`generate_signals()` が `_cfg` から渡す。

**Tech Stack:** Python 3.10+, PyYAML（既存依存）, pytest

---

## File Map

- Modify: `src/kabusys/strategy/signal_generator.py` — `_STRATEGY_CONFIG_DEFAULTS`, `_load_strategy_config()`, `_calc_sector_strengths()`, `_get_topix_size_multiplier()`, `generate_signals()` の 5 箇所
- Modify: `config/strategy_config.yaml` — `sector:` / `regime:` セクション追加
- Modify: `tests/test_signal_generator.py` — 新テスト追加

---

## Background（コードベース把握）

`signal_generator.py` の現状:
- `_STRATEGY_CONFIG_PATH` (line 103): `config/strategy_config.yaml` へのパス
- `_strategy_config_cache` / `_strategy_config_mtime` (lines 107-108): グローバルキャッシュ
- `_load_strategy_config()` (line 111): YAML を読んで flat dict を返す。`strategy:` セクションのみ解析済み
- `_STRATEGY_CONFIG_DEFAULTS` (line 91): デフォルト dict。現状 9 キー
- `_calc_sector_strengths(conn, target_date)` (line 533): `_SECTOR_QUARTILE` をモジュール定数として使用
- `_get_topix_size_multiplier(conn, target_date)` (line 447): `_TOPIX_DRAWDOWN_THRESHOLD` / `_TOPIX_SIZE_MULTIPLIER_BEAR` をモジュール定数として使用
- `generate_signals()` (line 989): `_cfg = _load_strategy_config()` を呼び出し済み（line 1028）

テスト:
- `TestGetTopixSizeMultiplier` クラス (line 624): `_get_topix_size_multiplier` を引数 2 つで呼ぶ既存テストがある。パラメータ追加後もデフォルト値で動作する。

---

## Task 1: `_load_strategy_config()` に sector/regime セクション解析を追加

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py:91-234`
- Modify: `tests/test_signal_generator.py`（末尾に追加）

### Step 1: 失敗するテストを書く

`tests/test_signal_generator.py` の末尾に追加する:

```python
# ---------------------------------------------------------------------------
# Task 1: _load_strategy_config() sector/regime セクション
# ---------------------------------------------------------------------------

import kabusys.strategy.signal_generator as _sg


def _load_cfg_with_yaml(yaml_text: str, tmp_path, monkeypatch) -> dict:
    """tmp_path に YAML ファイルを書き、モジュールのパスとキャッシュをパッチして _load_strategy_config() を呼ぶ。"""
    cfg_file = tmp_path / "strategy_config.yaml"
    cfg_file.write_text(yaml_text, encoding="utf-8")
    monkeypatch.setattr(_sg, "_STRATEGY_CONFIG_PATH", cfg_file)
    monkeypatch.setattr(_sg, "_strategy_config_cache", None)
    monkeypatch.setattr(_sg, "_strategy_config_mtime", -1.0)
    return _sg._load_strategy_config()


class TestLoadStrategyConfigSectorRegime:
    """_load_strategy_config() の sector/regime セクション解析テスト。"""

    def test_valid_sector_and_regime(self, tmp_path, monkeypatch):
        yaml_text = """
strategy:
  threshold: 0.60
sector:
  boost: 0.05
  quartile: 0.30
regime:
  topix_drawdown_threshold: -0.20
  topix_size_multiplier_bear: 0.4
"""
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_boost"] == 0.05
        assert cfg["sector_quartile"] == 0.30
        assert cfg["topix_drawdown_threshold"] == -0.20
        assert cfg["topix_size_multiplier_bear"] == 0.4

    def test_missing_sector_section_uses_defaults(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_boost"] == 0.03
        assert cfg["sector_quartile"] == 0.25

    def test_missing_regime_section_uses_defaults(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_drawdown_threshold"] == -0.15
        assert cfg["topix_size_multiplier_bear"] == 0.5

    def test_sector_boost_negative_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "sector:\n  boost: -0.01\n  quartile: 0.25\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_boost"] == 0.03  # default

    def test_sector_quartile_zero_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "sector:\n  boost: 0.03\n  quartile: 0.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_quartile"] == 0.25  # default

    def test_sector_quartile_one_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "sector:\n  boost: 0.03\n  quartile: 1.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_quartile"] == 0.25  # default

    def test_topix_drawdown_threshold_positive_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "regime:\n  topix_drawdown_threshold: 0.10\n  topix_size_multiplier_bear: 0.5\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_drawdown_threshold"] == -0.15  # default

    def test_topix_size_multiplier_bear_over_one_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "regime:\n  topix_drawdown_threshold: -0.15\n  topix_size_multiplier_bear: 1.5\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_size_multiplier_bear"] == 0.5  # default
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_signal_generator.py::TestLoadStrategyConfigSectorRegime -v
```

期待: `KeyError: 'sector_boost'` などで FAIL（キーがまだ存在しない）

- [ ] **Step 3: `_STRATEGY_CONFIG_DEFAULTS` に 4 キーを追加する**

`src/kabusys/strategy/signal_generator.py` の `_STRATEGY_CONFIG_DEFAULTS` (line 91) を以下に変更する:

```python
_STRATEGY_CONFIG_DEFAULTS: dict = {
    "weights": {k: v for k, v in _DEFAULT_WEIGHTS.items()},
    "threshold": _DEFAULT_THRESHOLD,
    "stop_loss_rate": _STOP_LOSS_RATE,
    "gap_up_threshold": _GAP_UP_THRESHOLD,
    "gap_down_threshold": _GAP_DOWN_THRESHOLD,
    "min_holding_days": _MIN_HOLDING_DAYS,
    "max_holding_days": _MAX_HOLDING_DAYS,
    "trailing_stop_atr_mult": _TRAILING_STOP_ATR_MULT,
    "reentry_cooldown_days": _REENTRY_COOLDOWN_DAYS,
    "sector_boost": _SECTOR_BOOST,
    "sector_quartile": _SECTOR_QUARTILE,
    "topix_drawdown_threshold": _TOPIX_DRAWDOWN_THRESHOLD,
    "topix_size_multiplier_bear": _TOPIX_SIZE_MULTIPLIER_BEAR,
}
```

- [ ] **Step 4: `_load_strategy_config()` の docstring を更新する**

`_load_strategy_config()` の Returns docstring (lines 119-129) を以下に変更する:

```python
    Returns:
        {
            "weights": dict[str, float],
            "threshold": float,
            "stop_loss_rate": float,
            "gap_up_threshold": float,
            "gap_down_threshold": float,
            "min_holding_days": int,
            "max_holding_days": int,
            "trailing_stop_atr_mult": float,
            "reentry_cooldown_days": int,
            "sector_boost": float,
            "sector_quartile": float,
            "topix_drawdown_threshold": float,
            "topix_size_multiplier_bear": float,
        }
```

- [ ] **Step 5: `_load_strategy_config()` に sector/regime 解析を追加する**

`_load_strategy_config()` 内の `# int スカラーパラメータ` ブロックの直後（line 229 の `_strategy_config_cache = result` の前）に以下を挿入する:

```python
    # sector セクション
    sec = data.get("sector")
    if isinstance(sec, dict):
        v = sec.get("boost")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and float(v) >= 0
        ):
            result["sector_boost"] = float(v)

        v = sec.get("quartile")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and 0.0 < float(v) < 1.0
        ):
            result["sector_quartile"] = float(v)

    # regime セクション
    reg = data.get("regime")
    if isinstance(reg, dict):
        v = reg.get("topix_drawdown_threshold")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and float(v) < 0
        ):
            result["topix_drawdown_threshold"] = float(v)

        v = reg.get("topix_size_multiplier_bear")
        if (
            v is not None
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            and 0.0 < float(v) <= 1.0
        ):
            result["topix_size_multiplier_bear"] = float(v)
```

- [ ] **Step 6: テストが通ることを確認する**

```
pytest tests/test_signal_generator.py::TestLoadStrategyConfigSectorRegime -v
```

期待: 8 件 PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "feat: _load_strategy_config に sector/regime セクション解析を追加"
```

---

## Task 2: `_calc_sector_strengths()` を `sector_quartile` パラメータ化する

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py:533-598`（`_calc_sector_strengths` 定義）
- Modify: `src/kabusys/strategy/signal_generator.py:1184-1186`（`generate_signals` 内の呼び出し箇所）
- Modify: `tests/test_signal_generator.py`（末尾に追加）

### Step 1: 失敗するテストを書く

`tests/test_signal_generator.py` の末尾に追加する:

```python
# ---------------------------------------------------------------------------
# Task 2: _calc_sector_strengths sector_quartile パラメータ
# ---------------------------------------------------------------------------

from kabusys.strategy.signal_generator import _calc_sector_strengths  # noqa: E402


class TestCalcSectorStrengthsQuartile:
    """_calc_sector_strengths の sector_quartile パラメータテスト。"""

    def _setup_4sectors(self, conn) -> None:
        """4セクター・4銘柄・21日分の価格データを挿入する。"""
        sectors = [
            ("1001", "製造業", 1.10),
            ("1002", "金融業", 1.05),
            ("1003", "情報通信", 1.02),
            ("1004", "小売業", 0.98),
        ]
        for code, sector, _ in sectors:
            conn.execute(
                "INSERT INTO stocks (code, sector) VALUES (?, ?)", [code, sector]
            )
        base = date(2026, 1, 1)
        for j in range(21):
            d = base + timedelta(days=j)
            for code, _, ret in sectors:
                c = 1000.0 * ret if j == 20 else 1000.0
                conn.execute(
                    "INSERT INTO prices_daily (date, code, open, high, low, close, volume)"
                    " VALUES (?, ?, 1000, 1000, 1000, ?, 1000)",
                    [d, code, c],
                )

    def test_default_quartile_gives_1_top_sector(self, conn):
        self._setup_4sectors(conn)
        top, _, _ = _calc_sector_strengths(conn, date(2026, 1, 21))
        assert len(top) == 1  # ceil(4 * 0.25) = 1

    def test_custom_quartile_50_gives_2_top_sectors(self, conn):
        self._setup_4sectors(conn)
        top, _, _ = _calc_sector_strengths(conn, date(2026, 1, 21), sector_quartile=0.50)
        assert len(top) == 2  # ceil(4 * 0.50) = 2
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_signal_generator.py::TestCalcSectorStrengthsQuartile -v
```

期待: `TypeError: _calc_sector_strengths() got an unexpected keyword argument 'sector_quartile'` で FAIL

- [ ] **Step 3: `_calc_sector_strengths()` のシグネチャと本体を更新する**

`src/kabusys/strategy/signal_generator.py` の `_calc_sector_strengths` 定義（line 533-534）を以下に変更する:

```python
def _calc_sector_strengths(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    sector_quartile: float = _SECTOR_QUARTILE,
) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
```

同関数内の `_SECTOR_QUARTILE` の使用箇所（lines 594-595）を以下に変更する:

```python
    top_n = max(1, math.ceil(n * sector_quartile))
    bottom_n = max(1, math.ceil(n * sector_quartile))
```

- [ ] **Step 4: `generate_signals()` の呼び出し箇所を更新する**

`generate_signals()` 内の `_calc_sector_strengths` 呼び出し（lines 1184-1186）を以下に変更する:

```python
        top_sectors, bottom_sectors, sector_map = _calc_sector_strengths(
            conn, target_date, sector_quartile=_cfg["sector_quartile"]
        )
```

- [ ] **Step 5: テストが通ることを確認する**

```
pytest tests/test_signal_generator.py::TestCalcSectorStrengthsQuartile -v
```

期待: 2 件 PASS

- [ ] **Step 6: 既存テストが壊れていないことを確認する**

```
pytest tests/test_signal_generator.py -v --tb=short
```

期待: 全件 PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "feat: _calc_sector_strengths に sector_quartile パラメータを追加"
```

---

## Task 3: `_get_topix_size_multiplier()` をパラメータ化する

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py:447-492`（`_get_topix_size_multiplier` 定義）
- Modify: `src/kabusys/strategy/signal_generator.py:1093`（`generate_signals` 内の呼び出し箇所）
- Modify: `tests/test_signal_generator.py`（`TestGetTopixSizeMultiplier` クラスに追加）

### Step 1: 失敗するテストを書く

`tests/test_signal_generator.py` の `TestGetTopixSizeMultiplier` クラス（line 624）の末尾に追加する:

```python
    def test_custom_drawdown_threshold_and_multiplier(self, conn):
        """カスタム drawdown_threshold と size_multiplier_bear が適用されることを確認する。"""
        # 240日は 2000.0、直近11日は 1600.0（乖離率≈-20%）
        self._make_topix_series(
            conn, TARGET_DATE - timedelta(days=250), 240, 2000.0, 2000.0
        )
        recent_start = TARGET_DATE - timedelta(days=10)
        self._make_topix_series(conn, recent_start, 11, 1600.0, 1600.0)

        # drawdown_threshold=-0.10 → 乖離率-20% < -10% → Bear 判定 → 0.3 を返す
        result = _get_topix_size_multiplier(
            conn, TARGET_DATE, drawdown_threshold=-0.10, size_multiplier_bear=0.3
        )
        assert result == 0.3

    def test_custom_threshold_not_triggered(self, conn):
        """乖離率が drawdown_threshold を超えない場合は 1.0 を返すことを確認する。"""
        # 250日すべて 2000.0（乖離率≈0%）
        self._make_topix_series(
            conn, TARGET_DATE - timedelta(days=250), 250, 2000.0, 2000.0
        )
        # drawdown_threshold=-0.10 → 乖離率≈0% > -10% → Bear 未判定 → 1.0
        result = _get_topix_size_multiplier(
            conn, TARGET_DATE, drawdown_threshold=-0.10, size_multiplier_bear=0.3
        )
        assert result == 1.0
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_signal_generator.py::TestGetTopixSizeMultiplier::test_custom_drawdown_threshold_and_multiplier tests/test_signal_generator.py::TestGetTopixSizeMultiplier::test_custom_threshold_not_triggered -v
```

期待: `TypeError: _get_topix_size_multiplier() got an unexpected keyword argument 'drawdown_threshold'` で FAIL

- [ ] **Step 3: `_get_topix_size_multiplier()` のシグネチャと本体を更新する**

`src/kabusys/strategy/signal_generator.py` の `_get_topix_size_multiplier` 定義（lines 447-492）のシグネチャを以下に変更する:

```python
def _get_topix_size_multiplier(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    drawdown_threshold: float = _TOPIX_DRAWDOWN_THRESHOLD,
    size_multiplier_bear: float = _TOPIX_SIZE_MULTIPLIER_BEAR,
) -> float:
```

同関数内の判定ロジック（line 490-491）を以下に変更する:

```python
    if ma200 > 0 and (close / ma200 - 1.0) < drawdown_threshold:
        return size_multiplier_bear
```

- [ ] **Step 4: `generate_signals()` の呼び出し箇所を更新する**

`generate_signals()` 内の `_get_topix_size_multiplier` 呼び出し（line 1093）を以下に変更する:

```python
    topix_multiplier = _get_topix_size_multiplier(
        conn,
        target_date,
        drawdown_threshold=_cfg["topix_drawdown_threshold"],
        size_multiplier_bear=_cfg["topix_size_multiplier_bear"],
    )
```

- [ ] **Step 5: テストが通ることを確認する**

```
pytest tests/test_signal_generator.py::TestGetTopixSizeMultiplier -v
```

期待: 6 件（既存 4 + 新規 2）すべて PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py tests/test_signal_generator.py
git commit -m "feat: _get_topix_size_multiplier に drawdown_threshold / size_multiplier_bear パラメータを追加"
```

---

## Task 4: `generate_signals()` で `sector_boost` を `_cfg` から読む + YAML 更新

**Files:**
- Modify: `src/kabusys/strategy/signal_generator.py:1221`（`generate_signals` 内 sector_boost 使用箇所）
- Modify: `config/strategy_config.yaml`（sector/regime セクション追加）

### Step 1: `generate_signals()` 内の `_SECTOR_BOOST` を `_cfg["sector_boost"]` に変える

`generate_signals()` 冒頭の `_cfg` 抽出ブロック（line 1028 周辺）に以下を追加する:

```python
    _cfg = _load_strategy_config()
    if threshold is None:
        threshold = _cfg["threshold"]
    if weights is None:
        weights = _cfg["weights"]
    if min_holding_days is None:
        min_holding_days = _cfg["min_holding_days"]
    if max_holding_days is None:
        max_holding_days = _cfg["max_holding_days"]
    if trailing_stop_atr is None:
        trailing_stop_atr = _cfg["trailing_stop_atr_mult"]
    sector_boost = _cfg["sector_boost"]  # ← 追加
```

`generate_signals()` 内の `_SECTOR_BOOST` の使用箇所（line 1221）を以下に変更する:

```python
            final_score += sector_boost
```

- [ ] **Step 2: `config/strategy_config.yaml` に sector/regime セクションを追加する**

ファイル末尾（`value_score:` セクションの後）に追加する:

```yaml
sector:
  # 上位セクター銘柄への final_score 加算量（≥ 0）
  boost: 0.03
  # 上位・下位セクターの区切り割合（0 < x < 1）
  quartile: 0.25

regime:
  # TOPIX 200MA 乖離率がこの値以下で地合い悪化と判定（負値）
  topix_drawdown_threshold: -0.15
  # 地合い悪化時の size_multiplier（0 < x ≤ 1）
  topix_size_multiplier_bear: 0.5
```

- [ ] **Step 3: 全テストを実行して PASS を確認する**

```
pytest tests/ -v --tb=short
```

期待: 全件 PASS（既存テストへの影響なし）

- [ ] **Step 4: ruff チェック**

```
ruff check src/kabusys/strategy/signal_generator.py
ruff format --check src/kabusys/strategy/signal_generator.py
```

期待: エラーなし（フォーマット差分があれば `ruff format` を実行して修正）

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/strategy/signal_generator.py config/strategy_config.yaml
git commit -m "feat: generate_signals で sector_boost を cfg から読み取り、strategy_config.yaml に sector/regime セクションを追加"
```
