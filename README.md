README
=====

概要
----
KabuSys は日本株の自動売買・リサーチを支援する Python 製のライブラリ／ミニフレームワークです。  
主な目的は次のとおりです。

- 日次ファクター計算・特徴量生成（DuckDB を用いた分析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実行エンジン（本番／ペーパートレード切替、ブローカー抽象化）
- 監視コンポーネント（システム・注文・リスクの定期チェックとアラート）
- AI 補助（ニュースのセンチメントや市場レジーム判定）  
- 補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

機能一覧
--------
主な機能（抜粋）：

- 環境設定管理（.env 読み込み、Settings クラス）
- 実行スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV により本番／paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 監視（monitoring）
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - trade_monitor: 注文の停滞/約定異常検出（trade_logs）
  - risk_monitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - kill_switch: 条件発生時に data/kill.flag を書き込み ExecutionEngine を停止
  - monitoring_engine: 各 Monitor をまとめて定周期で実行しアラート配信
- ポートフォリオ構築（portfolio）
  - 銘柄選定（スコア順、上位 N 抽出）
  - 重み付け（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース / 等配分 等、単元丸め・集約キャップ）
- 研究・リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を使ったニュースセンチメント評価 → ai_scores へ永続化
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - config_setup.py: .env 対話式ウィザード（初期作成・更新）
  - validate_config.py: .env および config/*.yaml の事前チェック
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成

前提 / 必要パッケージ
-------------------
必須（主要なもの）：
- Python 3.8+（ソースでの型ヒント・標準ライブラリ機能を前提）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config で YAML 検証を行う場合）

簡易インストール例:
    pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があれば pip install -r requirements.txt を推奨）

セットアップ手順
--------------
1. リポジトリを取得してパッケージインストール（オプション）:
    - git clone <repo>
    - cd <repo>
    - pip install -e .   （開発時のローカルインストール）

2. .env ファイルを作成（対話式ウィザード推奨）:
    - python -m kabusys.config_setup
      → 対話形式で設定を作成し .env を保存します。

   手動で作る場合は最低でも以下の必須項目を設定してください：
    - JQUANTS_REFRESH_TOKEN=...
    - KABU_API_PASSWORD=...
   主要なオプション（デフォルトを使用する場合は不要）：
    - KABUSYS_ENV=development|paper_trading|live
    - DUCKDB_PATH=data/kabusys.duckdb
    - SQLITE_PATH=data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    - OPENAI_API_KEY=...  （AI 機能使用時）
    - LOG_LEVEL=INFO

3. 設定の事前検証:
    - python -m kabusys.validate_config
      --strict オプションを付けると警告もエラー扱いになります。

4. ディレクトリの作成:
    - data/ と logs/ は自動作成されますが、権限等で失敗する場合があるので必要に応じて作成しておいてください。

使い方（起動・コマンド）
-----------------------

- 監視ループ起動（SystemMonitor）:
    python -m kabusys.run_monitoring

  補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - run_monitoring は常に production 相当の sqlite_path（Settings.sqlite_path）を使います。
    - 停止にはプロジェクトルート/data/stop_requested.flag ファイルを作成するか、Ctrl+C。

- 実行エンジン起動（ExecutionEngine）:
    python -m kabusys.run_execution

  補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全分離）。
    - 起動時に data/execution.pid が指定されます（Settings.pid_file_path）。
    - 停止は data/stop_requested.flag を作成することで実行中のエンジンへ通知されます。

- 設定ウィザード:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  引数 --db で別の SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照。

環境変数の主な説明
------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの執行モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（1 で有効。production では 0 推奨）

プロセス制御・フラグ
------------------
- 停止リクエスト:
  - プロジェクトルート/data/stop_requested.flag を作成するとループ系スクリプト（run_monitoring/run_execution）が検知して終了または停止処理を行います。
- Kill Switch:
  - 監視ロジックにより条件（ドローダウン・ポジション数等）を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止を促す仕組みがあります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 推奨）。
- PID ファイル:
  - run_execution は data/execution.pid を使用 / 作成します（Settings.pid_file_path）。

ログ
----
- setup_logging により標準出力（stdout）と日次ローテートログ（logs/<app_name>.log）を出力します。
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。

DB（永続化）
-----------
- DuckDB: 分析用（prices_daily, raw_financials, raw_news 等のテーブルを想定）
  - デフォルト: data/kabusys.duckdb
- SQLite: 監視・注文ログなど（monitoring）
  - デフォルト: data/monitoring.db
- ペーパートレード専用 SQLite:
  - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

セキュリティ
-----------
- .env は機密情報を含むため決して Git などにコミットしないでください。
- config_setup により生成された .env ヘッダにも「絶対に Git にコミットしない」旨が記載されています。

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 以下の主要ファイル／モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話型ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

注意事項 / 運用上のヒント
-----------------------
- 本番運用時（KABUSYS_ENV=live）は kill_flag や設定を慎重に扱ってください。validate_config は live 特有の警告を出します。
- run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定しようとします。環境により権限不足で設定に失敗することがあるため、ログで警告が出ます。
- AI（OpenAI）を使う場合は API コストやレート制限に注意してください。news_nlp や regime_detector はリトライ・バックオフロジックを持ちますが、完全ではありません。
- DuckDB / SQLite のファイルパスはデフォルトで data/ に配置されます。バックアップやアクセス制御は運用側で管理してください。

ライセンス／バージョン
--------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリの LICENSE を確認してください（存在する場合）。

お問い合わせ
-----------
不具合報告や改善要望はリポジトリの Issue または開発チームの連絡先へお願いします。

以上。