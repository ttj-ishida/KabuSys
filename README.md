KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（調査/ポートフォリオ構築/発注/監視/AI支援）用のコード群です。README は開発者・運用担当者向けの導入・実行手順と、主要コンポーネントの概要を日本語でまとめたものです。

要点
- Python で実装されたモジュール群（データ処理、リサーチ、ポートフォリオ構築、発注エンジン、監視、AI連携など）
- 永続化: DuckDB（分析用）・SQLite（監視 / ペーパートレード用）
- 環境設定は .env により管理。config_setup.py で初期作成ウィザードあり
- run_execution.py / run_monitoring.py がそれぞれ発注エンジン／監視ループの起動スクリプト

機能一覧
- 環境設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 発注エンジン起動（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使って data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度設定・PID 管理・停止フラグ監視対応
- 監視ループ起動（run_monitoring.py）
  - システム状態、データ鮮度、トレード状況、リスク指標の定期ポーリング
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
- 監視データ永続化（monitoring.monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを提供
- リスク監視（monitoring.risk_monitor）・キルスイッチ（monitoring.kill_switch）
  - 条件に応じて kill.flag を書き込み ExecutionEngine に停止を促す
- ポートフォリオ構築（portfolio）
  - 候補選定、等ウェイト／スコア加重、ポジションサイジング、セクターキャップ、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン、IC 計算、統計サマリー
- AI連携（ai）
  - ニュースを LLM（OpenAI）でスコア化（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - LLM 呼び出し部分はリトライ等のフェイルセーフ実装済み
- ユーティリティ
  - ロギング設定（utils.logging_setup）: stdout と日次ローテートファイル出力
  - プロセス優先度・CPU affinity（utils.process_priority）

セットアップ手順（開発 / ローカル実行向け）
1. Python 環境
   - Python 3.9+ を想定（各自の環境に合わせてください）
   - 仮想環境の作成を推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config 検証時に config/*.yaml をパースする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env の作成
   - 初回はウィザードを使うのが簡単:
     - python -m kabusys.config_setup
   - 主要な環境変数（最低限設定が必要なもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - 他: LINE 関連トークンなど（任意）
   - .env 自動読み込み:
     - プロジェクトルートにある .env / .env.local は起動時自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. ディレクトリ作成（必要に応じて）
   - data/ と logs/ は自動生成されることが多いですが、パーミッション等で失敗する可能性があります。手動で作成しておくと安心です。

使い方（主要なコマンド例）
- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告をエラー扱い）: python -m kabusys.validate_config --strict

- 発注エンジン（ExecutionEngine）起動
  - python src/kabusys/run_execution.py
  - 挙動:
    - 起動時にプロセス優先度を "high" に設定
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使い、本番 DB と分離
    - data/stop_requested.flag が存在すると起動をせず終了。実行中は同ファイルの作成で停止を促す
    - 実行時の PID は data/execution.pid に書き込まれる

- 監視ループ起動
  - python src/kabusys/run_monitoring.py
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 挙動:
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - System / Trade / Risk の各モニタを定期的に実行し、必要に応じて kill.flag を書き込む・アラートを送る

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

- AI スコアリング / レジーム判定（Python API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日用のニュースウィンドウ（前日15:00 JST〜当日08:30 JST）で記事をスコア化し ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 指標 + マクロニュースで市場レジームを判定し market_regime に書き込む
  - いずれも api_key を省略すると環境変数 OPENAI_API_KEY を参照

ロギング
- ログはデフォルトで stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日分保持）に出力されます
- LOG_DIR 環境変数でログ保存先を上書きできます
- アプリケーションごとのログファイル名は run_monitoring.py などの setup_logging で app_name を渡しています（例: execution → logs/execution.log）

運用に関する注意
- Kill Switch / Stop フラグ
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）: リスク条件等で監視コンポーネントが書き込むことで ExecutionEngine 側に停止を促します
  - stop_requested.flag（data/stop_requested.flag）: 起動スクリプトが周期的にチェックしている停止フラグ。作成するとループが終了します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を起動時にクリアする動作がありますが、本番では 0 を推奨します
- DB 分離
  - monitoring（監視）用の SQLite（SQLITE_PATH）は監視専用で、発注エンジンは paper_trading モードで paper_sqlite_path を使います。設定を誤るとデータが混在するため注意してください
- 本番環境
  - KABUSYS_ENV=live の設定は慎重に。validate_config で本番向けチェックや警告が出るようになっています
  - LINE 通知などの設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）は本番アラートに必要です

ディレクトリ構成（主要ファイル / モジュール）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動読み込み機能を含む）
  - config_setup.py
    - .env 初期作成ウィザード（対話式）
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化および永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （存在）トレード監視ロジック（コードベースに含まれる）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各モニタを束ねる実行ループ
    - alert_manager.py — （存在）アラート送信ロジック（LINE 等）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - ExecutionEngine の核心部分（発注・リスク管理・リコンサイル）
  - portfolio/
    - portfolio_builder.py — 候補抽出・重み計算
    - position_sizing.py — 発注株数計算・資金配分ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + 指標）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

補足（よくある質問）
- Q: 監視はどの DB を見るの？
  - A: run_monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。KABUSYS_ENV に関係なく本番 sqlite_path を参照します。
- Q: ペーパートレードの履歴は本番 DB に混ざる？
  - A: run_execution は KABUSYS_ENV=paper_trading の場合 settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用するので分離されます。
- Q: OpenAI の呼び出しが失敗したらどうなる？
  - A: AI 関連のモジュールはリトライ・フォールバック（スコアを 0 にする等）を実装しており、致命的な例外を上位に投げない設計が基本です。ただし API キー未設定などは明示的にエラーになります。

貢献 / 拡張のヒント
- strategy / execution のエンジン部分はプラグイン的にモデルやブローカークライアントを差し替えられる設計を想定しています
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news など）にデータを投入すれば、research モジュールをそのまま使って解析できます
- utils.logging_setup は起動スクリプトから呼び出せば一貫したログ出力が得られます。CI では LOG_DIR をログ収集先に設定してください

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）

連絡先
- このドキュメントの補足や質問があればリポジトリの Issue にお願いします。

以上がこのコードベースの主要な説明と運用手順です。必要であれば「設定ファイルのサンプル .env.example」や「起動ユニット（systemd / docker-compose）テンプレート」などの追加ドキュメントも作成します。どれが必要か教えてください。