KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視機能を備えた軽量なシステムです。  
主なモジュールは発注実行（ExecutionEngine）、監視（Monitoring）、ファクター計算／研究（Research）、ポートフォリオ構築（Portfolio）、および AI を使ったニュース解析（AI）です。  
このリポジトリは純粋関数群／DBアクセス層／起動スクリプトを含み、ローカル開発からペーパートレード、本番運用まで想定した設計になっています。

主な特徴
--------
- ExecutionEngine
  - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）の切替対応
  - paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- Monitoring（System / Trade / Risk）
  - 定期ポーリングでシステム稼働状況、データ鮮度、滞留注文、ドローダウン等を監視
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
- Portfolio construction
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム対応
- Research
  - DuckDB を用いたファクター（Momentum / Value / Volatility 等）計算、将来リターン・IC 計算
- AI モジュール
  - OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価および市場レジーム判定
  - API 呼び出しは堅牢なリトライ／バリデーション実装
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード & 設定検証 CLI
- ツール
  - Paper Trading の検証レポート生成スクリプト

セットアップ
-----------
前提（推奨）
- Python 3.9+
- sqlite3 (標準ライブラリ)
- システムにより追加のネイティブ依存が必要な場合があります（psutil 等）

必須 Python パッケージ（例）
- duckdb
- psutil
- openai  （AI 機能を使う場合）
- PyYAML （config の YAML 検証を使う場合、任意）

インストール例（仮想環境推奨）
- pip install duckdb psutil openai PyYAML

.env の準備
- 対話式ウィザードで作成できます:
  - python -m kabusys.config_setup
- 主要な環境変数（最低限設定が必要なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - LOG_LEVEL（例: INFO、デフォルト: INFO）

設定の検証
- .env を作成したら設定検証を実行:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

使い方（起動例）
----------------

メインスクリプト（モジュール実行形式）:
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - 実行中は data/execution.pid に PID を書きます
    - 停止: data/stop_requested.flag が存在すると起動ループが終了します（外部で作成可能）
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルト 60 秒間隔で SystemMonitor 等をポーリング
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（SQLITE_PATH）を使用します

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config

Kill Switch / 停止フラグ
- KillSwitch は risk / system / trade の評価に基づき data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- 実行スクリプト側の外部停止フラグ（run_execution / run_monitoring）が検知するフラグは data/stop_requested.flag（プロジェクトルート data ディレクトリ内）です
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアしますが、本番では 0 を推奨します

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一的に構成されます
  - 標準出力（stdout）と日次ローテート（logs/<app_name>.log、30日保持）
  - LOG_DIR を指定してログの出力先を変更できます

AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数）
- API 呼び出しに対して堅牢なリトライ・レスポンス検証を実装しています
- AI モジュール:
  - kabusys.ai.news_nlp.score_news
  - kabusys.ai.regime_detector.score_regime

注意点 / 運用メモ
----------------
- Monitoring は監視用の SQLite（SQLITE_PATH）を使用します。Monitoring DB には system_status / trade_logs / positions / risk_logs / dashboard テーブルを自動作成・マイグレーションします。
- run_monitoring は MONITOR_POLL_INTERVAL を使ってポーリング間隔を制御できます（デフォルト 60 秒）。0 以下や無効な値は無視されデフォルトにフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading で専用 DB を使い本番 DB と分離します。実運用時は KABUSYS_ENV=live を注意深く設定してください（validate_config がハイライトします）。
- process_priority: 起動時にプロセス優先度を "high" に設定しようとしますが、権限やプラットフォームにより設定に失敗する場合があります（ログに警告）。

主要ファイル / ディレクトリ構成
----------------------------
（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込みロジック（Settings クラス）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（監視用）
    - monitoring_engine.py          — 各モニタを束ねるエンジン
    - system_monitor.py             — システム状態・データ鮮度監視
    - trade_monitor.py              — （実装あり）注文滞留・異常検出
    - risk_monitor.py               — ドローダウン・ポジション数監視
    - kill_switch.py                — Kill Switch ロジック
    - alert_manager.py              — アラート送信（LINE 等、実装に依存）
  - execution/
    - execution_engine.py           — ExecutionEngine 本体
    - broker_factory.py             — Broker クライアント生成（Mock/実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
  - data/ (実行時に使用するファイル群)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid

よくある操作例
---------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ペーパートレードの検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 監視プロセス起動（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

トラブルシューティング（簡易）
-----------------------------
- DB が作られない／ファイルパーミッション
  - data ディレクトリが存在するか、またはプロセスの書き込み権限を確認してください。
- OpenAI 呼び出しでエラーが出る
  - OPENAI_API_KEY が設定されているか確認、ネットワークや API レート制限に注意
- ログが出力されない／ファイルに書けない
  - LOG_DIR 環境変数や logs ディレクトリのパーミッションを確認。ログディレクトリ作成に失敗するとコンソール出力のみになります。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

最後に
------
この README はコードベースの主要機能・起動方法を簡潔にまとめたものです。詳細な設計やアルゴリズム（PortfolioConstruction.md や StrategyModel.md 等）が別途あることを想定しています。追加の運用手順や環境固有の調整は運用ドキュメントに追記してください。