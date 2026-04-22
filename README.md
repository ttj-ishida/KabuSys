KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・運用支援ライブラリです。本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で注文管理・発注を行う（paper_trading モードあり）
- Monitoring（監視）: システム状態・注文状態・リスクを定期チェックし、Kill Switch やアラートを制御
- Portfolio モジュール: 候補選定・配分・ポジションサイズ計算・セクターキャップ等の純粋関数群
- Research モジュール: ファクター計算、特徴量探索、IC 計算などの分析機能（DuckDB を利用）
- AI モジュール: OpenAI を用いたニュースセンチメント、レジーム判定（gpt-4o-mini を想定）
- ユーティリティ: 設定ウィザード、設定検証、ログセットアップ、プロセス優先度設定、paper trading レポート等

主要な設計方針:
- 実行時の環境依存を最小化（.env 自動ロード、Settings クラス）
- DuckDB/SQLite を利用したデータ分析・監視永続化
- Paper trading と本番 DB の分離
- LLM や外部 API 呼び出しに対するリトライ・フェイルセーフ実装

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading を切替）
  - run_monitoring.py: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の妥当性検証ツール
- 監視
  - monitoring_engine.py: 各モニタ（System/Trade/Risk）を束ねる
  - monitoring_db.py: SQLite ベースの監視ログ永続化層
  - kill_switch.py: kill.flag による ExecutionEngine 停止メカニズム
- ポートフォリオ構築
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定／重み付け／株数算出／セクター制約 等
- リサーチ
  - factor_research.py, feature_exploration.py: ファクター算出、将来リターン、IC、統計サマリ
- AI
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py: MA とマクロセンチメントを合成して market_regime を書き込み
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.9+ を推奨（duckdb, psutil, openai 等が必要）
- SQLite は標準ライブラリで利用可能

依存ライブラリ（一例）
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例（仮）
- 仮想環境作成（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil openai pyyaml

初期設定
1. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザード後、.env がプロジェクトルートに作成されます（.env は Git 管理しないこと）

2. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の整合性をチェックします。--strict を付けると警告も失敗扱いになります。

3. データディレクトリ
   - 実行時に logs/ や data/ は自動作成されることが多いですが、手動で用意しておくと確実です。
   - 監視・実行用ファイル:
     - data/execution.pid
     - data/kill.flag
     - data/monitoring.db（デフォルト）
     - data/kabusys.duckdb（デフォルト）

使い方
------

主要コマンド（モジュール実行）

- ExecutionEngine を起動（本番／ペーパーは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - data/execution.pid に PID を書き込む

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に依存する sqlite_path（監視 DB）へ接続（Monitoring は環境に関わらず本番 sqlite_path を使用）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔秒数を上書き（デフォルト 60 秒）
    - data/stop_requested.flag が存在すると監視ループを終了

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH（PAPER_TRADING_SQLITE_PATH の代替）

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、ペーパートレードの約定挙動）
- OPENAI_API_KEY（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒、デフォルト 60）

例: .env の簡易スニペット
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

ログ
- ログは kabusys.utils.logging_setup.setup_logging を通じて設定され、デフォルトで logs/<app_name>.log に日次ローテーションで出力されます。logs/ は自動作成されますが、ディレクトリ作成に失敗した場合はコンソールのみの出力になります。

プロセス制御 / 停止フラグ
- 停止要求: data/stop_requested.flag（run_execution / run_monitoring が検知して停止）
- Kill Switch（自動停止）: kill_switch モジュールが data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与える仕組み
- PID: run_execution は data/execution.pid を使用／作成します

注意事項（運用上のポイント）
- 本番（KABUSYS_ENV=live）では LINE 通知や kill flag 設定等を慎重に確認してください（validate_config でいくつかのガードを出します）
- OpenAI API を使用する機能は API キー（OPENAI_API_KEY）と API コストに注意して利用してください
- paper_trading モードは本番 DB と完全に分離するよう設計されています（paper_sqlite_path を使用）

ディレクトリ構成（主要ファイル）
--------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py       — SQLite スキーマ / 永続化 API
      - monitoring_engine.py   — 各モニタを束ねるループ
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （注文監視ロジック; フォルダ内に存在）
      - risk_monitor.py        — ドローダウン / ポジション数監視
      - kill_switch.py         — kill.flag 書き込みロジック
      - alert_manager.py       — （アラート送信管理; フォルダ内に存在）
    - execution/
      - execution_engine.py    — ExecutionEngine 本体
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py      — ブローカークライアント生成（Mock を含む）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            — OpenAI を使ったニュースセンチメント
      - regime_detector.py     — 市場レジーム判定
    - tools/
      - paper_verification_report.py
    - data/ (実行時に使う)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag / stop_requested.flag

補足
----
- validate_config は PyYAML がインストールされていれば config/*.yaml のパース検証を行います。PyYAML が無い場合は警告を出してスキップします。
- AI 周りの API 呼び出しはリトライ・バックオフやレスポンスの厳密なバリデーションが組み込まれていますが、API 料金やレート制限に注意してください。
- DuckDB 接続を受け取る研究系関数（research/*）は外部依存（ネットワーク等）を持たず、prices_daily/raw_financials 等のテーブルを前提に動作します。

問題・貢献
-----------
- バグや改善提案は issue を作成してください。プルリクエスト歓迎です。

以上。必要があれば、README に記載する具体的な .env 例、systemd / Supervisor 用のサービス定義例、あるいは Docker 化手順などを追加で作成します。どの情報を追加したいか教えてください。