KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・運用支援を目的とした Python ベースのプロジェクトです。  
主な目的は以下。

- シグナル → ポートフォリオ構築 → 発注までの Execution Engine
- 実行状況・システム状態の監視とアラート（Monitoring）
- ファクター計算・リサーチ用ユーティリティ（Research）
- ニュース NLU によるセンチメント評価 / レジーム判定（AI）
- ペーパートレード検証用ツール類（tools）
- 環境設定ウィザード・設定検証 CLI（config_setup / validate_config）

設計方針の要点:
- DB: 分析用に DuckDB、ログ/監視用に SQLite を使用（デフォルトファイルは data/ 配下）
- 本番とペーパートレードは分離（KABUSYS_ENV による）
- ロギングは統一インターフェースで日次ローテート（logs/<app>.log）
- 外部 API 呼び出し（OpenAI など）は明示的に API キーを渡すか環境変数で指定

主な機能
--------
- ExecutionEngine: 注文作成・発注・注文再帰・リスク管理を行うエンジン
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring: SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視ループ
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - Kill Switch により条件（ドローダウン・ポジション上限等）で Execution を停止
- Portfolio Construction: 候補選定・重み計算・ポジションサイズ算出・セクター制限
- Research: DuckDB 上でファクター計算（momentum / volatility / value）・IC / 統計サマリを実行
- AI モジュール:
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント算出（ai_scores へ格納）
  - regime_detector: MA200 とマクロニュースを組合せて市場レジーム判定
- ユーティリティ:
  - logging_setup: 一貫したログ設定（コンソール + 日次ファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール:
  - paper_verification_report: ペーパートレード結果を集計して PASS/FAIL レポートを出力
- 設定補助:
  - config_setup: 対話式で .env ファイルを生成
  - validate_config: .env と config/*.yaml の事前検証

前提 / 要件
-----------
- Python 3.10+
- 必須パッケージ（一例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を行う場合）
- 推奨: 仮想環境（venv / pipx / conda）

インストール例
--------------
1. リポジトリをクローン:
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境の作成・有効化（例: venv）:
   python -m venv .venv
   source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があればそれを使ってください）

環境設定 (.env)
----------------
プロジェクトルートに .env を配置して環境変数を設定します。対話的に作成するには:

python -m kabusys.config_setup

必須となる主な環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 重要な変数:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: 分析 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: OpenAI を使う機能で必要

設定検証:
python -m kabusys.validate_config
--strict を付けると警告も失敗扱いになります。

セットアップ手順
----------------
1. .env を作成（上記の config_setup を推奨）。必須項目を必ず設定。
2. data/ ディレクトリと logs/ ディレクトリを作成（logging_setup が自動化しますが事前作成しておくと安全）:
   mkdir -p data logs
3. DuckDB / SQLite の初期スキーマは起動スクリプトが自動で作成・マイグレーションを行います。
4. 設定検証:
   python -m kabusys.validate_config

使い方（起動・操作）
-------------------

起動スクリプト
- ExecutionEngine を起動:
  python -m kabusys.run_execution

  動作:
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中に stop を要求するにはプロジェクトルートの data/stop_requested.flag を作成

- Monitoring を起動:
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）。
  python -m kabusys.run_monitoring

  動作:
  - 常に本番用の sqlite_path（Settings.sqlite_path）を使用して monitoring テーブルを初期化
  - stop フラグ（data/stop_requested.flag）を検知するとループを終了
  - 監視で Kill Switch 条件に触れた際は Settings.kill_flag_path（デフォルト data/kill.flag）へフラグを書き込む

停止 / Kill
- 停止フラグ: data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して停止します。
- Kill Switch: monitoring が条件を満たすと data/kill.flag を書き込み、Execution 側はこれを見て安全停止する運用を想定。

ツール
- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで別 DB を指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

ライブラリとしての利用例
- リサーチ関数を Python REPL / スクリプトから呼ぶ:
  from kabusys.research import calc_momentum
  import duckdb, datetime
  conn = duckdb.connect('data/kabusys.duckdb')
  results = calc_momentum(conn, datetime.date(2026, 4, 10))

- AI スコアリング（OpenAI API キーが必要）:
  from kabusys.ai import score_news
  import duckdb, datetime
  conn = duckdb.connect('data/kabusys.duckdb')
  score_news(conn, datetime.date(2026,4,10), api_key="sk-...")

ログ
---
- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。アプリ起動時に setup_logging(app_name="execution" など) が呼ばれます。
- コンソール出力は stdout へ出ます。

主要ファイル・ディレクトリ構成
----------------------------
（プロジェクトルートの src/kabusys を想定）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

subpackages:
- execution/                 — 発注エンジン関連（BrokerFactory, Engine, OrderManager 等）
- monitoring/
  - monitoring_db.py         — SQLite スキーマ・永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py              — ニュースセンチメント生成（OpenAI）
  - regime_detector.py       — レジーム判定（MA200 + マクロニュース）
- utils/
  - logging_setup.py         — 共通ログ設定
  - process_priority.py      — プロセス優先度設定
- tools/
  - paper_verification_report.py

デフォルトのデータパス（Settings のデフォルト）
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID / フラグ / ログ: data/ / logs/

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env の中身（APIキー等）を適切に管理し、.env をリポジトリにコミットしないこと。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にすることは危険。デフォルト 0 を推奨。
- OpenAI や外部 API を使うモジュールはエラー耐性を持つ設計だが、API キーやレート制限に注意すること。
- run_execution/run_monitoring はプロセス優先度を変更しようとします（管理者権限が必要になる場合があります）。

貢献・拡張
----------
- 新しい戦略モジュール、ブローカークライアント、監視ルールやアラート先（LINE 等）を追加可能。
- portfolio/ 以下の純粋関数はユニットテストしやすい設計なので、テスト追加を推奨します。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください。

最後に
------
この README はコードベースの主要な機能・使い方をまとめたものです。実際の環境で運用する前に必ず python -m kabusys.validate_config による検証と、少量のペーパートレードでの動作確認を行ってください。必要であれば README をプロジェクト固有の運用手順に合わせて追記してください。