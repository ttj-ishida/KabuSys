# KabuSys

日本株向け自動売買システムのコアライブラリ（モジュール群）。  
このリポジトリは戦略の研究、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース処理までを含むモジュール群で構成されています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド例）
- 環境変数（主なもの）
- 停止 / フラグファイルについて
- ディレクトリ構成

--------------------------------------------------------------------------------
プロジェクト概要
--------------------------------------------------------------------------------
KabuSys は日本株の自動売買システムを構築するためのモジュール群です。  
主な目的は以下です：
- 研究（ファクター計算、特徴量解析）用ユーティリティ
- ポートフォリオ構築・ポジションサイズ計算
- 発注エンジン（ExecutionEngine）とリコンシリエーション
- モニタリング（リスク監視、システム監視、アラート）
- ニュースを LLM によるセンチメント付与する AI モジュール
- Streamlit ダッシュボードや検証レポート生成ツール

設計方針の特徴：
- DuckDB を使った時系列データ処理（prices_daily / raw_financials 等）
- SQLite を使った運用監視ログ（monitoring.db）／paper trading 用 DB 分離
- 環境変数により動作モード（development / paper_trading / live）を切替
- 外部 API（OpenAI 等）呼び出しはフェイルセーフ設計（失敗時は安全側にフォールバック）

--------------------------------------------------------------------------------
主な機能一覧
--------------------------------------------------------------------------------
- research/
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- portfolio/
  - 候補選定、重み計算（等配分・スコア配分）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、集約キャップ）
- execution/
  - OrderManager、ExecutionEngine、リコンシリエーション（Reconciler）
  - Broker クライアント抽象化（本番/モックに対応）
- monitoring/
  - SystemMonitor（プロセス状態、CPU/メモリ/ディスク、データ鮮度）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（閾値発動時に停止フラグを書き込み）
  - AlertManager（LINE Push を用いた通知）
  - Streamlit ダッシュボード（簡易 UI）
- ai/
  - news_nlp: OpenAI を使ったニュースのセンチメント集約・ai_scores への書き込み
  - regime_detector: マクロセンチメントと ETF MA から市場レジーム判定
- tools/
  - paper_verification_report: Paper Trading DB から検証レポートを生成

--------------------------------------------------------------------------------
セットアップ手順
--------------------------------------------------------------------------------
以下はローカルで動かすための最小セットアップ例です（Unix 系を想定）。

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   本コードで使用されている主要パッケージ例：
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit

   例:
   - pip install duckdb psutil openai requests streamlit

   （プロジェクト配布時に requirements.txt があればそちらを使用してください）

3. データディレクトリの作成（必要に応じて）
   - mkdir -p data

4. 環境変数の設定
   .env / .env.local をプロジェクトルートに用意するか、環境変数で設定します（詳しくは次節）。

5. DuckDB / SQLite の DB ファイル
   - DuckDB（prices_daily 等の時系列データ）: デフォルト data/kabusys.duckdb
   - SQLite（監視ログ）: デフォルト data/monitoring.db
   - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

   既存の DB がない場合、各モジュールが必要に応じてテーブルを初期化します（init_monitoring_db 等）。

--------------------------------------------------------------------------------
使い方（主なエントリポイント）
--------------------------------------------------------------------------------
以下は代表的な起動コマンド例です。各コマンドはプロジェクトルート（pyproject.toml/.git がある場所）から実行してください。

1) 監視ループの起動（SystemMonitor をポーリング）
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。

2) ExecutionEngine（発注エンジン）の起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
   - 起動時に data/stop_requested.flag が存在すると起動をスキップします。

3) Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を read-only で開いてダッシュボード表示します。

4) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH（デフォルトは data/paper_trading.db）

5) AI モジュール（プログラムから呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - conn: duckdb connection（DuckDBPyConnection）
     - target_date: date オブジェクト
     - api_key: OpenAI API key（省略時は環境変数 OPENAI_API_KEY を参照）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

--------------------------------------------------------------------------------
主な環境変数
--------------------------------------------------------------------------------
（左: 環境変数名 — 右: 説明（デフォルト値））

- KABUSYS_ENV
  - 動作モード: development | paper_trading | live
  - デフォルト: development

- SQLITE_PATH
  - 監視用 SQLite DB パス（monitoring）
  - デフォルト: data/monitoring.db

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 DB パス（KABUSYS_ENV=paper_trading 時に使用）
  - デフォルト: data/paper_trading.db

- DUCKDB_PATH
  - DuckDB ファイルパス（時系列データ）
  - デフォルト: data/kabusys.duckdb

- OPENAI_API_KEY
  - OpenAI API キー（ai.score_news / score_regime で使用）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用トークン（必須な箇所がある）

- KABU_API_PASSWORD
  - kabu ステーション API パスワード（必須）

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - AlertManager（LINE通知）用。未設定時は送信せずログのみ。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60。

- PAPER_FILL_MODE
  - Paper Trading の MockBroker の挙動 ("instant" | "partial" | "never" | "reject")。デフォルト "instant"

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視・制御関連の設定（Settings クラス参照）

備考:
- .env/.env.local がプロジェクトルートにあれば自動読み込み（OS 環境変数を上書きしない / .env.local は上書き）されます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

--------------------------------------------------------------------------------
停止 / フラグファイルについて
--------------------------------------------------------------------------------
プロセスの停止・制御はファイルフラグで行う設計です。

- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルを参照してループ停止または起動スキップを行います。

- data/execution.pid
  - ExecutionEngine 起動時に PID を記録する想定のファイルパス（Settings.pid_file_path による）。

- data/kill.flag
  - KillSwitch によりスイッチが発動するとこのファイルを書き込み、ExecutionEngine に停止を促します。KillSwitch.clear() で削除可能。

--------------------------------------------------------------------------------
ディレクトリ構成（抜粋）
--------------------------------------------------------------------------------
src/
  kabusys/
    __init__.py              — パッケージ定義 / バージョン
    config.py                — 環境変数・設定読み込み（.env サポート）
    utils/
      process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
    research/
      factor_research.py     — Momentum/Value/Volatility ファクター計算
      feature_exploration.py — 将来リターン / IC / 統計サマリー
    portfolio/
      portfolio_builder.py   — 候補選定・重み計算
      position_sizing.py     — 発注株数計算・集約キャップ
      risk_adjustment.py     — セクターキャップ・レジーム乗数
    execution/
      order_manager.py       — OrderManager（発注フロー）
      reconciler.py          — 起動時リコンシリエーション
      ...                    — （BrokerFactory / ExecutionEngine 等は同階層に存在）
    monitoring/
      monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
      system_monitor.py      — システム状態・データ鮮度
      trade_monitor.py       — 注文滞留・約定異常検出
      risk_monitor.py        — ドローダウン/ポジション制限監視
      kill_switch.py         — kill.flag 書込ロジック
      alert_manager.py       — LINE 通知
      monitoring_engine.py   — 各モニタを束ねるループ
      streamlit_dashboard.py — Streamlit ダッシュボード
    ai/
      news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込
      regime_detector.py     — 市場レジーム判定（ETF MA + マクロセンチメント）
    tools/
      paper_verification_report.py — Paper Trading 検証レポート（CLI）
    data/                    — 実行時に使用するファイル（DB / flag / pid など。リポジトリには含めない）

--------------------------------------------------------------------------------
開発上の注意 / ポイント
--------------------------------------------------------------------------------
- DuckDB 接続を受け取る関数群（research / ai / regime_detector）は、テスト時にモック接続を差し替えやすい設計になっています。
- OpenAI 呼び出しはリトライ・フェイルセーフ（失敗時はスコア 0.0 やスキップ）を基本としています。
- Paper Trading（テスト用）は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- process priority / cpu affinity の設定は psutil を使ってOSの差分を吸収します。権限・プラットフォームにより動作しない場合は警告を出してスキップします。

--------------------------------------------------------------------------------
貢献・拡張
--------------------------------------------------------------------------------
- 新しい Broker 実装を追加する場合は execution/broker_api.py のプロトコルに従って実装し、BrokerClientFactory で選択するようにしてください。
- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news 等）スキーマに合わせてデータを投入することで research / ai 機能が利用できます。
- アラート先（LINE 以外）の追加は AlertManager を拡張してください。

--------------------------------------------------------------------------------
ライセンス
--------------------------------------------------------------------------------
（本リポジトリに LICENSE が同梱されている場合はそちらを参照してください。ここでは指定がないため各自で追加してください。）

--------------------------------------------------------------------------------
補足
--------------------------------------------------------------------------------
この README はソースコード内の docstring、コメント、Settings 等の情報を基に作成しています。運用環境での運用前には必ず .env を用意し、各種 API キー・パスワード・DB のバックアップ方針を確認してください。必要があれば README をプロジェクト固有の実行手順に合わせて追記してください。