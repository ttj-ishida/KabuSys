README
======

概要
----
KabuSys は日本株の自動売買システム（ライブラリ兼実行スクリプト群）です。本リポジトリにはトレーディング用エンジン起動スクリプト、監視機能、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI を用いたニュースセンチメント評価などの主要コンポーネントが含まれます。

主な設計方針
- 本番とペーパートレードを環境変数 KABUSYS_ENV により切り替え（development / paper_trading / live）。
- DB は DuckDB（分析用）と SQLite（監視・注文ログ）を使用。
- モジュール群は副作用を極力抑えた純粋関数・明確な I/O インターフェースで実装。
- OpenAI（gpt-4o-mini）を用いたテキスト評価機能を一部実装（APIキー必須、フェイルセーフ設計）。

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番/ペーパーの切替、MockBroker を用いた完全分離ペーパートレード、ExecutionEngine のスレッド実行／停止管理。
- 監視プロセス（run_monitoring.py）
  - システム負荷（CPU/メモリ/ディスク）、Execution プロセスの生存確認、データ鮮度チェック、監視ログ永続化。
  - ポーリング間隔は MONITOR_POLL_INTERVAL で調整可能（デフォルト 60 秒）。
- 監視エンジン / 各種 Monitor（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor）
  - kill.flag による停止シグナル、リスクイベントのログ化、LINE 通知用 AlertManager（push）。
- 監視 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard のテーブルを自動作成・マイグレーション。
- ポートフォリオ構築（portfolio/*）
  - 銘柄選定、重み計算（等金額・スコア重み）、セクター上限適用、ポジションサイズ計算（lot 丸め・aggregate cap）。
- リサーチ（research/*）
  - モメンタム / ボラティリティ / バリューファクター算出、将来リターン・IC 計算、統計サマリー。
- AI モジュール（ai/*）
  - ニュースを LLM（OpenAI）で評価して ai_scores に保存する news_nlp.score_news
  - マクロセンチメント＋ETF MA による市場レジーム判定 score_regime（regime_detector）
- ユーティリティ
  - 設定ウィザード (.env 作成支援: config_setup.py)
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

必要な外部ライブラリ（主要）
- python3.8+
- duckdb
- psutil
- requests
- openai
- PyYAML（config 検証を行う場合）
- sqlite3 は標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - ルートに src/ ディレクトリが配置されていることを想定

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai PyYAML
   - （requirements.txt があれば）pip install -r requirements.txt

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - そのほかの設定はウィザードで入力またはデフォルト利用可

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合: python -m kabusys.validate_config --strict

環境変数（主要・デフォルト）
----------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- ログ・プロセス
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効, デフォルト: "0"）
- 監視ループ
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- Paper Trading 振る舞い
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

使い方（代表的コマンド）
-----------------------

- 設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（SQLITE_PATH）を使用（KABUSYS_ENV にかかわらず本番 sqlite_path を参照します）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に書き込む（本番 DB と分離）
  - 起動中の停止は data/stop_requested.flag（プロジェクトルートの data 配下）を作成することで検知・停止されます
  - Kill Switch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - オプション --db でパスを指定可能

- AI / リサーチ機能（ライブラリ利用）
  - news_nlp.score_news(conn, target_date, api_key=...)
    - DuckDB 接続（duckdb.connect(...).cursor()／DuckDBPyConnection）を渡して使用
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic などは DuckDB 接続を渡して利用

注意点・運用メモ
----------------
- データファイル（data 配下）
  - data/kabusys.duckdb (DUCKDB_PATH)
  - data/monitoring.db (SQLITE_PATH)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - data/execution.pid（ExecutionEngine PID 保存）
  - data/kill.flag（Kill Switch フラグ）
  - data/stop_requested.flag（run_* スクリプトの停止フラグ）
- run_monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（監視用 DB）を使用します。ペーパートレード用 DB は run_execution 側で使い分けられます。
- monitoring_db.init_monitoring_db は冪等でテーブル作成および簡単なマイグレーション（列追加）を行います。既存 DB に対して安全に呼べます。
- OpenAI 呼び出しを伴う機能は API のレート制限・エラーに対してリトライやフォールバック動作を組み込んでいますが、APIキーの設定とコスト管理には注意してください。
- LINE 通知を有効にするには LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定してください。設定が空の場合は通知送信はスキップされ、ログに警告が出ます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings 管理
- config_setup.py                  — .env 対話式ウィザード
- validate_config.py               — 起動前設定検証 CLI
- run_monitoring.py                — 監視プロセス起動スクリプト
- run_execution.py                 — 実行エンジン起動スクリプト
- tools/
  - paper_verification_report.py    — ペーパートレード検証レポート生成
- ai/
  - news_nlp.py                     — ニュースセンチメント付与（OpenAI）
  - regime_detector.py              — 市場レジーム判定（OpenAI + MA）
- monitoring/
  - monitoring_db.py                — 監視 DB 層（SQLite）
  - monitoring_engine.py            — 各 Monitor を束ねる
  - system_monitor.py               — システム／データ鮮度監視
  - trade_monitor.py                — 注文滞留・約定異常監視
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - kill_switch.py                  — kill.flag 管理
  - alert_manager.py                — LINE 通知
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/ (上記)
- utils/
  - process_priority.py             — プロセス優先度、CPU affinity 設定ユーティリティ
- other modules for execution/データ/strategy 等（ExecutionEngine や BrokerFactory 等は別ファイル群に実装）

開発者向け補足
--------------
- テスト実行・単体関数利用は DuckDB のモック接続や sqlite3 の一時ファイルを利用して行うと安全です。
- OpenAI 呼び出し部分はテストしやすいように wrapper／内部呼び出し関数を切り出してあり、ユニットテスト時は patch による差し替えを想定しています（news_nlp._call_openai_api, regime_detector._call_openai_api 等）。
- process_priority.set_process_priority は OS による差分を吸収しますが、権限不足で設定できない場合は警告を出してスキップします。

お問い合わせ / 追加情報
-----------------------
- README に記載のない個別の実装詳細（ExecutionEngine、BrokerClientFactory、OrderRepository 等）は該当ソースファイルの docstring / コメントを参照してください。
- セキュリティ上の注意：.env は機密情報を含むため Git 等へコミットしないでください（config_setup は .env を生成する際に注意書きを出します）。

以上。必要であれば README に追記したい項目（CI/デプロイ手順、example .env.example、より詳細な運用マニュアルなど）を指定してください。