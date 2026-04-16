# KabuSys

日本株自動売買システムの内部ライブラリ群（プロトタイプ）。  
この README は、リポジトリ内の主要コンポーネントと利用方法をまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株の自動売買に関わる以下の機能群を持つモジュール群です：

- 戦略／ポートフォリオ構築（候補選定・重み付け・株数計算）
- 注文発行・状態管理・再同期（ExecutionEngine 周り）
- 監視（システム状態・注文滞留・リスク監視）とアラート送信（LINE）
- 研究用ファクター計算・特徴量探索（DuckDB を利用）
- AI（OpenAI）を用いたニュースセンチメント評価・レジーム判定
- Paper Trading 用検証レポート生成ツール
- Streamlit による監視ダッシュボード

設計方針の一部：
- DuckDB / SQLite を内部データ保存に使用（分析と運用ログで分離）
- 環境変数ベースの設定（`.env` / `.env.local` を自動ロード）
- 本番と Paper Trading を明確に分離して動作

---

## 主な機能一覧

- Execution
  - OrderManager（発注／重複検出／キャンセル等）
  - Reconciler（再起動時のブローカー突合）
  - RiskManager（発注制限など）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常監視
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じて実行エンジン停止フラグを書き込み
  - AlertManager：LINE へアラート送信（クールダウン管理あり）
  - Streamlit ダッシュボード（監視DBを可視化）
- Research / Portfolio
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 特徴量解析（将来リターン・IC・統計サマリー）
  - ポートフォリオ構築（候補選定 / 等重／スコア重み付け）
  - ポジションサイジング（リスクベース、単元丸め、集計キャップ）
- AI
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメントの算出・保存
  - regime_detector: ETF + マクロニュースから市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB の検証レポート生成
  - streamlit_dashboard: 監視DBを閲覧する UI

---

## 動作要件（概略）

- Python 3.9+（ソースは型ヒントで Python 3 系想定）
- 必要なパッケージ例（setup 時にインストール）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（組み込み）
- インターネット接続（OpenAI や LINE を使用する場合）

（本リポジトリに requirements.txt がある場合はそちらを使用してください。）

例：
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン／展開し、プロジェクトルートに移動する。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （存在しない場合は上記パッケージ群を個別インストール）

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くか、OS 環境変数を設定します。
   - 必須（Execution / 実運用で必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY
   - LINE 通知を使う場合（任意）:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - その他（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - SQLITE_PATH (監視DB, default: data/monitoring.db)
     - DUCKDB_PATH (分析DB, default: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper用DB, default: data/paper_trading.db)
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")
     - PID_FILE_PATH, KILL_FLAG_PATH など

注意: config.py はプロジェクトルートから `.env` / `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

---

## 使い方（実行例）

以下は主要な起動・実行コマンド例です。プロジェクトルートで実行します。

- モニタリングループを起動（SystemMonitor をポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止するにはプロセスを終了するか、プロジェクトルート下の data/stop_requested.flag を作成します。

- 実行エンジン（ExecutionEngine）を起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（モックブローカー、専用 DB を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ExecutionEngine は起動時に data/stop_requested.flag を検査し、存在すれば起動を中止します。
  - 実行中に停止したい場合は data/stop_requested.flag を作成すると Engine によって検知され停止されます。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可能）

- Streamlit 監視ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - `--db` オプションで読み取り対象の monitoring DB を指定できます（既定は data/monitoring.db）。

---

## 主要環境変数（抜粋）

- 必須（実行時に参照され、未設定だと Settings が例外を投げます）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用・挙動制御:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: ログレベル（INFO 等）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時の模擬約定挙動（instant|partial|never|reject）
  - OPENAI_API_KEY: OpenAI を使う AI 機能で必要
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）

- DB / パス:
  - SQLITE_PATH: monitoring DB（default: data/monitoring.db）
  - DUCKDB_PATH: 分析 DB（default: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（default: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH: 各種フラグファイルのパス

---

## ファイル・ディレクトリ構成（主なもの）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポートツール
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py (実装は省略されている箇所あり)
      - broker_factory.py / broker_api.py / ...（ブローカー抽象）
    - monitoring/
      - monitoring_db.py       — monitoring DB スキーマ + helper
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
      - news_nlp.py
      - regime_detector.py
    - data/ （実行時に利用するファイル群、リポジトリルートに配置）
      - monitoring.db (default)
      - paper_trading.db (paper_trading 用)
      - stop_requested.flag (run_* で監視される停止フラグ)
      - execution.pid
    - utils/
      - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

注: 上記はリポジトリ内の主要モジュールを抜粋したものです。実際のコードベースに応じてファイルが追加/変更されている場合があります。

---

## 運用上の注意 / 実装メモ

- run_monitoring は Settings.env にかかわらず常に本番の sqlite_path を使用する実装になっています（監視は一元化しておくため）。
- run_execution は KABUSYS_ENV=paper_trading のとき専用の paper_trading DB（デフォルト data/paper_trading.db）を使い、本番 DB と完全分離されます。
- Stop / Kill フラグ:
  - data/stop_requested.flag: run_* スクリプトでポーリング中に存在を検知して終了するための手動フラグ。
  - data/kill.flag: KillSwitch（監視の一部）が書き込む停止シグナル。ExecutionEngine 起動時に設定をクリアする設定があります（設定次第）。
- Settings はプロジェクトルートから `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出しはレート制限や一時エラーに対してエクスポネンシャルバックオフを実装していますが、API キーの管理・利用は自己責任で行ってください。
- MonitoringDB の init_monitoring_db は冪等であり、既存スキーマへのマイグレーション処理（カラム追加）を含みます。

---

## よく使うコマンドまとめ

- 仮想環境作成・依存インストール:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt
- モニタリング起動（60秒間隔）:
  - python -m kabusys.run_monitoring
- 実行エンジン起動（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

もし README に追加したい項目（例: requirements.txt の具体的内容、実行エンジンの詳細設定、サンプル `.env`、ユニットテストの実行方法、CI 設定など）があれば教えてください。必要に応じて README を拡張します。