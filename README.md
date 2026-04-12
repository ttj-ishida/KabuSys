# KabuSys

日本株自動売買システムのコアライブラリ群（リサーチ・ポートフォリオ構築・実行・監視・AI補助機能）です。  
このリポジトリはライブラリ・ツール群を提供しており、実運用用の ExecutionEngine / MonitoringEngine や、Paper Trading 検証、Streamlit ダッシュボード、ニュースNLP / レジーム判定などのサブシステムを含みます。

---

## プロジェクト概要

- 目的: 日本株向け自動売買システムの共通ロジック（ファクター計算、ポートフォリオ構築、発注管理、監視、AIベースのニュースセンチメント等）を提供する。
- 特徴:
  - DuckDB / SQLite を用いたローカルデータ処理と監視ログ永続化
  - Paper Trading モードで本番DBと分離して安全に検証
  - OpenAI（gpt-4o-mini など）を利用したニュースセンチメント、マクロ判定の仕組み
  - Streamlit による監視ダッシュボード
  - フェイルセーフ（クラッシュ時のリコンシリエーション、アラート、Kill Switch）

---

## 主な機能一覧

- research/
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- portfolio/
  - 候補選定、等重・スコア加重の重み計算
  - リスク制約（セクター上限）適用
  - 株数計算（リスクベース・等分配など）、単元株丸め、aggregate cap
- execution/
  - OrderManager / OrderRepository / Reconciler: 発注状態管理、再起動時の同期
  - ExecutionEngine（起動スクリプトあり）
  - Broker クライアントのファクトリ（paper_trading では MockClient を利用）
- monitoring/
  - SystemMonitor, TradeMonitor, RiskMonitor
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - MonitoringEngine（ポーリングループ）と run_monitoring 起動スクリプト
  - AlertManager（LINE Push を使った通知）
  - KillSwitch（flag ファイルで ExecutionEngine を停止）
  - Streamlit ダッシュボード（read-only で monitoring DB を可視化）
- ai/
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF の MA とマクロニュースで市場レジーム（bull/neutral/bear）を判定
- tools/
  - paper_verification_report: Paper Trading DB を集計し、稼働率・注文成功率・レイテンシ等の検証レポートを出力

---

## セットアップ手順

前提:
- Python 3.10+ を想定（型アノテーションに Union | を使用）
- SQLite / DuckDB を使用（ローカルファイル）

1. リポジトリをクローン
   - 例: git clone <repo_url>

2. 仮想環境作成 & 有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合、少なくとも以下をインストールしてください）
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数 / .env
   - プロジェクトルートの `.env` または `.env.local` に設定を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 代表的な環境変数（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - SQLITE_PATH (data/monitoring.db)
     - DUCKDB_PATH (data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — デフォルト: instant
     - OPENAI_API_KEY — OpenAI を使う機能に必要
     - KABU_API_PASSWORD — kabuステーション API の場合必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート用
     - PID_FILE_PATH (data/execution.pid)
     - KILL_FLAG_PATH (data/kill.flag)
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（既定 60）
     - LOG_LEVEL (INFO, DEBUG, ...)

6. DB 初期化
   - monitoring 用の SQLite は起動スクリプトが起動時にテーブルを作成します（init_monitoring_db を実行）。

注意:
- Paper Trading（KABUSYS_ENV=paper_trading）では ExecutionEngine は paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を利用して本番 DB と分離します。
- 環境自動ロードは config._find_project_root() が .git または pyproject.toml を検出できる場合にのみ行われます。

---

## 使い方（主要スクリプト）

以下は実運用で使う主要なエントリポイント例です。

1. 監視ループ（SystemMonitor 単体をポーリング）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を上書き可能（デフォルト 60）
   - 実行:
     - python -m kabusys.run_monitoring
   - 動作:
     - プロセス優先度を "high" に設定（可能な場合）
     - monitoring DB（settings.sqlite_path）を使ってシステム状態を定期記録
     - DuckDB からデータ鮮度等も検査

2. ExecutionEngine（実売買 / Paper Trading）
   - 実行:
     - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH に記録
     - ブローカークライアント生成、注文管理、リスク管理、リコンシリエーション、セッション実行

3. Streamlit 監視ダッシュボード
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - オプション:
     - --db で監視用SQLiteファイルを指定（デフォルト data/monitoring.db）
   - 説明:
     - read-only で positions / trade_logs / system_status / dashboard を可視化

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 日付を指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を明示:
       - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）および PASS/FAIL 判定

5. AI 機能（ニュース・レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime を呼ぶことで DuckDB 内データに基づく LLM 呼び出しを行い結果を書き込む（OpenAI API キーが必要）。
   - 注意: API 呼び出しはコスト発生の可能性あり。api_key 引数または環境変数 OPENAI_API_KEY を指定。

---

## 主要設定（Settings）一覧と説明

Settings クラス（kabusys.config.Settings）からアクセス可能。代表的なプロパティ:

- jquants_refresh_token: J-Quants API のトークン（必須）
- kabu_api_password: kabuステーション API のパスワード（必須）
- kabu_api_base_url: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id: LINE 通知用
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: Monitoring SQLite（デフォルト data/monitoring.db）
- paper_sqlite_path: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- paper_fill_mode: Paper Trading の約定挙動（instant/partial/never/reject）
- pid_file_path: Execution の PID ファイル（デフォルト data/execution.pid）
- kill_flag_path: KillSwitch のフラグファイル（デフォルト data/kill.flag）
- CPU / memory / disk の閾値等も環境変数で指定可能

設定値の不足や不正は Settings が ValueError を投げます。README に合わせて .env.example を用意しておくことを推奨します。

---

## 実装上の挙動・注意点

- 自動環境ロード:
  - リポジトリのルート（.git または pyproject.toml があるディレクトリ）から .env と .env.local を読み込む。
  - OS 環境変数が優先され、.env.local は既存の OS 環境変数を上書きしない（ただし override=True で挙動は変わる）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- Process Priority:
  - run_monitoring / run_execution 起動時に set_process_priority("high") が試みられます。psutil を利用して Windows/Linux の差分を吸収しますが、権限などで失敗した場合は警告に留まります。

- MonitoringDB のマイグレーション:
  - init_monitoring_db() は冪等にテーブルを作成し、欠けているカラム（例: peak_value, latency_ms）があれば ALTER TABLE で追加します。

- Kill Switch:
  - RiskMonitor が閾値を超えた場合、KillSwitch が data/kill.flag を書き込み ExecutionEngine 停止を促す仕組みがあります。KillSwitch.clear() で削除可能。

- OpenAI 呼び出し:
  - news_nlp および regime_detector は API 失敗時にフェイルセーフ（ゼロやスキップ）で継続する設計。
  - レート制限や接続障害に対して指数バックオフとリトライを行います。
  - レスポンスのバリデーションを厳密に行い、不正な出力を無視します。

---

## ディレクトリ構成

（src 配下を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — （期待される外部ディレクトリ: DuckDB/CSV など）
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティファクター
    - feature_exploration.py — 将来リターン・IC・統計
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・投下資金スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_api, order_repository, execution_engine 等)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

---

## よくある運用フロー例

1. データ収集と DuckDB の準備（prices_daily / raw_financials / raw_news 等を投入）
2. KABUSYS_ENV を設定し、実行環境を決定（development / paper_trading / live）
3. 監視を常駐
   - python -m kabusys.run_monitoring もしくは MonitoringEngine をデプロイ
4. 実行（当日セッション）
   - python -m kabusys.run_execution
5. 定期的に paper_verification_report で Paper Trading 結果を検証
6. Streamlit ダッシュボードで状況を可視化
7. OpenAI を使う分析・判定は API キー管理に注意して運用

---

## 開発・貢献

- コードはモジュール化されており、ユニットテストを追加しやすい構造になっています（各 pure function は DB 非依存でテスト可能）。
- LLM 呼び出しは _call_openai_api をモック/patch してテスト可能。
- 変更を加える際は .env.example を更新し、外部 API キー等の管理に留意してください。

---

必要であれば README にサンプル .env.example、requirements.txt の推奨内容、具体的な systemd / supervisor の起動例（run_monitoring/run_execution のサービス化）なども追記できます。どの情報を追加したいか教えてください。