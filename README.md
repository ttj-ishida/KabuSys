README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能が含まれます。

- 売買 ExecutionEngine（本番 / ペーパートレード切替対応）
- 監視（System / Trade / Risk）コンポーネントと Kill Switch
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ計算）
- リサーチ用ファクター計算（momentum / volatility / value 等）
- ニュース NLP を用いた銘柄センチメント評価（OpenAI 経由）
- 実行支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

主な設計方針は「フェイルセーフ」「ルックアヘッドバイアス排除」「本番とペーパートレードの分離」です。

機能一覧
--------
- 環境設定ウィザード（config_setup.py）: 対話式で .env を生成・更新
- 設定検証 CLI（validate_config.py）: .env および config/*.yaml の基本チェック
- ExecutionEngine 起動スクリプト（run_execution.py）:
  - KABUSYS_ENV により本番 / paper_trading を切替
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用
  - 停止は data/stop_requested.flag / data/kill.flag で制御
- Monitoring（run_monitoring.py / monitoring モジュール）:
  - System / Trade / Risk の定期チェック、アラート送出、Kill Switch 評価
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト 60 秒）
- Portfolio モジュール:
  - 銘柄選定（select_candidates）、重み計算（等配分・スコア重み）
  - セクター制約適用、レジーム乗数、ポジションサイズ算出
- Research モジュール:
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）や統計サマリ
- AI モジュール:
  - news_nlp: OpenAI を利用したニュースセンチメント集約・ai_scores への書込み
  - regime_detector: ETF 1321 の MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール:
  - paper_verification_report: ペーパートレード結果の検証レポート出力

前提・依存
-----------
主な依存ライブラリ（環境によっては追加でインストールしてください）:
- python >= 3.9
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の詳細検証を行う場合、必須ではない）

インストール例:
- 仮想環境作成: python -m venv .venv && source .venv/bin/activate
- 必要パッケージをインストール: pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo> && cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows (PowerShell): .venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. 環境変数を用意（.env）
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照して必要な値を設定）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

重要な環境変数
---------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

（AI 機能を使う場合）
- OPENAI_API_KEY

主要な任意 / 設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視用フラグ制御

使い方（実行例）
----------------

1) 環境設定ウィザード（.env 作成）
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いになります:
  - python -m kabusys.validate_config --strict

3) ExecutionEngine を起動
- 本番（KABUSYS_ENV=live）または開発（.env による）に従って動作します。
- 実行:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると実行ループが検出して停止します。
  - kill.flag は KillSwitch のトリガーとして ExecutionEngine に停止命令を出すために監視側が書き込むことがあります。

4) Monitoring を起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL (秒) でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6) AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を設定してから、各モジュールの関数を呼ぶ:
  - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date)
- これらは DuckDB 接続と target_date を受け取り、ai_scores / market_regime などのテーブルへ結果を書き込みます。

停止・安全機構
--------------
- data/stop_requested.flag: run_execution / run_monitoring のポーリングループ停止に使用
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine を停止させるための信号となる
- KILL_FLAG_CLEAR_ON_START 環境変数: 起動時に kill.flag を自動でクリアするかのフラグ（本番では 0 推奨）

ログ
----
- デフォルトは logs/<app_name>.log に日次ローテートで出力（30 日保持）
- setup_logging() はルートロガーを初期化し、stdout（コンソール）とファイルにログを出します
- ログレベルは .env の LOG_LEVEL あるいは setup_logging の引数で制御できます

ディレクトリ構成（主要ファイル）
-----------------------------
以下は主要なモジュールと簡単な説明です（パッケージは src/kabusys 以下）。

- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数の読み込み・ラッパー Settings（.env 自動ロード機能あり）
- config_setup.py
  - .env の対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py: SQLite による監視ログ永続化層
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py:（取引監視、ファイル内に実装あり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の作成 / 管理
  - alert_manager.py:（アラート送信の抽象化）
  - monitoring_engine.py: 各モニタを束ねるエンジン
- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など（実行コンポーネント）
- portfolio/
  - portfolio_builder.py: 銘柄選定・重み計算
  - position_sizing.py: 発注株数算出
  - risk_adjustment.py: セクター制限・レジーム乗数
- research/
  - factor_research.py: momentum/volatility/value 等
  - feature_exploration.py: 将来リターン / IC / 統計
- ai/
  - news_nlp.py: ニュースからの銘柄センチメント算出（OpenAI）
  - regime_detector.py: 市場レジーム判定（ETF MA + LLM）
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成
- utils/
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番 DB / 実際の発注が行われます。設定や権限を厳重に管理してください。
- .env は機密情報を含むため Git 等に絶対にコミットしないでください（config_setup でも注意喚起あり）。
- AI 機能は外部 API（OpenAI）に依存します。APIキー、レート制限、コストに注意してください。
- Monitoring は本番 sqlite_path を使って監視データを記録します（監視は本番 DB と分離されません）。ペーパートレードは paper_sqlite_path を使用して分離されます。

開発・拡張
-----------
- DuckDB のテーブル設計（prices_daily / raw_financials / raw_news 等）に従ってデータを投入することで research / ai 機能をローカルで検証できます。
- テストや CI で自動環境ロードを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モジュール設計は依存注入（DuckDB 接続や BrokerClient）で疎結合化されています。モックを用いた単体テストが容易です。

ライセンス・貢献
----------------
（リポジトリに LICENSE があればここに記載してください）

お問い合わせ
------------
実行・設定に関する質問やバグ報告はリポジトリの issue にお願いします。

--- End of README ---