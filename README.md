KabuSys — 日本株自動売買システム
===============================

このリポジトリは日本株向けの自動売買／研究／監視ツール群を含む内部ライブラリ群です。
README はコードベースから主要機能・使い方・セットアップ手順を抜粋してまとめたものです。

本文は日本語です。

概要
----
KabuSys は次のような機能を持つ小規模な自動売買フレームワークです。

- シグナル生成・ポートフォリオ構築・ポジションサイジングの純粋関数群（研究用/生成器）
- ExecutionEngine（発注実行）の起動スクリプト（本番 / ペーパートレード両対応）
- Monitoring（システム状態・注文状態・リスク監視）と Kill Switch による緊急停止
- AI を用いたニュースセンチメント評価 / レジーム判定（OpenAI）
- DuckDB / SQLite を用いたデータ保存・分析
- 環境設定ウィザード .env 作成 / 設定検証ツール

主な機能一覧
-------------
- execution
  - ExecutionEngine 起動（run_execution.py）
  - Broker クライアントの抽象化（本番・Mock 両対応）
  - Order 管理・リスク管理・再整合化（reconciler）
- monitoring
  - SystemMonitor：CPU/メモリ/Disk、プロセス存否、データ鮮度の監視
  - TradeMonitor：注文滞留・約定異常の検出（ソース内に実装あり）
  - RiskMonitor：ドローダウン／保有数上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記を定期実行しアラート送信
  - 永続化：SQLite を使った monitoring DB（monitoring_db.py）
- research / portfolio
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索（forward returns / IC / summary）
  - ポートフォリオ構築：候補選定、重み算出、セクター制約、ポジションサイズ算出
- ai
  - news_nlp.score_news：OpenAI を用いたニュースセンチメント集計・書き込み
  - regime_detector.score_regime：ETF とマクロニュースを組み合わせたレジーム判定
- tools
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.9+ を想定（プロジェクトの pyproject / requirements を参照してください）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - （PyYAML は設定検証で任意）

1. リポジトリ取得
   git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は duckdb, psutil, openai などを個別にインストール）

4. .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（下の「主要な環境変数」を参照）

5. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります:
   python -m kabusys.validate_config --strict

6. データディレクトリ準備
   - デフォルトの SQLite / DuckDB は data/ 以下に作成されます。必要に応じて .env でパスを上書きしてください。
   - logs/ ディレクトリはログ出力先（自動作成されます）。

主要な環境変数（代表）
---------------------
（.env には機密情報を含むため Git 管理しないでください）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabus API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使い data/paper_trading.db を利用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方・実行例
---------------
- 環境設定ウィザード（.env を作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - run_monitoring は monitoring DB に接続する際、KABUSYS_ENV にかかわらず本番 sqlite_path を使用します
  - 終了は Ctrl+C またはプロジェクトルート/data/stop_requested.flag を作成

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、paper_trading DB に記録します
  - run_execution は data/stop_requested.flag を検知すると安全に停止します
  - 実行中に強制停止させたい場合は data/kill.flag に理由を書き込みます（KillSwitch による処理）

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB のパスは --db で指定するか PAPER_TRADING_SQLITE_PATH 環境変数で指定

- AI 機能（プログラムから呼び出す例）
  from kabusys.ai import score_news
  score_news(conn, target_date, api_key="sk-...")

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。
- アプリ起動時に setup_logging(app_name=...) が呼ばれます。
- 失敗時もコンソール（stdout）に出力されます。

安全停止とフラグファイル
----------------------
- 停止リクエスト（監視・実行共通）:
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在するとループを終了）
- Execution 停止（Kill Switch）:
  - data/kill.flag — KillSwitch により作成される。ExecutionEngine は起動時にこのフラグの存在を確認するか、実行中に kill.flag を検出すると停止するよう設計されています。
- 注意: KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に自動クリアされます（本番では推奨しません）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下はソースディレクトリ src/kabusys の主要ファイルと役割です（抜粋）：

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・Settings ラッパー
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI
- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループの起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite による永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- src/kabusys/research/
  - factor_research.py, feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py, regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py

設計上のポイント / 注意点
------------------------
- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env/.env.local を自動読み込みします（OS 環境変数を優先）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DB の分離:
  - monitoring は常に Settings.sqlite_path（本番用）を参照しますが、Execution は paper_trading 時に paper_sqlite_path を使用して本番 DB から分離します。
- AI モジュール:
  - OpenAI API を使用するため OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフを備えていますが、API 利用料に注意してください。
- process priority:
  - 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（psutil 使用）。権限不足などで失敗する場合はログに警告が出ます。
- DuckDB / SQLite:
  - DuckDB は解析用途のためのファイル（デフォルト data/kabusys.duckdb）
  - monitoring 用の SQLite は data/monitoring.db（自動でテーブルを作成します）
- テスト性:
  - 多くのモジュールで依存注入（conn、client、api_key など）を受け取る設計であり、ユニットテストやモックがしやすくなっています。

よくあるコマンド一覧
-------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- ペーパー検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

さらに詳しく
-------------
プロジェクト内のドキュメント（PortfolioConstruction.md、StrategyModel.md など）が参照可能であれば、各モジュールの実装方針や数式の根拠が記載されています。コード内の docstring は詳細な挙動や注意点を説明しているため、実運用や拡張を行う際はソースコードの docstring を参照してください。

貢献・ライセンス
----------------
リポジトリの CONTRIBUTING / LICENSE ファイルに従ってください（なければプロジェクト管理者に確認してください）。

---

この README はコードベースの主要点を要約したものです。追加で「導入手順（例: systemd / supervisor 用の起動設定）」「詳細な設定例（.env.example の全文）」や「運用手順（バックアップ、ログローテーション設定）」の作成が必要であれば内容を指定して教えてください。