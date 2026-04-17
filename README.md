KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコア実装を含みます。
戦略のポートフォリオ構築、ポジションサイズ計算、取引実行周りの管理、監視（ログ・アラート・Kill Switch）、
リサーチ用ファクター計算、AI を用いたニュースセンチメント判定などの機能を備えています。

主な特徴
--------
- ExecutionEngine（発注実行）と Monitoring（監視）プロセス分離
  - 実行プロセスは本番または paper_trading（モックブローカー）モードで起動可能
  - 監視は本番の monitoring DB を常に参照して状態監視を行う
- ポートフォリオ構築モジュール（候補選定・重み計算・ポジションサイズ）
- リスク管理（ドローダウン、ポジション数上限、リスクロギング）
- 監視用 DB 層（SQLite）と DuckDB を利用したデータ分析基盤
- AI モジュール
  - ニュースから銘柄ごとのセンチメントを取得（OpenAI）
  - マクロ＋テクニカルを合成して市場レジームを判定（regime_detector）
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ベースの監視ダッシュボード
- プロセス優先度・CPU affinity 設定ユーティリティ（psutil 経由）

機能一覧
--------
- 発注管理: OrderManager、OrderRepository、ExecutionEngine（起動スクリプト: run_execution.py）
- 自動復旧（リコンシリエーション）: Reconciler
- 監視:
  - SystemMonitor（CPU/メモリ/ディスク、プロセス、データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件満足時に kill.flag を作成して実行停止）
  - AlertManager（LINE Push で通知）
  - MonitoringEngine（各モニタを束ねる）
  - 起動スクリプト: run_monitoring.py
- データ処理 / リサーチ:
  - DuckDB 接続ベースのファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI:
  - news_nlp: raw_news から OpenAI を呼び出して ai_scores を作成
  - regime_detector: ma200 とマクロニュースを合成して market_regime を作成
- 運用ツール:
  - paper_verification_report（紙上検証レポート）
  - streamlit_dashboard（監視ダッシュボード）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb openai psutil requests streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数の設定
   - 簡易的にはリポジトリルートに .env を作成してください（自動ロード機能あり）
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     PAPER_FILL_MODE=instant
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
   - 設定の自動読み込みはデフォルトで有効。テスト等で無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
6. DB 初期化
   - 監視用 DB（SQLite）は run_monitoring / run_execution 内で init_monitoring_db を呼びます。
   - DuckDB はテーブル作成やデータロードが別に必要（prices_daily, raw_financials, raw_news など）。

環境変数の主なキー
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH を使用
- PAPER_FILL_MODE: instant | partial | never | reject
- SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- PID_FILE_PATH / KILL_FLAG_PATH: 運用フラグ・PID ファイルのパス
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（代表的なコマンド）
-----------------------
- ExecutionEngine（発注ロジック）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットすると MockBrokerClient を使用し data/paper_trading.db に書き込みます
  - 起動前に data/kill.flag が存在すると起動を行いません（kill.flag は設定の停止シグナル）
  - 実行中の停止は data/stop_requested.flag を作ることでスレッドを止めます

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒, デフォルト 60）
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 引数 --db で別の DB を指定可能。既定は data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視情報・ポジション・注文ログを可視化（読み取り専用）

- AI 機能（プログラム経由で呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上のファイル / フラグ
- data/execution.pid — ExecutionEngine の PID（起動時に書き込まれる）
- data/kill.flag — KillSwitch が作成する停止シグナル（手動または自動）
- data/stop_requested.flag — run_* スクリプトが終了するためのローカル停止フラグ
- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading）
- data/kabusys.duckdb — DuckDB データベース（時系列価格・財務・ニュース等）

注意点 / 補足
-------------
- Settings（kabusys.config）はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読込します。OS 環境変数は優先されます。
- 監視の init_monitoring_db は冪等でスキーマ作成および軽微なマイグレーション（列追加）を行います。
- OpenAI を使用する機能は API 呼び出しを行うため、OPENAI_API_KEY の設定が必須です。API エラー時はフェイルセーフ（例: news_nlp は失敗時に該当銘柄のスコア取得をスキップ）をとっています。
- process_priority 設定（set_process_priority）は psutil を用い、プラットフォームごとに動作が異なります。権限不足時は警告が出てスキップされます。
- DuckDB を使用するリサーチ/AI モジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データの準備は別工程です。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数 / 設定読み取りロジック
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - data/                      — （ランタイム）DB / フラグを置く想定ディレクトリ
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層（テーブル作成・読み書き）
    - system_monitor.py        — システム状態監視
    - trade_monitor.py         — 注文監視
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag の管理
    - alert_manager.py         — LINE への通知
    - monitoring_engine.py     — 各種 Monitor を束ねる
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py         — 発注ワークフロー管理
    - reconciler.py            — 起動時自動復旧 / リコンシリエーション
    - (その他: broker_factory, order_repository, order_record, execution_engine など)
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算
    - feature_exploration.py   — 将来リターン・IC・統計
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/monitoring_db.py  — 監視 DB（テーブル定義・MonitoringDB クラス）

開発 / テスト
--------------
- 自動ロードを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 単体関数群（portfolio、research 等）は副作用なく動作するよう設計されています。DuckDB / SQLite をモックすることでユニットテストが可能です。
- OpenAI 呼び出しは _call_openai_api を patch/モックしてテストできます。

貢献 / ライセンス
-----------------
- 本リポジトリの利用・改変はプロジェクトポリシーに従ってください（ここではライセンスファイルは同梱されていません。必要に応じて LICENSE を追加してください）。

問い合わせ
----------
- 実行／監視の運用に関する質問は実装ドキュメント（各モジュールの docstring）を参照してください。追加の運用手順やデプロイ設定（systemd / supervisor など）は環境に合わせて作成してください。

以上。必要であれば README に含めるサンプル .env.example を作成したり、起動・運用例（systemd ユニット例など）を追記します。どの情報を追加しますか？