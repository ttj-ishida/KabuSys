README — KabuSys（日本株自動売買システム）
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには、
- 実行エンジン（ExecutionEngine）と監視ループ（Monitoring）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- DuckDB を使ったリサーチ/ファクター計算
- OpenAI を利用したニュース NLP（センチメント付与）／レジーム判定
- 環境設定ウィザードと設定検証ツール
などのコンポーネントが含まれます。

特徴
----
主な機能・設計上のポイント：
- ExecutionEngine と Monitoring を別プロセスで稼働させ、監視から自動的に停止信号（Kill Switch）を発行可能
- Paper Trading モード（KABUSYS_ENV=paper_trading）で本番 DB と分離し、MockBrokerClient を使用
- DuckDB を分析用（prices_daily, raw_financials 等）に利用、SQLite を監視・トレードログ保存に利用
- ニュース記事を LLM（OpenAI）でスコアリングする ai モジュール（バッチ・リトライ・バリデーション対応）
- ポートフォリオ選定・重み付け・ポジションサイズ算出の純粋関数群（テストしやすい設計）
- ロギングはコンソール + 日次ローテートファイル出力（logs/*.log、30 日保持）
- process priority / CPU affinity 設定で実行プロセスの優先度制御

前提・必要条件
--------------
推奨 Python バージョン: 3.10+
主な依存パッケージ（代表例）:
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML を厳密に検証したい場合）
インストール方法（例）:
- 仮想環境作成: python -m venv .venv && source .venv/bin/activate
- パッケージインストール: pip install duckdb psutil openai pyyaml
（本リポジトリに requirements.txt があればそれを使ってください）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成／有効化する。
2. 必要パッケージをインストールする（上記参照）。
3. data ディレクトリと logs ディレクトリを作成（scripts / 実行スクリプトでも自動作成されますが、手動作成しておくと権限問題を回避できます）。
   - mkdir -p data logs
4. .env を作成する（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを対話式に生成します。
5. 設定検証:
   - python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。
6. 必要に応じて DuckDB / SQLite の初期化は起動スクリプトが行います（monitoring 用テーブルなどは自動作成されます）。

主要な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／オプション:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading モード時）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: ニュース NLP / レジーム判定で必要
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、本番は 0 推奨）

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env の初期作成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（デフォルト data/paper_trading.db）を使用して MockBrokerClient を使用
    - pid ファイル: data/execution.pid（設定で上書き可）
    - 停止制御: data/stop_requested.flag（存在すると起動を抑止または停止トリガー）
    - プロセス優先度を "high" に設定しようとする（権限がなければ警告を出して続行）

- Monitoring（システム・トレード・リスク監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
    - 監視 DB（SQLite）は環境にかかわらず本番 sqlite_path を使用
    - stop_requested.flag を検知するとループ終了

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能

- ai モジュール（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OPENAI_API_KEY（または引数 api_key）を参照します。

動作の仕組み（ポイント）
-----------------------
- DB:
  - DuckDB: 分析 / リサーチ用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・トレードログ用（デフォルト data/monitoring.db）
  - Paper Trading モードでは専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と完全分離
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を使って統一的に設定
  - stdout（StreamHandler）と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）
- 優先度:
  - 起動スクリプトは set_process_priority("high") を呼び、可能な限りプロセス優先度を上げる
- 停止制御:
  - data/stop_requested.flag: run_*.py がポーリングループやスレッドを終了するために参照
  - Kill Switch: RiskMonitor 等の判定で data/kill.flag を作成して ExecutionEngine 停止を要求（Settings.kill_flag_path）
- 監視:
  - MonitoringEngine が SystemMonitor, TradeMonitor, RiskMonitor をまとめ、アラート通知や Kill Switch 発動を行う
- AI（OpenAI）:
  - ニュース NLU・レジーム検出は OpenAI API を利用。失敗時はフェイルセーフ（多くの場合スコアに 0 を用いるか処理をスキップ）
  - レスポンス検証、バッチ処理、指数バックオフ等を実装済み

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys をルートとした抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite スキーマ＆永続化 API
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （トレード監視。実装ファイルあり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み制御
    - alert_manager.py       — （アラート送信管理。実装ファイルあり）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig, run_session など）
    - broker_factory.py      — BrokerClientFactory（本番 / mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・集約キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

注意事項 / 運用上のヒント
-----------------------
- .env は機密情報を含むため絶対に Git 等へコミットしないこと。
- 本番運用時は KABUSYS_ENV=live を設定し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- OpenAI API 呼び出しはコストが発生するため、テストは mock か少量のデータで行ってください。
- ログディレクトリの書き込み権限や DB ファイルの配置場所（永続ストレージ）を事前に確認してください。
- Monitoring の閾値（CPU/MEM/DISK/ドローダウン等）は Settings または設定ファイルでチューニング可能です。

開発者向け・拡張ポイント
------------------------
- BrokerClientFactory に本物の broker クライアントをプラグインすることで実際の発注ロジックと接続可能
- ポートフォリオロジックやリスク制御は純粋関数で実装されているためユニットテストが書きやすい
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）を投入することで research / ai 機能を活用できます

ライセンス / バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報は本リポジトリのトップレベル LICENSE ファイルを参照してください（存在する場合）。

サポート / 連絡先
-----------------
実装上の不明点や仕様確認が必要な場合はリポジトリの Issues に記載してください。README の補足やセットアップ手順の改善提案も歓迎します。

以上。README の内容をプロジェクトの実態や運用方針に合わせて適宜調整してください。