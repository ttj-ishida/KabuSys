# KabuSys

KabuSys は日本株の自動売買・研究プラットフォームの一部を構成する Python コードベースです。本リポジトリには、モニタリング／実行エンジンの起動スクリプト、環境設定ウィザード、設定検証ツール、ポートフォリオ構築・リスク管理ユーティリティ、研究用ファクター計算、OpenAI を使ったニュース NLP / レジーム検出などのモジュールが含まれます。

以下は本コードベースの使い方・セットアップ方法・ディレクトリ構成の概要です。

プロジェクト概要
- 目的: 日本株向け自動売買システムの基盤ライブラリ群（実行エンジン・監視・ポートフォリオ構築・研究・AI補助機能等）。
- 設計方針:
  - 環境変数および .env による設定管理
  - Monitoring / Execution の分離（ペーパートレード用 DB もサポート）
  - DuckDB を用いた研究用データ処理、SQLite を監視/トレードログ用に利用
  - OpenAI API を用いたニュースセンチメント評価（オプション）
  - フェイルセーフ設計（API リトライ、部分失敗時の部分書き込み保護 等）

主な機能一覧
- 実行制御
  - run_execution: ExecutionEngine を起動（本番 / paper_trading 切替、PID 管理、stop フラグ監視）
- 監視
  - run_monitoring: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等へ記録
  - MonitoringEngine：System / Trade / Risk モニタを束ねてアラート・Kill Switch を評価
  - KillSwitch：ドローダウンやポジション上限に応じて data/kill.flag を書き込み Execution を停止
- 環境設定・検証
  - config_setup: 対話式ウィザードで .env を生成
  - validate_config: .env と config/*.yaml を事前検証
- 研究・ユーティリティ
  - research.factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB 利用）
  - research.feature_exploration: 将来リターン・IC 計算などの統計ツール
  - portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限 等
- AI（オプション、OpenAI 必須）
  - ai.news_nlp: ニュース記事をまとめて OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み
  - ai.regime_detector: ETF の MA とマクロニュースの LLM スコアを合成して market_regime を更新
- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、成功率、レイテンシ等）

前提・依存関係
- Python 3.10+（型ヒントの union などを想定）
- 必須ライブラリ（インストール推奨）:
  - duckdb
  - psutil
  - openai（OpenAI API を使う機能を実行する場合）
- 任意:
  - PyYAML（validate_config が config/*.yaml のパース検証を行う場合に必要）
- 標準ライブラリ: sqlite3, threading, logging, argparse など

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo_url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を使うなら）pip install PyYAML
   - もし requirements.txt が用意されていれば: pip install -r requirements.txt
4. .env の初期作成
   - python -m kabusys.config_setup
     - 対話式に各種環境変数を入力して .env を生成します
   - 自動ロード: デフォルトではプロジェクトルートの .env/.env.local を自動でロードします。自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict で警告も FAIL 扱いにできます
6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

主要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI 機能を使う場合に必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV: execution モード (development | paper_trading | live). デフォルト: development
- LOG_LEVEL (デフォルト: INFO)
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ

使い方（主なコマンド）
- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードが paper_trading の場合、MockBroker を使い data/paper_trading.db に記録
  - 実行時は data/execution.pid（PID ファイル）が使用されます
  - 停止: data/stop_requested.flag を作成するとスレッドが検知して停止します
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには MONITOR_POLL_INTERVAL 環境変数を設定（秒）
  - 監視は settings.sqlite_path（通常 data/monitoring.db）に書き込み
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- AI 系機能（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを呼ぶには DuckDB 接続と OPENAI_API_KEY（引数でも指定可）が必要

停止・安全関連
- data/stop_requested.flag
  - run_execution / run_monitoring の両方がこのフラグを見て安全に停止します（起動スクリプト参照）。
- data/kill.flag（Kill Switch）
  - Monitoring がリスク条件（例: ドローダウン超過）を検出したときに KillSwitch が書き込み、ExecutionEngine に停止を促します。
  - KillSwitch.clear() により起動時に自動クリアする挙動は KILL_FLAG_CLEAR_ON_START により制御可（本番では無効推奨）。
- PID ファイル: data/execution.pid（ExecutionEngine 用）

ログ
- ログは kabusys.utils.logging_setup.setup_logging によって統一的に設定されます:
  - コンソール出力（stdout）
  - ファイル出力: logs/<app_name>.log（日次ローテーション、30 日保持）
- LOG_DIR 環境変数でログディレクトリを上書き可能

DB とスキーマ
- DuckDB: 分析用（prices_daily, raw_financials, raw_news などのテーブルを想定）
- SQLite: 監視・発注ログ等（デフォルト data/monitoring.db / paper_trading.db）
- init_monitoring_db(conn) は監視に必要なテーブルを冪等に作成し、簡易マイグレーションも行います

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (※実装ファイルがある前提)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (※実装ファイルがある前提)
  - execution/ (ExecutionEngine 周りの実装)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

（注）上記はリポジトリ内の代表的なファイルを抜粋した一覧です。実際のツリーはプロジェクト内のファイル群に従ってください。

開発者向けノート
- 自動 .env 読み込みはプロジェクトルートの存在（.git または pyproject.toml）を基に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。
- OpenAI 呼び出し部はリトライ・ペイロード検証等を実装しており、部分失敗時に DB の既存データを保護するよう設計されています（部分 DELETE → INSERT 等）。
- process_priority は psutil を使って OS ごとに優先度を調整します。権限不足の場合は警告ログを出して継続します。
- DuckDB クエリは lookahead バイアスを避けるように日付条件に注意して設計されています（研究モジュール参照）。

よくある運用フロー（サンプル）
1. .env を用意（config_setup を実行）
2. validate_config で設定を検証
3. DuckDB / SQLite に必要なテーブルをロード（ETL スクリプト等、別途実行）
4. run_execution を本番/ペーパートレードで起動
5. run_monitoring を別プロセスで常時起動して稼働監視・Kill Switch を稼働
6. Paper Trading の評価は tools.paper_verification_report を定期実行して品質を確認

ライセンス・貢献
- 本 README にはライセンス情報を含めていません。リポジトリの LICENSE ファイルに従ってください。
- バグ報告・プルリクエストはリポジトリの Issue / PR ワークフローを使用してください。

---

不明点や README に追記したい内容（例: サンプル .env、より詳細な起動オプション、docker-compose 例など）があれば教えてください。必要に応じて README を拡張して YAML サンプルや運用手順を追加できます。