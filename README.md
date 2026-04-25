README — KabuSys (日本株自動売買システム)
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。
主な責務は以下の通りです。

- ExecutionEngine（発注・注文管理・リスク管理）の起動と運用
- Monitoring（システム稼働・注文・リスク監視）と Kill Switch による安全停止
- Portfolio 構築（候補選定・重み計算・ポジションサイズ決定）
- Research（ファクター計算・特徴量解析）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- Paper Trading 向け検証ツール（検証レポート等）

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading 環境では MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 環境設定 / 検証
  - config_setup.py: .env の対話式ウィザードで作成・更新
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
- モニタリング
  - system_monitor: CPU/メモリ/ディスク使用率、データ鮮度、プロセス監視
  - trade_monitor: 注文の滞留・約定異常等の検出
  - risk_monitor: ドローダウン・保有数上限の監視（Kill Switch と連携）
  - monitoring_engine: モニタを束ねポーリング/アラート発行
  - monitoring_db: SQLite に監視ログを永続化（テーブル作成・マイグレーション含む）
- ポートフォリオ構成
  - portfolio_builder: 候補選定・スコア降順ソート
  - position_sizing: 株数決定（risk_based / equal / score）、単元丸め、集約キャップ処理
  - risk_adjustment: セクターキャップ・レジーム乗数計算
- 研究用モジュール
  - research.factor_research: モメンタム / ボラティリティ / バリュー等の計算（DuckDB を利用）
  - research.feature_exploration: 将来リターン計算、IC、統計サマリー
- AI
  - ai.news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリング
  - ai.regime_detector: マクロニュース + ETF MA を合わせた市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の稼働・注文品質を検証するレポート生成

前提 / 必要環境
---------------
- Python 3.10+
- 推奨外部パッケージ（少なくとも以下は必要）
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML — config/*.yaml の検証に使用
- SQLite（標準ライブラリで可）
- ネットワークアクセス（kabuステーション API / OpenAI 使用時）

セットアップ手順
----------------
1. リポジトリをクローン／展開します。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - まず requirements.txt がある場合はそれを使うのが望ましいですが、なければ最低限:
     pip install duckdb psutil openai
   - YAML 検証を行う場合:
     pip install pyyaml

4. .env を作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - あるいはプロジェクトルートの .env を手動で用意する。
   - 代表的な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV = development | paper_trading | live
     - OPENAI_API_KEY（AI 機能を使う場合）
   - .env の自動ロード:
     プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を配置すると自動読み込みされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー取引用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要 CLI / 実行例）
---------------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or paper_trading に応じて挙動が分かれる）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます。
    - プロセス優先度を "high" に設定しようとします（psutil に依存）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - Monitoring は環境に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書きます。
  - 停止: ディレクトリ data に stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB を指定しない場合は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を参照します。

- AI 機能（例）
  - ニューススコアリング（ai.news_nlp.score_news）は DuckDB 接続と target_date, API キーを受け取り ai_scores テーブルへ書き込みます。OpenAI API キーには OPENAI_API_KEY を設定してください。
  - レジーム判定（ai.regime_detector.score_regime）も OpenAI を利用します。API 呼び出しは堅牢化（リトライ・フォールバック）されていますが、キーがないと ValueError が発生します。

停止フラグ / Kill Switch
-----------------------
- data/kill.flag: KillSwitch によって書き込まれるファイル。存在すると ExecutionEngine に停止シグナルを送る目的で使用されます。
- data/stop_requested.flag: run_* スクリプトが監視している「停止要求フラグ」。存在するとループを終了します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番環境では推奨されません）。

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - stdout（StreamHandler）と日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
  - LOG_DIR 環境変数でログ出力先を指定可能。

ディレクトリ構成
----------------
(主要ファイルのみ抜粋)

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話設定ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/               — ExecutionEngine / OrderManager / BrokerFactory 等（別ファイル群）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用)
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - monitoring.db / paper_trading.db など（デフォルトの配置先）

注意点・運用メモ
----------------
- Python バージョン:
  - 本コードベースは Python 3.10+ を想定（型ヒントに | を使用）。
- DB:
  - monitoring 用の初期テーブル作成・マイグレーションは init_monitoring_db() により自動化されています。
  - Paper Trading と本番用の SQLite は分離されるよう Settings により制御されています。
- OpenAI:
  - AI 機能は OPENAI_API_KEY を必要とし、API のエラー系はリトライ・フォールバック設計が入っています。利用時は API 使用料に注意してください。
- ログディレクトリ:
  - 権限やディスク容量によりログディレクトリの作成に失敗する場合があります。その場合は標準出力のみで継続します。
- セキュリティ:
  - .env 内の秘密情報 (.env) を Git にコミットしないでください。
- テスト:
  - API 呼び出しや外部依存をモックする設計が随所に含まれているため、ユニットテストでモックしやすくなっています。

貢献・拡張
----------
- 新しいブローカー実装は execution/broker_factory.py を経由して追加可能です。
- portfolio や research モジュールは DuckDB のテーブル（prices_daily / raw_financials）を前提としており、データパイプラインを整備すれば容易に拡張できます。
- AI モジュールは出力パースやリトライの挙動を理解した上でプロンプト調整やモデル切り替えを行ってください。

問い合わせ
----------
コード内のドキュメント文字列（docstring）に詳細な挙動と設計思想が記載されています。各モジュールの関数 docstring を参照してください。

以上。必要なら README に含めるサンプル .env テンプレートや systemd / supervisor の起動例、より詳細なディレクトリツリーを追記します。どの追加情報が必要か教えてください。