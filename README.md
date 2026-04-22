KabuSys — 日本株自動売買システム
================================

本ドキュメントは、このリポジトリ（Python パッケージ kabusys）の概要、主要機能、セットアップ手順、使い方、およびディレクトリ構成を説明します。

注意
----
- .env は機密情報（API トークン等）を含むため、決して Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）での運用には十分な検証と注意を払ってください。validate_config や各種ガードが用意されていますが、最終的な責任は運用者にあります。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
主な目的は以下の通りです。

- データ基盤（DuckDB / SQLite）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine による発注・リスク制御（paper_trading 用のモック可能）
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる停止）
- AI（OpenAI）を使ったニュース NLP、レジーム判定の統合
- ペーパートレード検証レポート生成ツール

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup.run_wizard）
  - .env の対話式生成・更新
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の検証（--strict オプションあり）
- Execution 起動スクリプト（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading 時に MockBroker を使用し data/paper_trading.db に記録
  - PID ファイル管理 / stop flag の監視
- Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor を定期ポーリング（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可）
  - 監視ログは SQLite（monitoring.db）に永続化（monitoring_db モジュール）
- モニタリングエンジン（MonitoringEngine）
  - System / Trade / Risk 各 Monitor を束ね、アラート・Kill Switch 評価を実行
- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - ペーパートレード結果に対する各種指標の算出と PASS/FAIL 判定
- AI モジュール
  - news_nlp: raw_news を OpenAI でセンチメント化し ai_scores に保存
  - regime_detector: MA200 とマクロニュースで市場レジーム判定
- リサーチ（kabusys.research）
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算など
- ポートフォリオ（kabusys.portfolio）
  - 候補選定、等重・スコア加重、セクター制限、ポジションサイズ計算
- ユーティリティ
  - logging_setup: 統一ロギング（stdout + 日次ローテーションファイル）
  - process_priority: 優先度・CPU affinity 設定

必須環境変数（主要）
--------------------
最低限設定が必要なキー（validate_config でもチェックされます）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — AI 機能を使う場合（news_nlp / regime_detector）

その他よく使う環境変数（デフォルトあり）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: INFO（または DEBUG 等）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、監視スクリプト用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（Settings 参照）

セットアップ手順
----------------

1. Python と依存パッケージのインストール（例）

   - Python 3.9+ を想定
   - 必要なパッケージ（一例）:
     pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそちらを使用してください）

2. プロジェクトルートに移動し、.env を作成

   - 対話式ウィザードを使う:
     python -m kabusys.config_setup

   - もしくは .env.example を参考に手動で .env を作成
   - 注意: .env は機密情報を含むため Git にコミットしないでください

3. 設定検証（任意だが推奨）

   - 通常モード:
     python -m kabusys.validate_config
   - 厳格モード（警告もエラー扱い）:
     python -m kabusys.validate_config --strict

4. データベース準備

   - DuckDB / SQLite のデフォルトファイルパスは .env もしくは Settings のデフォルトを参照します
   - 初回起動スクリプトが必要なテーブルを自動作成します（init_monitoring_db 等）

使い方（主要スクリプト）
-----------------------

- 環境設定ウィザード
  python -m kabusys.config_setup
  - .env を対話式に作成・更新します

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  python -m kabusys.run_execution
  動作ポイント:
  - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 起動中に data/stop_requested.flag が作成されると安全に停止します
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring を起動
  python -m kabusys.run_monitoring
  動作ポイント:
  - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します
  - stop フラグファイル（data/stop_requested.flag）を検知するとループ終了

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / LLM 関連
--------------
- news_nlp と regime_detector は OpenAI API（gpt-4o-mini 等）を使用します。API キーは OPENAI_API_KEY で指定してください。
- AI 機能の実行は API 呼び出しや料金が発生するため、必ずキーの管理と利用制限に注意してください。
- 失敗時は多くの処理がフォールバック（0.0 等）やスキップとなるよう設計されていますが、運用時のログ確認を推奨します。

ロギング
--------
- ログは stdout に出力され、かつデフォルトでは logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- ログレベルは LOG_LEVEL 環境変数で制御できます。カスタムログディレクトリは LOG_DIR 環境変数で指定できます。
- setup_logging(app_name="execution") のように各スクリプトで統一して呼び出されます。

プロセス優先度
--------------
- run_execution/run_monitoring は起動時に set_process_priority("high") を呼び出します（psutil による優先度設定）。
- 標準出力に警告が出ることがあります（権限不足など）。

Kill Switch / 停止フラグ
-----------------------
- Kill Switch: data/kill.flag に理由を書き込むことで ExecutionEngine に停止を促します（KillSwitch クラス）。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_execution および run_monitoring は起動/ループを停止します。
- Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み・デフォルト）
    - 自動 .env ロード（.env / .env.local）
  - config_setup.py
    - .env 対話式作成ウィザード
  - validate_config.py
    - 起動前検証 CLI（--strict）
  - run_execution.py
    - ExecutionEngine 起動ラッパー（PID 管理・stop flag）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 監視テーブル初期化と DB ラッパー（MonitoringDB）
    - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / プロセス監視
    - trade_monitor.py — （trade 関連監視、ソース参照）
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - monitoring_engine.py — モニタリング統合エンジン
    - kill_switch.py — フラグファイル操作
    - alert_manager.py — （LINE 等へ通知する抽象化）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - Execution のコアロジック（発注・リスク制御・再整合）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント（ai_scores への書込み）
    - regime_detector.py — MA200 とニュースで日次レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — 優先度 / CPU affinity ユーティリティ

テスト / 開発時のヒント
----------------------
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（ユニットテスト等）。
- DuckDB 接続はモジュール内で受け渡しをする設計です。ローカルで DuckDB ファイルを用意してリサーチ関数を実行できます。
- AI 呼び出しは _call_openai_api などをモックすることでテスト可能です（コード内にその旨のコメントあり）。
- monitoring_db.init_monitoring_db は冪等でマイグレーション処理（カラム追加）も行います。

よくある運用コマンドまとめ
-------------------------
- .env を作る:
  python -m kabusys.config_setup

- 設定チェック:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または DB を指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（ない場合は運用チーム内ルールに従ってください）。
- バグ修正・機能追加の提案は Issue/PR で行ってください。

付録: 参考（主な環境変数の一覧）
---------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- LOG_LEVEL (INFO 等)
- LOG_DIR (logs/)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒)

以上。運用・開発時の具体的な振る舞いや詳細実装は各モジュール（src/kabusys 以下）の docstring とコードコメントを参照してください。必要であれば README のサンプル .env テンプレートやデプロイ手順の追加も作成します。必要なら教えてください。