README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
売買エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などのコンポーネントを備え、ローカル開発／ペーパートレード／本番（live）を切り替えて動作します。

主な機能
--------
- Execution エンジン起動 / セッション実行（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB（data/paper_trading.db）に記録
  - プロセス優先度設定、PID 管理、停止フラグ対応
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システムリソース・データ鮮度・注文ログ・リスク指標の定期チェック
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート管理（AlertManager 経由で通知）
- Portfolio 構築（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイズ算出、セクターキャップ、レジーム乗数
- Research（research パッケージ）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン、IC 計算、統計サマリー
- AI（ai パッケージ）
  - ニュースの NLP による銘柄別センチメント（OpenAI を使用）
  - 市場レジーム判定（ETF MA とマクロ記事の LLM 評価を合成）
- ユーティリティ
  - .env 対話式作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - ログ設定・プロセス優先度ユーティリティなど

前提条件（推奨）
---------------
- Python 3.8+（アノテーションの未来 import を使用）
- 必須（機能による） Python パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の構文チェックに必要だが必須ではない）
- OS: Linux / macOS / Windows（process priority は OS に依存した実装を含む）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で配置（.env.example を参考にしてください）
   - 自動ロード:
     - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします
     - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付与

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

運用メモ
--------
- run_monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（SQLITE_PATH）を使用して監視データを保存します。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と分離）。
- 停止制御:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが安全に終了します（両起動スクリプトで参照）。
  - Kill Switch は data/kill.flag を書き込むことで ExecutionEngine の停止シグナルとして機能します（Monitoring が条件を検知して書き込む）。
- PID / ログ:
  - デフォルトログディレクトリ: logs/
  - PID ファイル（Execution）: data/execution.pid（run_execution が使用）
- AI 機能:
  - OPENAI_API_KEY が必須。API 呼び出しはリトライやスコア検証の工夫が実装されていますが、API 失敗時は安全フォールバックを行う設計です。

使い方（コマンド例）
-------------------
- 環境ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution エンジン起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - ペーパートレードを使う例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定 / DB 指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（プログラムから呼び出す例）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

プロジェクト構成（主なファイル／パッケージ）
-----------------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・検証・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID / stop flag 管理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — システムリソース・データ鮮度監視
  - trade_monitor.py — 注文ログ関連監視（存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねた実行ループ
  - alert_manager.py — アラート送信（存在）
- execution/
  - execution_engine.py、order_manager.py、order_repository.py、reconciler.py、risk_manager.py、broker_factory.py など（発注処理・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py、position_sizing.py、risk_adjustment.py（銘柄選定／配分／リスク調整）
- research/
  - factor_research.py、feature_exploration.py（ファクター計算・分析ツール）
- ai/
  - news_nlp.py（ニュース NLP → ai_scores）
  - regime_detector.py（市場レジーム判定）
- tools/
  - paper_verification_report.py（Paper Trading 検証レポート）
- data/
  - （デフォルトの DB / フラグ / PID を格納する場所として使用: data/*.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）

補足（設計上の注意）
-------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Monitoring は監視用の SQLite に対してマイグレーション処理（列追加など）を行います。既存 DB を扱う際はバックアップを推奨します。
- AI（OpenAI）関連は API キーとコストが発生します。ローカル開発ではモック（テスト時の差し替え）を推奨します。
- KABUSYS_ENV=paper_trading は実際の発注を行わないモードですが、必ず別 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番データと完全に分離してください。

以上がこのリポジトリの主要な説明と使い方です。導入や運用で不明点があれば、用途に応じたファイル（config.py、run_*.py、monitoring/*.py、execution/*.py）を参照してください。