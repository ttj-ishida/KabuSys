KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージ群です。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）とそれに付随するリスク管理・オーダー管理
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制約）
- リサーチ機能（ファクター計算、将来リターン、IC 計算など）
- AI（OpenAI）を用いたニュース NLP（記事センチメント）および市場レジーム判定
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- ペーパートレード用検証レポート生成ツール

主な設計方針
- DuckDB / SQLite を用いたローカル DB ベースの処理（本番とペーパートレードは分離可能）
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを渡すか環境変数で制御
- ルックアヘッドバイアス回避（多くのモジュールで date.today() 等を直接参照しない）
- フェイルセーフ：API 失敗やデータ不足時は例外を抑え安全側に振る舞う設計

機能一覧
--------
- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper/live/development を切替）
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定管理 / 検証
  - python -m kabusys.config_setup: 対話式 .env 作成ウィザード
  - python -m kabusys.validate_config: .env と config/*.yaml の検証 CLI
- 監視 / Kill Switch
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch による data/kill.flag の作成で ExecutionEngine を停止可能
- ポートフォリオ構築
  - 候補選定 (select_candidates)、等配分/スコア配分 (calc_equal_weights / calc_score_weights)
  - ポジションサイズ決定 (calc_position_sizes)、セクターキャップ適用 (apply_sector_cap)
- リサーチ
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア化（kabusys.ai.score_news）
  - マクロ記事 + ETF MA を用いた市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

前提 / 推奨環境
--------------
- Python 3.9+（型注釈・ typing を多用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を行う場合）
- ローカル用 DB ファイルとログディレクトリ（default: data/, logs/）

セットアップ手順
----------------

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例（最小）:
     - pip install duckdb psutil
   - AI 機能を使う場合:
     - pip install openai
   - validate_config の YAML 検証を有効にする場合:
     - pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

3. .env を用意する
   - 自動ロード: プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 対話式ウィザードで作る:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要変数の例:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）

4. 設定検証（起動前に必ず）
   - python -m kabusys.validate_config
   - --strict を付けると警告も fail 扱いになります

基本的な使い方
------------

- ExecutionEngine を起動
  - 本番・ペーパートレードは KABUSYS_ENV で切替:
    - python -m kabusys.run_execution
  - paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に書き込みます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き（秒、デフォルト: 60）
  - 監視は常に本番 sqlite_path（設定に依らず monitoring 用 DB）を使用します

- Kill / Stop 制御
  - ExecutionEngine 停止のためのフラグ:
    - Kill Switch: data/kill.flag を書くと ExecutionEngine が停止される（ファイル存在で判定）
    - 停止要求: data/stop_requested.flag（run scripts が監視している停止フラグ）
  - Execution 起動時に kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（注意: 本番では推奨しない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- AI（OpenAI）機能
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します（未設定だと例外）
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログと監査
----------
- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一して設定されます。
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30世代保存）
  - コンソールは stdout に出力
- 各起動スクリプトは最初に set_process_priority("high") を呼び出します（psutil が必要、権限によってはスキップされます）

重要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
  - SQLITE_PATH: data/monitoring.db (デフォルト)
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - OPENAI_API_KEY: OpenAI を使用する場合
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動削除（注意）

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内の主要モジュールと概略です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス（自動 .env ロードロジック含む）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
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
    - news_nlp.py             — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py      — マクロ + ETF MA でレジーム判定（OpenAI）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 + ラッパー
    - system_monitor.py
    - trade_monitor.py        — （TradeMonitor 実装は本リストの他ファイルに存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        —（アラート送信機能の抽象化）
  - execution/                — ExecutionEngine・OrderManager 等（発注ロジック）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

運用時の注意事項 / ベストプラクティス
-----------------------------------
- 本番(KABUSYS_ENV=live) では .env の内容を厳密に管理し、LINE 等の通知設定を必ず確認してください。
- kill.flag / stop_requested.flag の扱いに注意（特に KILL_FLAG_CLEAR_ON_START の設定）。
- OpenAI を使用する処理はコストが発生するためバッチサイズやリトライ設定を確認してください。
- データベースファイル（data/*.db）はバックアップを推奨します。ペーパートレード用 DB は本番 DB とは分離されています。
- validate_config で起動前に設定を検証する習慣を付けてください（--strict オプション推奨）。

貢献・拡張
-----------
- 新しい戦略を追加する場合は research / portfolio 周りの純関数を活用してください（DB を直接書き換えない設計）。
- AI 呼び出しのテストは _call_openai_api をパッチしてモック化することで容易になります（モジュール内にその旨のフックがあります）。
- YAML ベースの config ファイルを追加した場合は validate_config の _CONFIG_FILES に追加して検証を行ってください。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

最後に
------
この README はリポジトリ内の主要モジュールから抽出した説明です。詳細な使用法は各モジュールの docstring や関数コメントを参照してください。追加で「起動例」「.env のサンプル」「デプロイ手順」「単体テストの書き方」などを README に追記したい場合は要件を教えてください。