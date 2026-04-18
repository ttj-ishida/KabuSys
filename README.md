# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ群・起動スクリプト・ユーティリティ群）。

この README はコードベース（src/kabusys 以下）の主要コンポーネントと、初期セットアップ・実行方法をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な機能は次の通りです。

- 戦略（ファクター計算、特徴量解析）のための Research モジュール（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine とブローカークライアント（本番 / ペーパートレード分離）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- AI 補助：ニュース NLP によるセンチメント評価、レジーム判定（OpenAI 使用）
- 設定ウィザード・設定検証ツール・運用支援ツール（ペーパートレード検証レポート等）
- 汎用ユーティリティ（ログ設定、プロセス優先度設定など）

設計方針として、データ取得・解析と発注ロジックを明確に分離し、ペーパートレード用 DB を用意することで本番環境とローカル検証の分離を図っています。

---

## 機能一覧（代表的なもの）

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker 使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 設定
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
- 監視
  - monitoring.*: system/trade/risk のチェック、MonitoringDB（SQLite）永続化、KillSwitch、Alert 管理
- ポートフォリオ構築
  - portfolio.*: 候補選定、重み計算、セクターキャップ、ポジションサイズ計算
- リサーチ
  - research.*: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算など（DuckDB 前提）
- AI
  - ai.news_nlp: OpenAI を用いたニュースセンチメントスコアリング
  - ai.regime_detector: MA とマクロニュースを合わせたレジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成
- ユーティリティ
  - utils.logging_setup: 統一ログ設定
  - utils.process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.9+（コードは型注釈に対して 3.9+ を想定）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- psutil（プロセス情報取得）
- openai（AI 機能を使う場合）
- PyYAML（validate_config で YAML 検証を行う場合） — 任意

推奨手順（一例）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   例:
   ```
   pip install duckdb psutil openai
   # オプション: PyYAML を入れておくと validate_config の YAML 検証が有効になります
   pip install PyYAML
   ```
   ※ requirements.txt がない場合は上記を個別インストールしてください。

3. .env を用意
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成・更新します。
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY （AI 機能を使う場合）
   - 主要な環境変数（デフォルト値）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - KILL_FLAG_CLEAR_ON_START: 0/1

   .env の自動ロード:
   - 起動時に OS 環境変数を優先して .env（および .env.local）を自動ロードします。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```
   ただしスクリプトは実行時にディレクトリを作成することもあります。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で制御
  - 例（ペーパートレード）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 例（本番）:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - 実行前に .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Monitoring を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 停止方法: data/stop_requested.flag ファイルを作成するとループが終了します（または Ctrl+C）。

- .env ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可能。

- AI 関連（プログラム内 API）
  - ai.score_news(conn, target_date, api_key=None) — OpenAI API キーは OPENAI_API_KEY 環境変数か引数で指定
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ出力:
- utils.logging_setup.setup_logging により logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリは環境変数 LOG_DIR で変更可能。

停止フラグ / PID:
- stop_requested.flag（run_*.py で監視）を作ると起動ループを優雅に終了できます。
- run_execution は data/execution.pid を使用して PID 管理を行います。
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine 停止指令を送ります（monitoring が判定して書き込む）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー取引 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH など（Settings による）

.env の例（最低限）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - execution/               — Execution / Order 関連（OrderManager, ExecutionEngine 等）
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
  - data/ (実行時に利用するディレクトリ)
  - logs/ (ログ出力先、デフォルト)

（細かいファイルはコードベースを参照してください）

---

## 開発・運用上の注意

- KABUSYS_ENV=live では実際に注文が発行されます。設定・認証情報の管理は慎重に行ってください。
- .env は絶対にリポジトリにコミットしないこと（config_setup.py のヘッダにも注意書きあり）。
- Monitoring は本番 sqlite_path を参照する設計です（監視は本番データを前提に動作）。
- ExecutionEngine は KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite に記録され、本番 DB と完全分離されます。
- AI 系機能（news_nlp, regime_detector）は OpenAI API を使用します。API 利用時のコストやレート制限に注意してください。失敗時はフェイルセーフ（スコア 0.0 など）で継続する実装です。
- ログディレクトリ作成に失敗するとファイル出力は無効化されますが、コンソール出力は維持されます。

---

この README は主要な利用方法と構成をまとめたものです。詳細な挙動や設定項目は各モジュールの docstring / コメントを参照してください。必要であれば、特定モジュールの利用例や設定例を追加で作成します。