README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。システム監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、ファクター計算、AI を使ったニュース評価などの機能群を含み、SQLite / DuckDB によるデータ永続化と、OpenAI を使った NLP 処理を想定しています。

主な特徴
--------
- 実行環境を切り替え可能（development / paper_trading / live）
- ExecutionEngine：発注管理・リスク管理・約定処理（paper_trading はモックブローカーで本番 DB と分離）
- Monitoring：システム健全性、注文滞留、ドローダウン等の監視と Kill Switch（flag ファイルによる停止）
- Portfolio Construction：候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム調整
- Research：DuckDB を使ったファクター計算（Momentum/Volatility/Value）や特徴量解析
- AI：OpenAI を用いたニュースセンチメント（ai_scores）・市場レジーム判定モジュール
- ユーティリティ：.env 対話式ウィザード、設定検証 CLI、日次ローテーションログ設定 等
- レポート：Paper Trading の検証レポート生成スクリプト

セットアップ手順
----------------
1. 必要条件
   - Python 3.10+（コードは 3.10 の型記法（|）を使用しています）
   - SQLite（標準で付属）
   - 推奨パッケージ（インストール例は下記）

2. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

3. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

4. 依存パッケージをインストール（例）
   - pip install duckdb openai psutil pyyaml

   （requirements.txt があれば pip install -r requirements.txt を利用）

5. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
   - 自動ロードを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

使い方
------
起動スクリプト（パッケージモジュールとして実行可能）:

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは共通）

- Execution（注文実行）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます
  - 実行中に data/stop_requested.flag が存在すると Graceful に停止します
  - 実行時は data/execution.pid（デフォルト）に PID を書きます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI 機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日用のニューススコアを ai_scores テーブルに書き込みます
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームの算出と market_regime テーブルへの書き込み

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

運用に関する注意
- kill switch / stop flag:
  - KillSwitch は data/kill.flag を生成して ExecutionEngine に停止要求を送ります（ExecutionEngine は起動時にこの flag をチェック）
  - run_* スクリプトは data/stop_requested.flag を監視してループを終了します（外部から停止したいときにこのファイルを作成）
- ログ:
  - デフォルトで stdout（コンソール）と logs/<app_name>.log に日次ローテートで出力されます
  - LOG_DIR 環境変数でログディレクトリを上書きできます
- Paper trading:
  - paper_trading 環境では発注が仮想化（MockBroker）され、本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）
- .env は機密情報を含むため絶対に Git にコミットしないでください

ディレクトリ構成（要約）
--------------------
src/kabusys/
- __init__.py
- config.py — .env 自動読み込み、Settings クラス
- config_setup.py — .env 対話式ウィザード CLI
- validate_config.py — 起動前設定検証 CLI
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — OpenAI を用いたニュースのセンチメント集約・書き込み
  - regime_detector.py — マクロ + MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文関連監視）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねる polling engine
  - kill_switch.py — flag ファイルでの停止シグナル
  - alert_manager.py —（LINE 等のアラート送信を想定）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - ExecutionEngine とその依存コンポーネント
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・丸め・集約 cap
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- monitoring/（上記）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - logging_setup.py — 統一ロギング設定
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

主なファイル（抜粋）
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/monitoring/monitoring_db.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/tools/paper_verification_report.py

開発・デバッグのヒント
---------------------
- ロギング: setup_logging(app_name="execution") 等でログを統一設定しています。ローカルでは stdout と logs/ の両方を確認してください。
- DB 初期化: monitoring は起動時に init_monitoring_db() でスキーマを作成 / マイグレーションします。
- テスト: MonitoringEngine.run_once() を使えば単発実行で各モニタの挙動を確認できます。
- 環境の自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動的に読み込みます。テスト時にこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------
（リポジトリに合わせて適切に追記してください）

問い合わせ
--------
不具合・改善提案は issue を作成してください。技術的な質問はソース内の docstring を参照すると詳細な設計方針や仕様が書かれています。