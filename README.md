# KabuSys — 日本株自動売買システム (README)

バージョン: 0.1.0

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュール群です。取引エンジン、監視、ポートフォリオ構築、ファクター/リサーチ、AI（ニュース NLP / レジーム判定）など、運用に必要な主要機能を含みます。

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存関係
- セットアップ手順
- 使い方（起動コマンド例）
- 環境変数 / .env の例
- データベース・ログ・フラグファイルについて
- 推奨ワークフロー
- ディレクトリ構成（主要ファイル）


プロジェクト概要
- KabuSys は日本株向けの自動売買システム（バックテスト／ペーパートレード／本番運用を想定）。
- モジュールは「発注（Execution）」「監視（Monitoring）」「ポートフォリオ構築」「リサーチ（ファクター計算）」「AI（ニュースセンチメント・レジーム判定）」などで分離されている。
- DuckDB を使った分析用 DB、SQLite を使った監視/ログ永続化を併用する設計。
- OpenAI API を利用したニュースの NLP スコアリング、およびマクロセンチメントの利用によるレジーム判定機能を持つ（APIキー必須）。

主な機能
- ExecutionEngine：ブローカークライアント経由で発注を実行（paper_trading 環境では MockBrokerClient を使用）。
- Monitoring：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション数）をポーリングして記録・アラート。
- Kill Switch：条件により停止フラグ（data/kill.flag）を作成し Execution を安全停止。
- Portfolio：候補選定、重み付け、ポジションサイズ計算、セクターキャップやレジーム乗数の適用。
- Research：DuckDB 上でファクター計算（Momentum / Volatility / Value など）と特徴量解析（IC 計算等）。
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント取得（ai.score_news）とレジーム判定（ai.regime_detector.score_regime）。
- CLI ユーティリティ：.env 対話式ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成ツール（tools.paper_verification_report）。


前提条件 / 依存関係
- Python 3.10 以上（typing の | 記法等を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の検証に使用）
- 組み込みモジュール: sqlite3, logging, threading など
- 実運用では kabuステーション API などの外部ブローカー接続情報が必要

（注）requirements.txt は本リポジトリに含まれていない場合があるので、上記パッケージを明示的にインストールしてください。
例: pip install duckdb psutil openai pyyaml


セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてワークツリーに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\Activate      (Windows)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants トークン、kabu API パスワードなどを設定
   - あるいは / サンプルを直接作成（下方に例あり）

5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトでは data/ 以下に DB・PID・フラグファイルを置きます。
   - 必要に応じて環境変数でパスを上書きできます（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）


使い方（起動 / CLI）
- 設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も fail 扱い: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 本番 or 開発（KABUSYS_ENV の値に依存）:
    - python -m kabusys.run_execution
  - 停止: ディレクトリ data/ に stop_requested.flag を置くとプロセスが検知して停止します。
  - 実行時、KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使用（環境に依らず monitoring DB を本番パスで利用する設計）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （なければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）

- AI / レジーム関連（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を指定

ログ設定
- ログは kabusys.utils.logging_setup.setup_logging によって統一的に設定されます。
- デフォルトのログディレクトリ: logs/
- ログは stdout と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。


主要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）

（詳細は kabusys.config.Settings の docstring / プロパティを参照）


.data / フラグ / PID ファイル
- data/execution.pid — ExecutionEngine の PID（起動時に書き込まれる）
- data/stop_requested.flag — run_execution / run_monitoring で監視する停止フラグ
- data/kill.flag — Kill Switch が作成する停止理由を含むフラグ（Execution 停止トリガ）
- デフォルト DB パス:
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db（KABUSYS_ENV=paper_trading 時の専用 DB）


推奨ワークフロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB に日次データをロード（data pipeline を利用）
4. Execution を paper_trading モードで動作確認（KABUSYS_ENV=paper_trading）
5. Monitoring を別プロセスで常時稼働させる（run_monitoring）
6. 必要に応じて tools.paper_verification_report で運用評価


ディレクトリ構成（主要ファイル）
※ src/kabusys 以下を想定。コードベースから抜粋した主要モジュールを示します。

- src/kabusys/
  - __init__.py  (バージョン等)
  - config.py                (環境変数・設定読み込み)
  - config_setup.py          (.env 対話式ウィザード)
  - validate_config.py       (設定検証 CLI)
  - run_execution.py         (ExecutionEngine 起動スクリプト)
  - run_monitoring.py        (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py  (ペーパートレード検証レポート)
  - ai/
    - news_nlp.py             (ニュース NLP スコアリング)
    - regime_detector.py      (市場レジーム判定)
    - __init__.py
  - monitoring/
    - monitoring_db.py        (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py        (存在を想定; 監視ロジック)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        (存在を想定; 通知管理)
  - execution/
    - execution_engine.py     (ExecutionEngine 本体)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (ランタイムに作成される / DB・フラグ等を配置)
  - logs/ (ログファイルを出力)

（注）実際のリポジトリではさらに細かいモジュール・ファイル群（data pipeline, strategy 等）が存在する想定です。


サンプル .env（最低限の必須項目）
    # .env sample (絶対に Git にコミットしないこと)
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
    KABU_API_PASSWORD=your_kabu_api_password_here
    KABUSYS_ENV=development
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    LOG_LEVEL=INFO
    OPENAI_API_KEY=sk-xxxxx         # AI 機能を使う場合のみ

運用上の注意
- KABUSYS_ENV=live（本番）での起動前には validate_config を実行し、LINE 等の通知が正しく設定されているか確認してください。
- .env は機密情報を含むため、絶対にバージョン管理に含めないでください。
- Kill Switch / stop flag の挙動を理解した上で外部プロセス管理（systemd / supervisor / cron）を導入してください。
- OpenAI API を利用する機能はコストとレイテンシに注意して運用してください（リトライロジック・バックオフは組み込まれていますが、呼出頻度次第で料金が発生します）。

補足（開発者向け）
- ログ設定は kabusys.utils.logging_setup.setup_logging を全起動スクリプトの冒頭で呼ぶ設計です。
- process_priority でプロセス優先度を上げる処理があり、プラットフォーム差分（Windows / POSIX）を吸収する実装になっています。
- DuckDB を使ったファクター計算・分析は外部 API に依存しない設計です（prices_daily / raw_financials テーブルを前提）。

---

不明点や README に追記してほしい内容があれば教えてください。実行環境（OS / Python バージョン）や使いたい機能（本番運用 / ペーパートレード / AI スコアリング）を教えていただければ、より具体的な手順を追加します。