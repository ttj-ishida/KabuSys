KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム（KabuSys）のコアライブラリと起動スクリプト群を含みます。
本READMEはプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意
---
- .env は機密情報（API トークン等）を含みます。絶対にバージョン管理にコミットしないでください。
- 自動で .env を読み込む仕組みがあり（Settings モジュール）、テスト時や特殊なケースでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

プロジェクト概要
--------------
KabuSys は以下の主要コンポーネントを持つ自動売買フレームワークです。

- ExecutionEngine：発注・注文管理・リスク管理を行うエンジン（実取引 / ペーパートレード対応）
- Monitoring：システム監視（CPU/メモリ/ディスク・プロセス生存・データ鮮度）、リスク監視、アラート/Kill Switch 管理
- Portfolio：銘柄選定、ウェイト計算、ポジションサイズ計算、セクター制限等のポートフォリオ構築ロジック
- Research：DuckDB を用いたファクター計算 / 特徴量探索
- AI：OpenAI を使ったニュース NLP（センチメント）および市場レジーム判定
- CLI ツール類：環境設定ウィザード、設定検証、ペーパートレード検証レポート等

主な機能一覧
-------------
- 環境設定ウィザード（.env 生成 / 更新）：kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）：kabusys.validate_config
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker）/ live（実ブローカー）を切替
  - paper_trading は data/paper_trading.db に完全分離して記録
- Monitoring 起動スクリプト（run_monitoring.py）
  - 定期ポーリングでシステム状態・取引状態・リスクをチェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）
- Monitoring DB：SQLite ベース（テーブル自動作成・マイグレーション対応）
- Portfolio 構築：候補選定 / 等重・スコア重み / ポジションサイズ算出（単元株丸め・利用可能現金でスケーリング）
- Research：DuckDB を使ったファクター計算（Momentum, Value, Volatility）と統計ツール（IC 等）
- AI モジュール：
  - news_nlp.score_news: ニュース記事を LLM で評価し ai_scores に保存
  - regime_detector.score_regime: ETF を用いた MA200 乖離 + マクロ記事の LLM でレジーム判定
- ツール：paper_trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python バージョン
   - 推奨: Python 3.10 以上（型注釈に | 演算子等を使用しているため）

2. 依存関係のインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証を行う場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動し、初期ディレクトリを作成
   - data/ や logs/ は起動時に自動作成されます（ただし権限等で失敗する場合は事前作成してください）。

4. 環境変数の準備
   - .env を作成するには対話式ウィザードを使うのが簡単です:
     - python -m kabusys.config_setup
   - ウィザード実行後、生成された .env を確認してください。
   - 必須環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な環境変数（説明）
     - KABUSYS_ENV: 実行環境（development|paper_trading|live）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）

5. 設定の検証
   - 実行前に設定チェックを推奨:
     - python -m kabusys.validate_config
     - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

使い方
-------

起動スクリプト（本番 / ローカル実行）

- Monitoring を起動（ポーリングで監視を行う）
  - デフォルトポーリング間隔は 60 秒。環境変数で変更可:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 実行コマンド例:
    - python -m kabusys.run_monitoring

- ExecutionEngine を起動（発注エンジン）
  - KABUSYS_ENV に応じて paper_trading（MockBroker）か実ブローカーを使用
  - ペーパートレードは data/paper_trading.db に記録（本番 DB と分離）
  - 実行コマンド例:
    - python -m kabusys.run_execution

停止制御（フラグファイルベース）
- 停止フラグ（監視 / 実行ループの即時停止）:
  - data/stop_requested.flag を作成すると、run_monitoring / run_execution が検知して安全停止します。
- Kill Switch（自動停止トリガー）
  - data/kill.flag を書き込むと ExecutionEngine に停止シグナルが送られます。
  - KillSwitch は監視結果（ドローダウン・ポジション上限等）で自動的にファイルを書き込みます。
- PID ファイル:
  - 実行時に data/execution.pid (デフォルト) に PID を書きます。

ログ
- ログ設定は共通ユーティリティから行われ、logs/<app_name>.log に日次ローテートで出力されます。
- 環境変数 LOG_DIR でログディレクトリを指定可能。

ツール & スクリプト
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- AI / research モジュールは直接関数として利用:
  - 例: Python REPL / スクリプト内で duckdb 接続を作り、kabusys.ai.news_nlp.score_news(conn, target_date) を呼ぶ
  - OpenAI API を利用する場合は OPENAI_API_KEY を設定してください。

開発メモ
- 設定値の自動読み込み:
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動で読み込みます（OS 環境変数優先）。
- DB 初期化:
  - monitoring 起動時や execution 起動時に init_monitoring_db() が呼ばれ、必要なテーブルを冪等に作成します。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され本番 DB と分離して動作します。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は API の一時エラー・429・タイムアウト・5xx を指数バックオフでリトライする実装です。
  - テスト時には HTTP や OpenAI クライアント呼び出しをモックすることを推奨します。

ディレクトリ構成（抜粋）
----------------------
プロジェクトルート（例）
- .env.example
- pyproject.toml / setup.cfg / など

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_monitoring.py         — Monitoring 起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト

- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
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
- utils/
  - logging_setup.py
  - process_priority.py

ログ・データ等の出力先（デフォルト）
- data/kabusys.duckdb         — DuckDB（分析用）
- data/monitoring.db          — 監視用 SQLite DB
- data/paper_trading.db       — ペーパートレード専用 DB（paper_trading 時）
- data/execution.pid          — 実行中 PID（Execution）
- data/stop_requested.flag    — 管理者が作る停止フラグ
- data/kill.flag              — Kill Switch が書き込む停止フラグ
- logs/<app_name>.log         — ログファイル（例: logs/execution.log, logs/monitoring.log）

よくある実行例
----------------
- 環境変数を .env に保存した後、設定を検証:
  - python -m kabusys.validate_config

- ローカルでペーパートレードを試す:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセスを起動（ポーリング間隔 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading の検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- config/*.yaml（system_config.yaml 等）は設定テンプレート生成スクリプトがある場合があります。validate_config は PyYAML があれば YAML の中身も検証します（未インストールなら警告）。
- 本リポジトリに含まれる各モジュールは単体テスト可能な純粋関数群（portfolio, research 等）と、外部リソース（DB / API / ブローカー）に依存する実行コンポーネント（execution, ai, monitoring）で分かれています。ユニットテストでは外部依存をモックして使用してください。

ライセンス / 貢献
----------------
- 本プロジェクトのライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

お問い合わせ
----------
不明点や実行時の問題があれば、リポジトリの ISSUE を立てるか担当者にお問い合わせください。

以上。