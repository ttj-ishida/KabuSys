README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量なコードベースです。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 注文管理・発注実行（ExecutionEngine、OrderManager、Reconciler）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- ポートフォリオ構築（候補選定、配分・株数計算、セクター上限適用）
- リサーチ（ファクター計算、特徴量探索、将来リターン・IC）
- AI 補助（ニュースセンチメントスコアリング / レジーム判定）（OpenAI を利用）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な実行エントリはパッケージモジュール経由で起動可能です（python -m kabusys.run_monitoring など）。

主な特徴
--------
- 環境変数 / .env ベースの設定管理（起動時に .env / .env.local を自動ロード）
- 本番／ペーパー口座の分離（KABUSYS_ENV = development | paper_trading | live）
- SQLite（監視ログ等）および DuckDB（時系列・ファクタ計算）の併用
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント／マクロ判定（フェイルセーフ実装）
- Streamlit による監視ダッシュボード
- フェイルセーフ・冪等性を意識した DB 書き込み設計

前提条件
--------
- Python 3.10+
- 以下の主要ライブラリ（プロジェクトに requirements.txt がない場合は手動インストール）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- （任意）.env ファイルをプロジェクトルートに配置して必要な環境変数を設定

インストール（参考）
------------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

環境変数（代表例）
-----------------
本プロジェクトは .env / .env.local（プロジェクトルート）や OS 環境変数から設定を読み込みます。主要な環境変数:

- KABUSYS_ENV: 起動環境 (development | paper_trading | live) — デフォルト: development
- SQLITE_PATH: 監視用 SQLite パス — デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用）— デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading のマッチングモード ("instant" | "partial" | "never" | "reject") — デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証情報（必要に応じて）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチのフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする場合は "1"
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒） — デフォルト 60

設定ファイルの自動読み込みルール
- OS 環境変数が最優先
- プロジェクトルートに .env（上書き不可） → .env.local（上書き可）
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

セットアップ手順（初回）
----------------------
1. data ディレクトリ作成
   - mkdir -p data

2. DuckDB / SQLite ファイル配置（初期データが必要な場合はデータ投入）
   - デフォルトでは data/kabusys.duckdb と data/monitoring.db（または paper_trading.db）を利用

3. 必要な環境変数を .env に記載（例を下に記載）

例: .env（最小）
- KABUSYS_ENV=development
- OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
- SQLI_TE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb

（注）上記は一例です。実際には JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等も必要な機能があります。

使い方（主要コマンド）
--------------------

1) 監視ループ（Monitoring）
- 説明: SystemMonitor 等をポーリングして監視ログを記録、アラートや kill.flag を管理します。
- 起動:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視は Settings に従い常に本番用 sqlite_path を使用します（paper_trading 環境でも本番 DB に書き込む仕様）。

2) 発注エンジン（Execution）
- 説明: Broker クライアントを生成して ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合はモックブローカーを利用し、paper_trading 用 SQLite に書き込みます。
- 起動:
  - python -m kabusys.run_execution
- 注意:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用して本番 DB を完全に分離します。
  - 実行前に PID ファイルパス（PID_FILE_PATH）に書き込み権限があることを確認してください。

3) Streamlit ダッシュボード
- 説明: 監視データを可視化する簡易ダッシュボード。
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 備考:
  - ダッシュボードは監視 DB を読み取り専用で開きます（URI に ?mode=ro を付与）。

4) Paper Trading 検証レポート
- 説明: paper_trading SQLite のログから稼働率・注文成功率・レイテンシ等のレポートを生成します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI モジュール（ニューススコア・レジーム判定）
- 関数呼び出しで利用するケースが中心です（OpenAI API キーが必要）。
- 主要 API:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0 やスキップ）する設計ですが、API キーが未設定だと例外を投げる場合があります。

ログ・アラート
--------------
- AlertManager は LINE Messaging API（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を使い一方向プッシュ通知を行います。未設定の場合はログのみ。
- Monitoring モジュールは一定の閾値（CPU/MEM/DISK、データ鮮度、滞留注文、ドローダウン等）を監視し、必要に応じて risk_logs に記録して kill.flag を書きます。

重要なファイル／設定
------------------
- pid ファイル (Settings.pid_file_path) — ExecutionEngine の生存判定に使用
- kill.flag (Settings.kill_flag_path) — Monitoring が検出した重大事象で Execution を停止させるためのフラグファイル
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒）

ディレクトリ構成（主要ファイルの説明）
-------------------------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数の読み込み / Settings クラス
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の分離対応）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- monitoring/
  - monitoring_db.py — SQLite スキーマ作成・永続化レイヤ
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - trade_monitor.py — 注文滞留・約定異常検知
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 送信管理（クールダウン含む）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文の State Machine / 外向き API
  - reconciler.py — 再起動時のリコンシリエーション（ブローカー突合せ）
  - （その他ブローカー関連 / execution_engine 等は別ファイルで実装されている想定）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・aggregate cap
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー
- ai/
  - news_nlp.py — ニュースを LLM に投げて銘柄別スコアを生成
  - regime_detector.py — マクロ記事 + 1321 MA200 乖離を合成して日次レジーム判定
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

DB スキーマ（監視用）
-------------------
init_monitoring_db(conn) により以下のテーブルが作成されます（冪等）:
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok, ...)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の単一行で集計情報を保持)

運用上の注意 / トラブルシュート
-----------------------------
- PID ファイルや kill.flag の読み書きに必要なディレクトリ権限を事前に確認してください（デフォルトは data/ 以下）。
- OpenAI 利用時は API キーの有無に応じた動作（例外 or フェイルセーフ）に注意してください。
- monitor は常に production 用の sqlite_path を参照する点に注意（paper_trading 環境でも監視 DB が production を使う設計）。
- CPU 優先度変更・CPU affinity はプラットフォーム依存で失敗するとログに警告されます（権限不足など）。

開発者向けメモ
--------------
- 型アノテーションに PEP 604（| 型）を使っているため Python 3.10 以上を推奨します。
- DuckDB を使ったファクター計算は SQL と Python を組み合わせて行います。prices_daily / raw_financials 等のテーブルを用意してください。
- テスト時、AI 呼び出し部分は _call_openai_api を patch してモック可能なように設計されています。

ライセンス・貢献
----------------
- 本 README はコードベースの説明用です。ライセンスやコントリビュートフローが別途プロジェクトルートにあればそちらに従ってください。

最後に
------
この README はコードから読み取れる設計意図・使い方をまとめたものです。実運用する際は .env 設定、DB バックアップ、権限管理、監視の閾値調整などを十分に行ってください。必要であれば各モジュールの詳細ドキュメント（PortfolioConstruction.md や StrategyModel.md 等）を参照・整備してください。