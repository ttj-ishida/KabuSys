# Phase 7 Kill Switch + LINE アラート 設計仕様

**対象 Issue:** #40 Kill Switch実装 [CRITICAL]、#39 LINEアラート機能実装  
**作成日:** 2026-04-02

---

## 1. 概要

MonitoringEngine が検知した異常条件を起点として以下を実装する。

- `kill_switch.py` — フラグファイル書き込みによる ExecutionEngine 停止シグナル
- `alert_manager.py` — LINE Messaging API による一方向プッシュ通知
- `monitoring_engine.py` 改修 — KillSwitch / AlertManager の組み込み
- `execution_engine.py` 改修 — kill.flag ポーリングによる自動停止
- `config.py` 改修 — LINE トークン / kill_flag_path 追加

---

## 2. アーキテクチャ

```
MonitoringEngine.run_once()
    ├── SystemMonitor.check_once()  ─┐
    ├── TradeMonitor.check_once()   ─┼─→ KillSwitch.evaluate(results)
    └── RiskMonitor.check_once()   ─┘        ↓ トリガー条件に該当
                                        data/kill.flag を書き込み
                                        AlertManager.notify(level=CRITICAL)

                                    AlertManager.notify(level=WARNING/INFO)
                                    └─→ LINE Messaging API push

ExecutionEngine.run_session()（別プロセス）
    └── _process_signals() の先頭で kill.flag を確認
            ↓ ファイルあり
        self.kill_switch() 発動（既存実装）
```

**設計原則:**
- MonitoringEngine と ExecutionEngine は別プロセスで動作し、`data/kill.flag` ファイルで通信する（`execution.pid` と同パターン）
- `kill.flag` は人間が手動で作成しても発動する（手動 Kill Switch として機能）
- LINE トークンが未設定の場合は通知をスキップし、警告ログのみ出力（設定なしでも動作する）
- 既存の `SystemMonitor` / `TradeMonitor` / `RiskMonitor` は変更しない

---

## 3. KillSwitch (`kill_switch.py`)

### インポート

```python
from __future__ import annotations

from kabusys.monitoring.system_monitor import SystemCheckResult
from kabusys.monitoring.trade_monitor import TradeCheckResult
from kabusys.monitoring.risk_monitor import RiskCheckResult
```

`from __future__ import annotations` はプロジェクト全体の慣例（`execution_engine.py` line 1、`monitoring_engine.py` line 1 等）に合わせる。これらのモジュールは `KillSwitch` を import しないため、循環 import は発生しない。

### トリガー条件

| 条件 | kill.flag | LINE レベル |
|------|-----------|------------|
| `risk.drawdown_alert=True`（DD > 10%） | 書き込む | CRITICAL |
| `risk.position_limit_alert=True`（ポジション上限超過） | 書き込む | WARNING |
| `system.process_ok=False`（Execution プロセス停止） | 書き込まない | CRITICAL |
| `trade.stale_orders` 1件以上 | 書き込まない | WARNING |
| `trade.anomaly_fills` 1件以上 | 書き込まない | WARNING |
| `system.data_freshness_ok=False` | 書き込まない | WARNING |

### クラス API

```python
class KillSwitch:
    def __init__(self, flag_path: Path) -> None
    # flag_path は呼び出し元が Settings.kill_flag_path から渡す（デフォルト値なし）。
    # これにより KillSwitch が Settings に直接依存することを避け、テスト容易性を確保する。

    def evaluate(
        self,
        system: SystemCheckResult,
        trade: TradeCheckResult,
        risk: RiskCheckResult,
    ) -> str | None
    # トリガー条件を評価。該当すれば flag 書き込み＋理由文字列を返す（複数条件は最初の1件）。
    # flag が既に存在する場合は再書き込みしない（冪等）。
    # 該当なしは None を返す。

    def is_flagged(self) -> bool
    # data/kill.flag が存在するか確認する。

    def clear(self) -> None
    # data/kill.flag を削除する（ExecutionEngine 起動時のクリーンアップ用）。
```

### フラグファイルの内容

```
DRAWDOWN_ALERT: DD 12.3% exceeded threshold 10.0% at 2026-04-02T09:05:00+09:00
```

理由文字列を1行で記録する（デバッグ・運用ログ用）。

---

## 4. AlertManager (`alert_manager.py`)

### クラス API

```python
class AlertManager:
    def __init__(
        self,
        channel_access_token: str,
        user_id: str,
        cooldown_minutes: int = 30,
    ) -> None

    def notify(self, message: str, level: str = "INFO", category: str = "") -> bool
    # LINE Messaging API push message を送信する。
    # 同一 (level, category) の直近送信から cooldown_minutes 以内はスキップ（ログのみ）。
    # category を省略した場合は level のみでクールダウン管理する。
    # 送信した場合 True、スキップした場合 False を返す。
    # channel_access_token / user_id が空の場合は警告ログのみ（送信しない）。
    # requests.exceptions.RequestException または非 2xx レスポンス時はエラーログを出力し False を返す（例外を外部に伝播しない）。
```

### LINE メッセージ形式

```
[CRITICAL] KabuSys 監視アラート
DD 12.3% 超過 — kill.flag 書き込み済み
2026-04-02 09:05:00 JST
```

### LINE Messaging API 呼び出し

```python
requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers={"Authorization": f"Bearer {channel_access_token}"},
    json={"to": user_id, "messages": [{"type": "text", "text": message}]},
    timeout=10,
)
```

### cooldown 管理

`AlertManager` はインスタンス変数 `_last_sent: dict[tuple[str, str], datetime]` で `(level, category)` ごとの最終送信時刻を管理する（プロセスメモリ内）。

- `category` を指定した場合: キーは `(level, category)` — 例: `("CRITICAL", "DRAWDOWN")`
- `category` を省略（`""`）した場合: キーは `(level, "")` — 常に level のみで識別

これにより `drawdown_alert`（category="DRAWDOWN"）と `process_ok=False`（category="PROCESS"）が同一 CRITICAL レベルでも互いのクールダウンに影響しない。プロセス再起動でリセットされるが、60秒ポーリング運用では十分な抑制効果がある。

---

## 5. MonitoringEngine 改修 (`monitoring_engine.py`)

### 変更内容

`__init__` に `kill_switch: KillSwitch | None = None` と `alert_manager: AlertManager | None = None` を追加する。`run_once()` の末尾でそれぞれを呼び出す。

```python
class MonitoringEngine:
    def __init__(
        self,
        system_monitor: SystemMonitor,
        trade_monitor: TradeMonitor,
        risk_monitor: RiskMonitor,
        interval_sec: int = 60,
        kill_switch: KillSwitch | None = None,
        alert_manager: AlertManager | None = None,
    ) -> None:
        # 既存の self._monitors リストは削除し、個別インスタンス変数に分解する
        self._system_monitor = system_monitor
        self._trade_monitor = trade_monitor
        self._risk_monitor = risk_monitor
        self._interval_sec = interval_sec
        self._kill_switch = kill_switch
        self._alert_manager = alert_manager

    def run_once(self) -> None:
        # 既存の汎用ループ（self._monitors を順に呼び出す）を廃止し、
        # 各 Monitor を個別に呼び出して戻り値を変数で受け取る形に変更する。
        #
        # 変更後のシグネチャ（概念コード）:
        #   sys_result   = self._system_monitor.check_once()
        #   trade_result = self._trade_monitor.check_once()
        #   risk_result  = self._risk_monitor.check_once()
        #
        # KillSwitch / AlertManager はこれらの結果を受け取って動作するため、
        # __init__ で monitors を list に格納する既存設計を
        # 3つの個別インスタンス変数 (_system_monitor, _trade_monitor, _risk_monitor)
        # に分解する必要がある。
        # **重要:** 既存の `self._monitors` リストは完全に削除する。
        # 残存すると run_once() が各 Monitor を二重呼び出しし、DB に重複行が書き込まれる。
        #
        # 2. KillSwitch.evaluate(sys_result, trade_result, risk_result)
        # 3. AlertManager.notify() でアラート条件を通知
```

既存テストへの影響をゼロにするため、`kill_switch` / `alert_manager` はデフォルト `None`（省略可能）とする。

### アラート送信ロジック（run_once 末尾）

`AlertManager.notify()` の `category` 引数には条件を識別する固定文字列を渡す。これにより同一 level の異なる条件がクールダウンで相互干渉しない。

**二重アラートについて:** `drawdown_alert=True` / `position_limit_alert=True` の場合、kill-switch ブロックと個別アラートブロックの両方からメッセージが送信される（category が異なるためクールダウンは干渉しない）。これは意図的な設計で、kill-switch メッセージは「flag 書き込み実行」、個別アラートメッセージは「条件の詳細値」をそれぞれ通知する。

```python
# Kill Switch 評価
if self._kill_switch:
    reason = self._kill_switch.evaluate(sys_result, trade_result, risk_result)
    if reason and self._alert_manager:
        self._alert_manager.notify(f"Kill Switch 発動: {reason}", "CRITICAL", category="KILL_SWITCH")

# 個別アラート
if self._alert_manager:
    if not sys_result.process_ok:
        self._alert_manager.notify("Execution プロセス停止を検出", "CRITICAL", category="PROCESS")
    if trade_result.stale_orders:
        self._alert_manager.notify(f"滞留注文 {len(trade_result.stale_orders)} 件", "WARNING", category="STALE_ORDER")
    if trade_result.anomaly_fills:
        self._alert_manager.notify(f"約定異常価格 {len(trade_result.anomaly_fills)} 件", "WARNING", category="PRICE_ANOMALY")
    if risk_result.drawdown_alert:
        self._alert_manager.notify(f"DD {risk_result.drawdown_pct*100:.1f}% 超過", "CRITICAL", category="DRAWDOWN")
    if risk_result.position_limit_alert:
        self._alert_manager.notify(f"ポジション上限超過: {risk_result.position_count} 銘柄", "WARNING", category="POSITION_LIMIT")
    if not sys_result.data_freshness_ok:
        self._alert_manager.notify("株価データ鮮度異常", "WARNING", category="DATA_FRESHNESS")
```

---

## 6. ExecutionEngine 改修 (`execution_engine.py`)

### 起動時クリーンアップ（`run_session()` 追加）

**PID ファイル書き込みの直後** に kill.flag のクリアを追加する。settings import の直後ではない点に注意。これにより前回実行で残った kill.flag が起動時に自動削除され、かつ PID ファイルが書き込まれた後なので MonitoringEngine が `process_ok=True` を検出した状態でクリアが行われる（競合状態を回避）。

```python
# run_session() 内 — PID ファイル書き込みの直後（_active_pid_file.write_text(...) の次の行）
_active_pid_file.write_text(str(os.getpid()))    # 既存行
_config.kill_flag_path.unlink(missing_ok=True)   # NEW: 起動時に kill.flag をクリア
```

`_config` は既存の `from kabusys.config import settings as _config`（line 219）で取得済みの変数を再利用する。

### シグナル処理チェック（`_process_signals()` 追加）

`_process_signals()` の先頭に kill.flag チェックを追加する（4行）。

`self._config` は `EngineConfig` dataclass（`target_date` などを持つ実行設定）であり、`kill_flag_path` は持たない。`Settings` シングルトンは `run_session()` 内で既に `from kabusys.config import settings as _config`（line 219）として利用されているパターンと同じく、メソッド先頭でインポートして参照する。

```python
def _process_signals(self) -> None:
    from kabusys.config import settings as _settings   # kill.flag パス取得
    if _settings.kill_flag_path.exists():
        logger.warning("kill.flag を検出 — kill_switch を発動します")
        self.kill_switch()
        return
    # 以下、既存のシグナル処理（変更なし）
```

---

## 7. config.py 改修

`Settings` クラスに以下を追加する。

```python
# --- LINE Messaging API ---
@property
def line_channel_access_token(self) -> str:
    return os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

@property
def line_user_id(self) -> str:
    return os.environ.get("LINE_USER_ID", "")

# --- Kill Switch ---
@property
def kill_flag_path(self) -> Path:
    return Path(os.environ.get("KILL_FLAG_PATH", "data/kill.flag")).expanduser()
```

**デプロイメント制約:** `KILL_FLAG_PATH` が未設定の場合、パスは実行時の CWD に対する相対パスとなる。`MonitoringEngine` と `ExecutionEngine` は**必ず同一 CWD から起動すること**（既存の `execution.pid` も同じ制約に従っている）。本番運用では `KILL_FLAG_PATH` に絶対パスを設定することを推奨する。

既存の `slack_bot_token` / `slack_channel_id` プロパティは削除する（LINE に置き換え）。
事前調査により、これらのプロパティは `src/kabusys/config.py` 以外では参照されていないことを確認済み（安全に削除可能）。

---

## 8. テスト方針

`tests/test_kill_switch.py` と `tests/test_alert_manager.py` を新規作成する。

| テスト対象 | ケース |
|---|---|
| `KillSwitch.evaluate()` | drawdown_alert=True → flag 書き込み・理由返却 |
| `KillSwitch.evaluate()` | position_limit_alert=True → flag 書き込み |
| `KillSwitch.evaluate()` | process_ok=False のみ → flag **書き込まない**・None 返却 |
| `KillSwitch.evaluate()` | flag 既存時は再書き込みしない（冪等） |
| `KillSwitch.evaluate()` | 全条件 False → None 返却・flag なし |
| `KillSwitch.is_flagged()` | flag あり/なし |
| `KillSwitch.clear()` | flag 削除 |
| `AlertManager.notify()` | トークンあり → requests.post 呼び出し |
| `AlertManager.notify()` | トークン空 → スキップ（例外なし） |
| `AlertManager.notify()` | cooldown 内 → スキップ |
| `AlertManager.notify()` | cooldown 外 → 送信 |
| `AlertManager.notify()` | `requests.exceptions.RequestException` → False 返却・例外非伝播 |
| `AlertManager.notify()` | LINE API 非 2xx レスポンス → False 返却・例外非伝播 |
| `AlertManager.notify()` | 同一 level・異なる category → クールダウン非干渉（両方送信） |
| `MonitoringEngine.run_once()` | kill_switch/alert_manager が呼ばれること（mock） |
| `ExecutionEngine._process_signals()` | kill.flag あり → kill_switch() 発動・シグナル処理スキップ |
| `ExecutionEngine._process_signals()` | kill.flag なし → 通常処理 |
| `ExecutionEngine.run_session()` | 起動時に kill.flag が存在する場合は削除される |

`requests.post` は `unittest.mock.patch` でモックする。

---

## 9. 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `src/kabusys/monitoring/kill_switch.py` | 新規 |
| `src/kabusys/monitoring/alert_manager.py` | 新規 |
| `src/kabusys/monitoring/monitoring_engine.py` | 更新（KillSwitch/AlertManager 組み込み） |
| `src/kabusys/monitoring/__init__.py` | 更新（KillSwitch/AlertManager エクスポート追加） |
| `src/kabusys/execution/execution_engine.py` | 更新（kill.flag ポーリング追加） |
| `src/kabusys/config.py` | 更新（LINE 設定追加、Slack 設定削除） |
| `tests/test_kill_switch.py` | 新規 |
| `tests/test_alert_manager.py` | 新規 |

---

## 10. 依存ライブラリ

| ライブラリ | 用途 | 追加要否 |
|---|---|---|
| `requests` | LINE API HTTP 呼び出し | 既存 |

新規依存ライブラリの追加なし。
