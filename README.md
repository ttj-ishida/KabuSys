# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視用ライブラリ群です。  
このリポジトリは以下の主要機能を持つコンポーネント群で構成されています。

- Execution Engine（発注・リスク管理・リコンシリエーション）
- Monitoring（システム状態・注文異常・リスク監視、LINE通知、Streamlitダッシュボード）
- Portfolio Construction（銘柄選定・重み付け・株数計算）
- Research（ファクター計算・特徴量探索）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- ツール（Paper Trading 検証レポート生成 等）

以下はコードベースに基づいた README（日本語）です。

## 主な機能

- 発注・注文状態管理（OrderManager / ExecutionEngine）
- 起動時の自動リコンシリエーション（Reconciler）
- Paper Trading 向けの完全分離 DB（data/paper_trading.db を使用）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- Kill Switch（ドローダウンやポジション超過時に停止要求をフラグファイルへ書き込み）
- 監視データ永続化（SQLite）と集計用 DuckDB
- Streamlit による簡易ダッシュボード
- AI（OpenAI）を使ったニュースセンチメントと市場レジーム判定
- 研究用ファクター計算（DuckDB ベース）および特徴量評価ユーティリティ
- Paper Trading 検証レポート生成ツール

## セットアップ手順

前提: Python 3.9+（typing の一部機能を使用）を想定しています。環境に合わせて仮想環境を作成してください。

1. リポジトリをクローン
   - git clone <this-repo>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

3. 依存パッケージをインストール
   主要な依存例（プロジェクトによって細部は異なる場合があります）:
   - pip install duckdb psutil openai requests streamlit

   必要に応じて他パッケージも追加してください（上記はコード中で直接参照されるもの）。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   プロジェクトは .env / .env.local を自動読み込みします（プロジェクトルートが特定できる場合）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数例（必須項目はコードで require されるもの）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...         （AI 機能利用時）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （任意）
   - LINE_CHANNEL_ACCESS_TOKEN=...  （通知を使う場合）
   - LINE_USER_ID=...               （通知を使う場合）
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60    （run_monitoring のポーリング間隔（秒））

   .env ファイルはルートの .env / .env.local に書き、適宜設定してください。

6. DB 初期化
   Monitoring 用のテーブルはスクリプト実行時に自動で作成されます（init_monitoring_db が冪等に対応）。

## 使い方

以下は主要な実行コマンド例です。全てプロジェクトルートから実行します。

- Execution Engine を起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します。
    - ExecutionEngine は data/execution.pid を書きます。プロセスの存在チェック機構があります。

- Monitoring（SystemMonitor）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path（Settings.sqlite_path）を使用します（監視ログを一元化するため）。

- Streamlit ダッシュボードを起動（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - `--db` で監視用 SQLite のパスを指定できます（既定: data/monitoring.db）。読み取り専用 URI で開きます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db data/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
  - 出力: 標準出力へ検証サマリ（稼働率 / 注文成功率 / レイテンシ等）を表示します。

- AI 機能（ニュースセンチメント / レジーム判定）
  - 関数は kabusys.ai モジュールから利用できます（例: kabusys.ai.score_news）。
  - 実行には OpenAI API キー（OPENAI_API_KEY）が必要です。
  - これらは DuckDB 接続を受け取りテーブル（raw_news / news_symbols / ai_scores / prices_daily / market_regime）を参照・更新します。
  - 例（スクリプト内から呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

- 停止方法 / Kill Switch
  - グローバルにプロセスを停止させたい場合はファイル `data/stop_requested.flag` を作成してください。run_monitoring / run_execution の両方がこのファイルを監視しており、検出時に終了または停止処理を行います。
  - KillSwitch（監視ルール経由での停止要求）は `data/kill.flag`（Settings.kill_flag_path が既定）へ理由を書き込み、ExecutionEngine 側で適切に扱われます。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定しておくと、起動時に既存の kill.flag を消す挙動を制御できます（Settings.kill_flag_clear_on_start）。

## 設定 (Settings) の説明

主要プロパティ（Settings クラス）と意味:

- jquants_refresh_token: J-Quants API 用トークン（必須）
- kabu_api_password: kabuステーション API パスワード（必須）
- kabu_api_base_url: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id: LINE 通知用（未設定時は送信をスキップ）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: monitoring SQLite（デフォルト data/monitoring.db）
- paper_sqlite_path / PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- paper_fill_mode: Paper Trading の約定動作（instant, partial, never, reject）
- pid_file_path: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- kill_flag_path: kill flag のパス（デフォルト data/kill.flag）
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct: 監視の閾値（実監視ロジックで使用）
- env (KABUSYS_ENV): development / paper_trading / live
- log_level: ログレベル

.env の読み込み順序:
- OS 環境変数 > .env.local > .env（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成 CLI
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                          — 発注関連の実装（broker, order_repository 等）
  - monitoring/
    - monitoring_db.py             — monitoring 用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py            — レジーム判定（MA + マクロセンチメント合成）
  - utils/
    - process_priority.py           — process priority / cpu affinity ユーティリティ
  - data/ (実行時に生成されるデータファイル)
    - monitoring.db (SQLite)
    - paper_trading.db
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag

（上記は主要モジュールの抜粋です。実際のファイルはリポジトリを参照してください。）

## 実運用に関する注意点

- Monitoring はコード上で「本番用の sqlite_path」を参照するようになっています。monitoring と execution の DB を分離したい場合は設定で分けてください（ただしデフォルトでは monitoring は sqlite_path を使います）。
- Paper Trading は production DB と完全分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- .env の自動読み込みはプロジェクトルートの検出に基づいており、配布後やインストール後は CWD に依存しないように作られています。
- process priority の設定はプラットフォーム依存であり、権限不足や未対応 OS の場合は警告を出してスキップします（psutil を使用）。
- OpenAI を用いる機能は API エラーやネットワーク障害に対してリトライとフォールバックを備えていますが、APIキー・利用料管理は利用者側の責任で行ってください。
- SQLite / DuckDB のパスは Settings で設定可能です。初回実行時に monitoring のテーブルは自動作成（マイグレーション含む）されます。

## トラブルシューティング

- psutil による優先度設定で AccessDenied が出る場合はルート/管理者権限での実行、または設定値を変更してください。
- OpenAI 呼び出しで構造の異なるレスポンスが返る場合、news_nlp と regime_detector はレスポンス検証と整形をしていますが、モデル変更時には注意してください。
- Streamlit が DB を開けない場合はパスを確認し、Monitoring が起動していること（ファイルが存在すること）を確認してください。

---

この README はリポジトリのコードと docstring に基づいて作成しています。更に詳しい仕様（StrategyModel.md / PortfolioConstruction.md 等の設計ドキュメント）がある場合はそれらを参照してください。必要であれば、README にコマンド例や .env.example のテンプレートを追加できます。