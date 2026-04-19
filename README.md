KabuSys — 日本株自動売買システム
=========================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。シグナル生成・ポートフォリオ構築・発注（本番 / ペーパートレード）・監視・リスク管理・研究（ファクター計算）・ニュース NLP（LLM を利用したセンチメント評価）など運用に必要な機能群を提供します。設計方針としては、ルックアヘッドバイアス回避、DB（SQLite/DuckDB）中心のデータ管理、フェイルセーフな外部 API 呼び出しを重視しています。

主な機能
-------
- 環境設定ウィザード（.env の対話式作成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替、MockBroker 利用）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合、専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全に分離します
- Monitoring（System / Trade / Risk の監視）: run_monitoring.py、MonitoringEngine、KillSwitch
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 停止は data/stop_requested.flag / data/kill.flag によるフラグ管理
- 監視ログ永続化（SQLite）: monitoring_db モジュール（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築ユーティリティ（銘柄選定、重み計算、ポジションサイジング、セクター制限、レジーム調整）: kabusys.portfolio
- 研究用モジュール（ファクター計算、forward returns、IC、統計サマリ）: kabusys.research（DuckDB を利用）
- ニュース NLP（OpenAI を利用した銘柄ごとのセンチメントスコア）: kabusys.ai.news_nlp
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコア合成）: kabusys.ai.regime_detector
- ユーティリティ: ロギング設定、プロセス優先度 / CPU affinity 設定

セットアップ
------------
1. Python 環境
   - Python 3.9+ を推奨します（プロジェクトの pyproject.toml に準拠してください）。
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表例）
   - pip install duckdb psutil openai
   - PyYAML は config/*.yaml の検証を行う場合に必要: pip install PyYAML
   - 実際の運用用の追加パッケージやバージョンはプロジェクトの管理ファイルを参照してください。

3. 初期設定（.env 作成）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定例:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1) になります。

ログとデータファイル
- DuckDB デフォルト: data/kabusys.duckdb
- SQLite 監視 DB デフォルト: data/monitoring.db
- ペーパートレード SQLite デフォルト: data/paper_trading.db
- PID / フラグファイル:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（run_*.py の外部停止用フラグ）
  - data/kill.flag（KillSwitch が ExecutionEngine 停止を指示するためのファイル）
- ログ:
  - logs/<app_name>.log（日次ローテーション、デフォルト保存 30 日）

使い方（主なコマンド）
-------------------
- 環境設定ウィザード（.env を作る）
  - python -m kabusys.config_setup
  - オプション: --env-file PATH（保存先指定）

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- ExecutionEngine（トレード実行）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB に記録します
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します
    - 実行中に stop フラグが作成されるとエンジンを停止します

- Monitoring（システム・約定・リスクの監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境に依存せず本番 DB を監視する設計）

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- ニュース NLP / レジーム判定等は各モジュールを import して利用（スクリプト化して呼び出す想定）
  - OpenAI API を使う機能は OPENAI_API_KEY を環境変数に設定するか、関数引数で渡します。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用デフォルト data/paper_trading.db)
- LOG_LEVEL (デフォルト INFO)
- OPENAI_API_KEY (AI モジュール利用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数上書き)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します

設計・運用上の注意
------------------
- run_monitoring は監視専用の DB に書き込みを行います。監視は本番 sqlite_path を参照するため、監視/実行 DB の混同に注意してください（paper_trading モードでは Execution は paper DB を使いますが、Monitoring は常に sqlite_path を参照します）。
- KillSwitch はリスクアラート（ドローダウン・ポジション上限）を検出すると data/kill.flag を書き込みます。ExecutionEngine 起動時に kill flag の自動クリア挙動は KILL_FLAG_CLEAR_ON_START で制御されます（本番では 0 推奨）。
- OpenAI など外部 API 呼び出しはリトライとフェイルセーフを備えていますが、API キーやコストに注意してください。
- DuckDB を用いたファクター計算や研究用処理はローカルの prices_daily / raw_financials 等のテーブルを前提としています。データ投入 / スキーマに注意してください。
- ロギングは kabusys.utils.logging_setup.setup_logging で統一して設定してください（全起動スクリプトが利用）。

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py          — SQLite 監視 DB 用の永続化層
    - system_monitor.py         — システム状態 / データ鮮度監視
    - trade_monitor.py          — （約定監視・滞留注文検知 等）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag の書き込みロジック
    - monitoring_engine.py      — 各モニタの統合ポーリング
    - alert_manager.py          — （通知管理：LINE など）※実装に依存
  - execution/
    - execution_engine.py       — ExecutionEngine（発注セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py        — momentum / volatility / value 等
    - feature_exploration.py    — forward returns / IC / summary
  - ai/
    - news_nlp.py               — ニュースを LLM でスコアリング
    - regime_detector.py        — マクロ + MA200 合成でレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py          — 共通ログセットアップ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定
  - data/                       — デフォルトの DB・PID・フラグファイル格納場所（実行時に生成）
  - config/                     — YAML 設定テンプレート（system_config.yaml 等）

サンプルワークフロー
-------------------
1. 仮想環境を用意し依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で検証
4. (必要ならデータ投入: DuckDB / SQLite に価格・財務データ等をロード)
5. 監視を起動:
   - python -m kabusys.run_monitoring
6. 実トレード/ペーパーを起動:
   - python -m kabusys.run_execution

追加情報 / 参考
----------------
- 各モジュールは docstring に設計方針や注意点が詳述されています。実運用では README の補助として該当ソースの docstring を参照してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup でも警告あり）。
- OpenAI やブローカー API の利用は、それぞれの利用規約・鍵管理・コスト制御を十分に行ってください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください（存在する場合）。

問題報告 / コントリビュート
---------------------------
不具合報告や改善提案は issue を作成してください。拡張やテストの追加は歓迎します。設計方針に反する重大な変更は事前にディスカッションしてください。

以上。必要であれば README を英語版に翻訳したり、セットアップ手順を CI / Docker 化したサンプルを追加で作成します。どの項目を詳しく拡張しますか？