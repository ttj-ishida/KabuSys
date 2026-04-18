# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ + 実行スクリプト群）。  
このリポジトリには監視 / 実行 / リサーチ / ポートフォリオ構築 / AI ニュース解析などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う主要処理。
- 監視（Monitoring）: システム状態・注文ログ・リスク監視、Kill Switch による安全停止。
- ポートフォリオ構築: シグナルを基に候補選定・重み付け・株数計算を行う純関数群。
- 研究（Research）: ファクター計算、将来リターンやIC計算等の分析ツール。
- AI（news_nlp / regime_detector）: OpenAI を使ったニュースセンチメント評価・レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度、設定読み込みウィザード、設定検証ツール等。

設計方針としては「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避（日時参照を受け渡す）」「フェイルセーフ（API失敗時はフォールバック）」などが採用されています。

---

## 主な機能一覧

- config_setup: 対話式で `.env` を生成 / 更新
- validate_config: `.env` と config/*.yaml の事前検証ツール
- run_execution: ExecutionEngine を起動（KABUSYS_ENV によって paper/live を切替）
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）
- monitoring components:
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite に監視ログを永続化
  - KillSwitch: 条件で `data/kill.flag` を書き、Execution を停止
- portfolio: 候補選定 / 重み付け / 株数算出（等金額・スコア加重・リスクベース等）
- research: ファクター計算（momentum/value/volatility）、IC・統計サマリ
- tools.paper_verification_report: ペーパートレード DB を集計し PASS/FAIL レポート生成
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュース評価・レジーム判定（APIキー必要）

---

## セットアップ手順

前提:
- Python 3.10 以上（注: 型注釈で `X | Y` を使用）
- SQLite（標準ライブラリ）および DuckDB（パッケージ）が必要

推奨手順:

1. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - `openai` は AI モジュールを使用する場合に必要
   - `PyYAML` は `validate_config` の YAML 検証を有効にするための任意依存

3. 環境変数設定
   - 対話式ウィザードで `.env` を作る:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動作成（プロジェクトルートに配置）。最小で必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要なデフォルト値:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - KABUSYS_ENV: development | paper_trading | live

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. 設定検証（必須ではないが推奨）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパートレードは KABUSYS_ENV で切替
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring   # 30秒間隔
    ```
  - 監視は常に（KABUSYS_ENV に関わらず）本番の sqlite_path を使用します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系（ニューススコア / レジーム判定）
  - 実行には OpenAI API キーが必要:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - news_nlp / regime_detector は DuckDB 接続と target_date を受け取り呼び出します（ライブラリ関数として利用）。

停止制御・フラグ:
- run_execution / run_monitoring はプロジェクト内のフラグファイル `data/stop_requested.flag` をチェックして終了します。強制停止（運用上の終了シグナル）にはこのファイルを作成してください。
- Kill Switch: `data/kill.flag` が生成されると ExecutionEngine に停止シグナルを送ります（KillSwitch の評価条件に基づく）。`KILL_FLAG_CLEAR_ON_START=1` を `.env` に設定すると起動時に kill.flag が自動クリアされます（本番では推奨されません）。

ログ:
- デフォルトは `logs/` にアプリ毎のログファイル（例: logs/execution.log, logs/monitoring.log）を日次ローテーションで保存。
- 環境変数 `LOG_DIR` / `LOG_LEVEL` でカスタマイズ可能。
- `kabusys.utils.logging_setup.setup_logging()` で全スクリプト共通のログ設定を行います。

---

## よく使う環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 既定値:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- OPENAI_API_KEY — AI モジュール利用時に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1、デフォルト 0)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で `.env` を読み込まない

---

## ディレクトリ構成

主要なファイル・ディレクトリの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（自動 .env 読込実装あり）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                 — ニュースを OpenAI でスコアリング
    - regime_detector.py          — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py            — SQLite の永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py            — （trade 監視）※実装の詳細ファイルあり
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py            — （通知管理、実装あり）
  - execution/
    - execution_engine.py         — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py           — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / cpu affinity
    - __init__.py

プロジェクトルート（想定）:
- .env (ユーザ作成)
- data/ (DB・フラグファイル等)
  - monitoring.db (default)
  - paper_trading.db (paper mode)
  - stop_requested.flag
  - kill.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log

---

## 運用上の注意点・補足

- run_monitoring は MONITOR_POLL_INTERVAL でポーリング。0 以下や不正値は無視されデフォルト 60 秒にフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に書き込みます（本番 DB と分離）。
- Monitoring の DB 初期化は冪等処理（init_monitoring_db）で行われます。既存 DB に対して必要なカラム追加のマイグレーション処理も含まれます。
- AI モジュールで OpenAI を利用する際は API のレート制御やエラーに注意。実装側でリトライやフォールバックが組まれていますが、API キーの管理は十分に行ってください。
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。`KILL_FLAG_CLEAR_ON_START=1` は開発用の利便性設定で、誤って Kill Switch を無効化する可能性があります。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化されコンソールのみの出力になります。権限等を確認してください。

---

## トラブルシュートのヒント

- `.env` 自動読み込みが働かない／テストで無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- `stop_requested.flag` を作成すると `run_execution` / `run_monitoring` が順次終了します。逆に削除してもすぐに再開するわけではありません（再起動が必要）。
- ログが出力されない場合は `LOG_LEVEL` と `LOG_DIR`、ファイル/ディレクトリの権限を確認してください。
- DuckDB / PyYAML がないと一部機能（research、validate_config の YAML 検証）が限定されます。

---

この README はコードベースの現状（主要スクリプト・モジュール）を基に作成しています。実際の運用時は `config/*.yaml` や ExecutionEngine の詳細設定（strategy/risk/execution config）などプロジェクト固有の設定ファイルを合わせて確認してください。質問や追加要求（例: Dockerfile、systemd サービス定義、より詳細な API 使用例）があればお知らせください。