README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模なシステム群です。本リポジトリにはトレード実行エンジン周りの実装、監視（モニタリング）機能、ポートフォリオ構築ユーティリティ、ファクター計算・研究用モジュール、AI を用いたニュース評価・レジーム判定などが含まれます。

主な設計方針
- 本番・ペーパー環境の分離（KABUSYS_ENV=paper_trading 時は専用 SQLite を使用）
- DuckDB を用いた時系列・ファクタ計算（prices_daily / raw_financials 等のテーブル参照）
- 外部依存（OpenAI、kabu API、J-Quants）は Settings 経由で環境変数により設定
- 監視は SQLite にログを残し、streamlit ダッシュボードを表示可能

機能一覧
--------
- ExecutionEngine 起動スクリプト（run_execution） — ブローカーとの発注、リスク管理、再同期（Reconciler）など
- Monitoring 起動スクリプト（run_monitoring） — System / Trade / Risk の定期チェック、kill flag 発行、LINE 通知
- Monitoring ダッシュボード（streamlit） — positions / orders / system / dashboard 情報の可視化
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report） — paper_trading DB から各種指標を集計・判定
- Portfolio 構築モジュール — 候補選定、重み付け、ポジションサイズ計算、セクターキャップ/レジーム調整
- Research モジュール — モメンタム / ボラティリティ / バリューのファクター計算、将来リターン・IC・統計サマリ
- AI モジュール — ニュースの NLP スコアリング（OpenAI）、市場レジーム判定
- ユーティリティ — プロセス優先度・CPU affinity 設定、.env 自動読み込み、設定ラッパー（Settings）など
- 永続化：監視用 SQLite（data/monitoring.db 既定）、DuckDB（data/kabusys.duckdb 既定）、ペーパートレード用 SQLite（data/paper_trading.db 既定）

セットアップ手順
----------------
前提: Python 3.9+（推奨）。プロジェクトルートは .git / pyproject.toml の存在で自動検出されます。

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主なパッケージ例:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - requirements.txt がない場合は手動インストール:
     - pip install duckdb psutil openai requests streamlit

3. 環境変数 / .env
   - プロジェクトルートの .env または .env.local を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時に必須)
     - KABUSYS_ENV (development | paper_trading | live) — 未指定は development
     - DUCKDB_PATH (既定: data/kabusys.duckdb)
     - SQLITE_PATH (既定: data/monitoring.db)  — Monitoring DB（本番）
     - PAPER_TRADING_SQLITE_PATH (既定: data/paper_trading.db) — paper_trading 用 DB
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラート送信に利用）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））

4. データディレクトリ
   - data/ に DB ファイルや PID / flag ファイルを作成します（コードは存在しなければ作成します）。
   - 例:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - data/execution.pid, data/kill.flag, data/stop_requested.flag（ランタイムで使用）

使い方
------
- 実行エンジン（ExecutionEngine）起動
  - 本番モード（KABUSYS_ENV=live など）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレーディング（MockBroker）で起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行前に data/kill.flag が存在すると起動をスキップします（安全装置）。

- 監視ループ（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30
  - run_monitoring は環境にかかわらず monitoring 用の sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C を押下。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で DB が開けない場合はエラーメッセージを表示します。

- AI 機能
  - ニュース NLP スコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - OPENAI_API_KEY が必要（引数で上書き可）
  - 市場レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上のポイント
- KABUSYS_ENV によって ExecutionEngine が paper_trading 用 DB を使うか本番 DB を使うかを切り替えます。監視側（run_monitoring）は常に本番 monitoring DB を使用します（環境にかかわらず）。
- kill.flag による停止シグナルは KillSwitch により設定され、ExecutionEngine は起動時に旗を確認し停止します。
- PID ファイル（data/execution.pid）は ExecutionEngine が自身の稼働状態チェックに使用されます。stale PID（プロセス不存在）は SystemMonitor が検出して自動で削除し、risk_logs に記録します。
- .env の自動読み込みはプロジェクトルート検出に依存します。.git または pyproject.toml があるパスがルートとして扱われます。

ディレクトリ構成 (主要ファイル・概要)
-----------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数／設定読み込みロジック（Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — SQLite 監視用テーブル定義・永続化 API（MonitoringDB）
    - system_monitor.py — システム・データ鮮度監視（SystemMonitor）
    - trade_monitor.py — 注文滞留・約定異常監視（TradeMonitor）
    - risk_monitor.py — ドローダウン・ポジション上限監視（RiskMonitor）
    - kill_switch.py — kill.flag 制御ユーティリティ
    - alert_manager.py — LINE による通知送信
    - monitoring_engine.py — 複数 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, ... — 発注管理・同期ロジック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - utils/
    - process_priority.py — プロセス優先度 / CPU Affinity 設定
  - data/ (ランタイム生成を想定)
    - monitoring.db (SQLite、デフォルト)
    - paper_trading.db (ペーパートレード用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag など

さらに詳しい情報
----------------
- Settings（config.py）で必須となる環境変数は _require によりチェックされます。実行前に .env.example を参考に .env を作成してください（.env.example は本リポジトリ配布時の参考ファイルを想定）。
- AI 呼び出し（OpenAI）は API エラーに対してリトライやフォールバックを行う設計が組み込まれていますが、API キーは必須です。
- データベーススキーマやマイグレーションは monitoring_db.init_monitoring_db() 内に記述されています（冪等性あり）。

ライセンス・貢献
----------------
- 本 README はコードベースの説明を目的としています。実運用にあたっては各種設定・テストを行い、安全に配慮してください。

お問い合わせ
------------
不明点や実装に関する質問があれば、コード内の docstring やログメッセージを参照してください。必要であれば具体的な操作・エラーケースを提示いただければ README やドキュメントを補足します。