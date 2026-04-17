KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。  
主に環境設定、監視・稼働管理、ポートフォリオ構築ロジック、調査用ファクター計算、AI を使ったニュースセンチメント／レジーム判定などを含みます。

この README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

概要
----
KabuSys は次のような責務を持つモジュール群で構成された自動売買/研究フレームワークです。

- ExecutionEngine: 発注実行のエンジン（本番/ペーパートレードを切替可能）
- Monitoring: システム稼働状況・注文状況・リスク監視、Kill Switch（停止フラグ）
- Portfolio modules: 候補選定、重み計算、ポジションサイズ計算、セクター制限等の純粋関数（DB非依存）
- Research: ファクター計算、将来リターン計算、IC 等の統計ツール（DuckDB を利用）
- AI: OpenAI を使ったニュースの NLP スコアリング / 市場レジーム判定
- ユーティリティ: 設定管理、プロセス優先度設定、設定ウィザード、設定検証ツール 等

主な機能一覧
--------------
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートが特定できる場合）
  - 対話式ウィザードで .env を作成する kabusys.config_setup
  - 設定ファイル（config/*.yaml）の存在・基本的妥当性検査を行う kabusys.validate_config

- Execution（発注）
  - 本番/ペーパートレード切替（KABUSYS_ENV=paper_trading では MockBrokerClient を使用し data/paper_trading.db に記録）
  - PID ファイル管理（data/execution.pid）
  - 停止フラグの監視（data/stop_requested.flag / data/kill.flag を用いる）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス存在、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウンやポジション上限監視、dashboard 更新
  - KillSwitch: しきい値超過時に data/kill.flag を書き込みエンジン停止トリガー
  - Monitoring DB（SQLite）永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard 等）

- Research / Portfolio
  - ファクター計算: Momentum / Volatility / Value 等（DuckDB 上で完結）
  - 特徴量探索・IC 計算・統計サマリー
  - 候補選定 / 等重・スコア重み / セクター制限 / ポジションサイズ計算（単元丸め・利用可能現金に基づくスケーリング等）

- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを算出し ai_scores に書込み
  - regime_detector: ETF（1321）の MA200 乖離 + マクロニュースの LLM センチメントで日次の市場レジームを判定し market_regime に保存
  - API 呼び出しはリトライ・バックオフ・レスポンスバリデーションを含む堅牢な実装

セットアップ
-----------
以下はローカル開発環境向けの基本手順です。プロダクションでは適宜 OS パッケージやサービス化を検討してください。

1. リポジトリをクローン
   - リポジトリルートには src/ 以下にパッケージが配置されています。

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な Python パッケージをインストール
   - 主要な依存（最低限）:
     - psutil
     - duckdb
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証を有効にする場合）
   - 例:
     - pip install psutil duckdb openai pyyaml

   ※ requirements.txt がない場合は、上記を個別にインストールしてください。

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参考にする）

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（要点）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

実行環境指定:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い data/paper_trading.db を利用
  - live: 実際の発注が行われるため注意が必要

データベース:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

OpenAI:
- OPENAI_API_KEY — news_nlp / regime_detector が必要とする場合

通知（任意）:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）

プロセス／監視関連:
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch の flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

自動 .env ロード:
- プロジェクトルートに .env / .env.local があれば自動で読み込む（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

基本的な使い方（コマンド例）
---------------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - 起動時に data/stop_requested.flag が既に存在すると起動しません
    - 起動中の安全停止は monitoring の KillSwitch や data/stop_requested.flag によって行われます
    - ペーパートレードモード: KABUSYS_ENV=paper_trading を設定すると mock broker と data/paper_trading.db を使用

- Monitoring 起動（単独で稼働）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒。MONITOR_POLL_INTERVAL は秒単位の正の整数で指定

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトDB: data/paper_trading.db。別DBを使う場合は --db または env PAPER_TRADING_SQLITE_PATH を指定

- AI モジュール呼び出し（スクリプト外で利用する場合）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数渡しまたは環境変数 OPENAI_API_KEY）

停止・フラグ操作
----------------
- run_execution / run_monitoring は共にプロジェクトルート/data/stop_requested.flag の存在をチェックしています。外部から停止させたい場合はこのファイルを作成してください（存在すると監視ループが終了します）。
- KillSwitch（監視コンポーネント）は条件を満たすと data/kill.flag に理由を記述して書き込み、ExecutionEngine に停止を促します。
- ExecutionEngine が PID を書き出すファイル: data/execution.pid

データベース（既定パス）
-----------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db

設計上の注意・安全措置
---------------------
- 設定ファイルや環境変数の誤設定が本番で重大な影響を与えるため、validate_config, config_setup を用いた事前検証を推奨します。
- KABUSYS_ENV=live の場合は特に LINE 通知や kill flag の設定を確認してください。
- AI 呼び出しは外部APIを使うため失敗時にフェイルセーフとしてスコア 0.0 を用いるなどの保護が組み込まれていますが、運用時は API 利用制限やコストにも注意してください。
- process priority / CPU affinity 設定は psutil を使って OS に依存せず適用しようとしますが、権限不足で失敗することがあります（ログ警告）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys/ 以下の主なファイル・ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env 読み込み含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（AI + MA200）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート配送を統括：LINE 等に接続する想定）
  - execution/                — 発注エンジン・Order 管理（詳細実装は各モジュール）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時に利用するディレクトリ)
    - execution.pid
    - kill.flag
    - monitoring.db
    - paper_trading.db
    - stop_requested.flag

ドキュメント / 参照
------------------
- 各モジュールの docstring に詳細な設計メモ、入力/出力仕様、注意点が書かれています。運用前に該当モジュールの docstring を参照してください。
- 設定作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper 証明レポート: python -m kabusys.tools.paper_verification_report

最後に
-------
本 README はコードベースの主要要素をまとめたものです。実際の運用やデプロイ前には各設定項目・外部 API キー、通知設定、本番 DB パスなどを十分に確認してください。必要であれば運用手順書（起動スクリプト、 systemd ユニット、ログローテーション、バックアップ）を別途準備してください。

何か追加で README に載せたい情報（例: systemd ユニット例、より詳細な設定例、CI/CD 手順等）があれば指示をください。