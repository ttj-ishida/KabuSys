KabuSys
=======

概要
----
KabuSys は日本株の自動売買システム向けユーティリティ群・ライブラリ群の集合です。  
このリポジトリには、以下の主要機能を提供するモジュール群が含まれます。

- 注文実行エンジン起動スクリプト（ExecutionEngine 起動）
- 監視デーモン（System / Trade / Risk の監視および Kill Switch）
- 環境設定ウィザード（.env 作成）と設定検証ツール
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- リサーチ（ファクター計算、特徴量解析）
- AI 補助（ニュース NLP による銘柄センチメント、レジーム判定）
- ペーパートレード検証レポート生成スクリプト

各モジュールはできるだけ副作用を少なくし、DB／API へのアクセスは明示的に分離する設計になっています。

主な機能一覧
--------------
- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db を利用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可、デフォルト 60 秒）
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成/更新
  - validate_config.py: .env と config/*.yaml の簡易検査（--strict オプションで警告も失敗扱い）
  - Settings クラス: 環境変数アクセスラッパ（デフォルト値、型チェック、セーフガードを内蔵）
- 監視（monitoring パッケージ）
  - system_monitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度チェック
  - trade_monitor: 注文ログの滞留・約定異常等の検出（実装参照）
  - risk_monitor: ドローダウン・保有数上限監視、ダッシュボード更新、risk_logs 出力
  - kill_switch: 条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止させる
  - monitoring_db: SQLite に対するテーブル作成・読み書きユーティリティ（冪等）
  - monitoring_engine: 各 Monitor を束ねてポーリング、アラート通知フックを呼ぶ
- ポートフォリオ（portfolio パッケージ）
  - 銘柄選定（select_candidates）、等重/スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイジング（calc_position_sizes）: risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリング等
  - セクター上限フィルタ（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）
- リサーチ（research パッケージ）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - DuckDB を用いた集計処理を想定
- AI（ai パッケージ）
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を使って銘柄ごとのニュースセンチメントを算出し ai_scores テーブルへ書き込む（バッチ処理・リトライ・検証ロジックあり）
  - regime_detector.score_regime: ETF（1321）MA200 乖離＋マクロニュースセンチメントを合成して market_regime に書き込む
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）、合否判定の閾値を定義

セットアップ手順
----------------
前提
- Python 3.10+（型アノテーションに Path | None などを使用）
- 必要な外部ライブラリ（実行する機能により変わる）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合に必要）
  - （実行時に必要な他ライブラリは各機能に依存）

推奨手順（ローカル開発）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （requirements.txt があれば pip install -r requirements.txt を使用）

3. .env を作成
   - python -m kabusys.config_setup
     - 対話式ウィザードで J-Quants トークン、KABU API パスワード等を設定します。
     - 生成された .env は Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 本番稼働前は --strict モードで警告も FAIL として検査することを推奨します:
     - python -m kabusys.validate_config --strict

使い方
------
環境変数の主なキー（.env に設定）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト 60）

起動スクリプト例
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path（data/paper_trading.db）を使います。本番環境と DB を分離できます。

- 監視デーモンを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # ポーリング間隔を 30 秒に変更

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

ログ・プロセス管理
- ロギングは kabusys.utils.logging_setup.setup_logging により統一管理されます。デフォルトは標準出力と logs/<app_name>.log（日次ローテーション、30日保持）。
- 起動スクリプトは起動直後にプロセス優先度を set_process_priority("high") で上げようとします（psutil の権限に依存して失敗する場合は警告）。

Kill Switch / 停止フラグ
- data/kill.flag により ExecutionEngine 停止を指示する設計（KillSwitch がフラグファイルを書き込みます）。
- run_execution.py/run_monitoring.py は data/stop_requested.flag（または _STOP_FLAG）を監視して終了する仕組みを持っています。

データベース
- monitoring_db.init_monitoring_db で必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等に作成します。既存スキーマのマイグレーション（カラム追加）ロジックも一部含まれます。

重要な実装上の挙動（抜粋）
- run_monitoring.py: Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番パス）を使用します。MONITOR_POLL_INTERVAL 環境変数で間隔変更可。停止は data/stop_requested.flag を用いる。
- run_execution.py: KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して DB を分離。BrokerClientFactory がブローカークライアントを返します。
- news_nlp.score_news: OpenAI API（gpt-4o-mini）を用いてニュースを銘柄別にスコアリング。バッチ、トリム、リトライ、レスポンス検証を行い ai_scores に書き込みます。
- regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュース LLM スコアで regime_label を計算・永続化します（フェイルセーフで macro_sentiment=0.0 を許容）。

ディレクトリ構成
----------------
（抜粋 — 主要ファイル・サブパッケージ）
- src/kabusys/
  - __init__.py
  - config.py                    # Settings / 環境変数読み込みロジック
  - config_setup.py              # .env 対話ウィザード
  - validate_config.py           # 設定検証 CLI
  - run_execution.py             # ExecutionEngine 起動スクリプト
  - run_monitoring.py            # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py        # （実装参照）
    - kill_switch.py
    - alert_manager.py        # （実装参照）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                 # Execution 関連（Engine, risk manager, order manager, broker_factory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - data/                      # 実行時に生成される可能性のあるディレクトリ（SQLite / flag / pid 等）
  - config/                    # 設定テンプレート（system_config.yaml 等）

注意事項 / 運用上のポイント
----------------------------
- .env は機密情報を含むため Git 等にコミットしないこと。
- KABUSYS_ENV を "live" に設定する前に validate_config.py で全ての設定を慎重に確認してください（本番では LINE 通知や Kill Switch の設定が重要です）。
- OpenAI API を利用する機能は API キーとコストに注意して利用してください。API 呼び出しはリトライやフェイルセーフを実装していますが、予期しない挙動の可能性は常にあります。
- DuckDB / SQLite のパスは必要に応じて .env で指定してください。ペーパートレードは専用 DB に分離することを強く推奨します。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理されています（現状: 0.1.0）。
- ライセンス情報はリポジトリルートの LICENSE 等を参照してください（本 README には含まれていません）。

フィードバック・貢献
-------------------
バグ修正や改善提案は issue/pull request を通じて歓迎します。各モジュールは単体テストを書きやすいように設計されているため、ユニットテストの追加を歓迎します。