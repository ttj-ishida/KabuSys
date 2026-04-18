README
=====

概要
----
KabuSys は日本株向けの自動売買／バックテスト／リサーチ基盤を想定した Python パッケージです。本リポジトリには以下の機能群が含まれており、実取引（kabuステーション）やペーパートレード、監視・アラート、ファクター計算、ニュース NLP によるスコアリングなどを統合的に扱える設計になっています。

主なポイント
- 実行環境切替（development / paper_trading / live）
- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- Paper trading 用の DB 分離（data/paper_trading.db）
- DuckDB を用いた研究／ファクター計算
- OpenAI を使ったニュースセンチメント評価（AI モジュール）
- ログは stdout と日次ローテートファイルの両方に出力

機能一覧
-------
主な機能（抜粋）：

- 実行関連
  - 実行エンジン起動スクリプト: run_execution (python -m kabusys.run_execution)
  - 発注管理、リスク管理、再整合処理（ExecutionEngine 周辺。BrokerFactory により実ブローカー／モックを切替）

- 監視関連
  - run_monitoring: SystemMonitor を定期ポーリングして system_status 等を記録
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねてアラートや KillSwitch を評価
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を永続化

- ポートフォリオ構築
  - 銘柄選定・重み計算（equal / score）
  - セクター集中除外（apply_sector_cap）
  - ポジションサイズ計算（lot 単位、リスクベース・等分配など）

- リサーチ（DuckDB ベース）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、特徴量サマリ

- AI（OpenAI）
  - ニュース NLP（news_nlp.score_news）: 記事を集約して LLM に投げ、銘柄ごとに -1.0〜1.0 のスコアを ai_scores テーブルへ保存
  - レジーム判定（regime_detector.score_regime）: MA200 乖離＋マクロニュースセンチメントで日次レジームを判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

前提・依存
---------
最低限の依存（代表例）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合）

（実際の requirements.txt は本リポジトリに含まれていないため、用途に応じて必要パッケージをインストールしてください。）

セットアップ手順
------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）。
   - pip install duckdb psutil openai pyyaml

3. データディレクトリを作成（自動作成されることもありますが念のため）。
   - mkdir -p data logs

4. 環境変数設定（.env）を作成します。
   - python -m kabusys.config_setup
     → 対話式ウィザードで .env を生成できます。

必須環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（J-Quants API 用）
- KABU_API_PASSWORD（kabuステーション API 用）

主な任意/上書き可能変数
- KABUSYS_ENV: execution の動作モード（development / paper_trading / live）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）, run_monitoring 用、デフォルト 60）

自動 .env ロード順
- OS 環境変数（最優先）
- .env.local（存在すれば）
- .env

この自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます。

使い方
-----

設定検証・ウィザード
- .env を作成 / 更新（対話）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit 1）

起動スクリプト
- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。停止は data/stop_requested.flag を置くか Kill Switch により data/kill.flag が書き込まれます。実行中は PID ファイル（デフォルト data/execution.pid）が作成されます。

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - run_monitoring は Monitoring 用に本番 sqlite_path を使用します（環境にかかわらず monitoring DB は同じパスを使用する設計）。

停止制御（Kill / Stop）
- data/kill.flag: KillSwitch が書き込むファイル（ExecutionEngine に停止シグナルを送る）
- data/stop_requested.flag: run_execution / run_monitoring がループ中に検知すると安全終了するための外部停止フラグ

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）

プログラム API（例）
- ニュース NLP（スコア生成）をプログラムから呼ぶ例:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

- ポートフォリオヘルパ:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

ログ設定
-------
- ログは stdout（StreamHandler）に出力され、さらに logs/<app_name>.log に日次ローテートで保存されます（ログは最大 30 日分保持）。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。
- ログディレクトリは LOG_DIR 環境変数、またはデフォルト logs/ を使用します。

ディレクトリ構成
--------------
以下は本リポジトリの主要ファイル／ディレクトリ（src/kabusys 以下）です。実際のツリーは追加モジュールや未表示ファイルがある場合があります。

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数管理・自動 .env ロード
  - config_setup.py            # .env 対話ウィザード
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              # ニュースセンチメント（OpenAI）
    - regime_detector.py       # 市場レジーム判定（MA200 + マクロ LLM）
  - monitoring/
    - monitoring_db.py         # SQLite スキーマと DB ラッパー
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py         # （ファイルは本 README 提供分に含まれている想定）
    - kill_switch.py
    - alert_manager.py         # （アラート送信ロジック）
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
  - execution/                  # 実行エンジン周辺（ブローカー、order_manager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                       # データ周り（prices, raw_financials 等の処理）※参照箇所あり
  - strategy/                   # 戦略関連（存在する場合）
  - monitoring/                 # 上述

補足・運用上の注意
----------------
- KABUSYS_ENV=live を使用する際は特に注意してください。本番環境では実際に発注が行われます。validate_config の注意文を必ず確認してください（LINE 通知設定や Kill Switch 設定が本番向けになっているか等）。
- OpenAI API を使用する機能は API 料金・レート制限に影響されます。API キーは厳重に管理し、必要に応じてバッチ頻度やチャンクサイズを調整してください。
- run_execution と run_monitoring は外部の stop フラグファイル（data/stop_requested.flag）を参照して安全終了します。自動化スクリプトやデプロイツールから停止を行う場合はこのファイルを利用してください。
- DuckDB / SQLite のパスは環境変数で上書きできます。Paper trading 用 DB は本番 DB と分離するため、KABUSYS_ENV=paper_trading の場合は paper 用 DB が使用されます。

ライセンス・貢献
----------------
本 README はコードベースの簡易ドキュメントです。実際の LICENSE ファイルやコントリビューションガイドラインがある場合はそれに従ってください。

最後に
-----
この README はリポジトリ内の主要モジュールと使い方をまとめたものです。細かい実装や追加の CLI / 設定はソースコードの docstring / コメントを参照してください。必要であれば、インストール手順や運用手順（systemd / supervisor / cron での運用例）などの具体例も追記できます。