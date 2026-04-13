README — KabuSys (日本株自動売買システム)
====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を目的としたパッケージです。本コードベースは以下の主要機能群を含みます。

- 注文実行エンジン（ExecutionEngine）とブローカ連携（実運用 / Paper Trading 切替）
- 監視サブシステム（System / Trade / Risk モニタ）とアラート送信（LINE Push）
- モニタリング DB（SQLite）によるログ永続化と Streamlit ダッシュボード
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 研究用モジュール（ファクター算出、特徴量探索）
- AI 関連機能（ニュースセンチメントの LLM スコアリング、レジーム判定）
- 検証ツール（Paper Trading 検証レポート生成）

主な設計方針:
- DuckDB をリサーチ用データ（時系列等）に使用、SQLite を監視ログ／注文ログに使用
- 環境変数／.env ファイルによる設定（自動ロード機能あり）
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）
- 外部 API（OpenAI / kabuステーション 等）は必要に応じ設定

機能一覧
--------
- Execution:
  - 注文作成 → ブローカー送信 → 状態同期・再突合（Reconciler）
  - RiskManager による注文前検査
  - Paper Trading モード（MockBrokerClient）で本番と分離
- Monitoring:
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag で Execution 停止信号
  - AlertManager: LINE への一方向通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
- Research:
  - ファクター（モメンタム / ボラティリティ / バリュー）計算（DuckDB 経由）
  - 将来リターン・IC 計算・統計サマリ
- AI:
  - ニュースセンチメント（OpenAI）を銘柄ごとにスコア化し ai_scores に書込
  - マクロ + ETF MA200 を合成した市場レジーム判定（market_regime テーブルへ書込）
- Tools:
  - paper_verification_report: Paper Trading の検証レポート出力（稼働率・成功率・レイテンシ等）

動作要件（主な依存パッケージ）
------------------------------
以下は主要な外部依存です。環境に合わせてバージョンを固定してください。

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)

（プロジェクトに requirements.txt がない場合は上記を pip install してください。）

環境変数（主なもの）
-------------------
Settings クラスで参照される主な環境変数（.env に定義可能）:

必須/重要:
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）

その他（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient と data/paper_trading.db を使用
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60） — run_monitoring で使用
- LOG_LEVEL: "DEBUG"|"INFO"|...（ログレベル）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）に必要
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 各監視閾値（数値）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env と .env.local を自動ロードします
- OS 環境変数を優先し、.env.local は上書き (override=True) されます
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo> && cd <repo>

2. 仮想環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. data ディレクトリ作成（DB 等を格納）
   - mkdir -p data

5. .env を準備
   - .env.example があれば参照して .env を作成してください（必須トークンを設定）
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

6. データベース初期化
   - 監視 DB（monitoring.db）は run_monitoring または run_execution 起動時に自動でテーブル作成（init_monitoring_db）されます。
   - DuckDB のテーブルはリサーチ用に適切にロードしておく必要があります（prices_daily / raw_financials 等）。これは外部 ETL 処理が前提です。

使い方（実行コマンド）
---------------------

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ書き込まれます。
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority を使用）。

- Monitoring（単体ポーリングスクリプト）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用します（環境に依らず本番監視 DB を参照する設計）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で SQLite を開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）

- AI 機能（ニューススコア / レジーム判定）
  - 実行には OPENAI_API_KEY が必要です。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して DuckDB 接続と target_date を渡して実行します（スクリプトのエントリポイントは直接提供されていないため、ユースケースに応じて呼び出してください）。

重要な挙動メモ
--------------
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは実運用の DB とは分離された paper_trading DB を使用します（安全設計）。
  - PAPER_FILL_MODE により MockBrokerClient の約定挙動を制御できます（instant / partial / never / reject）。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag（Settings.kill_flag_path）を書き込み、これを見た ExecutionEngine が停止する仕組みです（KillSwitch により冪等に書き込み）。
- プロセス優先度:
  - run_execution / run_monitoring は起動時に set_process_priority("high") を試みます（許可がなければ警告でスキップ）。

ディレクトリ構成（主要ファイルと役割）
-----------------------------------
src/kabusys/
- __init__.py — パッケージメタ（バージョン等）
- config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
- run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper_trading 切替対応）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py, reconciler.py, ... — 発注関連ロジック、ブローカー抽象、リコンシリエーション
- monitoring/
  - monitoring_db.py — SQLite テーブル定義 / 操作（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 通知（クールダウン付き）
  - monitoring_engine.py — 各モニタを束ねるループ / run_once / run
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算（等重/スコア加重）
  - position_sizing.py — 発注株数算出（risk_based 等）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター
  - feature_exploration.py — 将来リターン計算 / IC / 統計
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）集約・スコア付与
  - regime_detector.py — マクロ + MA200 ベースのレジーム判定（OpenAI 使用）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ラッパー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

開発時のヒント / トラブルシュート
---------------------------------
- .env が自動で読み込まれない場合:
  - プロジェクトルートの検出は config._find_project_root() に依存します（.git または pyproject.toml を探索）。
  - 自動ロードを無効化している場合は env を手動で設定してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- SQLite ファイルがロックされて開けない / Streamlit で読み取りできない場合:
  - streamlit 側は read-only URI を使って接続します。ファイルパスの権限や同時アクセスを確認してください。
- OpenAI 呼び出しのリトライは内製ロジックで実装されていますが、API キーやネットワークの問題で失敗することがあります。ログを確認してください。

ライセンス・貢献
----------------
- （ここにプロジェクトのライセンスや貢献ルールを追加してください）

以上。必要であれば README にサンプル .env、起動スクリプトのより詳細なオプション、CI/デプロイ手順等を追記します。どの情報を追加しますか？