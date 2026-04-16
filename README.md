KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。
戦略の研究（ファクター算出・探索）、ポートフォリオ構築、発注/実行、監視、そして
Paper Trading用の検証ツールや Streamlit ダッシュボードなどを含みます。

主な特徴
--------
- データ解析・リサーチ
  - DuckDB を用いた prices_daily / raw_financials を参照するファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- ポートフォリオ構築
  - シグナル選択、等金額／スコア加重配分、リスク調整（セクター上限、レジーム乗数）
  - 発注株数（単元株丸め、リスクベース、キャッシュ制約によるスケーリング）
- 実行フレームワーク
  - OrderManager / ExecutionEngine / Reconciler による発注・状態同期・自動復旧
  - Paper Trading モードでは MockBroker を使用し、本番 DB と分離（data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - SQLite に監視ログを永続化（data/monitoring.db）
  - AlertManager による LINE プッシュ通知（任意設定）
  - KillSwitch による安全停止（flag ファイル）
  - Streamlit ダッシュボード（監視情報の可視化）
- AI 支援
  - news_nlp: OpenAI を用いたニュースセンチメント（銘柄別）スコアリング
  - regime_detector: マクロニュース + ETF MA200 を組み合わせ市場レジーム判定

機能一覧（モジュール単位）
-------------------------
- kabusys.config: 環境変数 / .env 自動ロード、Settings クラス
- kabusys.research: calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け取る）
- kabusys.research.feature_exploration: 将来リターン計算、IC、統計サマリ
- kabusys.portfolio: 候補選択・重み付け・ポジションサイズ計算・リスク調整
- kabusys.execution: OrderManager, Reconciler 等（発注ロジック）
- kabusys.monitoring: SystemMonitor, TradeMonitor, RiskMonitor, MonitoringDB, MonitoringEngine, AlertManager, KillSwitch, streamlit ダッシュボード
- kabusys.ai: news_nlp（OpenAI 呼び出しと結果バリデーション）、regime_detector
- kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト
- kabusys.utils.process_priority: プロセス優先度 / CPU affinity のユーティリティ

セットアップ手順
----------------

前提
- Python 3.10+（型注釈に Path | None 等を使用）
- SQLite3（標準ライブラリ）
- DuckDB（推奨）
- ネットワーク接続（API 使用時）

1. リポジトリをクローン／配置
   - この README と同位置にプロジェクトルートが存在する想定（.env 自動読み込みのため）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   例（pip）:
   - pip install duckdb psutil requests openai streamlit

   （requirements.txt が無い場合は上記を個別に追加してください）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（既定: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定動作）
     - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（既定: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
     - LOG_LEVEL: DEBUG|INFO|...（既定: INFO）

   .env の書式は shell 形式（export を許容）で、クォートやコメントも適切に処理されます。

起動・基本的な使い方
-------------------

※ すべてプロジェクトルートで実行することを想定しています。

A. 監視ループを起動（Production/常駐監視）
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60）。
- 実行:
  - python -m kabusys.run_monitoring
- 監視は常に本番の sqlite_path を使用（KABUSYS_ENV に依存しない）。
- プロセス優先度を "high" に設定して起動します。
- 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループは検知して終了します。

B. ExecutionEngine（発注エンジン）を起動
- KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）へ記録します。
- 実行:
  - python -m kabusys.run_execution
- 実行中、data/execution.pid に PID が書かれます。SystemMonitor はこの PID を監視します。
- 停止リクエスト:
  - プロジェクトルート/data/stop_requested.flag を作成すると run_execution は起動を行わないか、実行中は停止を試みます。
  - KillSwitch（監視ルール）が発動すると Settings.kill_flag_path（既定 data/kill.flag）へ理由を書き込み、ExecutionEngine に停止シグナルを送ります。

C. Paper Trading 検証レポートを生成
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 検証項目: 稼働率、注文成功率、送信率、P95 レイテンシ等。基準値はツール内に定義。

D. Streamlit 監視ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite DB を開き、Overview / Positions / Orders / System タブを表示します。

設定・運用上のポイント
--------------------
- 環境分離:
  - paper_trading モードは本番 DB（SQLITE_PATH）と分離された PAPER_TRADING_SQLITE_PATH を使用します。試験時は必ず paper_trading を利用してください。
- 自動 .env ロード:
  - プロジェクトルート（.git / pyproject.toml のあるディレクトリ）を検出して .env / .env.local を読み込みます。OS 環境変数は上書きされません（.env.local は上書き可）。
- 停止フラグ:
  - stop_requested.flag: run_monitoring / run_execution の外部停止制御に使用（プロジェクトルート/data/stop_requested.flag）。
  - kill.flag: KillSwitch が書き込む停止理由フラグ（Settings.kill_flag_path。デフォルト data/kill.flag）。ExecutionEngine 起動時にクリアする設定があります（KILL_FLAG_CLEAR_ON_START）。
- ログレベル:
  - 環境変数 LOG_LEVEL により変更可能。実行スクリプトは basicConfig(level=logging.INFO) を使用しています。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil により OS 依存で設定）。権限が不足する場合は警告を出してスキップします。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとした概要）

- src/kabusys/
  - __init__.py                       — パッケージ初期化（バージョン）
  - config.py                         — Settings / .env 自動ロード
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py                — SQLite スキーマ / MonitoringDB
    - system_monitor.py               — システム状態 / データ鮮度チェック
    - trade_monitor.py                — 注文滞留 / 約定異常
    - risk_monitor.py                 — ドローダウン / ポジション上限チェック
    - monitoring_engine.py            — 各 monitor を束ねる
    - alert_manager.py                — LINE Push 通知
    - kill_switch.py                   — kill.flag の読み書きロジック
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - reconciler 等（発注／リコンシリエーション実装）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                      — OpenAI を用いたニュースセンチメント
    - regime_detector.py               — 市場レジーム判定（MA200 + macro sentiment）
    - __init__.py

データ / ファイルパス（既定値）
------------------------------
- data/kabusys.duckdb         — DuckDB（既定: DUCKDB_PATH）
- data/monitoring.db          — 監視ログ（既定: SQLITE_PATH）
- data/paper_trading.db       — Paper Trading 用 SQLite（既定: PAPER_TRADING_SQLITE_PATH）
- data/execution.pid          — ExecutionEngine の PID（既定: PID_FILE_PATH）
- data/kill.flag              — KillSwitch が書く停止フラグ（既定: KILL_FLAG_PATH）
- data/stop_requested.flag    — 手動で作成する停止フラグ（run_* スクリプトで参照）

開発／テストのヒント
-------------------
- DuckDB / SQLite のテーブルはモジュール側で必要に応じて作成・マイグレーションされます（monitoring_db.init_monitoring_db 等）。
- OpenAI を使う機能は API キー必須。テストでは _call_openai_api のパッチやモックを利用してください（モジュール内で設計済み）。
- settings = Settings() は環境値の検証を行います。無効な値（例: PAPER_FILL_MODE の不正値、KABUSYS_ENV の不正）は例外になります。

FAQ（よくある質問）
-----------------
Q. Paper Trading と本番はどう分離されますか？
A. KABUSYS_ENV=paper_trading のとき run_execution は paper_sqlite_path（既定 data/paper_trading.db）を使用します。監視（monitoring）は常に本番 sqlite_path を使用します。

Q. 監視や実行を安全に停止するには？
A. プロジェクトルートに data/stop_requested.flag を作成すると、run_monitoring/run_execution は検知して終了または停止します。KillSwitch は条件に応じて data/kill.flag に理由を書き込み ExecutionEngine を停止します。

Q. LINE 通知はどのように設定しますか？
A. LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を環境変数に設定してください。未設定時は通知は送信されずログのみ出力します。

最後に
-----
この README はコードベースの主要な使い方と構成をまとめたものです。詳細な設計文書（PortfolioConstruction.md、StrategyModel.md 等）は別途参照してください。使用中に不明点や実行時エラーが出る場合は、ログと環境変数の設定をまずご確認ください。必要であれば具体的なエラーや実行環境を教えていただければ、さらに詳細なサポートを提供します。