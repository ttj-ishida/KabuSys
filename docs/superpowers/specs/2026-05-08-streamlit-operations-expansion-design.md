# Streamlit 運用フロー拡張（8ページ構成） — 設計仕様

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 既存 4 ページの Streamlit ダッシュボードを 8 ページ（Home 除く）構成に拡張し、KabuSys の日次運用フロー全体（初期構築→朝の確認→執行→ザラ場→障害対応）を UI から確認できるようにする。

**Architecture:** 新ページ用の DB クエリを `operations_data.py` に集約（`dashboard_data.py` は監視エンジン系のまま維持）。各ページはドメインモジュール（`pre_market_collector`・`validate_config` 等）を直接呼び出す。`validate_config.py` に `run_checks() -> ValidationResult` を追加してモジュールレベルグローバルを隠蔽する。

**Tech Stack:** Streamlit, DuckDB (read-only), SQLite (read-only), Python dataclasses

**Issue:** #260

---

## 1. ファイル構成

### 1.1 新規作成

| ファイル | 役割 |
|---------|------|
| `src/kabusys/monitoring/operations_data.py` | 運用系ページ用 DB クエリ・ドメイン集約関数 |
| `src/kabusys/monitoring/pages/2_Initial_Setup.py` | 環境設定・DB・Task Scheduler 確認ページ |
| `src/kabusys/monitoring/pages/3_Pre_Market.py` | 朝の READY/BLOCKED 判定ページ |
| `src/kabusys/monitoring/pages/4_Execution_Startup.py` | 起動直後の差分確認ページ |
| `src/kabusys/monitoring/pages/5_Intraday_Monitor.py` | ザラ場監視ページ（自動更新付き） |
| `src/kabusys/monitoring/pages/8_Failure_Recovery.py` | 障害対応集約ビュー |

### 1.2 リネーム（内容変更なし）

| 変更前 | 変更後 |
|--------|--------|
| `pages/1_WebManual.py` | `pages/9_WebManual.py` |
| `pages/2_Signal_Queue.py` | `pages/6_Signal_Queue.py` |
| `pages/3_Performance.py` | `pages/7_Performance.py` |
| `pages/4_Strategy_Lab.py` | `pages/10_Strategy_Lab.py` |

### 1.3 変更

| ファイル | 変更内容 |
|---------|---------|
| `src/kabusys/validate_config.py` | `ValidationResult` dataclass と `run_checks()` 関数を追加 |
| `src/kabusys/monitoring/pages/7_Performance.py` | Paper Verification タブを追加 |
| `src/kabusys/monitoring/streamlit_dashboard.py` | Home の Overview タブを簡略化（ザラ場監視情報を Intraday Monitor へ移動） |

### 1.4 最終サイドバー順

```
🏠 Home
⚙️  2 Initial Setup
🌅  3 Pre Market
🚀  4 Execution Startup
📡  5 Intraday Monitor
📋  6 Signal Queue
📈  7 Performance
🚨  8 Failure Recovery
📖  9 WebManual
🔬 10 Strategy Lab
```

---

## 2. `validate_config.py` リファクタリング

### 2.1 追加するデータクラスと関数

```python
from dataclasses import dataclass

@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    infos: list[str]

    @property
    def status(self) -> str:
        """OK / WARNING / ERROR を返す。"""
        if self.errors:
            return "ERROR"
        if self.warnings:
            return "WARNING"
        return "OK"


def run_checks() -> ValidationResult:
    """全チェックを実行して ValidationResult を返す。

    モジュールレベルのグローバルをリセットしてから各チェックを呼び出す。
    CLI エントリポイント（__main__）もこの関数を使うよう変更する。
    """
    global _errors, _warnings, _infos
    _errors, _warnings, _infos = [], [], []
    _check_required_env_vars()
    _check_optional_env_vars()
    _check_config_files()
    _check_db_files()
    return ValidationResult(
        errors=list(_errors),
        warnings=list(_warnings),
        infos=list(_infos),
    )
```

### 2.2 DB ファイル確認チェック（新規追加）

`run_checks()` 内で `_check_db_files()` を呼ぶ。確認対象:
- `settings.duckdb_path` — 存在しない場合 ERROR
- `settings.sqlite_path` — 存在しない場合 WARNING
- `settings.paper_trading_sqlite_path` — `KABUSYS_ENV=paper_trading` かつ存在しない場合 WARNING

### 2.3 後方互換性

既存の `if __name__ == "__main__":` ブロックは `run_checks()` を呼ぶ形に変更する。CLI 出力・終了コードの挙動は変わらない。

---

## 3. `operations_data.py` の設計

```python
"""operations_data.py — 運用系 Streamlit ページ用のデータ取得関数。

dashboard_data.py（監視エンジン系）と責務を分離する。
Streamlit に依存しないため単体テスト可能。
"""

# Pre-Market 用
def load_premarket_data(
    duckdb_conn,
    sqlite_conn: sqlite3.Connection,
    settings: Settings,
) -> dict:
    """pre_market_collector.collect() を呼び出し、表示用 dict に変換する。
    戻り値: {"status": "READY"|"BLOCKED", "items": [...], "generated_at": str}
    """

# Execution Startup 用
def load_execution_startup(artifacts_dir: Path) -> dict | None:
    """artifacts/execution_startup/{today}/summary.json を読み込む。
    ファイルが存在しない場合は None を返す。
    """

# Intraday Monitor 用
def load_intraday_summary(
    sqlite_conn: sqlite3.Connection,
    hours: int = 1,
) -> dict:
    """risk_logs / trade_logs / dashboard テーブルを集計して返す。
    戻り値: {"order_errors": int, "stale_orders": int, "drawdown_pct": float, ...}
    """

# Failure Recovery 用
def load_failure_summary(sqlite_conn: sqlite3.Connection) -> dict:
    """直近 24 時間の CRITICAL/KILL_SWITCH/ORDER_ERROR イベントを集計する。
    戻り値: {"critical_count": int, "kill_switch_active": bool, "recent_events": list[dict]}
    """

# Paper Verification 用（Performance ページ拡張）
def load_paper_verification_data(
    paper_sqlite_conn: sqlite3.Connection,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> dict:
    """paper_verification_report の集計ロジックを再利用して dict を返す。
    戻り値: {"uptime_pct": float, "send_rate_pct": float, "fill_rate_pct": float,
             "p95_latency_ms": float | None, "pass_fail": str}
    """
```

---

## 4. 各ページの仕様

### 4.1 2_Initial_Setup.py

**データソース:** `validate_config.run_checks()`, ファイルシステム, `pre_market_collector.check_task_scheduler()`

**レイアウト:**

```
[ERROR / WARNING / OK バナー（大）]
── タブ: 環境変数 | 設定ファイル | DB ファイル | Task Scheduler
   環境変数タブ:
     - 必須変数（各行 ✅/❌ + 値の有無のみ表示、値は非表示）
     - オプション変数（各行 ✅/⚠️）
   設定ファイルタブ:
     - config/*.yaml の存在確認（各行 ✅/❌）
   DB ファイルタブ:
     - DuckDB / SQLite / paper DB の存在・ファイルサイズ表示
   Task Schedulerタブ:
     - KabuSys_* タスクの Ready 状態（各行 ✅/❌）
     - schtasks が利用不可の場合は「Windows 環境外では確認不可」と表示
── サイドバー: Refresh ボタン（手動のみ。自動更新なし）
```

**エラーハンドリング:** `run_checks()` が例外を投げた場合は `st.error()` で表示してページを継続。

### 4.2 3_Pre_Market.py

**データソース:** `operations_data.load_premarket_data()` → `pre_market_collector.collect()`

**レイアウト（ステータス優先型）:**

```
[READY（緑）/ BLOCKED（赤）バナー（大）]
── カードグリッド（2行×3列）:
   データ鮮度 ✅/❌ | Signal Queue pending件数 | Task Scheduler ✅/❌
   停止フラグ ✅/❌ | ポジション数             | 生成時刻
── BLOCKED 時: 失敗項目のみ赤ハイライト
── サイドバー: Refresh ボタン（手動のみ）
```

**BLOCKED 判定条件（`pre_market_report._determine_status()` に準拠）:**
- `signal_queue_pending == 0`（本日 pending シグナルなし）
- `stop_flag_exists == True`（停止フラグが立っている）
- `task_scheduler_ready == False`（KabuSys_ExecutionStart が Ready でない）

**READY_WITH_WARNINGS 判定条件（BLOCKED でない場合）:**
- `data_freshness_ok == False`（prices_daily が 3 日以上古い）

**注意:** DuckDB（`prices_daily`・`signal_queue`）と SQLite（`positions`）の両方を read-only で接続する。

### 4.3 4_Execution_Startup.py

**データソース:** `operations_data.load_execution_startup(Path("artifacts/execution_startup"))`

**レイアウト:**

```
[READY（緑）/ READY_WITH_WARNINGS（黄）/ BLOCKED（赤）バナー]
── メトリクス: orders_synced | orders_no_status | position_discrepancies件数
── position_discrepancies テーブル（差分あり時のみ展開表示）
── warnings リスト（⚠️ アイコン付き）
── ファイルが存在しない場合: "本日の Execution はまだ起動していません" と表示
── サイドバー: 対象日付セレクター（デフォルト: today）+ Refresh ボタン
```

`load_execution_startup()` は `Path("artifacts/execution_startup") / date_str / "summary.json"` を読み込む。

### 4.4 5_Intraday_Monitor.py

**データソース:** SQLite（monitoring DB）、`operations_data.load_intraday_summary()`

**レイアウト:**

```
── 上部ステータス行: Kill Switch 状態 | Execution プロセス | Monitoring プロセス
── メトリクス行: ドローダウン% | 注文エラー（直近1h） | 滞留注文（直近1h）
── タブ: Risk Logs | Trade Logs
   Risk Logs タブ: risk_logs 直近 50 件テーブル（logged_at DESC）
   Trade Logs タブ: trade_logs 直近 50 件テーブル（logged_at DESC）
── サイドバー: 自動更新間隔 [30 / 60 / 120 秒] セレクター
```

**自動更新:** `time.sleep(interval); st.rerun()` パターン（Home と同様）。

**Home の簡略化:** Home の Overview タブから `注文エラー（直近1h）` / `滞留注文（直近1h）` / `risk_logs テーブル` を削除し、「詳細は Intraday Monitor ページへ」リンクを追加。

### 4.5 8_Failure_Recovery.py

**データソース:** `operations_data.load_failure_summary()`、PID ファイル確認

**レイアウト:**

```
── 上部: Kill Switch 状態（ON なら赤バナー）
── PID 状態: Execution / Monitoring プロセスの生存確認
── メトリクス: 直近24h CRITICAL件数 | KILL_SWITCH件数 | ORDER_ERROR件数
── イベントテーブル: CRITICAL / KILL_SWITCH / RISK_BREACH / ORDER_ERROR（直近24h）
── 復旧手順リンクセクション:
   - Kill Switch が発動した → [Failure Recovery WebManual へ]
   - 注文エラーが多い → [TradingRunbook へ]
   - ポジション差分あり → [Position Reconciliation Report の実行方法]
── 危険操作ボタンは一切持たない（確認・導線のみ）
── サイドバー: Refresh ボタン（手動のみ）
```

### 4.6 7_Performance.py（拡張）

**追加タブ:** Paper Verification

```
既存タブ（変更なし）: エクイティカーブ | ポジション | 取引履歴
追加タブ: Paper Verification
  ── KABUSYS_ENV != "paper_trading" の場合: "paper_trading 環境でのみ表示" と案内して終了
  ── paper DB 接続（PAPER_TRADING_SQLITE_PATH）
  ── 期間セレクター（from / to、デフォルト直近30日）
  ── メトリクス: 稼働率% | 送信率% | 約定率% | P95レイテンシ ms
  ── Pass/Fail 判定バナー（閾値: 稼働率≥99%, 約定率≥90%, 送信率≥95%, P95≤200ms）
```

---

## 5. 共通設計方針

### 5.1 DB 接続

- DuckDB: `duckdb.connect(str(settings.duckdb_path), read_only=True)` — 分析系ページのみ
- SQLite (monitoring): `sqlite3.connect(uri, uri=True)` read-only URI モード
- SQLite (paper trading): `sqlite3.connect(str(settings.paper_trading_sqlite_path))` read-only URI モード
- 各ページは `try/finally` で接続を確実にクローズする

### 5.2 エラーハンドリング

- DB ファイルが存在しない → `st.error()` を表示してページを停止（`st.stop()`）
- DB ファイルが存在するが読み取り失敗 → `st.error()` を表示
- ドメイン関数が例外 → `st.error()` + トレースバックを `st.exception()` で展開

### 5.3 自動更新

- 自動更新は **5_Intraday_Monitor のみ**（30/60/120秒）
- 他ページは手動 Refresh ボタンのみ（`st.button("🔄 Refresh") → st.rerun()`）

### 5.4 secrets の非表示

- `2_Initial_Setup.py` の環境変数表示: 値は表示せず「設定済み / 未設定」のみ表示

---

## 6. テスト方針

### 6.1 `validate_config.run_checks()` のテスト

- 必須環境変数が未設定 → `result.status == "ERROR"`
- 全変数設定済み → `result.status == "OK"` または `"WARNING"`
- 2回連続呼び出しで結果が独立していること（グローバルリセットの確認）

### 6.2 `operations_data.py` のテスト

- `load_premarket_data()`: モック DB で各フィールドを確認
- `load_execution_startup()`: ファイルあり / なし の両ケース
- `load_intraday_summary()`: 空 DB で 0 件返却を確認
- `load_failure_summary()`: CRITICAL イベントが集計されることを確認
- `load_paper_verification_data()`: 空 DB で None/0 返却を確認

### 6.3 Streamlit ページ

Streamlit ページ自体の自動テストは行わない（UI は手動確認）。データ取得ロジックは `operations_data.py` のテストでカバーする。

---

## 7. .gitignore 更新

`.superpowers/` を `.gitignore` に追加する（ビジュアルコンパニオンの作業ファイル）。
