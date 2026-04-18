KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を持ち、運用向けの実装（発注エンジン、監視、リスク制御、ファクター計算、LLM ベースのニューススコアリング等）を含みます。

主な特徴
- ExecutionEngine（発注エンジン）: 実売買／ペーパートレードを切替可能
- Monitoring: システム稼働状況・データ鮮度・注文状況・リスク監視
- Risk management: ドローダウンや保有上限の検出と Kill Switch 出力
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- Research: DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー等）
- AI モジュール: OpenAI を利用したニュースセンチメント（ai.news_nlp）／レジーム判定（ai.regime_detector）
- ユーティリティ: 設定ウィザード、設定検証ツール、ログ設定、プロセス優先度設定、運用レポート生成ツール

動作環境（概略）
- Python 3.9+
- 必須ライブラリ（例）: duckdb, psutil, openai
- optional: PyYAML（config/cfg 検証時に使用）

インストール & 初期セットアップ
-----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai
   - （設定検証で YAML を検証したい場合）pip install PyYAML

   ※ requirements.txt が存在する場合は pip install -r requirements.txt を利用してください。

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBroker を使用し data/paper_trading.db に分離して保存
  - live: 本番（発注されます）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 利用時に必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト INFO
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）デフォルト 60
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト時に利用）

自動 .env ロード挙動
- プロジェクトルート（.git または pyproject.toml を持つディレクトリ）を起点に .env/.env.local を自動読み込みします。
- OS 環境変数 > .env.local > .env の優先度で設定されます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要スクリプト）
-----------------

- 監視ループ（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
    - 監視は Settings の sqlite_path を使用（環境にかかわらず本番 sqlite を使用）
    - 停止フラグ: プロジェクト直下 data/stop_requested.flag が存在するとループを終了します
    - ログは logs/monitoring.log（デフォルト）に出力されます

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）
    - 起動時に data/execution.pid を PID ファイルとして扱います（設定によりパス変更可）
    - 停止フラグ: data/stop_requested.flag があると起動せず終了、起動中に存在すれば engine.stop() を呼んで停止します

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成・更新を対話式で行います

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に環境と config/*.yaml の有無等を検査します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / 研究系関数（API を呼ぶ関数は Python API として使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数か OPENAI_API_KEY 環境変数で渡す必要があります

ログ・ファイル
-------------
- ロギングは kabusys.utils.logging_setup.setup_logging により統一されます
  - コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）を設定
  - デフォルトログディレクトリ: logs/
  - LOG_DIR 環境変数で変更可
- 停止／制御フラグ
  - data/stop_requested.flag : 起動中スクリプトが監視している“即時停止”フラグ（run_monitoring/run_execution が参照）
  - data/kill.flag : KillSwitch が書き込む停止フラグ（ExecutionEngine に停止指示するため）
  - data/execution.pid : ExecutionEngine の PID ファイル（デフォルト）

データベース
-----------
- monitoring 用 SQLite（監視、トレードログ等）: デフォルト data/monitoring.db
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard（init_monitoring_db で自動作成・マイグレーション）
- DuckDB（解析用）: デフォルト data/kabusys.duckdb
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

実運用上の注意
--------------
- KABUSYS_ENV=live の場合は特に注意して設定を行ってください（validate_config にて注意喚起を行います）
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください
- OpenAI 利用部分は API キーやレート制限に配慮し、テスト時はモックすることを推奨します
- プロセス優先度設定には psutil が使われます。権限不足で設定できない場合は警告ログを出して続行します

ディレクトリ構成（抜粋）
--------------------
以下は src/kabusys 以下の主要ファイル／モジュールと簡単な説明です。

- kabusys/
  - __init__.py (バージョン)
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロード・検証・デフォルト）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI

  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py — ログの共通設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py —（トレード監視: ファイル内に定義あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 管理
    - monitoring_engine.py — モニタ群を束ねるエンジン
    - alert_manager.py —（アラート送信ロジック: LINE など）

  - execution/
    - execution_engine.py — 発注エンジンコア（EngineConfig, run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など

  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定、資金スケール
    - risk_adjustment.py — セクター制限、レジーム乗数

  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC 等の統計分析

  - ai/
    - news_nlp.py — ニュースの LLM ベースセンチメント集計（ai_scores テーブルへ書込み）
    - regime_detector.py — ETF MA とマクロニュースの LLM スコアを合成して市場レジーム判定

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

例: 監視のローカル起動
---------------------
1. .env を作成して必要環境変数を設定
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 監視を起動
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

例: 発注エンジン（ペーパートレード）起動
---------------------------------
- KABUSYS_ENV=paper_trading python -m kabusys.run_execution

AI 関連の実行例（Python から）
-----------------------------
- DuckDB 接続 conn を用意して:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

備考
----
- この README はコードベースの主要ファイルに基づいています。細かい設定や追加のユーティリティは各モジュールの docstring を参照してください。
- 本リポジトリを本番で利用する場合は、運用監視、証跡、テスト、セキュリティ（APIキー管理等）を十分に行ってください。

貢献・問い合わせ
----------------
- バグ報告や改善提案は Issues を立ててください。
- コントリビュート前にコードの意図・設計を Issue/PR で相談していただけるとスムーズです。

以上。必要であれば README に含めるサンプル .env の雛形や CLI の詳細なオプション一覧を追加します。どの情報を追記しますか？