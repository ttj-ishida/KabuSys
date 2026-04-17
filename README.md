# KabuSys — README

このリポジトリは「KabuSys」日本株自動売買システムの一部実装を含みます。  
以下はコードベースに基づいたプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

注意: README はソースコードの実装に沿って手作成しています。実運用時は .env の設定やシステム依存（OS・権限）に注意してください。

---

目次
- プロジェクト概要
- 機能一覧
- 動作要件（依存パッケージ）
- セットアップ手順
- 環境変数（主な設定）
- 使い方（実行例）
- 停止・キルスイッチについて
- ディレクトリ構成（主要ファイル説明）
- 補足・運用上の注意

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムの骨格モジュール群（監視、発注、ポートフォリオ構築、研究、AI支援など）を提供します。
- このリポジトリには監視エンジン、Execution エンジン起動スクリプト、ポートフォリオ構築関数群、リサーチ（ファクター計算・IC等）、ニュース NLP / レジーム判定（OpenAI API 利用）などが含まれます。
- SQLite / DuckDB をデータ永続化に利用し、環境（本番 / paper_trading / development）に応じた挙動の分離が実装されています。

機能一覧（抜粋）
- 監視（Monitoring）
  - システムリソース監視（CPU/Memory/Disk）
  - データ鮮度チェック（DuckDB の最終価格日）
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限監視とリスクログ記録
  - LINE によるアラート通知（AlertManager）
  - KillSwitch による停止フラグ出力（data/kill.flag）
  - Streamlit ベースの監視ダッシュボード
- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリによる本番/ペーパートレード切替（paper_trading 用 DB に分離）
  - リコンシリエーション（再起動後の状態同期）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分・スコア配分、リスク調整（セクター上限・レジーム乗数）
  - 株数決定（単元株丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value のファクター計算（DuckDB SQL）
  - 将来リターン、IC、統計サマリー
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュースを使った市場レジーム判定
- ユーティリティ
  - 環境ファイル自動読込 (.env / .env.local)
  - プロセス優先度・CPU affinity 設定ユーティリティ（psutil）

動作要件（依存パッケージ）
- Python 3.9+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 実際には requirements.txt は含まれていないため、上記を仮想環境にインストールしてください。

セットアップ手順（ローカル開発向け）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必須ライブラリのインストール（例）
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を作成（オプション）
   - config モジュールはプロジェクトルート（.git または pyproject.toml 基準）から .env, .env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - .env.example があれば参考にして設定してください（本リポジトリに例は含まれませんが、以下「環境変数」参照）。

環境変数（主要項目）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、実行側は paper_trading 用 DB（デフォルト data/paper_trading.db）を利用し、MockBrokerClient を使う設計想定。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector 利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用（未設定なら送信はスキップ）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のマッチングモード（instant / partial / never / reject）
- PID_FILE_PATH: ExecutionEngine PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60。無効値はデフォルトへフォールバック）

使い方（主要スクリプト）
- 監視ループ起動（run_monitoring.py）
  - 役割: SystemMonitor（システム状態の定期記録）をポーリングで実行する簡易起動スクリプト
  - 実行:
    - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 特記事項:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを残します（本番 DB に対して実行する点に注意）。

- 実行エンジン起動（run_execution.py）
  - 役割: ExecutionEngine を立ち上げ、OrderManager / RiskManager 等を初期化して取引セッションを実行
  - 実行:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離されます。
    - 起動前に data/stop_requested.flag があると起動をスキップし、起動時に PID ファイルを使用します（_EXECUTION_PID = data/execution.pid）。
    - プロセス優先度を high に設定しようとします（権限不足時は警告を出してスキップ）。

- Paper Trading 検証レポート（ツール）
  - スクリプト: kabusys.tools.paper_verification_report.generate_report / CLI
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間を指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定: --db PATH（省略時は env または data/paper_trading.db）
  - 出力: 標準出力に検証レポート（稼働率、注文成功率、送信率、P95 レイテンシなど）を表示

- Streamlit 監視ダッシュボード
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視 DB を read-only で開いてダッシュボードを表示します。MonitoringEngine が DB を書き込んでいる必要があります。

停止・キルスイッチ
- 手動停止（run_* スクリプト）
  - いくつかのスクリプトはプロジェクトルートの data/stop_requested.flag を監視しており、存在するとループを脱して終了します。停止したい場合はファイルを作成してください（または削除してクリア）。
- KillSwitch（自動停止トリガ）
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検知して安全に停止します。
  - KillSwitch は既存のファイルがある場合は再書き込みせず冪等です。kill.flag を手動でクリア可能です（KillSwitch.clear() を呼ぶかファイル削除）。

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 自動読み込みと Settings クラス（設定の取得・バリデーション）
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 対応）
  - data/ (想定) — 実行時生成される SQLite, DuckDB, PID, flag ファイル等（デフォルトは data/*.db 等）
  - monitoring/
    - monitoring_db.py — 監視ログ用の SQLite スキーマ初期化と永続化層（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度の監視ロジック
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限のチェック
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE へのプッシュ通知
    - monitoring_engine.py — 複数 Monitor の束ねとポーリング
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・同期・リコンシリエーション関連（OrderManager, Reconciler 等）
    - broker_factory.py etc. — ブローカークライアント生成（本番 / Mock 切替）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定、重み、株数計算、セクター制約、レジーム乗数
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算、将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース記事のセンチメント解析＆ai_scores 書き込み（OpenAI 利用）
    - regime_detector.py — マクロ + 1321 MA200 によるレジーム判定（OpenAI 利用）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI

補足・運用上の注意
- .env の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。
  - OS 環境変数は保護され、.env が上書きしないように処理されます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に不足カラムがあれば簡易マイグレーションを行います（例: dashboard.peak_value, trade_logs.latency_ms の追加）。
- OpenAI 利用:
  - news_nlp / regime_detector は OPENAI_API_KEY が必要です。API 呼び出しはリトライ・フォールバック（失敗時の安全側動作）を含む実装になっていますが、API コストに注意してください。
- 権限・プラットフォーム差:
  - process_priority.set_process_priority は Windows / POSIX (Linux/Mac/FreeBSD) を考慮しますが、権限不足時は設定に失敗して警告が出ます（動作は継続します）。
- PAPER_TRADING モード:
  - paper_trading を利用すると発注は Mock ブローカーに向けられ、本番 DB と分離された SQLite に記録される設計です（安全に検証できます）。

---

問題や不足しているドキュメント項目（例えば依存パッケージの確定版、実際の BrokerClient 実装、ExecutionEngine の詳細な設定ファイルなど）があれば、追加で README を拡張します。必要であれば起動例（systemd ユニット / Dockerfile / docker-compose）のテンプレートも作成できます。どの情報が欲しいか教えてください。