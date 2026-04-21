README
======

概要
----
KabuSys は日本株の自動売買システム（プロトタイプ）向けの Python パッケージです。本リポジトリは以下の主要機能を含みます:

- 戦略・ポートフォリオ構築（選定、重み付け、ポジションサイジング）
- 実行エンジン（ExecutionEngine） — 発注管理／リスク制御
- 監視（Monitoring） — システム状態、注文ログ、リスク監視、Kill Switch
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

機能一覧
--------
主な機能と特徴:

- 環境設定管理
  - .env 自動読込（OS 環境 > .env.local > .env、無効化可能）
  - config_setup による対話式 .env 作成
- 実行／監視プロセス
  - run_execution.py: ExecutionEngine を起動
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に分離保存
  - run_monitoring.py: SystemMonitor を定期ポーリング（デフォルト 60 秒）
    - 環境変数 MONITOR_POLL_INTERVAL で間隔変更可
  - stop/kill フラグファイルを通じた安全停止（data/stop_requested.flag, data/kill.flag）
- 監視データ永続化
  - SQLite を使用（monitoring 用 DB は data/monitoring.db がデフォルト）
  - monitoring_db モジュールでテーブル作成・マイグレーション管理
- ポートフォリオ構築
  - 候補選定、等分配・スコア重み配分、セクターキャップ、レジーム乗数
  - ポジションサイズ計算（Lot 単位丸め、集約キャップ）
- リサーチ
  - DuckDB を利用したファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント scoring（ai.news_nlp）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（ai.regime_detector）
  - API 呼び出しは冪等・バックオフ・検証済みの結果保存を行う
- 開発用ツール
  - config_setup: .env を対話的に生成
  - validate_config: 起動前設定検証（--strict で警告を FAIL 扱い）
  - tools.paper_verification_report: ペーパートレード結果の判定レポート生成

前提条件
--------
- Python 3.9+（ソースの型ヒント等を想定）
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - sqlite3（標準ライブラリ）
  - （任意）PyYAML（validate_config の YAML 検証に必要）
- OS 権限: プロセス優先度設定や CPU affinity の一部操作は管理者権限が必要な場合があります。

セットアップ手順
---------------
1. リポジトリをクローン / 展開
   - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出されます。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - validate_config の完全な YAML 検証を使う場合は pip install PyYAML

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは手動で .env をプロジェクトルートに配置。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - paper_trading: 実取引 API を使わず MockBroker を使用、DB を data/paper_trading.db に分離
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- OPENAI_API_KEY (AI 機能利用時に必須)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒、デフォルト: 60)
- KILL_FLAG_CLEAR_ON_START (0/1、本番では 0 推奨)

使い方
------
アプリケーションはモジュールとして実行できます。プロジェクトルートで実行してください。

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
    - paper_trading 環境では MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH を利用

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（1 以上）
  - 監視は Settings に基づき（環境にかかわらず）production 用 sqlite_path を使用する点に注意

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="…")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="…")
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY で指定
  - API 呼び出しは冪等性・バックオフ処理が組み込まれています

ロギング
--------
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="…")
- デフォルトで stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション、30世代保持）に出力
- ログディレクトリは環境変数 LOG_DIR またはデフォルト "logs" を使用

停止制御・フラグファイル
--------------------
- 実行エンジンの停止や起動制御にはファイルベースのフラグを使用しています:
  - data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（手動で作成して停止をトリガー可）
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る（検出時は停止）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では危険なので 0 推奨）

データベース
----------
- DuckDB: 分析・リサーチ用（デフォルト: data/kabusys.duckdb）
- SQLite:
  - 監視用 monitoring DB: data/monitoring.db（init_monitoring_db がテーブル作成・マイグレーションを行う）
  - ペーパートレード用 DB: data/paper_trading.db（paper_trading 環境で使用）
- monitoring_db モジュールによるスキーマ管理・簡易マイグレーション実装あり

注意事項 / トラブルシューティング
---------------------------------
- 設定検証: python -m kabusys.validate_config を起動前に必ず実行してください。PyYAML がないと YAML 検証はスキップされますが警告が出ます。
- OpenAI API:
  - OPENAI_API_KEY が未設定だと ai モジュールはエラーまたは ValueError を投げます。テスト時は API 呼び出し関数をモックしてください。
- プロセス優先度設定:
  - psutil を利用してプロセス優先度や CPU affinity を設定します。権限不足やプラットフォーム非対応の場合は警告を出してスキップします。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- monitoring はコード内コメントの通り「環境にかかわらず本番 sqlite_path を使用」します（監視対象 DB を間違えないよう注意）。

ディレクトリ構成
----------------
（プロジェクトルート直下に src/kabusys 以下が置かれている前提）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（自動 .env 読込含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py     — 共通ログ設定
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite テーブル初期化・永続化層
    - system_monitor.py    — システム状態 & データ鮮度監視
    - trade_monitor.py     — 注文ログ監視（該当ファイル参照）
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — Kill Switch（flag ファイル生成）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py     — アラート送信（LINE 等、該当実装を参照）
  - execution/             — ExecutionEngine, OrderManager, BrokerFactory 等
  - portfolio/             — portfolio_builder, position_sizing, risk_adjustment
  - research/              — factor_research, feature_exploration（DuckDB ベース）
  - ai/
    - news_nlp.py          — ニュース NLP（OpenAI を使ったセンチメント）
    - regime_detector.py   — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートツール
  - data/ (実行時に作成されることが想定)
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag / stop_requested.flag
  - logs/ (デフォルトのログ出力先)

付記
----
- 本 README はソースコードのコメント / 実装に基づき作成しています。実際の運用では config/*.yaml、各 BrokerClient 実装、通知チャネル（LINE 等）の設定やキー管理を適切に行ってください。
- 本ソフトウェアは金融資産の運用に関わるため、本番運用前に十分なテストとリスクレビューを行ってください。

お問い合わせ / 開発
-----------------
- 実装に関する質問や改善提案はリポジトリの Issue を使用してください。README にない CLI や内部 API を利用する場合は該当モジュールの docstring を参照してください。