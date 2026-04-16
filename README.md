# KabuSys

日本株アルゴリズム売買 / 研究プラットフォーム（部分的な実装サンプル）

このリポジトリは、売買実行・監視・ポートフォリオ構築・リサーチ・AI ニュース NLP などのコンポーネント群を含む日本株自動売買システムのコードベースです。本 README ではプロジェクト概要、機能、セットアップ方法、主要な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は次の関心事を分離して実装したモジュール群です：

- 実行エンジン（ExecutionEngine）と Order 管理（OrderManager / OrderRepository）
- 監視（Monitoring）: システム状態、注文の滞留・約定異常、リスク（ドローダウン・ポジション上限）監視、Kill Switch、アラート（LINE）
- ポートフォリオ構築（候補選択、重み付け、ポジションサイズ決定、セクター制限）
- 研究（ファクター計算 / 特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント / 市場レジーム判定） — OpenAI を利用
- ツール群（Paper Trading の検証レポート生成、Streamlit ダッシュボードなど）

設計のポイント：
- 環境変数 / .env による設定管理（自動ロードはデフォルト有効）
- Paper Trading 環境時は本番 DB と分離（専用 SQLite）
- DuckDB を時系列データ分析に使用、SQLite を監視・発注ログに使用
- フェイルセーフ（API 失敗時のフォールバック、冪等性、ログ重視）

---

## 主な機能一覧

- Settings（環境設定読み込み、バリデーション）
  - KABUSYS_ENV（development / paper_trading / live）
  - .env / .env.local の自動読み込み（無効化可）
- 実行関連
  - Execution 起動スクリプト（run_execution.py）
  - BrokerClientFactory により paper_trading 時は MockBroker を利用
  - Reconciler による再起動後の同期処理
- 監視関連
  - SystemMonitor（プロセス生存確認・CPU/メモリ/Disk・データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件一致で data/kill.flag を出力）
  - AlertManager（LINE Push でアラート送信、クールダウン管理）
  - monitoring DB 初期化 / MonitoringDB（永続化 API）
  - Streamlit ダッシュボード（監視情報の可視化）
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額、スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（ロット丸め、利用可能現金に対するスケール）
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等） — DuckDB 上で SQL と Python を併用
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI を利用）
  - ニュースの銘柄別センチメント取得（ai.news_nlp.score_news）
  - マクロニュース + ETF MA によるレジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - 監視ダッシュボード起動用スクリプト（streamlit）

---

## 必要な依存パッケージ（例）

主な外部依存（抜粋）：
- python 3.8+（型アノテーションに依存）
- duckdb
- psutil
- openai
- requests
- streamlit

（requirements.txt は本リポジトリに含めていない想定のため、実行環境に応じてこれらを pip でインストールしてください）

例:
pip install duckdb psutil openai requests streamlit

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install duckdb psutil openai requests streamlit
4. 環境変数を設定（.env または OS 環境変数）
   - 必須／重要な環境変数例:
     - JQUANTS_REFRESH_TOKEN — （J-Quants API 用）
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - OpenAI を使用する機能を動かす場合:
     - OPENAI_API_KEY を設定
   - 環境種別:
     - KABUSYS_ENV = development | paper_trading | live
       - paper_trading の場合、Mock ブローカーを使い data/paper_trading.db に記録
   - その他任意:
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
     - PAPER_FILL_MODE（instant / partial / never / reject）
5. （任意）.env / .env.local をプロジェクトルートに作成
   - Settings モジュールはプロジェクトルートを .git または pyproject.toml で探索し、
     .env を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方（主要スクリプト）

基本的にはパッケージ実行（-m）や Streamlit 経由で起動します。

1. 監視ループ（Monitoring）
   - 説明: SystemMonitor をポーリングして monitoring DB にログ保存、KillSwitch 等を評価。
   - 実行:
     - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。正の整数。デフォルト 60。
   - 停止:
     - プロジェクトルートの data/stop_requested.flag を作成するとループは終了します。

2. 実行エンジン（Execution）
   - 説明: ExecutionEngine を起動しトレードセッションを実行。paper_trading なら Mock ブローカーを使用。
   - 実行:
     - python -m kabusys.run_execution
     - Paper Trading モード例:
       - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとエンジンを停止します。
   - PID / フラグ:
     - data/execution.pid を作成してプロセスを管理する設計になっています（Settings.pid_file_path 参照）。

3. Streamlit ダッシュボード（監視可視化）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取りモードで SQLite を開き、ダッシュボード表示を行います。

4. Paper Trading 検証レポート（ツール）
   - 説明: paper_trading の SQLite（デフォルト data/paper_trading.db）を参照し各種 KPI を出力
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - 別 DB 指定:
       - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5. AI モジュール（ニュース NLP / レジーム判定）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB コネクションを渡し、OpenAI API を呼ぶことで ai_scores テーブルに書き込みます。
     - OPENAI_API_KEY 環境変数または引数で API キーを渡す必要があります。
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF（1321）の MA 乖離とマクロニュースを組み合わせて market_regime テーブルへ書き込みます。
   - 注意:
     - API 呼び出しはリトライやフォールバック（失敗時は 0.0 等）を取り入れており、例外耐性が設計されています。

---

## 監視 DB（SQLite）について

- デフォルトの監視 DB パス: data/monitoring.db（Settings.sqlite_path）
- init_monitoring_db(conn) によって以下のテーブルが作成されます（冪等）:
  - system_status
  - trade_logs
  - positions
  - risk_logs
  - dashboard
- MonitoringDB クラスを通してログ記録・取得を行います（SystemMonitor / TradeMonitor / RiskMonitor が利用）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- OPENAI_API_KEY: OpenAI API を利用する機能で必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

---

## 停止・フラグファイルについて

- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルが存在すると安全に終了します（外部から停止する手段）。
- data/kill.flag
  - KillSwitch がトリガーした場合に書き込まれ、ExecutionEngine 停止を示すために使用されます。
- data/execution.pid
  - 実行エンジンの PID を管理するために使用されます（SystemMonitor が PID を確認）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/.env 読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ & MonitoringDB
    - system_monitor.py — CPU/メモリ/Disk/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常
    - risk_monitor.py — ドローダウン・ポジション上限
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知クライアント
    - monitoring_engine.py — 複数モニタのオーケストレーション
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - （他: broker_factory, execution_engine, order_repository 等が想定）
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/  (ランタイムで使用する想定ディレクトリ。デフォルト DB・フラグを置く)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB ファイル)
    - stop_requested.flag / execution.pid / kill.flag

---

## 開発上の注意点 / 補足

- .env 自動読み込み
  - config.py はプロジェクトルートを .git または pyproject.toml で探索し、.env/.env.local を自動ロードします。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、実取引 API 呼び出しを置き換える Mock 実装が使われ、本番 DB とは分離した DB（data/paper_trading.db）に記録します。
- OpenAI 使用
  - API 呼び出しはリトライや JSON 検証等の耐性を備えていますが、利用時はレート制限や課金に注意してください。
- プロセス優先度
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出します。psutil による権限エラーは警告に留めて継続します。
- DB マイグレーション
  - init_monitoring_db は既存スキーマへ列追加等の簡易マイグレーションを行います（例: latency_ms / peak_value の追加）。

---

もし README に追加したいコマンド例や CI / デプロイ手順、既存の broker 実装や ExecutionEngine のより詳細な使い方が必要であれば、その目的に応じて追記します。