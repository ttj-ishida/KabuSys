README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤向けのモジュール群です。  
主な責務は次の通りです。

- データパイプライン／リサーチ（DuckDB を用いたファクター計算）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 実行エンジン（ExecutionEngine）およびペーパートレードの分離運用
- 監視（System / Trade / Risk のモニタリング、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント評価・レジーム判定）
- 運用ユーティリティ（設定ウィザード、設定検証、検証レポート生成など）

主な設計方針：
- 本番 DB（monitoring.db）とペーパートレード DB を明確に分離
- 環境変数 / .env による設定管理（自動読み込み機能有り）
- OpenAI を用いた NLP 部分はキー必須。失敗時はフォールバックで安全に動作

機能一覧
--------
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config, --strict オプション有り）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - プロセス優先度を高く設定、PID ファイル管理、停止フラグ検知
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
  - 停止フラグ (data/stop_requested.flag) を検知して安全終了
- 監視サブシステム
  - system_monitor: CPU/メモリ/Disk、データ鮮度、実行プロセス監視
  - trade_monitor: 注文滞留や約定異常検出（trade_logs）
  - risk_monitor: ドローダウン・ポジション上限の監視、KillSwitch 連携
  - monitoring_db: 監視用 SQLite スキーマの初期化と CRUD
  - monitoring_engine: 各 Monitor を束ねてポーリング・アラート発行
- ポートフォリオ構築ライブラリ
  - 候補選定 / 等重・スコア重み計算 / セクター上限適用 / レジーム乗数 / ポジションサイズ計算
- リサーチ（DuckDB）
  - momentum / volatility / value などのファクター計算
  - forward return / IC / 統計要約など
- AI モジュール
  - news_nlp: OpenAI（gpt-4o-mini）でニュースをスコア化し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して market_regime に記録
- ユーティリティ
  - tools/paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（型アノテーションに | が使用されているため）
- SQLite は標準ライブラリで利用
- 推奨パッケージ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML をパースする場合に必要）
  - （必要に応じて）その他依存パッケージ

例（venv を使う場合）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式で作る: python -m kabusys.config_setup
   - 手動で作る: リポジトリルートに .env を置く（.env は絶対にコミットしないこと）

重要な環境変数（最低限必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- そのほか（任意/デフォルトあり）:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - OPENAI_API_KEY: OpenAI を使う機能の API キー
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）

自動 .env 読み込み
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。
- 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------
設定検証
- python -m kabusys.validate_config
- 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

設定ウィザード
- python -m kabusys.config_setup
  - .env の初期作成・更新を対話式で行います。

実行エンジン（ExecutionEngine）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録します。
  - 起動時に PID ファイル（デフォルト data/execution.pid）を扱い、data/stop_requested.flag を置くと起動しない／停止させられます。
  - プロセス優先度を "high" に設定します（可能な環境で）。

監視ループ起動
- python -m kabusys.run_monitoring
  - SystemMonitor を定期実行して monitoring DB（SQLite）にログを残します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使います（KABUSYS_ENV に依存せず）。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - --from YYYY-MM-DD --to YYYY-MM-DD
- DB 指定:
  - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

AI 機能
- news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数か OPENAI_API_KEY 環境変数で指定
  - スコアは ai_scores テーブルへ書き込まれます
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースを組み合わせて market_regime に書き込み

停止・キルスイッチ
- Kill Switch: monitoring が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine はこれを検知して安全に停止します。
- 手動停止: data/stop_requested.flag を配置すると run_monitoring / run_execution のループは終了します。

ログ
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用してログを設定します。
- デフォルトは logs/<app_name>.log に日次ローテーションで出力（30 日保存）。
- 標準出力には StreamHandler（stdout）で出ます。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 内の主要なファイル・ディレクトリです。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB 操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※実装ファイル群が含まれます)
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

ファイル・パスのデフォルト
- DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で上書き)
- 監視 SQLite: data/monitoring.db (環境変数 SQLITE_PATH)
- ペーパートレード SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- PID / フラグ:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag

開発・運用上の注意
------------------
- .env は機密情報（API キー等）を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値を特に注意してください。validate_config による本番向けの追加警告があります。
- OpenAI API を利用する機能は API キーが必須です。API 呼び出しはリトライやフォールバックを含む実装になっていますが、API 制限や料金には注意してください。
- DuckDB / SQLite のパスは運用ポリシーに沿ってバックアップを検討してください（特にペーパートレード DB と本番 DB の混同に注意）。

トラブルシューティング
---------------------
- 設定検証でエラーが出る場合: .env を確認し必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。
- ログファイルが作成できない場合: 権限や LOG_DIR 環境変数を確認してください。ログディレクトリ作成に失敗した場合はコンソールのみログが出ます。
- モジュール読み込みや依存ライブラリエラー: duckdb / psutil / openai / PyYAML のインストールを確認してください。
- .env の自動読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）

お問い合わせ / 貢献
-------------------
バグレポートや改善提案はリポジトリの Issue にお願いします。プルリク歓迎です。

以上。README に掲載してほしい追加情報（サンプル .env、実行例、詳細な API ドキュメントなど）があれば教えてください。必要に応じて追記します。