README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主要機能は発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）などを含みます。  
設計方針として「本番とペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗はフォールバック）」を重視しています。

主な特徴
--------
- ExecutionEngine：リアル/ペーパーのブローカークライアントを切り替えて発注を行う。
- Monitoring：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期ポーリングして SQLite に永続化。Kill Switch（フラグファイル）でエンジン停止可能。
- Portfolio：候補選定、重み付け、ポジションサイズ計算、セクターキャップ・レジーム調整等の純粋関数群。
- Research：DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ。
- AI：ニュース記事を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込む。市場レジーム判定モジュールあり。
- Tools：Paper Trading 検証レポート生成スクリプト等ユーティリティ。
- 設定管理：対話式 .env 作成ウィザードと起動前設定検証 CLI を備える。

セットアップ手順
----------------
前提
- Python 3.9+ を推奨
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証で任意）
インストール例:
  pip install duckdb psutil openai PyYAML

リポジトリルートの想定構成:
  - .env / .env.local（環境変数）
  - data/（SQLite/duckdb 等を配置）
  - logs/（ログ出力）

1) 環境変数の準備
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨・よく使う設定例:
  - KABUSYS_ENV=development | paper_trading | live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=（ニュース NLP / レジームで必要）
  - PID_FILE_PATH=data/execution.pid
  - KILL_FLAG_CLEAR_ON_START=0  # 本番では 0 推奨
- .env 自動ロード:
  - プロジェクトルートが特定できれば .env/.env.local を自動読み込みします。
  - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

2) .env 作成（対話式）
  python -m kabusys.config_setup
  → 対話に従って .env を生成できます。

3) 起動前検証（任意だが推奨）
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いになります。

使い方（よく使うコマンド）
------------------------
- ExecutionEngine を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番DBとは分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に stop をしたい場合は data/stop_requested.flag を作成して下さい（run_execution はフラグ検知で engine.stop() を呼びます）。

- Monitoring（監視ループ）を起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず監視 DB は本番 DB を想定）。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- .env 作成ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite パスを上書き可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

- AI（ニューススコアリング / レジーム判定）
  - 実行はライブラリ関数を呼ぶか、専用スクリプト（存在する場合）を使用します。OpenAI API キーが必要です。
  - 実装例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime（いずれも api_key 引数 or 環境変数 OPENAI_API_KEY を参照）

停止・Kill Switch
-----------------
- Kill Switch（実行エンジン停止）:
  - KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止を促します。KillSwitch はリスク条件（ドローダウン、ポジション上限）で自動的に書き込まれることがあります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアします（本番では 0 推奨）。
- 一時的に全プロセス停止させたい場合は data/stop_requested.flag を作成してください（run_execution / run_monitoring が検知して終了します）。

ログ
---
- ログは stdout とファイルに出力されます（logs/<app_name>.log）。
- ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/。
- ログレベルは環境変数 LOG_LEVEL（デフォルト INFO）または setup_logging の引数で上書き可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール／ファイル一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - execution/
    - execution_engine.py    — 実行エンジン（起動・セッション制御）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
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

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

  - tools/
    - paper_verification_report.py

設定（環境変数一覧・主要説明）
------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 関連)
- MONITOR_POLL_INTERVAL (監視ポーリング秒数、デフォルト 60)
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか、0/1)

トラブルシューティング
----------------------
- 必須環境変数が未設定だと Settings のプロパティアクセス時に例外が発生します。validate_config で事前チェックしてください。
- DuckDB/SQLite ファイルのパーミッションや parent ディレクトリが存在しないとログや DB 作成に失敗する可能性があります。最初に data/ や logs/ の作成を確認してください。
- psutil によるプロセス優先度設定は管理者権限が必要な場合があります。AccessDenied 例外は警告としてスキップされます。
- OpenAI 関連は API レート制限やネットワーク障害に対してリトライを持ちますが、API キーが未設定だと ValueError が発生します。
- ログ出力先に問題がある場合は stdout にも出るようになっているので、まず stdout を確認してください。

開発者向けメモ
---------------
- monitor / execution は stop フラグ（data/stop_requested.flag）を参照して安全にシャットダウンします。CI やデバッグ実行時はこのファイルの存在を確認してください。
- monitoring_db.init_monitoring_db() は冪等にテーブルと列のマイグレーションを行います。
- research モジュールは DuckDB に prices_daily / raw_financials テーブルがあることを前提としています。ローカル開発ではダミーデータで動作確認してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（kabusys/__init__.py）

以上が主要な README 相当の内容です。必要ならばサンプル .env テンプレートや起動フロー図、より詳細な各モジュールの API ドキュメントを追記します。どの情報を優先して追加しますか？