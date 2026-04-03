# risk_logs デデュープ + peak_value DB永続化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue #141（risk_logs 連投防止）と #142（RiskMonitor peak_value DB永続化）を実装し、監視基盤の品質を向上させる。

**Architecture:** `MonitoringDB.log_risk_event()` に `dedup_minutes` 引数を追加して同一イベントの連続記録を防ぎ、`dashboard` テーブルに `peak_value` カラムを追加して `RiskMonitor` の再起動後もドローダウン計算が正確になるようにする。`upsert_dashboard()` は `INSERT ... ON CONFLICT DO UPDATE SET` + `COALESCE` パターンに移行し、`peak_value=None` のとき既存値を保護する。

**Tech Stack:** Python 3.10+, SQLite 3.24+（ON CONFLICT DO UPDATE SET 使用）, pytest

---

## ファイル構成

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/monitoring/monitoring_db.py` | 変更 | `log_risk_event()` デデュープ、`dashboard` カラム追加、`upsert_dashboard()` UPSERT 化 |
| `src/kabusys/monitoring/risk_monitor.py` | 変更 | `check_once()` で peak_value を DB から復元・永続化 |
| `src/kabusys/monitoring/trade_monitor.py` | 変更 | `log_risk_event()` 呼び出しに `dedup_minutes=30` 追加 |
| `tests/test_monitoring_engine.py` | 変更 | デデュープ・peak_value のテスト追加 |

---

### Task 1: `log_risk_event()` デデュープ実装

**Spec:** `docs/superpowers/specs/2026-04-03-risk-logs-dedup-peak-value-persistence.md` Section 1

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py:168-189`
- Test: `tests/test_monitoring_engine.py`

---

- [ ] **Step 1: 失敗テストを書く（デデュープ基本動作）**

`tests/test_monitoring_engine.py` に以下のテストクラスを追加する（ファイル末尾に追記）:

```python
# ─── Issue #141: log_risk_event デデュープ ────────────────────────────────────

class TestLogRiskEventDedup:
    """log_risk_event() の dedup_minutes 引数のテスト。"""

    def test_dedup_skips_within_window(self, mon_conn):
        """同一 (event_type, detail=None) を 30 分以内に再呼び出し → 2件目はスキップ。"""
        db = MonitoringDB(mon_conn)
        now = datetime.now(timezone.utc)

        r1 = db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.15, 0.10,
            logged_at=now, dedup_minutes=30,
        )
        r2 = db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.16, 0.10,
            logged_at=now + timedelta(minutes=10), dedup_minutes=30,
        )

        assert r1 is True
        assert r2 is False
        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 1

    def test_dedup_records_after_window(self, mon_conn):
        """直前レコードが 31 分前なら記録される。"""
        db = MonitoringDB(mon_conn)
        past = datetime.now(timezone.utc) - timedelta(minutes=31)
        now = datetime.now(timezone.utc)

        db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.15, 0.10,
            logged_at=past, dedup_minutes=30,
        )
        r2 = db.log_risk_event(
            "DRAWDOWN_ALERT", "drawdown_pct", 0.16, 0.10,
            logged_at=now, dedup_minutes=30,
        )

        assert r2 is True
        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 2

    def test_no_dedup_when_none(self, mon_conn):
        """`dedup_minutes=None`（デフォルト）では毎回記録される。"""
        db = MonitoringDB(mon_conn)
        now = datetime.now(timezone.utc)

        db.log_risk_event("DRAWDOWN_ALERT", "drawdown_pct", 0.15, 0.10, logged_at=now)
        db.log_risk_event("DRAWDOWN_ALERT", "drawdown_pct", 0.16, 0.10, logged_at=now)

        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 2

    def test_dedup_different_detail_records_both(self, mon_conn):
        """`detail` が異なれば別イベントとして記録される。"""
        db = MonitoringDB(mon_conn)
        now = datetime.now(timezone.utc)

        db.log_risk_event(
            "STALE_ORDER", "order_age_minutes", 35.0, 30.0,
            detail="order-001", logged_at=now, dedup_minutes=30,
        )
        db.log_risk_event(
            "STALE_ORDER", "order_age_minutes", 35.0, 30.0,
            detail="order-002", logged_at=now, dedup_minutes=30,
        )

        rows = mon_conn.execute("SELECT * FROM risk_logs").fetchall()
        assert len(rows) == 2
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestLogRiskEventDedup -v
```

Expected: `FAILED` — `log_risk_event() takes no keyword argument 'dedup_minutes'` または型エラー

- [ ] **Step 3: `log_risk_event()` にデデュープを実装**

`src/kabusys/monitoring/monitoring_db.py` の `log_risk_event()` を以下に置き換える:

```python
def log_risk_event(
    self,
    event_type: str,
    metric_name: str,
    metric_value: float,
    threshold: float,
    detail: str | None = None,
    logged_at: datetime | None = None,
    dedup_minutes: int | None = None,
) -> bool:
    """リスクイベントを risk_logs テーブルに追記する。

    dedup_minutes が指定されている場合、同一 (event_type, detail) ペアが
    直近 dedup_minutes 分以内に記録済みであれば INSERT をスキップして False を返す。
    スキップ判定 SELECT が失敗した場合はフェイルオープン（INSERT を実行）。

    Returns:
        True: INSERT 実行 / False: スキップ
    """
    from datetime import timedelta
    now_dt = logged_at or datetime.now(timezone.utc)
    ts = now_dt.isoformat()

    if dedup_minutes is not None:
        try:
            row = self._conn.execute(
                """
                SELECT MAX(logged_at) FROM risk_logs
                WHERE event_type = ?
                  AND (
                        (detail IS NULL AND ? IS NULL)
                        OR detail = ?
                      )
                """,
                (event_type, detail, detail),
            ).fetchone()
            last_ts = row[0] if row else None
            if last_ts is not None:
                last_dt = datetime.fromisoformat(last_ts)
                if now_dt - last_dt < timedelta(minutes=dedup_minutes):
                    return False
        except Exception:
            pass  # フェイルオープン: SELECT 失敗時は INSERT を実行

    self._conn.execute(
        """
        INSERT INTO risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ts, event_type, metric_name, metric_value, threshold, detail),
    )
    self._conn.commit()
    return True
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestLogRiskEventDedup -v
```

Expected: 4 PASSED

- [ ] **Step 5: 既存テストへの影響がないことを確認**

```bash
python -m pytest tests/test_monitoring_engine.py -v --tb=short
```

Expected: 全テスト PASS（`log_risk_event()` の戻り値変更は既存呼び出し元が無視しているので影響なし）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_engine.py
git commit -m "feat: add dedup_minutes to log_risk_event to suppress repeated alerts (Issue #141)"
```

---

### Task 2: `dashboard` テーブルへの `peak_value` カラム追加

**Spec:** `docs/superpowers/specs/2026-04-03-risk-logs-dedup-peak-value-persistence.md` Section 2

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py:12-77` (`init_monitoring_db`)
- Modify: `src/kabusys/monitoring/monitoring_db.py:191-214` (`upsert_dashboard`)
- Test: `tests/test_monitoring_engine.py`

---

- [ ] **Step 1: 失敗テストを書く（マイグレーション + upsert）**

`tests/test_monitoring_engine.py` に追加:

```python
# ─── Issue #142: dashboard peak_value カラム ──────────────────────────────────

class TestDashboardPeakValue:
    """dashboard テーブルの peak_value カラム追加テスト。"""

    def test_migration_adds_peak_value_column(self):
        """既存 DB（peak_value カラムなし）に init_monitoring_db() を再実行してもエラーなし。"""
        conn = sqlite3.connect(":memory:")
        # peak_value なしで旧スキーマを作成
        conn.execute("""
            CREATE TABLE dashboard (
                id               INTEGER PRIMARY KEY CHECK (id = 1),
                updated_at       TEXT    NOT NULL,
                portfolio_value  REAL    NOT NULL,
                cash             REAL    NOT NULL,
                drawdown_pct     REAL    NOT NULL,
                open_order_count INTEGER NOT NULL,
                position_count   INTEGER NOT NULL
            )
        """)
        conn.commit()
        # init_monitoring_db を再実行 → エラーなし
        init_monitoring_db(conn)
        # peak_value カラムが存在することを確認
        cols = [row[1] for row in conn.execute("PRAGMA table_info(dashboard)").fetchall()]
        assert "peak_value" in cols

    def test_upsert_dashboard_sets_peak_value(self, mon_conn):
        """peak_value を指定すると dashboard に保存される。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=1_000_000, cash=500_000, drawdown_pct=0.0,
            open_order_count=0, position_count=0, peak_value=1_200_000,
        )
        row = db.get_dashboard()
        assert row["peak_value"] == 1_200_000

    def test_upsert_dashboard_preserves_peak_value_when_none(self, mon_conn):
        """peak_value=None で呼ぶと既存の peak_value が保護される。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=1_000_000, cash=500_000, drawdown_pct=0.0,
            open_order_count=0, position_count=0, peak_value=1_200_000,
        )
        # peak_value=None（デフォルト）で再呼び出し
        db.upsert_dashboard(
            portfolio_value=900_000, cash=400_000, drawdown_pct=0.1,
            open_order_count=0, position_count=0,
        )
        row = db.get_dashboard()
        assert row["peak_value"] == 1_200_000  # 保護されていること
        assert row["portfolio_value"] == 900_000  # 他フィールドは更新
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestDashboardPeakValue -v
```

Expected: `FAILED` — `upsert_dashboard() got unexpected keyword argument 'peak_value'`

- [ ] **Step 3: `init_monitoring_db()` にマイグレーションを追加**

`src/kabusys/monitoring/monitoring_db.py` の `init_monitoring_db()` を以下に変更する:

`CREATE TABLE IF NOT EXISTS dashboard` のカラム定義に `peak_value REAL` を追加し、`conn.commit()` の後にマイグレーション処理を追加する:

```python
def init_monitoring_db(conn: sqlite3.Connection) -> None:
    """5テーブル + インデックスを作成する（冪等）。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS system_status (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at    TEXT    NOT NULL,
            cpu_percent    REAL    NOT NULL,
            memory_percent REAL    NOT NULL,
            disk_percent   REAL    NOT NULL,
            process_ok     INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_system_status_recorded_at
            ON system_status (recorded_at);

        CREATE TABLE IF NOT EXISTS trade_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at       TEXT    NOT NULL,
            event_type      TEXT    NOT NULL,
            client_order_id TEXT    NOT NULL,
            code            TEXT    NOT NULL,
            side            TEXT    NOT NULL,
            qty             INTEGER NOT NULL,
            price           REAL    NOT NULL DEFAULT 0.0,
            filled_qty      INTEGER NOT NULL DEFAULT 0,
            state           TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_trade_logs_logged_at
            ON trade_logs (logged_at);
        CREATE INDEX IF NOT EXISTS idx_trade_logs_client_order_id
            ON trade_logs (client_order_id);

        CREATE TABLE IF NOT EXISTS positions (
            code          TEXT    PRIMARY KEY,
            qty           INTEGER NOT NULL,
            avg_price     REAL    NOT NULL,
            current_price REAL,
            updated_at    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_positions_updated_at
            ON positions (updated_at);

        CREATE TABLE IF NOT EXISTS risk_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at    TEXT    NOT NULL,
            event_type   TEXT    NOT NULL,
            metric_name  TEXT    NOT NULL,
            metric_value REAL    NOT NULL,
            threshold    REAL    NOT NULL,
            detail       TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_risk_logs_logged_at
            ON risk_logs (logged_at);
        CREATE INDEX IF NOT EXISTS idx_risk_logs_event_type
            ON risk_logs (event_type);

        CREATE TABLE IF NOT EXISTS dashboard (
            id               INTEGER PRIMARY KEY CHECK (id = 1),
            updated_at       TEXT    NOT NULL,
            portfolio_value  REAL    NOT NULL,
            cash             REAL    NOT NULL,
            drawdown_pct     REAL    NOT NULL,
            open_order_count INTEGER NOT NULL,
            position_count   INTEGER NOT NULL,
            peak_value       REAL
        );
    """)
    conn.commit()

    # 既存 DB に peak_value カラムがない場合のマイグレーション
    try:
        conn.execute("ALTER TABLE dashboard ADD COLUMN peak_value REAL")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise
```

- [ ] **Step 4: `upsert_dashboard()` を `INSERT ... ON CONFLICT DO UPDATE SET` に置き換える**

```python
def upsert_dashboard(
    self,
    portfolio_value: float,
    cash: float,
    drawdown_pct: float,
    open_order_count: int,
    position_count: int,
    updated_at: datetime | None = None,
    peak_value: float | None = None,
) -> None:
    """ダッシュボード集計を更新する（常に id=1 の1行のみ保持）。

    peak_value=None の場合、既存の peak_value を上書きしない。
    INSERT ... ON CONFLICT DO UPDATE SET + COALESCE を使用することで、
    INSERT OR REPLACE の DELETE→INSERT 問題を回避する。
    """
    ts = updated_at.isoformat() if updated_at else self._now()
    self._conn.execute(
        """
        INSERT INTO dashboard
            (id, updated_at, portfolio_value, cash, drawdown_pct,
             open_order_count, position_count, peak_value)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            updated_at       = excluded.updated_at,
            portfolio_value  = excluded.portfolio_value,
            cash             = excluded.cash,
            drawdown_pct     = excluded.drawdown_pct,
            open_order_count = excluded.open_order_count,
            position_count   = excluded.position_count,
            peak_value       = COALESCE(excluded.peak_value, dashboard.peak_value)
        """,
        (ts, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value),
    )
    self._conn.commit()
```

- [ ] **Step 5: テストが通ることを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestDashboardPeakValue -v
```

Expected: 3 PASSED

- [ ] **Step 6: 全テストへの影響がないことを確認**

```bash
python -m pytest tests/ --tb=short -q
```

Expected: 全テスト PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_engine.py
git commit -m "feat: add peak_value column to dashboard with UPSERT migration (Issue #142)"
```

---

### Task 3: `RiskMonitor` peak_value DB 読み書き

**Spec:** `docs/superpowers/specs/2026-04-03-risk-logs-dedup-peak-value-persistence.md` Section 3

**Files:**
- Modify: `src/kabusys/monitoring/risk_monitor.py:33-89` (`check_once`)
- Test: `tests/test_monitoring_engine.py`

---

- [ ] **Step 1: 失敗テストを書く**

`tests/test_monitoring_engine.py` に追加:

```python
# ─── Issue #142: RiskMonitor peak_value 永続化 ────────────────────────────────

def _setup_dashboard_with_peak(
    conn: sqlite3.Connection,
    portfolio_value: float,
    peak_value: float | None = None,
    cash: float = 0.0,
) -> None:
    db = MonitoringDB(conn)
    db.upsert_dashboard(
        portfolio_value=portfolio_value,
        cash=cash,
        drawdown_pct=0.0,
        open_order_count=0,
        position_count=0,
        peak_value=peak_value,
    )


class TestRiskMonitorPeakValuePersistence:
    """RiskMonitor の peak_value DB 永続化テスト。"""

    def test_peak_value_persisted_on_new_high(self, mon_conn):
        """新高値更新時に dashboard.peak_value が DB に書き込まれる。"""
        _setup_dashboard_with_peak(mon_conn, portfolio_value=1_000_000)
        monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
        monitor.check_once()

        row = MonitoringDB(mon_conn).get_dashboard()
        assert row["peak_value"] == 1_000_000.0

    def test_peak_value_restored_on_restart(self, mon_conn):
        """RiskMonitor を再生成して check_once() を呼ぶと DB から peak_value が復元される。"""
        # 1回目: peak = 1,200,000
        _setup_dashboard_with_peak(mon_conn, portfolio_value=1_200_000)
        monitor1 = RiskMonitor(mon_conn, dd_threshold=0.10)
        monitor1.check_once()

        # "再起動": portfolio_value を下げた状態で新しい RiskMonitor を生成
        _setup_dashboard_with_peak(mon_conn, portfolio_value=1_000_000, peak_value=1_200_000)
        monitor2 = RiskMonitor(mon_conn, dd_threshold=0.10)
        result = monitor2.check_once()

        # _peak_value が 1,200,000 から復元されているためドローダウン計算が正確
        assert monitor2._peak_value == 1_200_000.0
        assert result.drawdown_pct == pytest.approx((1_200_000 - 1_000_000) / 1_200_000)

    def test_drawdown_correct_after_restart(self, mon_conn):
        """再起動後もドローダウン計算が正確（peak_value=1,200,000 から 1,000,000 に下落）。"""
        # 1回目の稼働: peak を 1,200,000 に設定
        _setup_dashboard_with_peak(mon_conn, portfolio_value=1_200_000, peak_value=1_200_000)
        monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
        result = monitor.check_once()
        assert result.drawdown_pct == pytest.approx(0.0)

        # "再起動" 後: portfolio が下落
        _setup_dashboard_with_peak(mon_conn, portfolio_value=1_000_000, peak_value=1_200_000)
        monitor2 = RiskMonitor(mon_conn, dd_threshold=0.10)
        result2 = monitor2.check_once()

        expected_dd = (1_200_000 - 1_000_000) / 1_200_000
        assert result2.drawdown_pct == pytest.approx(expected_dd)
        assert result2.drawdown_alert is True  # 16.7% > 10% 閾値
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestRiskMonitorPeakValuePersistence -v
```

Expected: `FAILED` — `peak_value` が DB に書き込まれない / 再起動後の復元が機能しない

- [ ] **Step 3: `RiskMonitor.check_once()` を更新する**

`src/kabusys/monitoring/risk_monitor.py` の `check_once()` を以下に置き換える（最終バージョンのみ）:

```python
def check_once(self, now: datetime | None = None) -> RiskCheckResult:
    now = now or datetime.now(timezone.utc)
    logged_at = now.isoformat()

    dashboard = self._db.get_dashboard()
    if dashboard is None:
        return RiskCheckResult(
            logged_at=logged_at,
            drawdown_pct=0.0,
            drawdown_alert=False,
            position_count=0,
            position_limit_alert=False,
        )

    portfolio_value = dashboard["portfolio_value"]

    # ハイウォーターマーク: 初期化時 or 新高値更新時のみ DB に書き込む
    peak_updated = False
    if self._peak_value is None:
        db_peak = dashboard.get("peak_value")
        self._peak_value = db_peak if db_peak is not None else portfolio_value
        if db_peak is None:
            peak_updated = True
    elif portfolio_value > self._peak_value:
        self._peak_value = portfolio_value
        peak_updated = True

    if peak_updated:
        self._db.upsert_dashboard(
            portfolio_value=portfolio_value,
            cash=dashboard["cash"],
            drawdown_pct=0.0,
            open_order_count=dashboard["open_order_count"],
            position_count=dashboard["position_count"],
            peak_value=self._peak_value,
        )

    drawdown_pct = (
        (self._peak_value - portfolio_value) / self._peak_value
        if self._peak_value > 0
        else 0.0
    )
    drawdown_alert = drawdown_pct > self._dd_threshold

    row = self._conn.execute(
        "SELECT COUNT(*) FROM positions WHERE qty != 0"
    ).fetchone()
    position_count = row[0]
    position_limit_alert = position_count > self._max_positions

    if drawdown_alert:
        self._db.log_risk_event(
            event_type="DRAWDOWN_ALERT",
            metric_name="drawdown_pct",
            metric_value=drawdown_pct,
            threshold=self._dd_threshold,
            dedup_minutes=30,
        )

    if position_limit_alert:
        self._db.log_risk_event(
            event_type="POSITION_LIMIT",
            metric_name="position_count",
            metric_value=float(position_count),
            threshold=float(self._max_positions),
            dedup_minutes=30,
        )

    return RiskCheckResult(
        logged_at=logged_at,
        drawdown_pct=drawdown_pct,
        drawdown_alert=drawdown_alert,
        position_count=position_count,
        position_limit_alert=position_limit_alert,
    )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestRiskMonitorPeakValuePersistence -v
```

Expected: 3 PASSED

- [ ] **Step 5: 全テストが通ることを確認**

```bash
python -m pytest tests/ --tb=short -q
```

Expected: 全テスト PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/risk_monitor.py tests/test_monitoring_engine.py
git commit -m "feat: persist peak_value to DB and restore on restart (Issue #142)"
```

---

### Task 4: `TradeMonitor` に dedup_minutes 適用 + RiskMonitor デデュープ結合テスト

**Spec:** `docs/superpowers/specs/2026-04-03-risk-logs-dedup-peak-value-persistence.md` Section 4

**Files:**
- Modify: `src/kabusys/monitoring/trade_monitor.py:47-53,64-70`
- Test: `tests/test_monitoring_engine.py`

---

- [ ] **Step 1: 失敗テストを書く**

`tests/test_monitoring_engine.py` に追加:

```python
# ─── Issue #141: Monitor レベルのデデュープ統合テスト ─────────────────────────

class TestMonitorDedup:
    """TradeMonitor / RiskMonitor の dedup_minutes 統合テスト。"""

    def test_risk_monitor_dedup_suppresses_repeated_drawdown_alert(self, mon_conn):
        """RiskMonitor.check_once() を連続呼び出し → risk_log の DRAWDOWN_ALERT は 1 件のみ。"""
        db = MonitoringDB(mon_conn)
        db.upsert_dashboard(
            portfolio_value=850_000, cash=0, drawdown_pct=0.15,
            open_order_count=0, position_count=0, peak_value=1_000_000,
        )
        monitor = RiskMonitor(mon_conn, dd_threshold=0.10)
        monitor.check_once()
        monitor.check_once()  # 2回目: 同じ条件（30分以内）
        monitor.check_once()  # 3回目

        rows = mon_conn.execute(
            "SELECT * FROM risk_logs WHERE event_type='DRAWDOWN_ALERT'"
        ).fetchall()
        assert len(rows) == 1  # デデュープにより1件のみ

    def test_trade_monitor_dedup_suppresses_stale_order(self, mon_conn):
        """同一注文の STALE_ORDER は 30 分以内は 1 件のみ記録される。"""
        import sqlite3 as _sqlite3
        from kabusys.execution.order_repository import OrderRepository, init_orders_db
        from kabusys.execution.order_record import OrderState

        order_conn = _sqlite3.connect(":memory:")
        init_orders_db(order_conn)
        repo = OrderRepository(order_conn)

        # 31 分前に作成された注文を挿入
        past = datetime.now(timezone.utc) - timedelta(minutes=31)
        order_conn.execute(
            """INSERT INTO orders
               (client_order_id, signal_id, code, side, qty, order_type, price,
                state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("ord-001", "sig-001", "7203", "buy", 100, "limit", 1000.0,
             OrderState.Sent.value, past.isoformat(), past.isoformat()),
        )
        order_conn.commit()

        monitor = TradeMonitor(mon_conn, repo, stale_minutes=30)
        monitor.check_once()
        monitor.check_once()  # 同じ注文・30分以内

        rows = mon_conn.execute(
            "SELECT * FROM risk_logs WHERE event_type='STALE_ORDER'"
        ).fetchall()
        assert len(rows) == 1  # デデュープにより1件のみ
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestMonitorDedup -v
```

Expected: `FAILED` — TradeMonitor の `log_risk_event()` 呼び出しにまだ `dedup_minutes` がない

- [ ] **Step 3: `TradeMonitor` の `log_risk_event()` 呼び出しに `dedup_minutes=30` を追加**

`src/kabusys/monitoring/trade_monitor.py` を変更:

```python
            # 注文滞留チェック
            if age >= timedelta(minutes=self._stale_minutes):
                stale_orders.append(order.client_order_id)
                self._db.log_risk_event(
                    event_type="STALE_ORDER",
                    metric_name="order_age_minutes",
                    metric_value=age.total_seconds() / 60,
                    threshold=float(self._stale_minutes),
                    detail=order.client_order_id,
                    dedup_minutes=30,
                )

            # 約定異常価格チェック（成行は除外）
            if (
                order.state in (OrderState.PartialFill, OrderState.Filled)
                and order.price != 0.0
                and order.avg_fill_price is not None
            ):
                deviation = abs(order.avg_fill_price - order.price) / order.price
                if deviation > self._price_anomaly_pct:
                    anomaly_fills.append(order.client_order_id)
                    self._db.log_risk_event(
                        event_type="PRICE_ANOMALY",
                        metric_name="fill_price_deviation",
                        metric_value=deviation,
                        threshold=self._price_anomaly_pct,
                        detail=order.client_order_id,
                        dedup_minutes=30,
                    )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_monitoring_engine.py::TestMonitorDedup -v
```

Expected: 2 PASSED

- [ ] **Step 5: 全テストを実行**

```bash
python -m pytest tests/ --tb=short -q
```

Expected: 全テスト PASS（567 + 新規テスト分）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/monitoring/trade_monitor.py tests/test_monitoring_engine.py
git commit -m "feat: apply dedup_minutes=30 to TradeMonitor log_risk_event calls (Issue #141)"
```

---

### Task 5: GitHub Issues クローズ + PR 作成

**Files:** なし（git / GitHub 操作のみ）

- [ ] **Step 1: Issue #141 と #142 のクローズコメントを確認**

```bash
gh issue view 141
gh issue view 142
```

- [ ] **Step 2: PR を作成する**

```bash
gh pr create \
  --title "feat: risk_logs dedup + peak_value DB persistence (Issues #141 #142)" \
  --body "$(cat <<'EOF'
## Summary
- Issue #141: `log_risk_event()` に `dedup_minutes` 引数を追加。同一 `(event_type, detail)` ペアが指定時間内に記録済みなら INSERT をスキップ（フェイルオープン）
- Issue #142: `dashboard` テーブルに `peak_value` カラムを追加（マイグレーション対応）。`RiskMonitor` 再起動後も `peak_value` が DB から復元されドローダウン計算が正確に継続
- `upsert_dashboard()` を `INSERT ... ON CONFLICT DO UPDATE SET` に移行（`INSERT OR REPLACE` + `COALESCE` の TOCTTOU バグ回避）

## Test Plan
- [ ] `python -m pytest tests/test_monitoring_engine.py -v` — 全テスト PASS
- [ ] `python -m pytest tests/ -q` — 全テスト PASS
- [ ] 既存の `_setup_dashboard()` ヘルパーが引き続き動作すること（シグネチャ後方互換）

Closes #141
Closes #142
EOF
)"
```
