KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。本リポジトリは次のような機能群を含みます。

- 注文実行エンジン（ExecutionEngine）とブローカー抽象化（本番 / ペーパートレード分離）
- システム監視（SystemMonitor）・取引監視・リスク監視・Kill Switch
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクター制限）
- ファクター計算・特徴量探索（DuckDB を用いた研究用モジュール）
- ニュースを用いた LLM（OpenAI）ベースのセンチメントスコアリングと市場レジーム判定
- 各種 CLI（.env 設定ウィザード、設定検証、監視/実行スクリプト、検証レポート）

主な設計方針
- DuckDB / SQLite をローカル DB として利用（分析用・監視用・ペーパートレード用を分離）
- OpenAI 呼び出しは可変で、フェイルセーフ（API 失敗時にスキップ・デフォルト値で継続）
- .env 自動読み込み（プロジェクトルートを検出して .env / .env.local を読み込む）
- ログはコンソール + 日次ローテートファイルへ出力（logs/ ディレクトリ）

機能一覧
--------
- 環境セットアップ
  - 対話式 .env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行 / 監視
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）
    - 監視は常に production sqlite_path を使用（環境に依存しない）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナル

- モニタリング / アラート
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - RiskMonitor（ドローダウン・保有数上限の判定）と KillSwitch の連携
  - MonitoringEngine による定期実行・アラート発行

- ポートフォリオ構築
  - 候補選定（スコア基準）、等金額／スコア重み計算
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap、コストバッファ考慮）

- リサーチ（DuckDB を前提）
  - ファクター計算: momentum / volatility / value
  - 特徴量探索: forward returns, IC（Spearman）計算, 統計サマリー

- AI（OpenAI）連携
  - news_nlp: ニュース集合を LLM に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF (1321) の MA200 乖離 + マクロニュース LLM による日次レジーム判定

- ツール
  - ペーパートレード検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成してアクティベートすることを推奨
     - python -m venv .venv
     - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 依存パッケージのインストール
   - 主要依存（プロジェクトの使用機能により追加で必要）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があればそれを使用してください：pip install -r requirements.txt）

3. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）

4. 設定検証（必須環境変数のチェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit 1 になる:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトで SQLite / DuckDB / ログはプロジェクト内の data/ や logs/ に作成されます。
   - 必要に応じて環境変数でパスを上書きしてください（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）

主要な環境変数（代表）
----------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）（run_monitoring 用）

使い方（コマンド例）
-------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書きする場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    - プロジェクトルート/data/stop_requested.flag を作成するとループは検知して停止します

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすれば MockBrokerClient が使われ、data/paper_trading.db に記録されます
  - 実行中に停止したい場合は data/stop_requested.flag を作成してください
  - 実行中は data/execution.pid に PID を書きます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパス指定可能

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

ロギング
--------
- setup_logging() により stdout と日次ローテートファイル（logs/<app_name>.log）へ出力します。
- LOG_DIR 環境変数または setup_logging の引数で出力先を変更できます。

停止 / Kill Switch / フラグファイル
---------------------------------
- data/stop_requested.flag: run_monitoring/run_execution がループを抜けるために監視する停止フラグ（外部ツールや CI から作成）
- data/kill.flag: KillSwitch が危険状態（例: ドローダウン超過）を検出した際に作成するフラグ。ExecutionEngine はこのフラグがあれば起動/継続しない（本番保護）。kill.flag は clear() によって削除可能。
- data/execution.pid: 実行エンジンの PID を記録

ディレクトリ構成
----------------
（リポジトリの src/kabusys 配下を抜粋して説明）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数の読み込み・Settings クラス、自動 .env ロード
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - utils/
    - logging_setup.py       — ルートロガーの設定（stdout + ファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定（psutil ベース）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 取引監視（滞留注文・約定異常など）※実装参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 複数モニタを束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等）※実装参照
  - execution/
    - broker_factory.py      — ブローカークライアント生成（本番 / mock）
    - execution_engine.py    — ExecutionEngine（セッション実行）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — forward returns, IC, summary
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロ LLM）
  - data/                    — 実行時に使用するデフォルトのディレクトリ（data/*.db, flags）
  - logs/                    — デフォルトのログ出力先

開発上の注意点 / 補足
-----------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup も README に注記あり）
- config.py はプロジェクトルート (.git または pyproject.toml) を起点に .env 自動ロードを行います。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます（テスト向け）。
- 実行時の DB マイグレーション（monitoring_db.init_monitoring_db）は冪等に実行されます。既存テーブルへのカラム追加等も含む簡易マイグレーションを行います。
- OpenAI の呼び出しは retry/backoff を実装していますが、API キーは必ず設定してください（AI 機能を使う場合）。
- 監視は監視 DB（SQLITE_PATH）を使用します。run_monitoring は KABUSYS_ENV に関係なく監視用 sqlite_path を使用します。

バージョン
----------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）

ライセンス
---------
- 本 README に特定のライセンス記述がない場合、プロジェクトルートの LICENSE ファイルを参照してください。

お問い合わせ / 開発者向け
-----------------------
- 変更や拡張（たとえば broker の追加実装、ログ形式の変更、AI プロンプト調整）は各モジュールの docstring / コメントに従ってください。ユニットテストやモックを用いて OpenAI 呼び出し等は差し替え可能です（モジュール内で _call_openai_api のパッチが想定されています）。

以上が本コードベースの概要と基本的な操作手順です。必要であれば「特定機能の詳細な使い方（例: position sizing パラメータの調整、AI プロンプトの変更方法、DB スキーマ詳細など）」について別途ドキュメントを作成します。ご希望があれば教えてください。