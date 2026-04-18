KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。  
主な目的は以下です。

- 日次・オンデマンドのファクタ計算・特徴量探索（research）
- ポートフォリオ構築とポジションサイズ計算（portfolio）
- 発注エンジン（ExecutionEngine）とリスク監視（execution, monitoring）
- Paper Trading 検証・レポート生成（tools）
- ニュース NLP / 市場レジーム判定（AI モジュール: OpenAI を利用）

本リポジトリはモジュール群（src/kabusys 以下）で構成され、CLI スクリプトやライブラリ関数を提供します。

主な機能
--------
- 環境設定ウィザード（.env の作成 / 更新）: kabusys.config_setup
- 設定検証（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト: kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading 用 DB に記録
  - 停止は data/stop_requested.flag によるフラグ検出または monitoring 側の kill.flag による
- Monitoring 起動スクリプト: kabusys.run_monitoring
  - システム監視・トレード監視・リスク監視を定期実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- MonitoringDB（SQLite）によるログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- リスク監視（ドローダウンアラート、ポジション上限監視）と Kill Switch（data/kill.flag）
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ計算）
- Research 用ファクター計算（モメンタム / ボラティリティ / バリュー 等） — DuckDB 使用
- AI モジュール
  - news_nlp: raw_news を OpenAI（gpt-4o-mini 等）でセンチメント評価して ai_scores に保存
  - regime_detector: ETF MA とマクロニュースを組み合せて市場レジーム判定
- Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. リポジトリをクローン、またはソースを配置する。
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（主要な例）:
     - duckdb
     - psutil
     - openai
   - 任意（機能向上）:
     - PyYAML（validate_config が config/*.yaml をパースする場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt が無い場合は上記を手動でインストールしてください。

4. 環境変数 (.env) の作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 自動ロード:
     - デフォルトでプロジェクトルートの .env および .env.local を自動で読み込みます。
     - テスト時などに自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 重要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - paper_trading のとき、発注はモックで data/paper_trading.db を使用
   - OPENAI_API_KEY: news_nlp / regime_detector 実行時に必要
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数）
   - KILL_FLAG_CLEAR_ON_START（本番環境でオンにしないことを推奨）

基本的な使い方
--------------
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）になります。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB にログを残します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動を行いません。

- 監視エンジン起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔秒を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュール（プログラムから使用）
  - ニュース評価:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
    - OPENAI_API_KEY が必要。未設定だと ValueError が発生します。
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

停止・Kill 処理
----------------
- 手動停止（全体／簡易）
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して安全に終了します。
- Monitoring による停止（Kill Switch）
  - monitoring 側の条件（ドローダウンやポジション上限）で data/kill.flag が書き込まれると ExecutionEngine に停止シグナルが送られます。
  - KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に自動クリアされますが、本番では無効 (0) を推奨します。

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます（logs/ ディレクトリ）。
- setup_logging(app_name="execution" または "monitoring") を各スクリプトから呼び出して統一的に設定されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定します。

注意点 / トラブルシューティング
------------------------------
- OpenAI API
  - news_nlp と regime_detector は OPENAI_API_KEY を要求します。未設定だと例外が発生します。
  - API 呼び出しは再試行やフォールバック（失敗時は安全に継続）を組み込んでいますが、適切なレート制限設定とキーが必要です。
- PyYAML
  - validate_config が config/*.yaml のパースチェックを行うには PyYAML が必要です。未インストール時は YAML 検証はスキップされ、警告が出ます。
- psutil 権限
  - process_priority の設定や CPU affinity の設定は管理者権限が必要になる場合があります。失敗しても警告が出力され動作は継続します。
- DuckDB / SQLite
  - デフォルトの DB ファイルは data/ ディレクトリ下に作成されます。権限やパスに注意してください。
- .env 自動読み込み
  - デフォルトでプロジェクトルートの .env / .env.local を読み込みます。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主なディレクトリ構成
--------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリ（抜粋）です。

- kabusys/
  - __init__.py                            — パッケージ定義（__version__ 等）
  - config.py                              — 環境変数 / 設定取得ロジック（Settings クラス）
  - config_setup.py                         — .env 対話ウィザード
  - validate_config.py                      — 起動前設定検証 CLI
  - run_execution.py                        — ExecutionEngine 起動スクリプト
  - run_monitoring.py                       — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py                           — ニュース NLP（OpenAI 呼び出し、ai_scores 更新）
    - regime_detector.py                    — 市場レジーム判定（ETF MA + マクロニュース）

  - monitoring/
    - monitoring_db.py                      — SQLite のテーブル初期化 / 永続化層（MonitoringDB）
    - system_monitor.py                     — システム監視（CPU/メモリ/データ鮮度）
    - trade_monitor.py                       — トレード監視（trade_logs を監視）※（該当コード参照）
    - risk_monitor.py                       — ドローダウン / ポジション上限監視
    - kill_switch.py                         — kill.flag 書き込みと評価
    - monitoring_engine.py                   — 各 Monitor を束ねるエンジン
    - alert_manager.py                       — （アラート送信を担う想定コンポーネント）

  - execution/
    - execution_engine.py                    — ExecutionEngine （発注セッション管理）
    - broker_factory.py                      — Broker クライアント生成（本番 / mock 切替）
    - order_manager.py                        — 注文管理
    - order_repository.py                     — 発注ログ永続化
    - reconciler.py                           — 注文整合処理
    - risk_manager.py                         — 実行時のリスク管理ロジック

  - portfolio/
    - portfolio_builder.py                   — 銘柄選定、スコア並べ替え
    - position_sizing.py                     — 株数・投下金額計算
    - risk_adjustment.py                      — セクター上限やレジーム乗数

  - research/
    - factor_research.py                     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py                  — 将来リターン計算、IC、統計サマリー

  - tools/
    - paper_verification_report.py           — Paper Trading 検証レポート生成

  - utils/
    - logging_setup.py                       — ログ設定ユーティリティ
    - process_priority.py                    — プロセス優先度・CPU affinity 設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, ... （生成/編集が必要な場合あり）

- data/
  - monitoring.db (default: data/monitoring.db)
  - paper_trading.db (paper_trading 用)
  - stop_requested.flag, kill.flag, execution.pid などのフラグ/制御ファイル

開発メモ / 拡張ポイント
-----------------------
- ポートフォリオの lot_size を銘柄毎に持たせる等、将来的な拡張が設計上考慮されています。
- AI モジュールは API 呼び出し部分をテストでモック可能に設計されています（単体テストしやすい）。
- DuckDB を分析基盤として利用しており、prices_daily / raw_financials / raw_news といったテーブルを想定しています。

ライセンス / コントリビュート
-----------------------------
（ここにプロジェクトのライセンスやコントリビュートに関する案内を追記してください）

最後に
-------
この README はコードベースの主要点をまとめたガイドです。詳細な仕様やアルゴリズム説明（PortfolioConstruction.md など）が別ドキュメントとして存在する想定です。実運用時は config/*.yaml と .env の内容を慎重に確認し、本番（KABUSYS_ENV=live）では特に Kill Switch / LINE 通知設定を事前に整備してください。