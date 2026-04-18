KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。発注エンジン（ExecutionEngine）、監視用の Monitoring サービス、ポートフォリオ構築・ポジションサイズ算出、研究用ファクター計算、LLM を使ったニュース／レジーム判定などの機能を含みます。設計方針としては以下を重視しています。

- 本番とペーパートレードを明確に分離（DB・モックブローカー等）
- 監視（システム・注文・リスク）によるキルスイッチとアラート
- DuckDB を使った分析・リサーチ処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定（オプション）
- 小さなユーティリティ群（ログ設定、プロセス優先度設定、.env ウィザード等）

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番または paper_trading モードで起動
  - paper_trading モードでは MockBroker を使い data/paper_trading.db に記録
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - system / trade / risk モニタリング、Kill Switch の評価、アラート通知
  - SQLite に監視ログを永続化（init_monitoring_db）
  - ポーリング間隔は環境変数で調整可能
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株処理、aggregate cap）
- 研究（kabusys.research）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリー
  - DuckDB 接続を受け取って純関数的に実行
- AI 系（kabusys.ai）
  - news_nlp.score_news: raw_news を LLM に送り銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime: ETF の MA200 乖離とマクロニュースを LLM で判定して market_regime に書込
- ツール
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - ロギング設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします。
   - 必須（最低限）: duckdb, psutil
   - OpenAI 機能を使う場合: openai
   - YAML 検証を行う場合: PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 初期 .env を作成します（対話式ウィザード推奨）。
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
   - 既に .env を用意している場合はプロジェクトルートに配置してください。
   - 自動ロードはデフォルトで有効です（ルートの .env / .env.local を読み込み）。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証を実行します。
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリを作成（作業環境によっては不要）。
   - デフォルトで使用されるファイル:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (監視 SQLite)
     - data/paper_trading.db (paper_trading 用 SQLite)
     - logs/（ログ出力先）
   - 必要に応じて .env でパスを上書きしてください。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- OPENAI_API_KEY — OpenAI を使う場合に必須（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方（起動例）
----------------
- ExecutionEngine を起動（デフォルトは環境に応じた DB を使用）
  - python -m kabusys.run_execution
  - 注意: 起動前に data/kill.flag が存在すると起動をスキップします。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 停止フラグ: data/stop_requested.flag を作成するとループが終了します。

- 設定ウィザード
  - python -m kabusys.config_setup
  - --env-file で書き込み先を指定可能

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告で終了コード 1 を返す

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

注意点 / 実運用メモ
------------------
- Monitoring の init_monitoring_db は「環境にかかわらず」settings.sqlite_path（本番監視 DB）を使用します。
- Execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使い、本番 DB と分離します。
- Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）を用いて外部から安全に停止できます。
- ログ: utils.logging_setup.setup_logging を全起動スクリプトで利用しており、logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。
- OpenAI を使う機能は API キーが必須です。API 失敗時のフォールバックやリトライロジックを実装していますが、料金・レート制限には注意してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

ディレクトリ構成
----------------
（src/kabusys 以下を基に要約）

- kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / Settings 管理、.env 自動ロード（.git / pyproject.toml をルート探索）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py — ログの統一設定（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py — 監視用 SQLite のスキーマ初期化 + DB ラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文監視ロジック）※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねる実行ループ
    - kill_switch.py — data/kill.flag の管理
    - alert_manager.py — アラート通知（LINE など）※実装ファイルあり

  - execution/
    - execution_engine.py — 発注エンジンコア（EngineConfig, run_session 等）
    - broker_factory.py — ブローカークライアント生成（本番 / モック切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理・整合・リスク管理等

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（lot/aggregate cap 等）
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — momentum / value / volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込み
    - regime_detector.py — マクロ + ETF MA200 からレジーム判定

  - data/ (実行時に生成・使用)
    - *.db（monitoring.db, paper_trading.db, kabusys.duckdb など）
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル

  - tools/
    - paper_verification_report.py — paper_trading の実行結果検証レポート生成スクリプト

拡張・開発メモ
---------------
- DuckDB を用いたリサーチ機能はテーブル（prices_daily / raw_financials / raw_news 等）に依存します。データパイプラインが整っていることを前提としています。
- AI 統合は OpenAI の JSON Mode を想定しており、レスポンスバリデーション・リトライを行います。カスタムモデルや他サービスに変更する場合は ai モジュールの抽象化を検討してください。
- ローカル開発では KABUSYS_ENV=development を使用し、本番（live）では必要な注意（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認）を払ってください。

よくあるコマンドまとめ
---------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper トレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を追加してください）

フィードバックや追加のドキュメント（API リファレンス、アーキテクチャ図、デプロイ手順等）が必要であれば教えてください。README に追記します。