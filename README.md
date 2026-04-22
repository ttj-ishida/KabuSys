KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買および運用検証のためのモジュール群です。  
主な機能はシグナル生成・ポートフォリオ構築・発注エンジン・監視・リスク制御・研究用ファクター計算・ニュース NLU によるセンチメント評価などを含みます。  
このリポジトリはライブラリとしての再利用を想定しつつ、以下の CLI / 起動スクリプトで運用できる設計になっています。

主な特徴（機能一覧）
-----------------
- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 起動前設定検証ツール（環境変数・config/*.yaml）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（実際の発注処理 or ペーパートレード）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading.db に分離して記録
- Monitoring（System / Trade / Risk モニタリング）: run_monitoring.py / MonitoringEngine
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - 停止フラグ: data/stop_requested.flag（スクリプト自身の終了用）
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI を用いた銘柄センチメント評価）: kabusys.ai.news_nlp
  - OpenAI API（OPENAI_API_KEY）が必要
- ファクター計算 / 研究ユーティリティ（DuckDB を利用）: kabusys.research
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング・セクター制約）: kabusys.portfolio
- ロギング設定ユーティリティ（統一ログ出力・日次ローテーション）: kabusys.utils.logging_setup

必須 / 主要環境変数
-------------------
（.env を用いて設定することを想定、config_setup で対話的に生成可能）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 推奨:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で必要（ニュース NLP / レジーム検出）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知に使用（任意）

セットアップ手順
--------------
1. リポジトリをクローンし、Python 仮想環境を準備します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（requirements.txt がある場合はそれを使用）。
   - pip install duckdb psutil openai
   - Optional: PyYAML（config/*.yaml の検証を行う場合）：pip install PyYAML

3. 環境変数設定（.env）を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - 生成した .env は絶対に Git にコミットしないでください。

4. 設定検証を行います。
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリ・ログディレクトリの確認
   - デフォルト DB / ログは data/ と logs/ に置かれます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を設定してください。

基本的な使い方
--------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env ファイルを対話的に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に必須環境変数やファイルパス、YAML の整合性チェックを行います。

- 実際の ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading のときは MockBroker を使い、paper_trading.db に書き込みます。
  - 起動時に data/execution.pid が作成されます。
  - 停止方法:
    - 外部から正式に停止する場合は monitoring の Kill Switch が data/kill.flag を書くことで ExecutionEngine に停止シグナルが送られます。
    - 監視スクリプトや手動で data/stop_requested.flag を作成すると起動スクリプトのループを終了します（run_execution/run_monitoring の停止フラグ）。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - Monitoring は常に本番監視用 sqlite_path（SQLITE_PATH）を使用します（環境に依らず本番 DB を参照する設計）。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

- ニュース NLP / レジーム判定（API を使う機能）
  - OPENAI_API_KEY を設定してください。関数はライブラリ関数として提供されています（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。
  - エラー時はフェイルセーフで処理を継続するよう設計されていますが、APIキー未設定時は例外が発生します。

運用上の注意
------------
- KABUSYS_ENV の値が live の場合は本番稼働扱いです。LINE 通知や Kill Switch 設定などを十分に確認してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR を設定するとそこに出力されます。
- Paper Trading（ペーパートレード）は本番データベースと分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー内の主要なディレクトリ / ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化層
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（滞留注文・異常約定など） ※実装参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 監視フロー統合
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計ユーティリティ
  - utils/
    - logging_setup.py       — 統一ロギング設定（console + 日次ファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定（psutil）
  - (その他) data, strategy, execution モジュール群（実装依存）

（補足）ファイルフラグ / PID
- data/stop_requested.flag: run_* スクリプトの外部停止フラグ（存在することでループ停止）
- data/kill.flag: Kill Switch が ExecutionEngine 停止を指示するために書き込むフラグ
- data/execution.pid: ExecutionEngine の PID ファイル（起動時に書き込み）

開発・拡張のヒント
------------------
- DuckDB 接続を引数で受け取る設計が多く、研究・計算ロジックは副作用を持たない純粋関数として実装されています（テストしやすい）。
- OpenAI 呼び出しを行う箇所では API 呼び出し関数を切り替え可能に設計しており、単体テスト時にはモック置換が容易です。
- monitoring_db のスキーマは冪等に作成・マイグレーションを行うように実装されています。

ライセンス / バージョン
-----------------------
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- ライセンス情報はリポジトリのトップレベル（LICENSE 等）を参照してください（本リポジトリに含まれる場合）。

問題や拡張案があれば README を更新していただくか、Issue / PR で提案してください。