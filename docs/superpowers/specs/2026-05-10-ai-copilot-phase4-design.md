# AI Co-Pilot Phase 4 — パラメータ自動反映・バックテスト再実行ループ 設計仕様

**Issue:** #279  
**前提:** Issue #233 (AI Co-Pilot Phase 1-3) 完了済み

---

## 1. 概要

AI Co-Pilot ウィザード（Phase 1-3）の拡張。AI がテキスト提案に加えて JSON ブロックでパラメータ変更案を出力し、ユーザーが確認・適用→バックテスト再実行→変更前後の比較までを Co-Pilot タブ内で完結できるようにする。

**目標:**
- AI 提案パラメータを UI で確認し、ワンクリックで `strategy_config.yaml` に適用
- 適用前に自動バックアップ、UI からのロールバックを提供
- ホワイトリスト外キーの変更を防止
- 適用後にバックテストをサブプロセスで再実行し、変更前後の指標を並列表示

---

## 2. アーキテクチャ

### 新規ファイル

| ファイル | 責務 |
|---|---|
| `src/kabusys/ai/param_extractor.py` | AI 返答テキストから JSON ブロックを抽出・ホワイトリスト検証 |
| `src/kabusys/ai/config_manager.py` | YAML 読み取り・バックアップ・書き込み・ロールバック |
| `src/kabusys/monitoring/components/param_review.py` | Streamlit UI: レビュー・適用・サブプロセス実行・比較表示 |

### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `src/kabusys/monitoring/components/ai_wizard.py` | システムプロンプト更新、`render()` シグネチャ拡張、`param_review` 呼び出し追加 |
| `src/kabusys/monitoring/pages/10_Strategy_Lab.py` | `render_wizard()` に `duckdb_path` / `config_path` を追加 |

### テストファイル

| ファイル | 内容 |
|---|---|
| `tests/test_param_extractor.py` | JSON 抽出・ホワイトリスト検証 |
| `tests/test_config_manager.py` | バックアップ・適用・ロールバック（tempfile） |
| `tests/test_param_review.py` | session_state 変化・subprocess mock・ロールバック動作 |

---

## 3. 詳細設計

### 3-1. システムプロンプト変更 (`ai_wizard.py`)

`_SYSTEM_PROMPT_TEMPLATE` 末尾に以下を追記する:

```
改善案がある場合は、回答末尾に必ず以下の形式で JSON ブロックを出力してください。
変更不要なパラメータは含めないでください。
weights は変更する重みキーのみ含めてください（例: {"weights": {"momentum": 0.45}}）。

```json
{"threshold": 0.65, "trailing_stop_atr_mult": 2.5}
```
```

---

### 3-2. `param_extractor.py`

```python
ALLOWED_KEYS = frozenset({
    "weights", "threshold", "sector_boost", "sector_quartile",
    "stop_loss_rate", "trailing_stop_atr_mult",
    "gap_up_threshold", "gap_down_threshold",
    "min_holding_days", "max_holding_days",
    "topix_drawdown_threshold", "topix_size_multiplier_bear",
})

ALLOWED_WEIGHT_KEYS = frozenset({
    "momentum", "value", "volatility", "liquidity", "news",
})

def extract_params(text: str) -> dict | None:
    """AI 返答テキストの末尾 ```json ... ``` ブロックを抽出し、ホワイトリスト検証済み dict を返す。

    - JSON ブロックが存在しない場合は None を返す。
    - ホワイトリスト外キーはそのキーのみ除外し、警告ログを出す。
    - weights は ALLOWED_WEIGHT_KEYS のキーのみ許可。
    - 有効なキーが 1 つも残らない場合は None を返す。
    """
```

実装詳細:
- `re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)` で全ブロックを抽出し、最後の要素を使用
- `json.loads()` でパース、失敗時は警告ログを出して None を返す
- ホワイトリスト外キーを除外後、残ったキーが 0 件なら None を返す

---

### 3-3. `config_manager.py`

```python
BACKUP_DIR = Path("config/backups")

def backup_config(config_path: Path, backup_dir: Path = BACKUP_DIR) -> Path:
    """strategy_config.yaml を config/backups/strategy_config_YYYYMMDD_HHMMSS.yaml にコピー。
    戻り値: バックアップファイルの Path。"""

def apply_params(config_path: Path, params: dict) -> None:
    """params の各キーを strategy_config.yaml の該当セクションに上書き保存。

    セクションマッピング:
    - weights.*              → strategy.weights.*（他ファクターは保持）
    - threshold, stop_loss_rate, trailing_stop_atr_mult,
      min_holding_days, max_holding_days,
      gap_up_threshold, gap_down_threshold  → strategy.*
    - sector_boost           → sector.boost
    - sector_quartile        → sector.quartile
    - topix_drawdown_threshold, topix_size_multiplier_bear → regime.*

    YAML 全体を読み込み→パッチ→書き戻す。コメントは失われる。"""

def list_backups(backup_dir: Path = BACKUP_DIR) -> list[Path]:
    """タイムスタンプ降順でバックアップ Path 一覧を返す。"""

def restore_backup(backup_path: Path, config_path: Path) -> None:
    """指定バックアップを config_path に上書き復元。"""
```

---

### 3-4. `param_review.py`

#### シグネチャ

```python
def render_param_review(
    suggested_params: dict,
    config_path: Path,
    duckdb_path: Path,
    prev_run_id: str | None,
) -> None:
```

#### UI フロー

```
┌─ 📋 AI 提案パラメータ ────────────────────────────────┐
│  パラメータ            現在値     → 提案値              │
│  threshold             0.60         0.65               │
│  trailing_stop_atr_…   2.0          2.5                │
├──────────────────────────────────────────────────────── │
│  [✅ 適用する]  [❌ キャンセル]                        │
├─ 適用後: バックテスト再実行 ──────────────────────────── │
│  開始日 [YYYY-MM-DD]  終了日 [YYYY-MM-DD]              │
│  （最新バックテストの期間で初期化）                     │
│  [▶ バックテスト実行]   [⏪ ロールバック]              │
├─ 比較結果 ──────────────────────────────────────────── │
│  指標        変更前    変更後    差分                   │
│  CAGR        +12.3%   +14.1%   +1.8%                  │
│  Sharpe      1.23     1.41     +0.18                   │
│  MaxDD       -18.5%   -16.2%   +2.3%                  │
└──────────────────────────────────────────────────────── ┘
```

#### session_state キー

| キー | 型 | 内容 |
|---|---|---|
| `param_review_suggested` | `dict \| None` | extract_params() の結果（再レンダリング時に提案 UI を維持するため保持） |
| `param_review_applied` | `bool` | True = 適用済み |
| `param_review_backup_path` | `str` | バックアップファイルパス |
| `param_review_prev_run_id` | `str \| None` | 変更前 run_id |
| `param_review_new_run_id` | `str \| None` | 変更後 run_id（subprocess 完了後） |

#### バックテスト subprocess 呼び出し

```python
result = subprocess.run(
    [
        sys.executable, "-m", "kabusys.backtest.run",
        "--start", start.isoformat(),
        "--end", end.isoformat(),
        "--db", str(duckdb_path),
        "--output-format", "json",
    ],
    capture_output=True, text=True, timeout=600,
)
```

- `st.status("バックテスト実行中...")` ブロック内で実行
- stdout を `json.loads()` して `run_id` を取得
- 終了コード != 0 の場合は stderr を `st.error()` で表示
- 成功後 `st.session_state["param_review_new_run_id"] = run_id` をセット→ `st.rerun()`

#### 比較表示

`prev_run_id` と `new_run_id` を使って DuckDB から各行を取得し、CAGR / Sharpe / Max Drawdown / Win Rate / Total Trades を並列表示。差分は符号付きで色付け（改善=緑、悪化=赤）。

#### ロールバック

- 「⏪ ロールバック」ボタンは `param_review_applied=True` の間常時表示
- クリック時: `restore_backup(backup_path, config_path)` → session_state をリセット → `st.rerun()`

---

### 3-5. `ai_wizard.py` の変更

#### シグネチャ

```python
def render(
    duckdb_conn: duckdb.DuckDBPyConnection,
    sqlite_conn: sqlite3.Connection,
    duckdb_path: Path,
    config_path: Path,
) -> None:
```

#### ストリーミング完了後の追加処理

```python
if response_text:
    db.save_wizard_message(session_id, "assistant", str(response_text))
    suggested = extract_params(str(response_text))
    if suggested:
        st.session_state["param_review_suggested"] = suggested

# 再レンダリング時も提案 UI を維持するため、session_state を確認して常時呼び出す
if st.session_state.get("param_review_suggested") or st.session_state.get("param_review_applied"):
    render_param_review(
        suggested_params=st.session_state.get("param_review_suggested", {}),
        config_path=config_path,
        duckdb_path=duckdb_path,
        prev_run_id=prev_run_id,
    )
```

`prev_run_id` は `load_latest_summary` 呼び出し前に同一クエリで取得する（`SELECT run_id FROM backtest_runs ORDER BY created_at DESC LIMIT 1`）。

「❌ キャンセル」クリック時は `render_param_review` 内で `param_review_suggested` をリセットして `st.rerun()`。

---

### 3-6. `10_Strategy_Lab.py` の変更

```python
with tab_copilot:
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
    try:
        init_monitoring_db(sqlite_conn)
        render_wizard(
            conn,
            sqlite_conn,
            duckdb_path=settings.duckdb_path,
            config_path=Path("config/strategy_config.yaml"),
        )
    finally:
        sqlite_conn.close()
```

---

## 4. ホワイトリスト詳細

| パラメータ | 型 | 値域 |
|---|---|---|
| `weights.momentum` | float | 0.0〜1.0 |
| `weights.value` | float | 0.0〜1.0 |
| `weights.volatility` | float | 0.0〜1.0 |
| `weights.liquidity` | float | 0.0〜1.0 |
| `weights.news` | float | 0.0〜1.0 |
| `threshold` | float | 0.0〜1.0 |
| `sector_boost` | float | 0.0〜1.0 |
| `sector_quartile` | float | 0.0〜1.0（exclusive） |
| `stop_loss_rate` | float | -1.0〜0.0 |
| `trailing_stop_atr_mult` | float | 0.1〜10.0 |
| `gap_up_threshold` | float | 0.0〜1.0 |
| `gap_down_threshold` | float | -1.0〜0.0 |
| `min_holding_days` | int | 0〜365 |
| `max_holding_days` | int | 1〜365 |
| `topix_drawdown_threshold` | float | -1.0〜0.0 |
| `topix_size_multiplier_bear` | float | 0.0〜1.0 |

値域チェックは `param_extractor.extract_params()` 内で実施。範囲外の値は警告ログを出してそのキーを除外。

---

## 5. エラーハンドリング

| ケース | 対応 |
|---|---|
| AI が JSON ブロックを出力しない | `extract_params()` が None → `render_param_review` を呼ばない（通常チャットのまま） |
| JSON パース失敗 | 警告ログ、None を返す |
| ホワイトリスト外キーのみ | None を返す、エラー表示なし（ユーザーは通常テキスト回答を見る） |
| バックアップ作成失敗 | `st.error()` 表示、config 変更は行わない |
| subprocess タイムアウト（600s） | `st.error()` 表示、config は変更済みのまま（ロールバックボタンで対処） |
| subprocess 終了コード != 0 | `st.error()` に stderr を表示 |

---

## 6. テスト方針

### `test_param_extractor.py`

- JSON ブロックあり → 正常抽出
- JSON ブロックなし → None
- ホワイトリスト外キーのみ → None（ログ確認）
- ホワイトリスト外キーが混在 → 外キー除外して残りを返す
- weights に未知ファクターキー → 除外
- 値域外の数値 → そのキーを除外
- 不正 JSON → None

### `test_config_manager.py`

- `backup_config`: ファイル名パターン確認、元ファイルの内容が保持される
- `apply_params`: 各セクションへの正しいマッピング（tempfile 使用）
- `apply_params` weights: 指定キーのみ更新、他ファクターは保持
- `list_backups`: タイムスタンプ降順
- `restore_backup`: バックアップ内容が復元される

### `test_param_review.py`

- 適用ボタン押下 → `param_review_applied=True`、`param_review_backup_path` がセット
- subprocess mock 成功 → `param_review_new_run_id` がセット
- subprocess mock 失敗（returncode != 0）→ `st.error` 呼び出し確認
- ロールバックボタン → `restore_backup` が呼ばれ session_state がリセット
- `suggested_params` が空 dict → コンポーネントが何も表示しない
