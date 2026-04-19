README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチツールキットです。  
本リポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター・リサーチ、AI ベースのニュース NLP（OpenAI 経由）など、トレーディング・ワークフローに必要な主要コンポーネントが含まれます。

特徴
----
- ExecutionEngine（発注実行）:
  - 本番 / ペーパートレード（分離された SQLite DB）をサポート
  - ブローカー抽象化（MockBroker をテスト用に使用）
  - リスク管理・注文管理・照合（reconciler）を統合

- Monitoring（監視）:
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック、滞留注文・約定異常・ドローダウン等の監視
  - Kill Switch（条件に応じて data/kill.flag を書き込み、実行を停止）
  - 日次ログローテーション設定済み

- Portfolio（ポートフォリオ構築）:
  - 候補選定、等金額 / スコア加重配分、リスクベース寸法
  - セクター上限適用、レジーム乗数

- Research（リサーチ）:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI（OpenAI 統合）:
  - ニュース記事をまとめて LLM に投げ、銘柄別 sentiment を ai_scores に保存
  - マクロニュースを用いた市場レジーム判定（regime_detector）

- ユーティリティ:
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギング・プロセス優先度ユーティリティ等

セットアップ手順
--------------
前提:
- Python 3.9+（typing 機能を利用）
- 必要な Python パッケージをインストールしてください。例:

  pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを使用してください）

1. プロジェクトをクローン／配置
   - ソースは src/kabusys 以下に配置されています。

2. 環境変数の初期化（.env）
   - 対話式ウィザードで .env を作成・更新できます:

     python -m kabusys.config_setup

   - 生成される主なキー（.env のサンプル）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|...)
     - KILL_FLAG_CLEAR_ON_START (0|1)
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB パス）
     - PAPER_FILL_MODE（instant|partial|never|reject）
     - OPENAI_API_KEY（AI 機能を使う場合）

3. 設定検証
   - 作成した .env や config/*.yaml の整合性をチェック:

     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict   # 警告も失敗扱い

4. ログディレクトリ
   - デフォルトで logs/ に日次ローテーションログを出力します。必要に応じて LOG_DIR 環境変数で変更してください。

運用上の注意
- KABUSYS_ENV が paper_trading の場合、実際の発注は行われず、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB と完全分離されます。
- Kill Switch: KillSwitch が条件を満たすと data/kill.flag を作成します。ExecutionEngine の起動時・監視ループでこのフラグにより停止が行われます。
- 停止フラグ: run_monitoring/run_execution は data/stop_requested.flag を参照して優雅に終了します。

使い方
------

一般的な CLI／モジュール実行例:

- .env の作成（対話式）:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution エンジン起動（通常はサービスとしてデーモン化して実行）:

  python -m kabusys.run_execution

  - 実行中に data/stop_requested.flag を作ると Engine を停止します。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われます。

- Monitoring ポーリング起動:

  python -m kabusys.run_monitoring

  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は本番 sqlite_path を常に使用します（環境に依らず監視 DB は本番パスを参照）。

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（コード呼び出し例）:
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

  どちらも OpenAI API キー（OPENAI_API_KEY または引数）を必要とします。

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / 重要:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（分析用）
  - SQLITE_PATH: 監視用 SQLite（monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading.db）
  - OPENAI_API_KEY: AI 機能を使う場合に必要
  - LOG_LEVEL, LOG_DIR

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要なファイルとディレクトリの一覧（本 README 作成時点のもの）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成 / CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （トレード監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック：LINE等に接続）

  - execution/
    - execution_engine.py    — 実行エンジン本体
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（エンジン関連モジュール）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

補足
----
- DuckDB を使って大規模分析やファクター計算を行います。prices_daily / raw_financials / raw_news 等のテーブル設計はコード内クエリを参照してください。
- コード内のコメント／ドキュメント文字列（docstring）は実装方針や注意点を多く含んでいます。実運用前に validate_config で設定を検証し、KABUSYS_ENV を慎重に設定してください（特に live）。
- AI（OpenAI）機能を有効にする場合、API 呼び出しのレート制限やコスト、応答のバリデーションに注意してください。レスポンスの失敗は多くの場合フェイルセーフでスコア 0 やスキップにフォールバックします。

ライセンス / バージョン
----------------------
package version: __version__ = "0.1.0"（src/kabusys/__init__.py）

（ライセンス情報がリポジトリ内にある場合はそちらを参照してください）

お問い合わせ
-----------
実装や運用に関する質問・改善提案は、ソースコードの該当モジュールの docstring コメントに沿って行ってください。README に書かれていない追加のスクリプトや設定ファイルがある場合は、それらも合わせて参照してください。