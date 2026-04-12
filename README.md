# KabuSys

日本株自動売買システムのコードベース（抜粋）。  
この README はリポジトリ内の主要機能・使い方・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群を提供します。主な機能は以下のとおりです。

- 注文作成・送信・状態管理（Execution）
- 取引・システムの監視（Monitoring）
- ポートフォリオ構築（ポジションサイズ計算、セクター制限、重み付け）
- 研究用ファクター計算・特徴量解析（Research）
- ニュースを LLM（OpenAI）で解析して銘柄ごとのセンチメントスコアを付与（AI）
- Paper Trading 検証レポート生成ツール、Streamlit ベースの監視ダッシュボード等の補助ツール

コードは主に純粋関数群（ポートフォリオ・リサーチ等）、永続層（SQLite / DuckDB）、外部 API ラッパー（OpenAI、ブローカー）で構成されています。

---

## 主な機能一覧

- execution
  - OrderManager / ExecutionEngine（発注ロジック、リスク管理、リコンシリエーション）
  - ブローカークライアントの切り替え（本番 / Paper Trading 用 Mock）
- monitoring
  - SystemMonitor（CPU/Memory/Disk、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文、約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（閾値超過時に flag ファイルを書いて Execution を停止）
  - AlertManager（LINE による通知）
  - MonitoringEngine（各モジュールのポーリング管理）
  - streamlit_dashboard（監視用 GUI）
- portfolio
  - 候補選定 / 重み付け（等金額、スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate キャップ）
- research
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 特徴量解析（前方リターン、IC、統計サマリー）
- ai
  - news_nlp.score_news(): raw_news を LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime(): ma200 とマクロ記事センチメントで日次レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

以下はローカルで動かすときの一般的な手順です。

1. Python 環境（推奨: 3.10+）を用意する。
2. 必要なパッケージをインストールする（requirements.txt がある想定）:

   - 例:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
     - （その他、環境によって依存が追加される可能性があります）

   インストール例:
   ```
   pip install -r requirements.txt
   ```
   または開発インストール:
   ```
   pip install -e .
   ```

3. 環境変数（または .env/.env.local）を設定する:

   - 必須（実行する機能により変わります）:
     - JQUANTS_REFRESH_TOKEN : J-Quants 用トークン（必要な場合）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（Execution の場合に必要）
   - OpenAI 関連:
     - OPENAI_API_KEY : news_nlp / regime_detector を使う場合
   - その他（デフォルトがあるものを上書きする場合）
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH : 監視 SQLite DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH : DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH : Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知用
     - PAPER_FILL_MODE : paper_trading の挙動（instant | partial | never | reject）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（監視 / キルスイッチ関連）
     - LOG_LEVEL（DEBUG/INFO/...）

   - 自動で .env を読み込む機能があるため、プロジェクトルートに .env を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. データベース初期化:
   - 多くの起動スクリプトは起動時に必要なテーブルを生成（init_monitoring_db）します。監視を始める場合は特別な手順は不要です。

注意:
- Monitoring（run_monitoring.py）は KABUSYS_ENV にかかわらず production の sqlite_path（SQLITE_PATH）を使用します。
- Execution（run_execution.py）は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。

---

## 使い方（実行例）

- 監視ループを起動（ポーリング）:
  ```
  python src/kabusys/run_monitoring.py
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）。
  - 起動直後にプロセス優先度を "high" に設定しようとします（psutil を使用、権限により失敗する場合あり）。

- ExecutionEngine（発注エンジン）起動:
  ```
  python src/kabusys/run_execution.py
  ```
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、Paper Trading 用 DB に書き込みます。
  - 実行前に KABU_API_PASSWORD 等の環境変数を設定してください。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit 監視ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI スコアリング（プログラムから呼ぶ場合）:
  - news_nlp.score_news(conn, target_date, api_key=None)  — OpenAI API キーは OPENAI_API_KEY または引数で指定
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な設定（環境変数）

以下は config.Settings で扱われる主な環境変数（デフォルトや備考を併記）:

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API を使う場合）
- KABU_API_PASSWORD: 必須（kabu API を使う場合）
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- PAPER_TRADING_SQLITE_PATH: デフォルト "data/paper_trading.db"
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）
- PID_FILE_PATH: デフォルト "data/execution.pid"
- KILL_FLAG_PATH: デフォルト "data/kill.flag"
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 閾値（監視用）
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト 60）

.env の書式や読み込みルールは config モジュール内の実装に従います。`.env.example` を参照して .env を作成してください（リポジトリに example ファイルがあればそちらを使用）。

---

## 注意点 / 運用メモ

- プロセス優先度や CPU affinity を設定するために psutil を使用します。権限不足により設定が失敗しても警告を出してスキップします。
- DuckDB 接続はリサーチ系で多用されます。prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- news_nlp / regime_detector は OpenAI の呼び出しを行うため、API 利用料金とレート制限に注意してください。リトライ・バックオフの実装がありますが、API キー未設定時は例外になります。
- Monitoring の DB 初期化（init_monitoring_db）は冪等です。既存スキーマにカラムがなければマイグレーション的に追加します。
- KillSwitch はファイルベース（デフォルト data/kill.flag）。KillSwitch が書き込まれると Execution 側で停止シグナルとして扱う実装になっています（ExecutionEngine 側の実装に依存）。

---

## ディレクトリ構成

（リポジトリ内の src/kabusys 配下を抜粋した構成）

- src/kabusys/
  - __init__.py  — パッケージ初期化、バージョン等
  - config.py  — 環境変数 / 設定の読み込みロジック（.env 自動ロード含む）
  - run_monitoring.py  — SystemMonitor のポーリング起動スクリプト
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 用検証レポート生成ツール（CLI）
  - monitoring/
    - __init__.py
    - monitoring_db.py  — SQLite ベースの永続層（テーブル初期化・読み書きラッパー）
    - system_monitor.py  — CPU/Memory/Disk・プロセス・データ鮮度監視
    - trade_monitor.py  — 注文滞留・約定異常監視
    - risk_monitor.py  — ドローダウン・ポジション上限監視
    - kill_switch.py  — flag ファイルによる停止シグナル管理
    - alert_manager.py  — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねたポーリングエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/ (一部のみを参照: broker_factory, order_manager, reconciler, ...)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py  — ニュースセンチメントスコア生成（OpenAI）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
    - __init__.py
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - data / （実行時に配置する想定のデータフォルダ）
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
    - execution.pid / kill.flag など

---

## 開発・テストのヒント

- モジュールは外部 API 呼び出し（kabu、OpenAI 等）を抽象化しているため、ユニットテストではモックを差し替えてテスト可能です（コード中に patch を想定した呼び出し箇所あり）。
- DuckDB 接続は並列実行で read-only URI（?mode=ro）を使用すると安全にダッシュボードから参照可能です（streamlit の実装例あり）。
- .env の自動読み込みはプロジェクトルート検出（.git / pyproject.toml）に依存します。配布後の動作も考慮した設計です。

---

必要であれば README にサンプル .env.example や requirements.txt の例、さらに各モジュール（ExecutionEngine や OrderManager、Execution の起動オプション）についての詳細な使い方を追加できます。どの部分を詳しく書きたいかを教えてください。