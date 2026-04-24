KabuSys — 日本株自動売買システム
=============================

この README は、与えられたコードベース（src/kabusys 以下）を元にした概要・セットアップ・実行方法の簡易ガイドです。開発者向けの補助ドキュメントとして、主要機能やディレクトリ構成、よく使うコマンド／環境変数を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買に関する以下の機能群を含むパッケージです（ライブラリ＋起動スクリプト）:

- 実行エンジン（ExecutionEngine）の起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock / 実ブローカー）
  - 注文管理・リスク管理・照合（reconciler）を組み合わせて取引セッションを実行
- 監視（Monitoring）の起動スクリプト（run_monitoring.py）
  - システム稼働・データ鮮度・注文状況・リスクなどを定期ポーリング
  - Kill Switch（条件でエンジン停止フラグを書き込む）をサポート
- 研究用モジュール（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）など
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- AI 関連（ai）
  - ニュースの NLP スコアリング（OpenAI を利用）
  - 市場レジーム判定モジュール（AI＋MA200 を合成）
- ユーティリティ（utils）
  - ログ設定、プロセス優先度設定など
- ツール（tools）
  - Paper Trading 検証レポート生成スクリプトなど
- コンフィグ支援
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

主な機能一覧
--------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - Settings クラス経由で環境変数取得（バリデーションあり）
- 実行・監視
  - run_execution.py: ExecutionEngine を起動して取引セッションを実行
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録
  - run_monitoring.py: SystemMonitor を定期実行し system_status 等を監視・永続化
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
- データ永続化（SQLite / DuckDB）
  - monitoring 用の SQLite（デフォルト data/monitoring.db）を初期化・マイグレーションするユーティリティ
  - DuckDB を分析用 DB として使用（デフォルト data/kabusys.duckdb）
- AI (OpenAI)
  - ニュース集約→LLM で銘柄ごとにセンチメントを算出して ai_scores テーブルへ書込
  - 市場レジーム（bull/neutral/bear）の算出と永続化
- 研究用・ポートフォリオ関数群
  - ファクター計算、IC 計算、position sizing、sector cap などは純粋関数として提供（副作用なし）

セットアップ手順
----------------
下記は推奨のローカル開発セットアップ手順の例です。

1. Python 環境
   - Python 3.9+ を推奨（プロジェクトの実際の最小バージョンはプロジェクト設定に従ってください）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
     - （開発用）PyYAML を入れると validate_config の YAML 検証が有効化されます
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （実運用では requirements.txt / poetry / pipenv を用意してください）

3. .env の初期作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください
   - 重要: .env は決して Git にコミットしないでください（ウィザードにもその旨が記載されています）

4. 設定検証
   - python -m kabusys.validate_config
   - 本番運用前は --strict を付けて警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリの確認
   - data/ (DB や PID・フラグファイルを置く想定)
   - logs/ (ログ格納)
   - スクリプトは起動時に多くはディレクトリを自動作成しますが、権限やマウント先の確認を行ってください

使い方（主要コマンド）
---------------------

- 実行エンジン（Execution）
  - 標準起動:
    - python -m kabusys.run_execution
  - KABUSYS_ENV により動作モードを切替:
    - ペーパートレード: export KABUSYS_ENV=paper_trading
    - 本番: export KABUSYS_ENV=live
  - ペーパートレード時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録され、本番 DB とは分離されます

- 監視（Monitoring）
  - 標準起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - export MONITOR_POLL_INTERVAL=30  # 30 秒ごとにポーリング
  - 停止フラグ:
    - data/stop_requested.flag を作成すると対象スクリプトが検知して安全終了します（監視/実行ともに使用）

- .env ウィザード / 検証
  - 設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でファイルパスを指定可能。

- AI 機能（プログラム内 API）
  - ニューススコアリング:
    - 関数 kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を利用
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API キーは必須。API 呼び出しはネットワーク/料金のリスクがあるため実行時に注意してください

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行モード（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite DB デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite DB（paper_trading 時に使用） デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） デフォルト: 60
- PAPER_FILL_MODE: ペーパートレードの注文約定モード（instant/partial/never/reject） デフォルト: instant
- KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag をクリアするか（0/1） デフォルト: 0（本番では 0 推奨）

ディレクトリ構成（src/kabusys ベース）
--------------------------------------
大まかなファイル・パッケージ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # Monitoring 起動スクリプト
  - config.py                 # Settings / .env 自動読み込み
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - utils/
    - logging_setup.py        # ログ設定ユーティリティ
    - process_priority.py     # プロセス優先度設定ユーティリティ
  - monitoring/
    - monitoring_db.py        # SQLite スキーマと永続化 API
    - monitoring_engine.py    # 各 Monitor を束ねるエンジン
    - system_monitor.py       # システム・データ鮮度監視
    - trade_monitor.py        # 注文系監視（コードベースに含まれる）
    - risk_monitor.py         # ドローダウン・ポジション上限監視
    - kill_switch.py          # Kill Switch 実装
    - alert_manager.py        # 通知管理（コードベースにある想定）
  - execution/                 # エンジン本体（複数ファイル: engine, order_manager, risk_manager など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

注意点 / 運用上のヒント
-----------------------
- DB 分離
  - ペーパートレード用 DB と本番監視 DB は明確に分離されています（paper_trading.db vs monitoring.db）。
- ログ
  - setup_logging() は stdout と日次ローテーションファイル（logs/<app_name>.log）を設定します。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。
- プロセス管理
  - スクリプト起動時に set_process_priority("high") が試みられます。psutil による権限の問題で失敗することがありますが、警告が出てスキップされます。
- Kill / Stop フラグ
  - data/stop_requested.flag: モニタリング・エンジンが検知して安全に終了するための停止フラグ
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine を停止するために使用される（内容は理由文字列）
- AI 呼び出し
  - ai モジュールは外部 API（OpenAI）に依存します。API エラーはリトライロジックやフォールバック（例: macro_sentiment=0.0）で扱われますが、実行時に料金とレート制限が発生する点に注意してください。
- テストと自動化
  - validate_config.py による事前チェックを CI に組み込むと安全です
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます（テスト等で使用）

付録: よく使うコマンド例
-----------------------
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（ペーパートレード例）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視起動（デフォルト 60 秒間隔、変更可）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースに含まれる設計意図・起動スクリプト・設定周りの使い方をまとめたものです。実運用やデプロイ時はログローテーションの方針、DB バックアップ、API キー管理、監視・アラート設定（LINE など）を別途整備してください。必要ならば README の内容を拡張して、デプロイ手順・運用手順・テスト手順を追加できます。必要な拡張があれば教えてください。