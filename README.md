KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した小規模フレームワークです。  
主な役割は次の通りです。

- 日次ファクター計算・リサーチ（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュース系の AI スコアリング（OpenAI 経由）
- 運用補助ツール（.env ウィザード、設定検証、検証レポート）

このリポジトリはモジュール単位で再利用しやすいように設計されています（DB 接続は DuckDB / SQLite、ログは stdout とファイルに出力）。

主な機能
--------
- 環境設定ウィザード（.env の対話的作成・更新）
- 設定検証 CLI（.env と config/*.yaml の存在／簡易チェック）
- ExecutionEngine の起動（KABUSYS_ENV により paper_trading を分離）
  - paper_trading の場合は MockBroker を使用し、専用 SQLite（data/paper_trading.db）へ記録
- 監視プロセス（SystemMonitor）および統合 MonitoringEngine（ポーリング）
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更
  - stop フラグ（data/stop_requested.flag 等）で安全停止
- Kill Switch：条件（ドローダウン、ポジション上限等）で data/kill.flag を書き込み Engine を停止
- Paper Trading 検証レポート生成スクリプト（orders / system stability / latency 等を集計）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア）
- 市場レジーム検出（ETF の MA とマクロニュースの LLM スコアを合成）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算、セクター制約）

セットアップ手順
----------------

前提
- Python 3.10+（型アノテーションで Union | を使用）
- Git リポジトリルートにて操作することを想定

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

2. 依存ライブラリをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai （AI 機能を使う場合）
     - PyYAML（config YAML の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がない場合は必要なパッケージを個別にインストールしてください）

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - ウィザードで設定した .env はプロジェクトルートに保存されます（.env は絶対に Git にコミットしないでください）

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う厳格モード:
     - python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリを確認 / 作成
   - デフォルト DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/（デフォルト。環境変数 LOG_DIR で変更可能）
   - ログディレクトリは自動作成されますが、パーミッション等に注意してください

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の模擬約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアする (0/1)

使い方
------

基本的な CLI / モジュール起動例:

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - スクリプトは起動時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存で失敗する場合あり）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に書き込みます（本番 DB と分離）。
    - 停止は data/stop_requested.flag の作成または Kill Switch による data/kill.flag の作成で制御します。
    - 実行中は PID が data/execution.pid に記録されます（設定で変更可能）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は production 環境の sqlite_path を使ってログを記録します（KABUSYS_ENV にかかわらず本番 sqlite_path を参照する設計上の注意）。

- Paper Trading 検証レポート作成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で指定）
  - 実行例（コード内関数呼び出し）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 注意: API 呼び出しは課金対象となるため、キーとコストに注意して運用してください。

ログと監視ファイル
------------------
- ログ
  - stdout に常時出力され、加えて logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）
  - setup_logging() でログレベル・保存先を制御可能

- フラグファイル
  - data/stop_requested.flag — スクリプトを外部から停止するためのフラグ（run_monitoring / run_execution が監視）
  - data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガ）
  - PID ファイル: data/execution.pid（ExecutionEngine の PID）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI 経由で銘柄スコア）
  - regime_detector.py      — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py        — SQLite テーブル定義・永続化ヘルパ
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py         — ドローダウン・ポジション監視
  - kill_switch.py          — kill.flag の評価・書き込み
  - monitoring_engine.py    — 各 Monitor を束ねる
  - (他: trade_monitor, alert_manager など)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py      — momentum/value/volatility 等
  - feature_exploration.py  — forward_returns, IC, summary 等
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity
  - (他ユーティリティ)

運用上の注意
-------------
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。
- OPENAI API を使う処理は外部 API 呼び出しを行い、コスト・レイテンシ・障害の影響を受けます。フェイルセーフが実装されていますが、運用ポリシーを策定してください。
- paper_trading と本番 DB（monitoring.db）は分離されます。間違って本番 DB に書き込まないよう .env を慎重に設定してください。
- run_* スクリプトは起動直後に set_process_priority("high") を試みます。権限やプラットフォーム差分でログに警告が出る場合があります。

開発者向けメモ
----------------
- DuckDB 接続を渡して計算する設計により、研究・検証関数は I/O を分離しています（単体テストが容易）。
- monitoring_db.init_monitoring_db() は冪等であり、マイグレーション的にカラム追加処理を含みます。
- 設定ファイル（config/*.yaml）を用いる箇所は validate_config.py で存在チェックを行います。PyYAML がない場合は警告となります。

ライセンス / 貢献
-----------------
この README はコードベースの概要と使い方を示すドキュメントです。ライセンスや貢献ルールはリポジトリのトップレベルに LICENSE / CONTRIBUTING.md があればそちらを参照してください。

問い合わせ
----------
不明点や不具合はリポジトリの issue を作成してください。簡単な実行時ログを添えると原因特定が速くなります。

以上。