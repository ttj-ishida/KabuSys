KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買システム KabuSys のコアモジュール群です。
README は開発者／運用者向けの簡易ドキュメントで、プロジェクトの概要、機能一覧、
セットアップ手順、基本的な使い方（起動スクリプト）、およびディレクトリ構成をまとめます。

要点
-----
- Python モジュール群は src/kabusys 以下に配置されています。
- 設定は .env / 環境変数で管理します（自動ロード機構あり）。
- 実行用スクリプト（監視 / 実行エンジンなど）はパッケージ内にあり、モジュールとして起動します。
- ログはデフォルトで logs/ に日次ローテーションで出力されます。
- 永続化は主に SQLite（監視用）と DuckDB（分析用）を使用します。

プロジェクト概要
----------------
KabuSys は以下のような関心領域に分かれたモジュール群を提供します。

- 実行（Execution）: 発注エンジン、ブローカークライアント、オーダー管理、リスク管理など
- 監視（Monitoring）: システム稼働、注文ログ、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- ポートフォリオ構築（Portfolio）: 候補選定、配分重み、ポジションサイズ計算、セクター制限など
- 研究（Research）: ファクター計算（モメンタム、バリュー、ボラティリティ）、特徴量解析
- AI / NLP: ニュースセンチメント集約（OpenAI を利用した scoring）、市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定読み込みウィザード／検証など
- ツール: Paper Trading の検証レポート生成スクリプト など

主な機能一覧
--------------
- Settings クラスによる環境変数ベースの設定管理（.env/.env.local の自動読み込み）
- 実行エンジン起動スクリプト（run_execution）：
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading DB に記録
  - 停止フラグ（data/stop_requested.flag）・kill.flag による安全停止
- 監視ループ起動スクリプト（run_monitoring）：
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（デフォルト 60 秒）
- MonitoringDB：SQLite を使った監視ログ永続化（system_status/trade_logs/positions/...）
- KillSwitch：条件に応じて data/kill.flag を作成し ExecutionEngine に停止シグナルを送る
- Portfolio モジュール：候補選定・等分配・スコア重み・リスク調整・ポジションサイズ算出
- Research モジュール：DuckDB を用いたファクター計算（momentum/value/volatility）や IC 計算
- AI モジュール：OpenAI を用いたニュースセンチメント集約（score_news）と市場レジーム判定（score_regime）
- tools/paper_verification_report.py：paper_trading DB から検証レポートを生成

セットアップ手順
-----------------
前提
- Python 3.9+（依存パッケージはプロジェクトの pyproject.toml / requirements に従う）
- DuckDB、sqlite3 は Python 標準／外部ライブラリで利用可能
- OpenAI API を利用する機能を使う場合は OpenAI の API キーが必要

1. リポジトリをクローンしてソース配下へ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt または pyproject.toml に従う

3. 環境変数設定 (.env)
   - プロジェクトルートに .env を置くか、環境変数で設定します。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

重要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - OPENAI_API_KEY: OpenAI を用いる機能で必要
- 監視用:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリア（1=クリア、デフォルト 0）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）

.env を対話的に作成する
- python -m kabusys.config_setup
  - ウィザード形式で .env を作成・更新できます

設定の検証
- python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit code 1）になります

使い方（起動・運用）
--------------------

1) 監視（Monitoring）を起動する
- 目的: SystemMonitor をポーリングして状態を SQLite に記録し、Kill Switch 等を評価
- 実行コマンド例:
  - python -m kabusys.run_monitoring
- 説明:
  - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で変更可能。
  - 監視ループはプロジェクトルート/data/stop_requested.flag を検知すると終了します。

2) 実行エンジン（Execution）を起動する
- 目的: 発注エンジン（ExecutionEngine）を起動して取引を行う（または paper_trading にて模擬）
- 実行コマンド例:
  - python -m kabusys.run_execution
- 説明:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と完全分離します。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルが送られます。
  - 実行中は data/execution.pid に PID を書く仕組みがあります（設定により変更可能）。

3) Kill Switch / 停止フラグ
- KillSwitch は監視処理が条件を満たしたときに Settings.kill_flag_path（デフォルト data/kill.flag）へ書き込みを行い、ExecutionEngine 側でこれを検知して停止できます。
- 手動でプロセスを止めたい場合はプロジェクトルート/data/stop_requested.flag を作成すると run_* の polling ループは終了します。

4) Paper Trading 検証レポート
- tools/paper_verification_report.py を使って検証レポートを生成できます。
- 実行例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の SQLite ファイルを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も可）

5) AI（ニュースセンチメント / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）。
- プログラムから呼び出す例（簡易）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")
- 注意: LLM 呼び出しはリトライやフェイルセーフ実装あり。API キー未設定時は例外になります。

ログ
-----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30 日保持）。
- setup_logging を各起動スクリプトが呼び出して統一的なログ管理を行っています。
- ログレベルは LOG_LEVEL 環境変数で制御できます。

ディレクトリ構成
----------------
以下は主要なファイル／モジュールの一覧（抜粋）。実際のファイル数はこれより多くあります。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / .env 読み込みと Settings
    - config_setup.py                — .env 対話ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - ai/
      - news_nlp.py                  — ニュースセンチメント（OpenAI）
      - regime_detector.py           — 市場レジーム判定（OpenAI）
      - __init__.py
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py             — （存在する想定のモジュール）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py             — （存在する想定のモジュール）
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
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/
      - (ExecutionEngine, BrokerFactory, OrderManager などの実装モジュール)
    - data/
      - pipeline.py                   — DuckDB データ取得ユーティリティなど（参照有）

補足・運用上の注意
------------------
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブル／カラム追加を行う設計です。run_* が起動時に呼び出しています。
- 自動 .env ロード:
  - プロジェクトルートは .git または pyproject.toml によって自動検出されます。
  - OS 環境変数は上書き不可（保護されます）。
- 実行プロセス優先度:
  - run_* スクリプトは起動直後に set_process_priority("high") を呼びます。プラットフォームによっては権限が必要で失敗する場合がありますが警告に留まります。
- セキュリティ:
  - .env は機密情報を含むため決して Git にコミットしないでください（config_setup も同旨の注意を出力します）。
- 本番運用:
  - KABUSYS_ENV=live 時は通知設定（LINE）や kill flag の自動クリア設定等を特に注意してください。validate_config は本番向けチェック（警告）を行います。

トラブルシュート（よくある質問）
--------------------------------
- 起動時に設定エラーが出る:
  - python -m kabusys.validate_config を実行して必須環境変数が揃っているか確認してください。
- ログファイルが作成されない:
  - LOG_DIR 環境変数やログディレクトリに書き込み権限があるか確認してください。ログディレクトリ作成に失敗すると標準出力のみになります。
- 実行エンジンが停止しない／停止してほしい:
  - プロジェクトルート/data/stop_requested.flag を作成すると監視プロセス・実行スレッドは終了します。
  - KillSwitch は条件を満たすと data/kill.flag を書き込みます。KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアされるため、本番では 0 を推奨します。

ライセンス・貢献
----------------
- このリポジトリのライセンス情報およびコントリビュート方針はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

その他
-----
- この README はコードコメントと docstring に基づいて要点をまとめたものです。各モジュールの詳細な使用法や拡張方法については該当ファイルの docstring を参照してください。
- 追加の実行スクリプトや運用ツールを導入する場合は、ログ・DB のパスや kill/stop フラグの互換性に注意してください。

必要であれば、この README を Markdown ファイルとして出力したり、起動手順の具体的なコマンド例（systemd / Docker / supervisor での設定例）を追記します。どの形式で欲しいか教えてください。