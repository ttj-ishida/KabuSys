# KabuSys

日本株向けの自動売買システム（ライブラリ + 実行スクリプト群）

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要な以下の機能群を持つプロジェクトです：

- ファクター計算・リサーチ（DuckDB を利用した価格・財務データ計算）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限等）
- ExecutionEngine（発注ロジック、リスク管理、Order 管理、ブローカークライアント抽象化）
- Paper Trading 対応（本番 DB と分離された専用 SQLite を使用）
- AI モジュール（ニュース NLP によるセンチメント、レジーム検出：OpenAI API を使用）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor、kill switch、アラート連携）
- 設定ウィザード・検証ツール・運用用ユーティリティ

設計方針として、DuckDB や SQLite をデータ層に用い、LLM 呼び出しは明示的に API キーを要求して安全に扱います。運用時の安全弁（Kill Switch、監視ログ、PID/フラグファイル）を備えています。

---

## 主な機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でファクターを計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価・IC 計算
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes：発注株数算出（lot 単位丸め・aggregate cap）
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジーム乗数
- ai
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime：MA200 とマクロセンチメントを組み合せて日次レジーム判定
- execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler（ブローカー抽象化あり）
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 専用 DB に記録
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB：監視ログの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch：data/kill.flag による ExecutionEngine 停止シグナル
- ユーティリティ
  - config_setup: .env のインタラクティブ作成ウィザード
  - validate_config: 起動前チェック（必須環境変数・YAML 等）
  - tools.paper_verification_report: Paper Trading の検証レポート出力
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 要件（依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config の YAML 検証を行う場合は任意）

インストール例（pip）:
```bash
python -m pip install duckdb psutil openai pyyaml
```

（AI 機能を使わない場合は `openai` は不要）

---

## セットアップ手順

1. リポジトリをクローン／展開し、プロジェクトルートに移動します（pyproject.toml または .git が基準になります）。

2. Python 仮想環境を作成して依存パッケージをインストールします（上記参照）。

3. 初期設定ファイル（.env）を作成する：
   - 対話式ウィザードを使う（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成します（`.env` は絶対に Git にコミットしないでください）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: KABUSYS_ENV は `development` | `paper_trading` | `live` のいずれかである必要があります。

4. 設定検証を実行:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にする strict モード:
   python -m kabusys.validate_config --strict
   ```

5. DB（data ディレクトリなど）は起動時に自動作成される場合がありますが、必要に応じて事前にディレクトリ作成してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live）
- OPENAI_API_KEY（AI 機能利用時）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定挙動: "instant" | "partial" | "never" | "reject"）
- LOG_LEVEL（DEBUG/INFO/…）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。開発用）

注意:
- Monitoring（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。
- Execution エンジンは KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（主要スクリプト）

- 環境ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（foreground）:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により挙動が変わります（`paper_trading` は MockBrokerClient を使用）。
  - 実行中に data/stop_requested.flag が存在すると安全に停止します。
  - 実行時に data/execution.pid が作成されます。

- Monitoring を起動（ポーリング）:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - 監視ループは data/stop_requested.flag の存在で終了します。
  - 監視は常に本番 SQLITE_PATH を参照します（環境にかかわらず）。

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ライブラリ呼び出し例、アプリから利用）:
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

（これらはライブラリ関数なので、DuckDB 接続オブジェクトを渡して呼び出します）

---

## 運用に関するポイント

- Kill Switch:
  - KillSwitch は監視結果に基づいて data/kill.flag を書き込みます。ExecutionEngine は起動時や巡回でこのフラグを検知して停止できます（設定次第）。
  - 本番では KILL_FLAG_CLEAR_ON_START は 0 を推奨します。

- PID / stop flag:
  - 実行時に data/execution.pid を作成します。PID ファイルが古く（プロセスが存在しない）なっている場合、SystemMonitor は stale PID として検知し削除します。
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが安全に終了します。

- Paper Trading:
  - paper_trading モードでは発注は仮想化され、PAPER_TRADING_SQLITE_PATH にトレードログ等が保存されます。本番 DB とは完全に分離されています。
  - PAPER_FILL_MODE により mock の約定挙動を制御できます（instant/partial/never/reject）。

- ロギング:
  - スクリプトは基本的に logging.basicConfig(level=logging.INFO) を使用します。LOG_LEVEL 環境変数で制御できます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数と設定管理（.env 自動読み込み等）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py             — ニュースNLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
    - __init__.py
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - execution/                 — Execution エンジン周り（OrderRepository 等）※詳細実装は別ファイル
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（schema + MonitoringDB クラス）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジック：実装ファイル参照）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

---

## MonitoringDB（主なテーブル）

- system_status: system モニタログ（cpu, memory, disk, process_ok, recorded_at）
- trade_logs: 発注イベントログ（event_type: Created/Filled/Sent 等、latency_ms あり）
- positions: 現在の保有（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスク関連イベント（例: DRAWDOWN_ALERT, STALE_ORDER）
- dashboard: 集計（id=1 の単一行で portfolio_value, cash, drawdown_pct 等）

初回起動時にテーブルとインデックスを作成します。既存 DB に対しては互換性のための簡単なマイグレーション（列追加）を行います。

---

## 開発・拡張メモ

- DuckDB を使った分析系は SQL を中心に実装されており、データソースを整備すれば即座に研究環境で利用できます。
- AI（OpenAI）呼び出しは retry とレスポンス検証の仕組みを備えていますが、API キーの取り扱いとコストに注意してください。
- position sizing や risk 管理はパラメータ化されているため、strategy/config で新しい設定を導入できます。
- テスト時は .env 自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して環境を制御できます。

---

必要であれば、README にサンプル .env（例）やより詳細な API 使用例（research/ai の関数呼び出しサンプル）、実運用時の systemd / supervisor 用のユニット例などを追加できます。どの追加情報が必要か教えてください。