README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のモジュール群です。  
本リポジトリには、実際の注文実行エンジン（ExecutionEngine）、監視機構（Monitoring）、ファクター計算やポートフォリオ構築、ニュースNLP を用いた AI スコアリングなど、取引・運用に必要な主要コンポーネントが含まれます。

主な設計方針
- モジュールは可能な限り副作用を避け、純粋関数としテストしやすく設計。
- 本番環境/ペーパートレードは環境変数で切替可能（DB は分離）。
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB に利用。
- OpenAI を利用した NLP 機能はフェイルセーフで、API 失敗時は局所的にフォールバック。

機能一覧
--------
- Execution
  - ExecutionEngine 起動用スクリプト（run_execution.py）
  - ブローカークライアント抽象化（paper_trading 時は MockBroker を利用）
  - OrderManager / RiskManager / Reconciler 等の発注・リスク制御コンポーネント
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン（run_monitoring.py）
  - SQLite ベースの監視ログ永続化（monitoring_db）
  - Kill Switch（リスクトリガーで data/kill.flag を書込み Execution を停止）
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制約やレジーム乗数（portfolio パッケージ）
- Research
  - DuckDB 上で動くファクター計算（momentum, volatility, value など）
  - 将来リターン計算、IC 計算、特徴量サマリー
- AI
  - ニュース記事のセンチメント算出（OpenAI を用いた news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- 開発支援
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - 統一ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ

セットアップ手順
----------------

前提
- Python 3.9+（コードは型ヒントや pathlib, typing の新機能を使用）
- SQLite（Python 標準ライブラリに含む）
- DuckDB（pip インストール）
- OpenAI SDK（AI 機能を使う場合）
- psutil（プロセス優先度・CPU情報取得）
- PyYAML（検証時に config/*.yaml を検証したい場合）

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install PyYAML

3. プロジェクトルートに移動（README と同じ階層に .env を置く想定）

4. .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict オプションで警告も失敗扱いにできます

環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- その他: PAPER_FILL_MODE（paper_trading の注文約定モード）等

使い方
------

一般的なワークフロー例

1) .env を作成・検証
- python -m kabusys.config_setup
- python -m kabusys.validate_config

2) 監視プロセス起動（Monitoring）
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
- python -m kabusys.run_monitoring
- 注意: 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
- 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。

3) 実行エンジン起動（Execution）
- 実行は環境により挙動が変わります:
  - KABUSYS_ENV=paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
  - KABUSYS_ENV=live: 実口座での発注が行われます（十分に注意してください）
- python -m kabusys.run_execution
- 起動時に project_root/data/execution.pid へ PID を書く等の処理あり。停止は project_root/data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）経由で実行エンジンに停止シグナルを送ります。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で別パスの SQLite を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

5) AI 機能（ニュース NLP / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - conn: duckdb connection
  - target_date: date オブジェクト（ルックアヘッドバイアスを防ぐため内部で date.today() を参照しない）
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に DuckDB を受け取り market_regime テーブルへ書き込みます

注意点（運用）
- ログ: kabusys.utils.logging_setup.setup_logging を各スクリプト冒頭で呼んでいるため、logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリは環境変数 LOG_DIR で変更可能。
- Kill Switch: RiskMonitor がトリガー条件を満たすと data/kill.flag を書き込み、ExecutionEngine はこれを検出して安全に停止します。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされる設定になります（本番では 0 推奨）。
- ペーパートレード: paper_trading モードでは発注処理とログが本番 DB から分離されます（PAPER_TRADING_SQLITE_PATH を利用）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証ツール
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（OpenAI+MA200）
- monitoring/
  - monitoring_db.py       — SQLite による監視ログ永続化
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 管理
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - (その他: alert_manager, trade_monitor 等を想定)
- execution/
  - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
  - broker_factory.py      — ブローカークライアント生成
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

data/（実行時に使用）
- data/monitoring.db       — デフォルト監視 SQLite（Settings.sqlite_path）
- data/paper_trading.db    — paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）
- data/kill.flag           — Kill Switch フラグ（作成で Execution 停止）
- data/stop_requested.flag — 起動スクリプトを外部から終了させるためのフラグファイル
- data/execution.pid       — 実行エンジンの PID ファイル

補足／開発者向けメモ
-------------------
- DuckDB 接続は分析処理（research / ai）で多用します。接続は kabusys.config.Settings.duckdb_path を参照して作成してください。
- 設定ファイルの自動ロードは .env, .env.local をプロジェクトルートから読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Logging は各スクリプトで setup_logging(app_name="...") を呼んでください。既存ハンドラをクリアして再設定する仕様です。
- テストや CI では .env を差し替え、KABUSYS_ENV=development で実行することを推奨します。AI に関するテストは OpenAI のコールをモックする設計（内部の API 呼び出し関数をパッチ可能）です。

ライセンス / 貢献
-----------------
（必要に応じてライセンス情報や貢献方法をここに記載してください）

お問い合わせ
------------
実装に関する質問や追加ドキュメントが必要であれば、どの機能について詳しく知りたいかを教えてください。README の補足や例を追加します。