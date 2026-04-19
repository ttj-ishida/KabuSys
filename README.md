README.md

概要
----
KabuSys は日本株向けの自動売買システムのリポジトリです。
本コードベースは取引エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、
ポートフォリオ構築・ポジションサイズ計算、リサーチ/ファクター計算、AI（ニュースセンチメント・レジーム判定）
などを含むモジュール群で構成されています。

バージョン: 0.1.0（パッケージ定義: src/kabusys/__init__.py）

主な特徴
--------
- ExecutionEngine：発注系のエンジン。実口座（live）/ペーパートレード（paper_trading）に対応し、
  paper_trading 時は MockBrokerClient を用いて専用 SQLite（data/paper_trading.db）へ記録。
- Monitoring：システム（CPU/メモリ/ディスク）、データ鮮度、注文・リスク指標を定期ポーリングして記録・アラートを行う。
- Kill Switch：ドローダウンやポジション上限などの条件で安全に ExecutionEngine を停止する仕組み（flag ファイル）。
- ポートフォリオ構築：候補選定、等金額／スコア加重配分、セクター上限フィルタ、レジーム乗数などの純粋関数実装。
- リサーチ：DuckDB を使ったファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ。
- AI（OpenAI 利用）：ニュースを LLM でスコアリングして ai_scores に書き込む機能／市場レジーム判定。
- 運用用ユーティリティ：.env ウィザード（config_setup）、設定検証 CLI（validate_config）、Paper Trading 検証レポート生成ツール。

動作要件
--------
- Python 3.10+
- 必要パッケージ（一部機能）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config ファイル検証を行う場合）
- DB: SQLite（組み込み） / DuckDB（分析用）

インストール（例）
-----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - pip install duckdb psutil openai pyyaml
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使ってください）

初期セットアップ手順
-------------------
1. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development/paper_trading/live）などを対話的に作成します。
   - 生成された .env は絶対にリポジトリにコミットしないでください。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

3. ディレクトリ作成
   - data/ と logs/ は自動作成されますが、必要に応じて事前に作っておくとアクセス権の問題を回避できます。
     - mkdir -p data logs

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (例: INFO)
  - LOG_DIR (デフォルト: logs/)
- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector 使用時）
- その他:
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。0/1）

使い方（実行コマンド）
-------------------

1. 環境設定ウィザード（.env 生成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

3. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - 動作モードは KABUSYS_ENV に依存します:
     - paper_trading: MockBrokerClient を使用し data/paper_trading.db に分離して記録
     - live: 本番設定
     - development: ローカル開発向け（発注抑止など）

   停止: run_execution は data/stop_requested.flag を監視し、フラグがあれば安全停止します。
   PID ファイル: data/execution.pid（ExecutionEngine が書き込みます）

4. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
   - 監視は Settings.sqlite_path（本番 monitoring DB）を使用します（KABUSYS_ENV に依存しない）。
   - 停止: data/stop_requested.flag を置くとループが終了します。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6. AI 関連（プログラム的に）
   - ニューススコアリング:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="...")

   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="...")

運用上の注意
------------
- Kill Switch:
  - リスク条件（ドローダウンやポジション上限）が満たされると kill.flag（既定: data/kill.flag）が書き込まれ、
    ExecutionEngine に停止指示を送ります。フラグは手動でクリアするか、KILL_FLAG_CLEAR_ON_START により起動時に自動クリアできますが、
    本番では自動クリアは推奨されません。

- Stop フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します（運用上の緊急停止等に使用）。

- ログ:
  - デフォルトロケーションは logs/<app_name>.log。ログはコンソール（stdout）と日次ローテートのファイルに出力されます。
  - LOG_DIR 環境変数で変更可能。

- Paper Trading の分離:
  - paper_trading モードでは SQLite が data/paper_trading.db に分離され、本番データと混ざらないよう設計されています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                     - パッケージ定義 / バージョン
- config.py                       - 環境変数読み込み・Settings
- config_setup.py                 - .env 対話ウィザード
- validate_config.py              - 設定検証 CLI
- run_execution.py                - ExecutionEngine 起動スクリプト
- run_monitoring.py               - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                    - ニュースの LLM スコアリング処理
  - regime_detector.py             - 市場レジーム判定
- monitoring/
  - monitoring_db.py               - SQLite 監視 DB 永続層
  - system_monitor.py              - システム状態・データ鮮度監視
  - risk_monitor.py                - ドローダウン／ポジション上限監視
  - kill_switch.py                 - kill.flag 書き込みロジック
  - monitoring_engine.py           - 各 Monitor を束ねるランナー
  - alert_manager.py (参照)        - アラート送信ロジック（LINE 等）
  - trade_monitor.py (参照)        - 取引ログ監視（滞留注文など）
- portfolio/
  - portfolio_builder.py           - 候補選定・重み計算
  - position_sizing.py             - 株数決定・スケール調整
  - risk_adjustment.py             - セクター制限・レジーム乗数
- research/
  - factor_research.py             - ファクター計算（momentum/value/volatility）
  - feature_exploration.py         - IC/forward returns/統計サマリ
- tools/
  - paper_verification_report.py   - Paper Trading 検証レポート生成
- utils/
  - logging_setup.py               - ログ設定ユーティリティ
  - process_priority.py            - プロセス優先度 / CPU affinity ユーティリティ

開発者向けメモ
---------------
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。
  - テスト時に自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 型・互換性:
  - Python 3.10 の構文（型ヒントの | ）を使用しています。3.10 以上を推奨します。

- テスト:
  - 主要な外部 API 呼び出し（OpenAI 等）は内部的に呼出し関数をラップしているため、unit test ではモック差替えが容易です。
    例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", ...)

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して idempotent なテーブル作成と限定的なカラム追加（マイグレーション）を行います。

ライセンス
---------
（この README にはリポジトリのライセンス情報を含めていません。必要に応じて LICENSE ファイルを追加してください。）

サポート
-------
不明点や実行時のトラブルがあれば、実行ログ（logs/）と .env 設定、使用したコマンドを添えて問い合わせてください。