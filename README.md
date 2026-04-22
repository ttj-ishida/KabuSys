KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要スクリプト・モジュールを元に作成した簡易ドキュメントです。
開発・運用に必要な概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買フレームワークです。  
主な責務は以下の通りです。

- シグナル（ファクター）計算・研究（DuckDB を使ったファクター群）
- ポートフォリオ構築（候補選定、配分重み、ポジションサイズ計算）
- ExecutionEngine による発注・注文管理（paper_trading 環境用のモック対応）
- 監視（System / Trade / Risk モニタ）と Kill Switch による安全停止
- AI を用いたニュース NLP（OpenAI API を利用したセンチメント評価）
- ツール（ペーパートレード検証レポート等）

主要な設計方針の例:
- DuckDB / SQLite をデータ基盤として使用（分析/監視を分離）
- 環境変数 / .env で設定を管理（config_setup.py によるウィザードあり）
- 本番環境では慎重なガード（Kill Switch / リスク監視）を実装

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
- Monitoring（ポーリング）起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB は共有）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築: 候補選定 / 等重・スコア重み / リスク制約・セクターキャップ / 単元丸め 等
- 研究モジュール: momentum, volatility, value ファクター計算、将来リターン・IC 計算
- AI モジュール: ニュースセンチメント（OpenAI）および市場レジーム判定
- 監視モジュール: system_status/trade_logs/risk_logs/dashboard の永続化とアラート評価

前提 / 必須依存
---------------
- Python 3.9+
- 必要パッケージ（主要）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の構文チェック用）
- SQLite（Python 標準 sqlite3 を使用）
- 環境へ応じた API キー等（下記参照）

重要な環境変数（主要）
--------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注はモック、paper 用 SQLite に記録
  - live: 実際に発注を行う点に注意
- OPENAI_API_KEY — AI モジュール利用時に必要
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject）
- KILL_FLAG_PATH — Kill Switch フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）

セットアップ手順
----------------
1. リポジトリをチェックアウト
   - このドキュメントは src/kabusys 配下のモジュールを想定しています。

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML が必要な場合）pip install pyyaml

   ※requirements.txt が存在する場合はそれに従ってください。

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照して値を設定）
   - 重要: JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須

5. 設定を検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も exit(1) 扱いになります（本番前の確認に推奨）

6. データディレクトリの用意
   - デフォルトでは data/ 以下に sqlite/duckdb/logs ファイルを作成します
   - ログディレクトリは LOG_DIR 環境変数で変更可能

基本的な使い方
-------------
- 環境セット（例）
  - export $(cat .env | xargs)  # 簡易的に読み込む方法（注意して使用）
  - あるいは .env は自動的にロードされます（config.py の自動ロード機構）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番準備時は python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - paper_trading 環境で試す（モックブローカー動作）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は data/execution.pid に PID を書きます

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=120
    - python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - 停止は data/stop_requested.flag を作成して行います

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - 出力は標準出力のテキストレポート

- AI モジュール（ニューススコア、レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - ニューススコアリング: kabusys.ai.score_news（コードから呼び出す API）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

運用上の注意（要点）
-------------------
- KABUSYS_ENV=live の設定は本番発注を行います。十分な確認の上で使用してください。
- Kill Switch:
  - RiskMonitor がトリガー条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時にこのフラグを自動クリアします（本番では 0 推奨）。
- Logging:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトで使用。ログは stdout と logs/<app_name>.log に出力（デフォルト）。
- Process priority:
  - run_execution/run_monitoring は起動時に高優先度 (high) に設定する試みを行います（プラットフォーム依存）。

ディレクトリ構成（要約）
----------------------
このリポジトリの src/kabusys 配下の代表的な構成:

- kabusys/ (パッケージルート)
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装未列挙の可能性あり)
  - execution/
    - execution_engine.py (実行・発注ロジック)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成する想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - stop_requested.flag / kill.flag / execution.pid など

（上記は主要ファイルのみ抜粋しています。詳細は src/kabusys 以下を参照してください）

開発・拡張のヒント
------------------
- DuckDB へは conn（kabusys.research 等）を渡してクエリ実行する設計。SQL を組み合わせた計算が簡潔に書かれています。
- AI 関連は外部 API（OpenAI）呼び出しを想定しており、API 呼び出し部分はテスト時に差し替えられるよう設計されています（モック可能）。
- MonitoringDB（SQLite）はマイグレーション（列追加）に対応するコードが含まれており、既存 DB に対しても冪等的に初期化します。
- 設定検証・ウィザードにより、本番投入前の安全チェックが容易です。

トラブルシュート（よくある項目）
-------------------------------
- .env が自動ロードされない場合:
  - config.py はプロジェクトルート（.git または pyproject.toml）を基に自動ロードします。プロジェクトルートが見つからない場合は自動ロードをスキップします。
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- ログファイルが作成されない:
  - 権限や LOG_DIR のディレクトリ作成に失敗している可能性があります。stdout に警告が出ます。
- OpenAI API 通信エラー:
  - 一部処理はリトライ実装がありますが、API キーやネットワーク／レート制限に注意してください。

ライセンス・貢献
----------------
- この README はコードから自動的にまとめたドキュメントです。実際のライセンスはリポジトリ内の LICENSE ファイルを参照してください。
- 変更・拡張を行う際は unit tests / validate_config を使って設定を確認することを推奨します。

付録: よく使うコマンド（例）
---------------------------
- .env 作成/編集: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- PaperReport: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。運用に関する詳細は各モジュール（src/kabusys 以下）の docstring を参照してください。必要であれば README に追記・整備します。