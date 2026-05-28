# TODO: Paper Trading Sandbox 初期資金・検証レポート不整合

## 背景

`documents/WebManual/C_PaperTrading.md` の「結果を確認する」に従い、以下を実行した。

```powershell
.\.venv\Scripts\python -m kabusys.tools.paper_verification_report
```

結果は以下のように、全指標が `N/A` または `0` となり `FAIL` になった。

```text
総ポーリング数:   0
エラー発生数:     0
稼働率:           N/A

総注文数:         0
成立数(Filled):   0
成功率:           N/A

Created 注文数:   0
Sent 注文数:      0
送信率:           N/A

判定: FAIL (稼働率: N/A (データなし); 注文データなし（対象期間に Created イベントが存在しない）)
```

DB を確認したところ、`data/paper_trading.db` にはテーブルは存在するが、検証対象のデータが入っていなかった。

```text
system_status  0
trade_logs     0
risk_logs      0
orders         0
positions      0
```

## 実行ログから分かったこと

`run_execution` は `paper_trading` として起動している。

```text
起動環境: KABUSYS_ENV=paper_trading
```

ただし、実際には `MockBrokerClient` ではなく、kabuステーション検証環境へ接続している。

```text
POST http://localhost:18081/kabusapi/token
GET  http://localhost:18081/kabusapi/wallet/cash
GET  http://localhost:18081/kabusapi/positions
WebSocket 接続確立: ws://localhost:18081/kabusapi/websocket
```

その結果、起動時資産が 0 円になっている。

```text
起動時総資産: 0 円（現金 0 円 + ポジション 0 件）
```

kabuステーション検証環境の `/wallet/cash` が 0 扱いになること自体は自然だが、Paper Trading としては `PAPER_TRADING_INITIAL_CASH` を使うべき設計に見える。

## 現状の実装

`src/kabusys/execution/broker_factory.py` では、`paper_trading` かつ `KABU_USE_SANDBOX=true` の場合、`MockBrokerClient` ではなく `KabuStationClient` を返す。

```python
if settings.is_paper and settings.kabu_use_sandbox:
    return create_broker_api(
        mock=False,
        api_password=password,
        trade_password=settings.kabu_trade_password,
        base_url=_SANDBOX_BASE_URL,
    )
```

一方、`PAPER_TRADING_INITIAL_CASH` が使われるのは Mock 分岐のみ。

```python
if settings.is_paper or settings.is_dev:
    cash = (
        available_cash
        if available_cash is not None
        else settings.paper_trading_initial_cash
    )
    return create_broker_api(
        mock=True,
        fill_mode=settings.paper_fill_mode,
        available_cash=cash,
        initial_positions=initial_positions,
    )
```

そのため現在の挙動は以下になる。

```text
KABUSYS_ENV=paper_trading
KABU_USE_SANDBOX=true
    -> KabuStationClient を使用
    -> /wallet/cash を読む
    -> cash=0
    -> PAPER_TRADING_INITIAL_CASH は使われない
```

## FAIL の直接原因

`src/kabusys/execution/risk_manager.py` の BUY 注文チェックでは、発注前に broker の余力を確認している。

```python
cash = self._broker.get_available_cash()
if cash < order_value:
    return RiskResult(
        False,
        f"余力不足: 余力={cash:.0f}円, 発注額={order_value:.0f}円",
        reject_reason=RiskRejectReason.INSUFFICIENT_CASH,
    )
```

`KabuStationClient` が返す cash が 0 のため、BUY シグナルは Gate 1 で余力不足になり、注文作成まで進まない。

結果として以下が発生する。

```text
Created 注文が作られない
Sent 注文が作られない
Filled 注文が作られない
trade_logs が空のまま
paper_verification_report が「注文データなし」で FAIL
```

## 追加で疑わしい点

`paper_verification_report` は `trade_logs` を集計する。

```text
Created / Sent / Filled
latency_ms
```

しかし `src/kabusys/run_execution.py` では、`ExecutionEngine` 生成時に `MonitoringDB` を渡していない。

```python
engine = ExecutionEngine(
    broker=broker,
    repo=repo,
    risk_manager=risk_manager,
    order_manager=order_manager,
    duckdb_conn=duckdb_conn,
    sqlite_conn=sqlite_conn,
    config=EngineConfig(target_date=today),
    reconciler=None,
    pid_file=_EXECUTION_PID,
)
```

`src/kabusys/execution/execution_engine.py` では、`self._monitoring_db is not None` の場合のみ `trade_logs` に書き込む。

```python
if latency_ms is not None and self._monitoring_db is not None:
    self._monitoring_db.log_trade_event(...)
```

このため、仮に注文送信まで進んでも `trade_logs` が記録されない可能性がある。

## 修正方針案

### 案 A: Sandbox 接続時も Paper Trading 資金を使う

`paper_trading + KABU_USE_SANDBOX=true` では、API 接続は sandbox を使いつつ、リスク判定用の余力は `PAPER_TRADING_INITIAL_CASH` または `paper_trading.db` 復元値を使う。

検討事項:

- `KabuStationClient` をラップする Paper Trading 用 broker を作る
- `get_available_cash()` だけ Paper Trading 用残高を返す
- `send_order()` は sandbox API に送る
- 約定・注文状態は `paper_trading.db` に保存する

### 案 B: Pure Mock と Sandbox E2E を明確に分ける

現在の実装どおり、`KABU_USE_SANDBOX=true` は「kabuステーション検証環境 E2E」と位置付ける。

その場合は手順書を修正し、以下を明記する。

- Pure Mock では `KABU_USE_SANDBOX=false`
- `PAPER_TRADING_INITIAL_CASH` は Pure Mock のみ有効
- Sandbox E2E では `/wallet/cash` が 0 になる可能性があり、BUY 注文は余力不足で落ちる
- Sandbox E2E の検証では SELL または別の検証シナリオが必要

ただし、この場合 `paper_verification_report` を PASS させる運用とは相性が悪い。

### 案 C: `MonitoringDB` を `ExecutionEngine` に渡す

`run_execution.py` で `MonitoringDB(sqlite_conn)` を作成し、`ExecutionEngine` に渡す。

```python
monitoring_db = MonitoringDB(sqlite_conn)

engine = ExecutionEngine(
    ...
    monitoring_db=monitoring_db,
)
```

これにより、注文送信時に `trade_logs` が記録されるようになる。

ただし、これだけでは cash=0 の余力不足は解消しない。

## TODO

- [ ] `paper_trading + KABU_USE_SANDBOX=true` の正式な仕様を決める
- [ ] `PAPER_TRADING_INITIAL_CASH` を sandbox Paper Trading でも使うべきか決める
- [ ] 使う場合、RiskManager が参照する cash を Paper Trading 用残高に差し替える
- [ ] `run_execution.py` から `ExecutionEngine` に `MonitoringDB` を渡す
- [ ] 注文作成時にも `Created` を `trade_logs` に記録する必要があるか確認する
- [ ] `Sent` / `Filled` の記録タイミングを確認する
- [ ] `paper_verification_report` が `system_status` をどの DB から読むべきか確認する
- [ ] `C_PaperTrading.md` の Pure Mock と Sandbox E2E の説明を修正する
- [ ] `KABU_USE_SANDBOX=true` かつ `/wallet/cash=0` の再現テストを追加する
- [ ] 修正後に `paper_verification_report` が PASS/FAIL を妥当に判定することを確認する

## 現時点の結論

今回の FAIL は手順ミスだけではなく、実装と運用手順の不整合が原因と考えられる。

特に重要なのは以下。

```text
KABUSYS_ENV=paper_trading + KABU_USE_SANDBOX=true では
PAPER_TRADING_INITIAL_CASH が使われない。
その結果、kabuステーション検証環境の cash=0 がそのまま RiskManager に渡り、
BUY 注文が余力不足で落ちる。
```

