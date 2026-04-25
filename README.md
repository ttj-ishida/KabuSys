# KabuSys

日本株自動売買システムの一部をまとめたリポジトリ（ライブラリ & 起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）の使い方、設定、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / 各種コマンド）
- 環境変数（主要）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システム向けユーティリティ群・コアロジック群です。
- 主に以下の機能を提供します：
  - ExecutionEngine（発注エンジン）起動スクリプトと発注管理
  - Monitoring（監視）ループとアラート / Kill Switch
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
  - 研究用モジュール（ファクター計算・特徴量解析）
  - AI 補助（ニュースの NLP スコアリング、レジーム判定）
  - ユーティリティ（ロギング設定、プロセス優先度設定、.env ウィザード、設定検証、紙トレード検証レポート生成）

主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の際はモックブローカーを使用して paper_trading DB に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可。
- 設定関連
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env や config/*.yaml の起動前チェック
- モニタリング
  - monitoring_engine.py: 各種 Monitor（System / Trade / Risk）を束ねて定周期で実行
  - monitoring_db.py: SQLite による監視ログ永続化層（テーブル作成 / マイグレーション含む）
  - kill_switch.py: 条件に応じて data/kill.flag を書き込む
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py：候補選定、重み計算、株数決定、セクター制限 等
- リサーチ
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - research.feature_exploration: 将来リターン、IC、統計サマリ
- AI 関連
  - ai.news_nlp: ニュース記事を OpenAI API でセンチメント評価し ai_scores に書き込む
  - ai.regime_detector: マクロ記事 + ETF MA200乖離で市場レジームを判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプト
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ラッパー

セットアップ手順（開発用）
1. リポジトリをクローン・作業ディレクトリへ
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML (validate_config の YAML 検証を使用する場合)
   - 例: pip install duckdb psutil openai PyYAML
   （リポジトリに requirements.txt があればそれを使用してください）
4. 初期設定ファイル（.env）を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは .env.example を参照して手動作成
   - 自動で .env をロードする仕組みがあり、CWD に依存せずプロジェクトルートから .env を読み込みます。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

使い方（代表的なコマンド）
- 実行（ExecutionEngine）
  - 本番/ペーパーを含む実行エンジンを起動:
    - python -m kabusys.run_execution
  - ペーパートレードで起動（MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中停止:
    - data/stop_requested.flag を作成するとスレッドループが検知して停止します。実際の運用では kill.flag を KillSwitch 用に使用します。
  - PID ファイル: data/execution.pid に書き込まれます（Settings.pid_file_path で変更可）

- 監視（Monitoring）
  - 監視ループ起動（SystemMonitor）
    - python -m kabusys.run_monitoring
    - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 監視は常に（環境にかかわらず）settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - 停止:
    - data/stop_requested.flag を作成するとループが終了します

- .env ウィザード / 設定検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラムから呼び出す）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY か関数引数で渡す
  - 例（Python REPL やスクリプト内）:
    - from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")

注意 / 運用メモ
- 環境変数 KABUSYS_ENV の値:
  - development, paper_trading, live
  - paper_trading のとき、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離する設計です。
- ログ:
  - ログは stdout に出力され、かつ logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリは自動作成されます）。
  - LOG_LEVEL / LOG_DIR 環境変数で変更可
- Kill Switch / 停止フラグ:
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を使い、リスク条件（ドローダウン、ポジション上限 等）で書き込まれます。ExecutionEngine はこれを検知して安全に停止します。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。不正値（<=0）はデフォルトにフォールバックします。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env を自動で読み込みます。
  - 自動ロードを無効化する場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 使用:
  - ai.news_nlp / ai.regime_detector は OpenAI を呼びます。API キー未設定時は関数が ValueError を送出します。
  - レート制限・ネットワーク障害は実装側でリトライやフォールバック（0.0）を行う設計です。

主要な環境変数（抜粋とデフォルト）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / デフォルト:
  - KABUSYS_ENV — execution 環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
  - LOG_LEVEL — INFO（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
  - LOG_DIR — logs/
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
  - PAPER_FILL_MODE — paper_trading の MockBroker fill モード（instant | partial | never | reject；デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消すか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

簡単な CLI 例まとめ
- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視を起動（ポーリング 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（ペーパー）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py (省略)
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (一部参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/                — (発注エンジン関連モジュール群、factory, engine, order_manager 等)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時に生成されるファイル: DB, flag, pid 等（ディレクトリ）
    - monitoring.db (デフォルト)
    - paper_trading.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - kill.flag, stop_requested.flag, execution.pid など

最後に（開発者向けメモ）
- DB スキーマは monitoring_db.init_monitoring_db で冪等に作成 / マイグレーションします。
- ロギングは共通ユーティリティで統一され、起動スクリプトから必ず setup_logging を呼び出してください。
- 外部 API（kabuステーション、J-Quants、OpenAI）は設定・トークンが必要です。テスト・開発用に paper_trading モード / MockBroker を用意しています。
- 重要な設計方針の一つは「ルックアヘッドバイアス回避」。AI / リサーチ系は date 引数ベースで動作し、date.today() の直接参照を避ける実装になっています。

問題や追加情報が必要な場合は該当ファイル（README と同じレポジトリ内）を参照してください。README 以外に CLI のヘルプや各モジュールの docstring に詳細な使い方が記載されています。