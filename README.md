README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量なフレームワークです。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine（注文実行・リスク管理）
- Monitoring（システム状態・注文・リスク監視、Kill Switch）
- ポートフォリオ構築アルゴリズム（候補選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算、将来リターン、IC 計算）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI API 使用
- 開発用ユーティリティ（.env ウィザード、設定検証、検証レポート）

この README では、機能一覧、セットアップ、使い方、ディレクトリ構成を日本語でまとめます。

機能一覧
--------
- 環境設定ウィザード（.env の対話式生成 / 更新）
- 設定検証 CLI（.env および config/*.yaml の妥当性確認）
- ExecutionEngine 起動（本番 / ペーパートレード分離）
  - paper_trading モードでは MockBrokerClient を使用し DB を分離（data/paper_trading.db がデフォルト）
- Monitoring（定期ポーリングで system / trade / risk をチェック）
  - Kill Switch（一定条件で data/kill.flag を出力して ExecutionEngine を安全停止）
  - stop フラグ（data/stop_requested.flag）による外部停止
- Monitoring の永続化（SQLite）：system_status / trade_logs / positions / risk_logs / dashboard を管理
- ポートフォリオ構築ユーティリティ（候補選定、等金額/スコア加重、リスクベースの発注株数計算、セクター制限、レジーム乗数）
- Research 用関数（momentum, volatility, value, forward returns, IC, 統計サマリー）
- AI によるニューススコアリング（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を融合）
- ツール: Paper Trading 検証レポート出力（稼働率・成功率・レイテンシ等の判定）

前提 / 必要要件
---------------
- Python 3.10+
- 推奨パッケージ（主要な機能を使用する場合）:
  - duckdb
  - psutil
  - openai（AI 機能）
  - pyyaml（設定ファイル検証を行う場合）
- SQLite（標準ライブラリで動作）
- ネットワークアクセス（kabuステーション API / OpenAI API を使用する場合）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストールします（プロジェクトに requirements.txt があることを想定）。
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ テストや軽い利用で AI 機能を使わない場合は openai を省略できます。ただし ai モジュールを使うには OPENAI_API_KEY が必要です。

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードでは J-Quants / kabuAPI のクレデンシャルや DB パス等を対話的に入力できます。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定の検証を行います。
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit code 1）。

5. （初回）data ディレクトリや DB ファイルは実行時に自動作成します。必要に応じて事前に作成してください。

主要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（default: development）: development / paper_trading / live
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db） — Monitoring 用（Monitoring は常に本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用の分離 DB、default: data/paper_trading.db）
- LOG_LEVEL（default: INFO）
- OPENAI_API_KEY（AI モジュール使用時に必要）
- PAPER_FILL_MODE（paper_trading 時のモック埋め具合: instant/partial/never/reject）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒 — run_monitoring で上書き可、default: 60）
- KILL_FLAG_CLEAR_ON_START（実行時に kill.flag を自動クリアするか、default: 0）

使い方（CLI）
--------------
- 環境設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると Paper Trading 用の MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます。
  - 起動前に data/kill.flag が存在すると起動せずに終了します（安全対策）。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用します。
  - data/stop_requested.flag の検出で監視ループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

その他の挙動 / 運用上の注意
------------------------
- ログ
  - ログはデフォルトで stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
  - setup_logging(app_name="execution") などを利用してアプリ名を指定します。
  - ログディレクトリは環境変数 LOG_DIR またはデフォルト "logs" を使用します。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼び出してプロセス優先度を上げます（実行環境に依存し失敗した場合は警告を出します）。

- Kill Switch / Stop フラグ
  - Kill Switch: 条件（ドローダウンやポジション上限超過）で Settings.kill_flag_path（default data/kill.flag）を作成します。ExecutionEngine は kill.flag の存在を検出すると安全に停止します。
  - 強制停止: data/stop_requested.flag を作成すると run_monitoring/run_execution のループが終了してプロセスがシャットダウンします（用途: CI / 管理用）。

- Paper Trading
  - paper_trading 環境下では本番 DB と分離され、MockBrokerClient を使って発注がシミュレートされます。PAPER_FILL_MODE により約定挙動を調整できます。

- AI モジュール
  - news_nlp（銘柄別センチメント）と regime_detector（市場レジーム判定）は OpenAI API を利用します。使用時は OPENAI_API_KEY を設定してください。
  - API 呼び出しはリトライやフェイルセーフが実装されていますが、API キー未設定時は例外となります。

ディレクトリ構成（抜粋）
---------------------
以下は主要ファイルの階層（src/kabusys 以下）です。実際のリポジトリでは他にも多数のモジュールがあります。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP スコアリング
    - regime_detector.py        — 市場レジーム判定
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
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
    - logging_setup.py
    - process_priority.py

開発上の注意点
--------------
- .env の自動読み込みは Settings モジュールがプロジェクトルート（.git または pyproject.toml）を検出できる場合に行われます。テスト時などで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring の DB 初期化（init_monitoring_db）は冪等です。既存 DB への簡易マイグレーション（カラム追加）処理を含みます。
- DuckDB を用いた Research / AI は大規模データの高速集計を想定しています。prices_daily / raw_financials / raw_news 等のテーブルを前提とします。
- 本番運用では KABUSYS_ENV=live による設定確認（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認等）を必ず行ってください。

貢献・ライセンス
----------------
本 README はコードベースから生成された概要です。詳細な設計やアルゴリズム、API 実装（kabuステーションクライアント等）は対応するモジュールのドキュメントやソース内コメントを参照してください。

---

必要であれば、README に以下を追加できます:
- さらに詳しい環境変数一覧（説明付き）
- システムアーキテクチャ図（実行フロー）
- サンプル .env.example
- テストの実行方法（unit tests があれば）

上記いずれか追加希望があれば教えてください。