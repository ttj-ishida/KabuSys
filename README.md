KabuSys — 日本株自動売買システム（簡易 README）
===========================================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（研究／ポートフォリオ構築／実行／監視／AI 支援）を目的としたコードベースです。本リポジトリは以下の機能群を含み、モジュールを組み合わせて実運用からペーパートレード、研究ワークフローまでカバーします。

主な特徴
--------
- 環境設定管理 (.env 自動ロード / ウィザード)
- 起動前設定検証ツール（validate_config）
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading で MockBroker を使用し、本番 DB と分離
- 監視プロセス（run_monitoring / MonitoringEngine）
  - システム状態、注文ログ、リスク制御、Kill Switch
- ポートフォリオ構築ライブラリ（候補選定、重み計算、ポジションサイジング、セクター制約）
- リサーチ用ファクター計算（momentum / volatility / value 等）
- AI モジュール（ニュース NLP、レジーム判定） — OpenAI API 利用
- ユーティリティ（ロギング設定、プロセス優先度 / CPU affinity）
- 運用ツール（Paper Trading 検証レポート生成スクリプト）

必要な依存（代表）
-----------------
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config yaml の構文チェック時にあると便利）
※ 実行環境に応じて requirements.txt を用意してください（このリポジトリ内には明示的な requirements ファイルがありません）。

環境変数（主要）
----------------
重要な環境変数の一部。詳細は config_setup のウィザードや .env.example を参照してください。
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能で必要）
- PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動します。
2. 仮想環境を作成・有効化（推奨）。
3. 必要パッケージをインストール：
   - 例: pip install duckdb psutil openai pyyaml
   - またはプロジェクト用 requirements.txt を用意して pip install -r requirements.txt
4. 初期設定ファイル (.env) を作成：
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動: .env を作成して必要な環境変数を設定
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. データディレクトリ（data/）やログディレクトリ（logs/）は自動作成されますが、必要に応じて手動で作成してください。

起動・使い方
------------

主なスクリプト（モジュール経由で実行可能）

- 設定ウィザード（.env 生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作中に data/stop_requested.flag が存在すると停止します。
  - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使い、MockBroker を使用（本番 DB と分離）
  - 実行時に data/execution.pid を書きます（PID ファイル）

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 停止は data/stop_requested.flag を作成することで行います
  - 監視は本番の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

運用上の注意
-------------
- Kill Switch:
  - リスク条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。
- ログ:
  - デフォルトで stdout に出力し、logs/<app_name>.log に日次ローテーションで出力します。
  - ログディレクトリは環境変数 LOG_DIR で変更可能。
- Paper Trading:
  - paper_trading 環境では本番 DB を汚さないよう専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。

内部コンポーネント（簡易説明）
------------------------------
- kabusys.config
  - .env 読み込み、自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
  - Settings クラスで環境変数アクセスをラップ
- kabusys.config_setup / kabusys.validate_config
  - 対話式設定生成と起動前検証ツール
- run_execution.py
  - ExecutionEngine の組み立て・起動スクリプト（BrokerFactory, OrderManager, RiskManager, Reconciler 等）
- run_monitoring.py / monitoring/*
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine、kill switch、アラート等
  - monitoring_db.py は SQLite を用いた永続層（テーブル作成・マイグレーション含む）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py：候補選定・重み・サイズ計算・セクター制約等
- research/
  - factor_research.py, feature_exploration.py：DuckDB を使ったファクター計算・IC・統計
- ai/
  - news_nlp.py：ニュースを OpenAI に送り銘柄ごとのセンチメントを取得し ai_scores に書き込む
  - regime_detector.py：ETF の MA 等とマクロ記事を用いて市場レジームを判定し market_regime に書き込む
- tools/
  - paper_verification_report.py：Paper Trading の検証レポートを生成
- utils/
  - logging_setup.py：統一的ログ初期化
  - process_priority.py：OS を抽象化したプロセス優先度 / CPU affinity 設定

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (存在する場合)
- execution/            (ExecutionEngine関連モジュール群)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py

開発・テストのヒント
-------------------
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行われます。テスト環境で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite を使ったデータアクセスは外部 API を必要としないため、ローカルファイルを用意すればリサーチ機能をオフラインで試せます。
- AI 機能は OpenAI API を使用するためテスト時はモック化（unittest.mock.patch）することを推奨します（コード中で _call_openai_api を差し替えられるよう設計済み）。

ライセンス・その他
------------------
- この README はコードから自動的に生成された説明に基づき作成しています。実運用前に config/*.yaml 等の設定や broker 実装、リスクパラメータを必ず確認してください。

お問い合わせ / 追加ドキュメント
----------------------------
さらに詳細な設計や仕様（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクト内にある想定です。それらを参照してアルゴリズムやパラメータの根拠を確認してください。必要であれば README を拡張して起動例・設定例を追加します。