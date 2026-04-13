KabuSys — 日本株自動売買システム
============================

このリポジトリは、日本株向けの自動売買フレームワーク「KabuSys」の主要コンポーネント群です。
本READMEはコードベース（src/kabusys 以下）を参照して作成した概要ドキュメントです。

要点
- 言語: Python 3.9+
- DB: SQLite（監視用 / paper trading 用）、DuckDB（時系列・分析用）
- 外部サービス: kabuステーション API（本番）、MockBroker（paper_trading）、OpenAI（ニュースNLP / レジーム判定）、LINE Messaging（アラート）
- 主な依存: duckdb, psutil, requests, openai, streamlit（ダッシュボード）など

プロジェクト概要
----------------
KabuSys は自動売買の実行基盤と、監視・検証・リサーチ機能を備えたパッケージです。主な責務は次の通りです。

- ExecutionEngine / OrderManager / Reconciler: 注文作成・送信・再同期（リコン）を担当
- Monitoring: システム状態・注文状態・リスクの定期チェック、kill flag による停止制御、LINE 通知
- Portfolio モジュール: 候補選定・配分（等金額・スコア加重）、ポジションサイズ算出、セクター制限、レジーム乗数
- Research: ファクター計算（Momentum / Volatility / Value）、特徴量解析・IC 計算
- AI: ニュースの NLP（OpenAI）による銘柄別センチメントスコアリング、マクロセンチメントを用いた市場レジーム判定
- Tools: Paper Trading 結果の検証レポート生成、Streamlit ダッシュボード等

主な機能一覧
--------------
- 実行
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパートレードの切替（KABUSYS_ENV により MockBroker 使用）
  - ブローカーとの同期（Reconciler）・リスク管理（RiskManager）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（定期ポーリング）
  - sqlite に監視ログを永続化する MonitoringDB（テーブル作成・マイグレーション含む）
  - kill.flag による ExecutionEngine 停止シグナル発行
  - LINE 通知（AlertManager）および Streamlit ダッシュボード起動スクリプト
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等分・スコア加重）
  - ポジションサイズ決定（risk_based / equal / score）
  - セクターキャップ・レジーム乗数適用
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC、ファクター統計
- AI（OpenAI）
  - ニュース記事を銘柄別に集約してセンチメントスコアを取得し ai_scores テーブルに書き込む
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から期間別の検証レポートを生成

セットアップ手順
----------------
前提: Python 3.9+ がインストールされていること

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際のプロジェクトでは requirements.txt を用意することを推奨）

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 主要な環境変数（設定クラス Settings で参照）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （AI を利用する場合は必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に必要）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60 秒）
     - LOG_LEVEL（INFO など）

4. データディレクトリの作成
   - mkdir -p data

注意:
- プロセス優先度設定（set_process_priority）は psutil を使います。権限不足や未対応 OS の場合は警告してスキップされます。
- OpenAI / LINE など外部 API キーの管理は .env を利用するのが便利です。

使い方
------
主な実行コマンド例を示します。

1. 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
   - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）にログを記録します（monitoring は常に本番 sqlite パスを使う点に注意）。

2. ExecutionEngine を起動（実運用・ペーパートレード）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを記録して本番 DB と完全分離します。
   - 起動時に Reconciler による自動復旧処理が行われます。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定している場合は省略可）
   - 出力: 稼働率、注文成功率、送信率、P95 レイテンシなどを表示し PASS/FAIL を判定します。

4. Streamlit ダッシュボード（監視画面）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only 接続で監視 DB を参照し、Overview / Positions / Orders / System タブを表示します。

5. AI モジュール（プログラム的に呼ぶ場合）
   - DuckDB 接続を用意して score_news, score_regime を呼び出します（OpenAI API キー必須）。
   - 例（擬似コード）:
     - import duckdb
     - from kabusys.ai.news_nlp import score_news
     - conn = duckdb.connect("data/kabusys.duckdb")
     - score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

6. 監視 / 実行の停止
   - 実行プロセスは KeyboardInterrupt（Ctrl+C）で停止します。
   - KillSwitch（監視側）によって data/kill.flag が書き込まれると ExecutionEngine が停止する設計です（ExecutionEngine 側で kill.flag を監視していることを前提）。

設定の挙動（いくつかの詳細）
- .env 自動読み込み:
  - プロジェクトルート（.git か pyproject.toml）から .env を読み込みます。
  - .env → .env.local の順で読み、OS 環境変数は保護され上書きされません（.env.local では override）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のとき、run_execution は専用の PAPER_TRADING_SQLITE_PATH を使います。PAPER_FILL_MODE は模擬約定動作（instant/partial/never/reject）を制御します。
- モニタリングの DB マイグレーション:
  - init_monitoring_db は既存 DB を壊さずに必要テーブル・カラムを作成します（冪等）。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュールとファイルの概要です。

- kabusys/
  - __init__.py (バージョン)
  - config.py (Settings: 環境変数読み込み・検証)
  - run_monitoring.py (監視ポーリング起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py (Paper Trading 検証レポート CLI)
  - monitoring/
    - __init__.py
    - monitoring_db.py (SQLite 用永続化層 + MonitoringDB クラス)
    - system_monitor.py (システム状態・データ鮮度チェック)
    - trade_monitor.py (滞留注文・約定異常チェック)
    - risk_monitor.py (ドローダウン・ポジション数監視)
    - kill_switch.py (kill.flag 制御)
    - alert_manager.py (LINE Push)
    - monitoring_engine.py (各 Monitor を束ねる)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py (Order 管理)
    - reconciler.py (起動時のリコンシリエーション)
    - （その他: broker_factory, execution_engine, order_repository 等が存在する想定）
  - portfolio/
    - __init__.py
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数算出)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - research/
    - __init__.py
    - factor_research.py (Momentum/Volatility/Value 計算)
    - feature_exploration.py (将来リターン・IC・統計)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント -> ai_scores)
    - regime_detector.py (マクロ + MA200 で市場レジーム判定)
  - utils/
    - __init__.py
    - process_priority.py (プロセス優先度 / CPU affinity 設定ユーティリティ)
  - portfolio/, monitoring/, research/, ai/ などのテスト可能で純粋関数的な実装が意識されています（DB参照は限定、DuckDB を利用した分析を想定）。

注意事項・運用上のヒント
------------------------
- 実行時の権限: プロセス優先度や CPU affinity の設定は権限不足だと失敗します（警告のみ）。
- DB 分離: paper_trading 用 DB は本番 DB と確実に分離してください（PAPER_TRADING_SQLITE_PATH を設定）。
- OpenAI 呼び出し: レート制限や一時エラーに対して指数バックオフでリトライする実装がありますが、API キー・コスト管理は運用側で注意してください。
- ログレベル: LOG_LEVEL 環境変数で制御（DEBUG/INFO/...）。
- Streamlit: ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine を起動してログが作られている状態で利用してください。

サンプル .env.example（抜粋）
---------------------------
以下は最低限の例（ファイル名: .env）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

最後に
------
この README はコードベースから抽出した設計意図と操作方法の概要です。実際の運用や開発では追加のドキュメント（設計書、運用手順、DB スキーマ定義、テストケース等）を整備することを推奨します。必要があれば、各モジュールの詳細なドキュメントや起動例（systemd / docker compose / k8s マニフェスト等）も作成できますので指示ください。