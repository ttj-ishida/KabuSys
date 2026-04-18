KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株自動売買システム「KabuSys」のコードベースです。戦略生成、ポートフォリオ構築、発注管理、監視、検証ツールおよび AI を使ったニュース評価などを含むモジュール群で構成されています。

概要
----
KabuSys は以下の主要機能を持つ自動売買プラットフォームのコンポーネント群です。

- 戦略 / ファクター計算（DuckDB を使った過去価格・財務データ参照）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- ExecutionEngine（ブローカークライアント経由の発注／リスク管理／再調整）
- 監視（システム状態・注文状態・リスク監視・Kill Switch）
- Paper Trading 用の分離 DB（発注を本番 DB と完全に分離）
- AI モジュール（ニュースの NLP スコアリング / 市場レジーム判定、OpenAI 使用）
- 検証ツール（Paper Trading 検証レポート生成）
- 設定ウィザード・設定検証 CLI

主な機能一覧
--------------
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 対話式ウィザードで .env を生成（kabusys.config_setup）
  - 起動前に設定を検証（kabusys.validate_config）
- 実行／監視スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring: SystemMonitor をポーリング（MONITOR_POLL_INTERVAL 環境変数で間隔指定可）
- 監視・Kill Switch
  - system, trade, risk の監視、kill.flag による ExecutionEngine 停止指示
  - stop_requested.flag を置くことで起動ループの安全終了
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスク調整（セクター上限、レジーム乗数）、株数決定（単元丸め）
- 研究用モジュール
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン、IC 計算、統計サマリー）
- AI（OpenAI）
  - ニュース NLP による銘柄センチメントスコア化（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA による日次レジーム判定（market_regime テーブル）
- ツール
  - paper_verification_report: Paper Trading の稼働率・注文成功率・レイテンシ等の検証レポート生成

前提・依存（代表）
------------------
必須環境変数（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

（任意 / デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_*（LINE 通知を有効にする場合）

代表的な Python パッケージ（requirements.txt があればそちらを利用してください）
- duckdb
- psutil
- openai
- PyYAML（config 検証のためにあると便利）

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実際はプロジェクトの requirements.txt / setup.cfg に従ってください（存在する場合）

4. .env の用意
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
     - ウィザードは .env（デフォルト）を作成・更新します
   - 既存の .env を直接編集することも可能
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）にある .env / .env.local を読みます。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告をエラー化する場合は --strict を付ける

使い方（起動 / ツール）
----------------------

- ExecutionEngine を起動（パッケージ形式で実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。live では本番 API を使います。
  - 起動時は data/execution.pid（PID ファイル）を作成します。
  - 起動前に data/stop_requested.flag があると起動をスキップします。

- Monitoring を起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - run_monitoring は常に production（本番）用の sqlite_path を使って監視 DB を初期化します（monitoring は環境に依らず本番 sqlite を参照する設計）

- 停止方法
  - 監視ループ / 実行ループを外部から停止するにはプロジェクトルートの data/stop_requested.flag を作成します（run_* スクリプトはこのファイルを監視して安全終了します）。
  - Kill Switch（リスク条件到達時）により data/kill.flag が書き込まれます。ExecutionEngine はこの kill.flag を検出して動作を停止します（KillSwitch は冪等にファイルを書きます）。設定で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では推奨されません。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。--db で指定可。

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
- デフォルト出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテーション、30日分保持）
- LOG_DIR / LOG_LEVEL 環境変数で上書き可能

データベース
----------
- DuckDB: 分析用（デフォルト data/kabusys.duckdb）
- SQLite: 監視ログ（data/monitoring.db）
- Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）: data/paper_trading.db（本番 DB と完全分離）
- monitoring_db.init_monitoring_db(conn) は必要なテーブル・インデックスの作成と簡易マイグレーションを行います（冪等）

主要ファイル / ディレクトリ構成
------------------------------
以下は src/kabusys 以下の主なファイルと役割（抜粋）です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス（環境変数・.env の読み込み/検証ユーティリティ）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- kabusys/execution/  (発注エンジン関連)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
  - ExecutionEngine は broker（実またはモック） / OrderRepository / RiskManager 等を組み合わせて動作

- kabusys/monitoring/  (監視)
  - monitoring_db.py — SQLite の永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・資金配分と制限
  - risk_adjustment.py — セクター上限・レジーム乗数

- kabusys/research/
  - factor_research.py — Momentum/Volatility/Value などのファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン計算、IC 計算、統計サマリー

- kabusys/ai/
  - news_nlp.py — ニュースの LLM によるセンチメント評価（OpenAI）
  - regime_detector.py — マクロニュース + ETF MA による日次レジーム判定

- kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力

- kabusys/utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定ヘルパ
  - など

運用メモ / 注意点
-----------------
- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。CWD に依存しない実装になっています。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録します。本番 DB は汚しません。
- Run スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足の場合は警告のみで継続します。
- AI 機能（news_nlp / regime_detector）を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフを備えていますが、API キー未設定の場合は ValueError を送出します。
- monitoring は監視結果の永続化とリスクイベントの記録を行います。Kill Switch による自動停止機能は本番稼働時に重要です。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（デフォルト 0 を推奨）。

よく使うコマンド例
-----------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視ポーリング起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - または DB を直接指定: python -m kabusys.tools.paper_verification_report --db /path/to/db

ライセンス・貢献
----------------
（この README にライセンスや貢献手順が必要であればここに追記してください）

お問い合わせ / 開発者向けメモ
--------------------------
- コードはモジュール単位でユニットテストしやすいように設計されています（外部 API 呼び出し箇所は差し替え可能）。
- DuckDB 接続を各種研究／AI モジュールへ渡す設計になっています。DB スキーマは config/generate などで初期化する想定です（config/*.yaml 関連の生成スクリプトがある場合はそれに従ってください）。
- 既知の補助スクリプト（生成やマイグレーション）や requirements.txt がプロジェクトルートにある場合はそちらを優先してください。

以上が本プロジェクトの概要・セットアップ・使い方・ディレクトリ構成の要点です。必要であれば README に含める例 .env テンプレートや起動フローチャート、監視アラート仕様などを追記します。どの情報を追加しますか？