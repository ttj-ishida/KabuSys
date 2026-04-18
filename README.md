# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ＋起動スクリプト群）。

この README はリポジトリ内の Python モジュール群（src/kabusys 以下）に基づき、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の要素を含む自動売買基盤です。

- 銘柄選定・配分（portfolio モジュール）
- 発注・ExecutionEngine（execution パッケージ）
- 監視・Kill Switch（monitoring パッケージ）
- 研究・ファクター計算（research パッケージ、DuckDB を利用）
- AI を用いたニュースセンチメント（ai パッケージ、OpenAI 利用）
- 環境設定ウィザード、設定検証、ツール類

設計思想としては、データ永続化は DuckDB（分析）と SQLite（監視・トレードログ）で分離し、paper_trading（ペーパートレード）モードでは本番 DB と分離して動作します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文管理（OrderManager / OrderRepository / RiskManager / Reconciler）
  - paper_trading 環境では MockBrokerClient を利用し `data/paper_trading.db` を使用
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス状態・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常・ドローダウンやポジション上限監視
  - KillSwitch: 条件で `data/kill.flag` を書き、Execution を停止させる仕組み
  - MonitoringDB: SQLite ベースの監視・ログテーブル（初期化・マイグレーションロジックあり）
- Portfolio construction
  - 候補選定、等重／スコア重み、リスク基づく株数決定、セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI 関連
  - news_nlp: OpenAI を使ったニュースのセンチメント集計・ai_scores 書き込み（バッチ・リトライ・検証あり）
  - regime_detector: MA200 とマクロニュースを合成して市場レジーム（bull/neutral/bear）判定・書き込み
- ユーティリティ
  - ログ設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール  
   （requirements.txt がない場合は主要パッケージを手動インストール）
   ```bash
   pip install duckdb psutil openai
   # optional: PyYAML があれば config YAML の検証ができる
   pip install pyyaml
   ```

3. .env を作成する（ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   このウィザードで主要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を対話式に設定します。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等を作成（必要に応じて）
   - デフォルト DB / ログパス:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
     - SQLite（monitoring）: data/monitoring.db（環境変数 SQLITE_PATH）
     - paper_trading の SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - ログディレクトリ: logs/（LOG_DIR で変更可）

---

## 環境変数と主な設定

重要な環境変数（主なもの）:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 DB に記録
    - live: 本番動作（注意深く設定を確認）

- データベース / ログ
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_DIR (default: logs/)
  - LOG_LEVEL (DEBUG/INFO/... default: INFO)

- Execution / Monitoring
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1, default: 0) — ExecutionEngine 起動時に kill.flag を自動クリアするか
  - MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒, default: 60）
  - PAPER_FILL_MODE — ペーパートレードの約定モード (instant|partial|never|reject)

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector で利用

Settings は `kabusys.config.Settings` クラスで集中管理され、.env / 環境変数から取得されます。

---

## 実行方法（主要スクリプト）

各スクリプトはパッケージモジュールとして実行できます（プロジェクトルートで実行）。

- ExecutionEngine（注文実行）
  ```bash
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録して本番 DB と分離します。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中に `data/stop_requested.flag` を作成すると停止します。
  - 実行中は PID ファイル（data/execution.pid）を書きます。

- Monitoring（SystemMonitor ポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - 停止は `data/stop_requested.flag` によって行います。

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## ログと永続化

- ログ:
  - デフォルトでは logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
  - LOG_DIR や LOG_LEVEL で制御可能。
  - 標準出力にも出力されます（StreamHandler は stdout を使います）。

- DB:
  - DuckDB: 分析・研究用の大容量データベース (`prices_daily`, `raw_financials` 等)
  - SQLite: 監視・トレードログ（monitoring_db）やペーパートレード用の軽量 DB
  - monitoring_db は init_monitoring_db() によりテーブル・マイグレーションを自動で行います。

---

## Kill / Stop フロー

- Kill Switch:
  - リスク条件（ドローダウン超過やポジション上限超過）が満たされると `KillSwitch` が `data/kill.flag` を書き込みます。
  - ExecutionEngine はこれを検出して安全に停止する仕組みを持ちます。

- stop フラグ:
  - `data/stop_requested.flag` を作成することで run_execution/run_monitoring のループを終了させます（手動停止用）。

- 起動時の自動クリア:
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に `kill.flag` を自動クリアします（本番では推奨されません）。

---

## 開発・実装メモ（注目ポイント）

- process_priority と CPU affinity は `kabusys.utils.process_priority` で抽象化。psutil を使用してプラットフォーム差を吸収します。
- logging は `kabusys.utils.logging_setup.setup_logging()` で全スクリプト共通の設定を行っています。
- AI 関連（news_nlp / regime_detector）は OpenAI API に依存。API 呼び出しはリトライやレスポンス検証を厳密に行う実装です。
- portfolio モジュールは純粋関数群（副作用なし）で、ユニットテストしやすい設計です。
- research モジュールは DuckDB に SQL を流してファクターや将来リターンを計算します（pandas 等に依存しない実装）。

---

## ディレクトリ構成（抜粋）

プロジェクトルートに `src/kabusys` があり、主なファイル・ディレクトリは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                   — Execution 系（Engine / OrderManager / BrokerFactory 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は主なモジュールのみを抜粋しています。詳細はソースツリーを参照してください。）

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）で稼働させる場合は、必須環境変数を必ず設定し、validate_config の出力を確認してください。
- kill.flag / stop_requested.flag の操作は慎重に行ってください。特に `KILL_FLAG_CLEAR_ON_START` を本番で `1` にするのは危険です。
- Paper trading の DB は本番と完全に分離されますが、設定ミスで本番 DB を上書きしないように .env を管理してください。
- OpenAI API を利用する機能は API 料金が発生します。API キーや呼び出し頻度の管理に注意してください。

---

もし README の内容に加えたい具体的な実行例や設定ファイルのテンプレート（.env.example / config/*.yaml の具体内容）などがあれば、その情報を提供してください。README をさらに詳細に拡張して作成します。