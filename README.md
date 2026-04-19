KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のスケルトン実装です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注／注文管理／リスク管理の実行ループ
- 監視（Monitoring）: システム状態・注文状況・リスクの定期チェックと Kill Switch
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、株数決定などの純関数群
- リサーチ（Research）: ファクター計算、将来リターン、IC 計算など
- AI モジュール（AI）: ニュース NLP（OpenAI）によるセンチメント評価、レジーム判定
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定 等
- ツール: ペーパートレードの検証レポート生成スクリプト 等

特徴
----
- 設定は .env / 環境変数ベースで管理（自動読み込み機構を搭載）
- Paper Trading と Live 環境を DB レベルで分離（paper_trading 専用 SQLite）
- DuckDB を分析用途に使用、SQLite を監視・発注ログ用に使用
- OpenAI（gpt-4o-mini 等）連携でニュースセンチメントやレジーム判定を実行可能
- ロギングはコンソール＋日次ローテートファイルを統一的に設定
- Kill Switch により異常時に ExecutionEngine を安全に停止可能

必要条件（例）
--------------
（実プロジェクトでは requirements.txt を用意してください。ここはコード依存から推測した例です）
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（設定検証で任意）
- （標準ライブラリ: sqlite3, logging 等）

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - ルートに src/ があり、パッケージは pakage 名 kabusys として配置されています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（下記に代表的な環境変数の一覧を示します）。

環境変数（代表）
----------------
※ Settings クラス / config_setup.py / validate_config.py に記載されたキーを参照しています。

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

その他（デフォルトあり / 任意）
- KABUSYS_ENV — 実行環境: development | paper_trading | live  （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- LOG_DIR — ログを出力するディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI を使用する機能（news_nlp / regime_detector）の API キー
- PAPER_FILL_MODE — paper_trading における約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env 自動読み込み
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、
  OS 環境変数 > .env.local > .env の順で環境変数を読み込みます。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

クイック使い方
--------------

1. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告でも exit 1 になります。

2. 起動前ウィザード（.env 作成）
   - python -m kabusys.config_setup

3. 実行エンジン（ExecutionEngine）を起動
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は paper_trading.db に記録されます（本番 DB と分離）。
     - 実行中、data/stop_requested.flag が存在するとエンジンは安全に停止します。
     - 実行中は data/execution.pid に PID を書き込みます。

4. 監視ループを起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
   - 監視は Settings.sqlite_path（monitoring.db）へ永続化します。Monitoring は環境にかかわらず本番 sqlite_path を使用します。
   - 監視プロセスは停止フラグ data/stop_requested.flag を検知すると終了します。

5. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプションで期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB は --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定

6. AI 機能（ニューススコアリング / レジーム判定）
   - プログラム的に使用:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=...)
   - OPENAI_API_KEY が必要です（関数は api_key 引数でも受け取れます）。
   - API 呼び出しはリトライやバリデーションを備えていますが、API キー未設定時はエラーになります。

ファイル／フラグの取り扱い
--------------------------
- data/kill.flag — KillSwitch が発動した際に作成されるフラグ。ExecutionEngine 側はこのフラグの存在で停止します。
- data/stop_requested.flag — ローカルで監視・実行ループを停止させたい場合に使用。run_* スクリプトはこのファイルを監視して安全に停止します。
- data/execution.pid — run_execution が PID を書き込むファイル
- logs/ — ログファイルを出力（<app_name>.log、日次ローテーション）

注意点 / 運用上のポイント
------------------------
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。Paper トレード中に本番 DB を汚す心配はありません。
- validate_config は .env と config/*.yaml（存在すれば）を検証します。PyYAML が無い場合 YAML 検証はスキップされます。
- OpenAI を利用する機能は API レートやコストに注意してください。失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計ですが、運用ポリシーを検討してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみでログ出力されます。

ディレクトリ構成（主要）
----------------------
以下は src/kabusys 以下の主要モジュール構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py        — 監視 DB 永続化層（SQLite）
      - system_monitor.py       — システム監視
      - trade_monitor.py        — （trade 監視ロジック）※本ツリーに実装あり
      - risk_monitor.py         — ドローダウン / ポジション監視
      - kill_switch.py          — Kill Switch 制御
      - monitoring_engine.py    — モニタリングを束ねるエンジン
      - alert_manager.py        — （LINE などへの通知管理）※実装参照
    - execution/
      - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py             — ニュース NLP スコアリング
      - regime_detector.py      — 市場レジーム判定
    - tools/
      - paper_verification_report.py

（実際のリポジトリではさらにファイルやサブモジュールが含まれる場合があります）

開発者向けメモ
---------------
- DB マイグレーション: monitoring_db.init_monitoring_db はテーブル作成と簡単なカラム追加（マイグレーション）を行います。初回起動時に呼び出してください（run_* スクリプトが自動で呼び出しています）。
- ロギング: setup_logging(app_name=...) を各起動スクリプトの最初で呼び出して統一したログ出力にしてください。
- テスト: AI API 呼び出しや外部依存はモック（patch）してテスト可能なように設計されています（_call_openai_api など）。
- 自動読み込みの挙動確認: .env の自動読み込みは Settings モジュールがインポートされる際に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

サンプル .env（最低限の例）
--------------------------
例（省略形。実運用ではトークン等を正しく設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

最後に
-------
この README はコードベースの現状から主要部分を抜粋してまとめたものです。実際の運用前には必ず python -m kabusys.validate_config を実行して設定をチェックし、.env の内容や API キー/DB パスを確認してください。質問や補足の要望があれば実装箇所を指定して教えてください。