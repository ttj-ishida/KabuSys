README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 実行エンジン起動スクリプト（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch（停止シグナル）
- DuckDB を使ったリサーチ（ファクター計算・特徴量解析）
- OpenAI を使ったニュース NLP（センチメント評価 / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード等）
- 各種ツールスクリプト（例: ペーパートレード検証レポート）

主な特徴
--------
- モジュール化された純関数的なポートフォリオ構築ロジック（DB参照なし）
- DuckDB を用いた分析・ファクター計算（prices_daily / raw_financials 前提）
- 実行エンジンは環境に応じて MockBroker を利用可能（paper_trading で分離）
- 監視機能は SQLite に永続化し、Kill Switch による安全停止が可能
- OpenAI（gpt-4o-mini など）との統合でニュースセンチメントや市場レジームを評価
- ログは stdout と日次ローテートファイルへ出力（logs/<app>.log）

依存関係（代表）
----------------
必要最低限のパッケージ例（実際の requirements.txt に従ってください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証を行う場合）

インストール（例）
-----------------
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

環境設定（.env）
----------------
- .env / .env.local を使って環境変数を設定します。
- 用意された対話式ウィザードで .env を生成・更新できます。

実行例:
- python -m kabusys.config_setup
  - 対話形式で .env を生成します（既存 .env の読み込み・再利用可）。
- python -m kabusys.validate_config
  - .env と config/*.yaml の基本的な検証を行います。
  - --strict を付けると警告がある場合も exit(1) になります。

主要な環境変数（代表）
---------------------
（.env.example 相当のキー）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
  - paper_trading: MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル保存先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用）

セットアップ手順（推奨）
---------------------
1. リポジトリをクローンして仮想環境を作成・有効化。
2. 依存パッケージをインストール（duckdb, psutil, openai, pyyaml 等）。
3. python -m kabusys.config_setup で .env を作成。
4. python -m kabusys.validate_config で設定を検証。
5. data/ ディレクトリや logs/ は自動作成されますが、権限等を確認してください。

実行方法
--------
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了する。
    - 実行中は data/execution.pid に PID を書きます（_EXECUTION_PID）。
    - 停止シグナルは data/stop_requested.flag を作成するか、監視側の kill.flag（data/kill.flag）で止めます。

- 監視ループ（SystemMonitor）起動:
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使用（環境に依らず）。
    - run_monitoring は data/stop_requested.flag を見ることでループ終了します。

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

AI（OpenAI）機能
----------------
- news_nlp.score_news / ai.regime_detector.score_regime などの関数は OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または引数で渡す）。
- OpenAI 呼び出しはリトライや入力クリーニング等のフォールトトレラント実装になっていますが、API 利用量やレート制限に注意してください。

監視 / Kill Switch の仕組み
---------------------------
- 監視系は MonitoringDB（SQLite）へログを永続化します（system_status, trade_logs, positions, risk_logs, dashboard）。
- RiskMonitor はドローダウン / ポジション上限を監視し、必要に応じて risk_logs に記録および KillSwitch をトリガーします。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を促します（ExecutionEngine は起動時・ループ中にこのフラグの存在を参照して停止します）。
- 手動停止用のファイル: data/stop_requested.flag（run_* スクリプトが終了を検知するためのフラグ）

ログ
----
- ログは stdout とファイルの両方へ出力されます（logs/<app_name>.log を日次ローテート、デフォルト 30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要なファイルと担当概略です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・自動 .env ロード・Settings クラス
  - config_setup.py
    - .env 生成 / 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/  (実行関連コンポーネント、OrderManager 等)
  - monitoring/
    - monitoring_db.py      : SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py     : CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py      : 注文ログ監視（stale / anomaly 検出）
    - risk_monitor.py       : ドローダウン・ポジション上限監視
    - kill_switch.py        : kill.flag 書き込みロジック
    - monitoring_engine.py  : 各 Monitor を束ねるループ
    - alert_manager.py      : アラート送信（LINE 等、実装に依存）
  - portfolio/
    - portfolio_builder.py  : 候補選定・重み計算
    - position_sizing.py    : 株数算出・資金制約処理
    - risk_adjustment.py    : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    : モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py: 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py           : ニュースセンチメント評価（OpenAI 呼び出し）
    - regime_detector.py    : 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポート出力
  - utils/
    - logging_setup.py      : ログ設定ユーティリティ
    - process_priority.py   : プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のポイント
---------------------------
- 本番運用（KABUSYS_ENV=live）では LINE 通知や kill flag の挙動を入念に確認してください。.env のプレースホルダが残っていると警告・エラーになります。
- paper_trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能は API コストとレート制限に注意して運用してください。
- ログディレクトリや data/ 配下のファイルは適切なバックアップ・パーミッションを確保してください。
- DuckDB / SQLite ファイルは同一マシン上のファイルロック挙動に注意（複数プロセスの並列書き込みなど）。

よく使うコマンド集
-----------------
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

最後に
------
この README はコードベースの主要要素と実行手順を端的にまとめたものです。詳細な設計・仕様（PortfolioConstruction.md、StrategyModel.md など）が別途ある想定です。運用前には必ず validate_config で設定を確認し、ローカルでの動作確認を行ってください。質問や追加ドキュメント化が必要であればお知らせください。