KabuSys
=======

日本株自動売買システムの一部モジュール群を含むリポジトリ。  
実運用向けの ExecutionEngine（発注処理）・Monitoring（監視）・Portfolio/Research/AI ツール等を含みます。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

概要
----
KabuSys は日本株の自動売買に必要な以下の主要コンポーネントを提供します。

- ExecutionEngine: ブローカークライアント経由で注文を管理・送出する実行エンジン（本番／ペーパートレード切替対応）。
- Monitoring: システムリソース・データ鮮度・注文状況・リスク指標を定期的に監視し、Kill Switch（停止フラグ）を発動可能。
- Portfolio: 候補選定、重み付け、ポジションサイジング、セクター制限などのポートフォリオ構築ロジック（純粋関数）。
- Research: DuckDB 上の市場データからファクター計算・将来リターン・IC 等の研究用ユーティリティ。
- AI モジュール: OpenAI を用いたニュースセンチメント評価（銘柄別）やマクロセンチメントを組み合わせたレジーム判定。
- ユーティリティ: ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証等。

主な機能一覧
--------------
- 環境別動作:
  - KABUSYS_ENV によるモード切替: development / paper_trading / live
  - paper_trading モードは MockBrokerClient を使用し、ペーパートレード用 DB に完全分離して記録
- Execution と Monitoring の独立起動:
  - execution: 実際の発注ロジックを実行（PID 管理、停止フラグ監視）
  - monitoring: SystemMonitor / TradeMonitor / RiskMonitor をポーリングしてログ・アラートを出す
- Kill Switch:
  - リスクやドローダウン条件で data/kill.flag を書き込み、ExecutionEngine に停止要求を出す仕組み
- ロギング:
  - コンソール(stdout) と 日次ローテーションファイル出力（logs/<app_name>.log）を統一的に設定
- AI（OpenAI）連携:
  - ニュース記事を集約して LLM でセンチメントを算出し ai_scores テーブルへ保存
  - マクロニュースと ETF の MA を組み合わせた市場レジーム判定
- DuckDB / SQLite を利用したデータ層:
  - DuckDB: 研究・ファクター計算用（prices_daily / raw_financials 等）
  - SQLite: 監視ログや注文ログの永続化（data/monitoring.db、paper_trading 用 DB は分離）

前提条件
--------
- Python 3.9+（コードは型注釈等を利用）
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/*.yaml の検証を行う場合に必要）
- SQLite は標準ライブラリで利用可能
- 実運用で kabuステーション API を使う場合はそのクライアントの設定 / パスワードが必要

セットアップ手順
----------------
1. リポジトリをクローンしてソースルートへ移動
   - この README はパッケージが src/ 配下にある前提です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストールしてください）

4. .env の作成（環境変数設定）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成／更新します。生成後は内容を確認してください。
   - 手動で環境変数を用意する場合は .env.example を参考に .env を配置してください。
   - 自動で .env を読み込む処理はデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります: python -m kabusys.validate_config --strict

主な環境変数（重要）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

よく使うオプション（デフォルト値は括弧内に示す）
- KABUSYS_ENV (development | paper_trading | live) — 実行モード（デフォルト: development）
- DUCKDB_PATH (data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (data/monitoring.db) — 監視用 SQLite（Monitoring が常に本番 sqlite_path を使用する点に注意）
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — ペーパートレード専用 DB（paper_trading モードで使用）
- LOG_LEVEL (INFO) — ログレベル
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE (instant) — ペーパートレード用 MockBroker の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START (0) — Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動 / 実行）
--------------------

1. ExecutionEngine を起動する
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録し MockBrokerClient を使用
     - 起動前に data/stop_requested.flag（プロジェクトルート data/stop_requested.flag）があれば起動を中止
     - 実行中に stop flag が作成されるとエンジンを停止
     - 実行中は data/execution.pid に PID を書き込み（設定により異なる）

2. Monitoring を起動する
   - python -m kabusys.run_monitoring
   - 挙動:
     - 環境にかかわらず Settings.sqlite_path（本番パス）を使って監視 DB に接続します
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
     - 停止制御: プロジェクトルート/data/stop_requested.flag を検知するとループを終了

3. 設定ウィザード / 検証
   - 対話式 .env 作成: python -m kabusys.config_setup
   - 設定検証: python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止 / Kill Switch / フラグ
-------------------------
- Kill Switch
  - リスク条件等で KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は既に kill.flag が存在する場合は上書きしません（冪等）。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は自動でクリアされます（本番では 0 推奨）。

- 停止フラグ
  - run_execution.py と run_monitoring.py は data/stop_requested.flag を確認し、存在すれば起動を止めたりループを終了したりします。
  - 手動で停止したい場合はこのファイルを作成してください（ファイルに理由テキストを書いても可）。

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30 日保持）へ出力されます。
- setup_logging(app_name="execution") のようにアプリ名を指定してログファイルが logs/<app_name>.log に出力されます。
- ログレベルは LOG_LEVEL または setup_logging の引数で指定可能。

ディレクトリ構成（抜粋）
----------------------
トップレベル（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env 読込
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/                — Execution 用コンポーネント（broker_factory, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/                — portfolio_builder, position_sizing, risk_adjustment
  - research/                 — factor_research, feature_exploration
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — レジーム判定（MA + LLM）
  - data/                     — data ファイル群（例: monitoring.db, paper_trading.db）
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

開発メモ / 注意点
-----------------
- Monitoring は Settings.sqlite_path（本番パス）を使用します。テスト時に監視 DB を分離したい場合は注意してください。
- paper_trading モードでは、ExecutionEngine は settings.paper_sqlite_path を使って記録し、本番 DB と分離されます。
- OpenAI を利用する AI 機能は OPENAI_API_KEY が必須です。キーがなければ例外が出ます（関数によっては API 失敗でフォールバックする実装あり）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CI やテストで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority.set_process_priority はプラットフォーム依存の操作を行い、権限がない場合は警告が出てスキップされます。
- DuckDB への executemany はバージョンによって挙動差があるため、AI モジュール等では空リストを渡さないよう対策が入っています。

よくあるコマンドまとめ
--------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースの主要機能と起動手順を簡潔にまとめたものです。各モジュールの詳細な使用法や設計文書（PortfolioConstruction.md、StrategyModel.md 等）が別途ある場合はそちらも参照してください。必要であれば、導入手順を環境別に細かく分けたドキュメントや運用手順書を追加できます。ご希望があれば作成します。