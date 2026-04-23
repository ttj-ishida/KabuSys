README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリは以下を主に提供します。

- 注文実行エンジン（ExecutionEngine）の起動スクリプト
- 監視（Monitoring）コンポーネントとポーリングループ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量探索ユーティリティ（DuckDB ベース）
- AI を用いたニュース NLP（OpenAI API 統合）
- 設定ウィザード / 設定検証用 CLI、各種ユーティリティ

主な設計方針は「本番 DB とペーパートレードを分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的に管理」「監視/アラートで安全停止（Kill Switch）」です。

特徴一覧
--------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録して本番と分離
  - プロセス優先度設定・PID ファイル管理・停止フラグ検知機構を備える
- Monitoring（run_monitoring.py / monitoring package）
  - System / Trade / Risk の各モニタを束ねて定期ポーリング
  - Kill Switch 実装により危険状態で data/kill.flag を生成して Execution を停止
  - SQLite（監視ログ） + DuckDB（分析データ）を使用
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定、等金額/スコア加重配分、リスクベースの株数算出、セクター制限、レジーム乗数
- 研究モジュール（kabusys.research）
  - DuckDB 経由でモメンタム／ボラティリティ／バリュー系ファクター算出、IC 計算、統計サマリー
- AI モジュール（kabusys.ai）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価、マクロセンチメントによるレジーム判定
  - バッチ処理、リトライ、レスポンス検証、DB への冪等書き込みを実装
- ツール
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - ロギング設定（logs/ 日次ローテート）
  - プロセス優先度 / CPU アフィニティ設定
  - 設定（.env）自動読み込み・検証

前提・依存
-----------
- Python 3.10+
  - 型ヒントに '|'（PEP 604）を使用しているため
- 主な外部パッケージ
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（config 検証時に存在すれば YAML ファイルのパース検証を行う）
- DB
  - SQLite（組み込み）
  - DuckDB（分析用ファイル）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を用意してください。

   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要なパッケージをインストールします（最低限）:

   - 例:
     pip install duckdb psutil openai PyYAML

   - 補足:
     - OpenAI を使わないなら openai パッケージは不要。
     - PyYAML は設定ファイル（config/*.yaml）検証を行いたい場合のみ必要。

3. .env の作成（対話式ウィザード推奨）

   - 対話式ウィザードを実行して .env を生成:
     python -m kabusys.config_setup

   - ウィザードで必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）

   - 重要な環境変数の例とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG 等に変更可）
     - OPENAI_API_KEY: OpenAI を使う場合に設定

4. 設定検証（任意）

   - 設定検証を実行:
     python -m kabusys.validate_config
   - 警告を厳密モードで FAIL 扱いにする:
     python -m kabusys.validate_config --strict

5. データディレクトリの準備（必要に応じて）

   - デフォルトで logs/、data/ 等を使用します。自動作成される場面もありますが、権限等に注意してください。

使い方（主要スクリプト）
-----------------------
- ExecutionEngine 起動（実際の取引またはペーパートレード）
  - 起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV による挙動:
    - paper_trading: MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離
    - live: 本番ブローカーを使う（設定を十分に確認してください）

  - 起動時の動作:
    - process priority を "high" に設定し、PID ファイル（デフォルト data/execution.pid）を書きます
    - data/stop_requested.flag を検知すると安全に停止します

- Monitoring 起動
  - 起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔:
    - デフォルト 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依らない）
  - 実行中に data/stop_requested.flag を作成するとループを終了します

- 環境設定ウィザード（.env 作成）
  - 実行:
    python -m kabusys.config_setup

- 設定検証
  - 実行:
    python -m kabusys.validate_config
  - --strict を指定すると警告があると exit 1 になります

- Paper Trading 検証レポート
  - 実行:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH を利用可能

- AI モジュール利用（ニューススコア / レジーム判定）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY を設定するか、各関数に api_key 引数を渡す
  - 例（DuckDB コネクションを渡して呼ぶ）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

注意点（運用上）
----------------
- Kill Switch: RiskMonitor が条件を満たすと KillSwitch が data/kill.flag を書き、Execution 側が停止します。
- データ鮮度・監視: SystemMonitor は DuckDB の prices_daily などを参照してデータ鮮度を判定します。
- ログ: デフォルトは logs/ に日次ローテーションで出力されます（ログファイル名は起動時の app_name、例: logs/execution.log）。
- 自動 .env 読み込み: 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KILL_FLAG_CLEAR_ON_START: 本番でこれを 1 に設定すると起動時に kill.flag を自動クリアしますが、本番では通常 0 を推奨します。

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル・ディレクトリと簡単な説明）

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数の読み込み・Settings クラス（各種パス・閾値などの取得）

- config_setup.py
  - .env を対話的に作成するウィザード

- validate_config.py
  - 起動前に環境設定や config/*.yaml を検証する CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度、DB 接続、スレッド実行、停止フラグ検知）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔指定可能）

- execution/ (ディレクトリ)
  - 注文実行に関する実装（broker_factory、execution_engine、order_manager、order_repository、reconciler、risk_manager 等）
  - (ソースは本 README には含まれていませんが、run_execution から利用されます)

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と永続化 API（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 発注／約定の健全性チェック（コードベース内にあり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 操作ユーティリティ
  - monitoring_engine.py: 各 Monitor を束ねてポーリング・アラート発報するエンジン
  - alert_manager.py: アラート通知の集約（LINE 等への通知機構）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（等重・スコア重み）
  - position_sizing.py: 株数計算（risk_based / equal / score）
  - risk_adjustment.py: セクター上限適用・レジーム乗数

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン計算 / IC 計算 / 統計サマリー

- ai/
  - news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py: マクロ + ETF MA200 乖離で市場レジーム判定して market_regime に書き込む

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- utils/
  - logging_setup.py: Stream + TimedRotatingFileHandler 設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - （実行時に使用するディレクトリ。デフォルトの SQLite/DuckDB ファイル・PID/flag ファイルなどを置く想定）
  - 例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag

追加情報・開発者メモ
-------------------
- DuckDB 接続オブジェクトを各関数に渡す設計のため、テスト時はメモリ上の DuckDB を作って関数を呼ぶと簡単に検証できます。
- OpenAI 呼び出し箇所はテストしやすいように _call_openai_api をモジュール内で抽象化しており、patch によりモック可能です。
- monitoring_db.init_monitoring_db は冪等でのテーブル作成と、既存 DB に対する簡易マイグレーション（列追加）を行います。

問題が発生したら
----------------
- まず python -m kabusys.validate_config で設定の整合性を確認してください。
- ログは logs/<app_name>.log に出力されます。起動時に logs/ ディレクトリ作成に失敗するとコンソールのみ出力になります。
- AI 関連で API エラーが出る場合は OPENAI_API_KEY の設定とネットワーク接続を確認してください。

ライセンス
----------
- （ここにはプロジェクトのライセンス情報を記載してください。例: MIT ライセンス等）

以上。必要があれば README にサンプル .env、起動例スクリプト、追加の運用手順（systemd unit、cron など）を追記します。どの形式を優先しますか？