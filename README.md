README
=====

プロジェクト概要
-------------
KabuSys は日本株自動売買システムのコードベースです。戦略（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行、監視・アラート、AI を使ったニュースセン評点などを含むモジュール群で構成されています。開発・ペーパートレード・本番（live）を切り替えて動作させられる設計です。

主な設計方針
- DuckDB / SQLite を使用したデータ管理（分析用 / 監視用）。
- 環境変数（.env / .env.local）による設定管理。自動ロード機能あり（無効化可能）。
- ペーパートレード時は MockBroker を用いて本番 DB と完全分離。
- OpenAI を用いた NLP（ニュースセンチメント）やレジーム判定をサポート（API キー必須）。
- ロギングは統一された setup_logging を通して stdout と日次ローテートファイルへ出力。

機能一覧
--------
- 設定管理
  - .env を自動読み込み / 対話式ウィザード（config_setup.py）
  - 起動前の設定検証ツール（validate_config.py）
- 実行エンジン（Execution）
  - Broker クライアント（実口座 / Mock）
  - Order 管理、リスク管理、照合（Reconciler）
  - ペーパートレード専用 DB 分離
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor, RiskMonitor, MonitoringEngine（ポーリング）
  - Kill Switch: 条件により Execution を停止するフラグ操作
  - 永続化層（monitoring_db.py）: system_status/trade_logs/positions/risk_logs/dashboard
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、ポジションサイズ決定（単元株丸め 等）
  - セクター上限適用、レジーム乗数計算
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP による銘柄別センチメント（OpenAI）
  - マクロニュース + ETF MA200 乖離を合成した市場レジーム判定（OpenAI）
- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・成功率・レイテンシ等の検証レポート生成

セットアップ手順
----------------
1. Python と依存パッケージ
   - 本プロジェクトは Python 3.10+ を想定しています（typing の記法など）。
   - 主な依存ライブラリ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config YAML 検証を行う場合、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

2. 環境変数 / .env
   - プロジェクトルートに .env を置くことで自動ロードされます（.env.local で上書き可）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 対話式ウィザードで初期 .env を作成:
     - python -m kabusys.config_setup
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
   - 重要な環境変数（デフォルト含む）:
     - KABUSYS_ENV: development | paper_trading | live （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: ペーパートレードの約定モード (instant|partial|never|reject)

3. ディレクトリ作成
   - data/ および logs/ は自動作成されますが、権限やディスク容量に注意してください。

4. DB の初期化
   - 実行スクリプト run_monitoring/run_execution が起動時に monitoring DB（SQLite）や DuckDB 接続を初期化します。monitoring 用のテーブルは init_monitoring_db() により自動作成・マイグレーションされます。

使い方
------
基本的な CLI 実行例（プロジェクトルートで実行）:

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も致命扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）
  - 開発/本番/ペーパートレードは KABUSYS_ENV に依存
  - 起動:
    - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
    - 起動時に data/stop_requested.flag があると起動を中止します。
    - 実行中に停止させるには data/stop_requested.flag を作成するか、Execution 側に設定された Kill Switch（kill.flag）を使います。

- 監視（SystemMonitor を含む監視ループ）
  - 起動:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は monitoring 用の SQLite（Settings.sqlite_path）を用い、環境に依らず本番 sqlite_path を参照します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db。別 DB を指定するには --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数。

- AI 機能
  - OpenAI の API キーが必要（OPENAI_API_KEY または引数で指定）。
  - ニューススコアやレジーム判定はモジュール関数を直接呼び出せます（例: kabusys.ai.score_news）。
  - 例（スクリプトや REPL から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

停止・Kill Switch
- KillSwitch はリスク条件（ドローダウン・ポジション上限等）により data/kill.flag を書き込みます。ExecutionEngine は Kill Switch の存在を検知して停止する設計です。
- 手動で停止ループ（run_* スクリプト）を止めたい場合は data/stop_requested.flag を作成してください。ループはこのフラグ検出で安全に終了します。

ロギング
- 共通の logging 設定は kabusys.utils.logging_setup.setup_logging() を経由して行われます。
- デフォルトのログ出力先:
  - コンソール stdout
  - ファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- LOG_DIR 環境変数でログディレクトリを変更できます。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋、プロジェクトルート直下に src/ を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング開始スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロ記事）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化 API
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — （取引監視: 滞留注文等）※詳細はコード参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成/削除ロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知送信ロジック）※詳細はコード参照
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - broker_factory.py      — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 注意事項
--------------
- .env は機密情報を含むため決して Git にコミットしないでください（config_setup も注意書きを出します）。
- KABUSYS_ENV=live のときは設定を十分に確認してください（validate_config による注意喚起あり）。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です。
- OpenAI を利用するモジュールは API レートやレスポンスの不安定さに備えてリトライやフェイルセーフ（失敗時スコアを 0 とみなす等）の実装が入っていますが、API キーの管理やコストには注意してください。
- run_execution / run_monitoring はデーモン的に実行することを想定しています（systemd / Supervisor / cron 等で管理することを推奨）。

必要であれば、各モジュール（ExecutionEngine の起動手順、監視ルールのカスタマイズ、AI モジュールのテスト用モック例など）について別ドキュメントを作成します。ご希望があれば対象を指定してください。