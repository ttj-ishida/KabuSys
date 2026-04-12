# KabuSys — 日本株自動売買システム (README)

このドキュメントは本リポジトリに含まれる主要スクリプト・モジュールの概要、セットアップ方法、利用手順、ディレクトリ構成を日本語でまとめたものです。

目的：
- 日本株向けの自動売買エンジン（ExecutionEngine）およびそれを監視する仕組み（Monitoring）
- 研究・リサーチ用のファクター計算、ポートフォリオ構築ユーティリティ
- AI（LLM）を用いたニュースセンチメント評価・市場レジーム判定の実装
- Paper Trading 環境の検証・レポート作成ツール

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine を起動してブローカーに対して注文を発行・管理
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い、データを `data/paper_trading.db` に保持して本番 DB と完全分離
  - 起動時にプロセス優先度を "high" に設定（プラットフォームに依存）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセス PID、データ鮮度を監視してログに保存
  - TradeMonitor: 注文の滞留（stale orders）や約定価格の異常をチェック
  - RiskMonitor: ドローダウン監視、ポジション上限監視、ダッシュボードの更新
  - KillSwitch: 危険時にフラグファイル（`data/kill.flag` など）を書き出して ExecutionEngine を停止させる
  - AlertManager: LINE Messaging API で通知（オプション）

- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）を DuckDB 上の価格・財務データから計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等

- ポートフォリオ構築（Portfolio）
  - 候補選定 / 等配分・スコア加重配分 / リスク調整（セクターキャップ・レジーム乗数） / ポジションサイズ計算（単元株丸め・リスク制限）

- AI（OpenAI）
  - ニュース記事のセンチメントを LLM（gpt-4o-mini）で評価 → ai_scores テーブルに書き込み（batched、リトライ付き）
  - マクロニュース + ETF ma200 を用いた市場レジーム判定（score_regime）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## 要件（依存ライブラリの例）

最低限必要な Python パッケージ（例）:
- python >= 3.10（型ヒントで | を使うため）
- duckdb
- psutil
- requests
- openai
- streamlit

実際にはプロジェクトの requirements.txt があればそれに従ってください。なければ例として以下をインストールします:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  （requirements.txt がない場合は上記パッケージ群を個別インストール）
3. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を使えます（自動読み込み機能あり）
   - 自動ロードを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - AI 機能利用時:
     - OPENAI_API_KEY を設定
   - オプション:
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - KABUSYS_ENV を設定（development / paper_trading / live）
     - PAPER_FILL_MODE（paper_trading 時）: instant / partial / never / reject
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite のパス
     - DUCKDB_PATH / SQLITE_PATH: データベースパス（デフォルト data/kabusys.duckdb / data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH など
4. データディレクトリを作成（必要な場合）
   - mkdir -p data

注意: config モジュールはプロジェクトルート（.git または pyproject.toml）を探して `.env` を自動ロードします。CI やテストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 実行方法（主要コマンド）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング周期を変更: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使い、MockBrokerClient が利用されます（本番 DB と分離）
  - Execution 起動時もプロセス優先度を High に設定します

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring DB を読み取り専用で開きます（存在しない場合は MonitoringEngine を起動してください）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

---

## 環境変数（主なもの）

- KABUSYS_ENV: environment (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants）
- KABU_API_PASSWORD: 必須（kabuステーション）
- OPENAI_API_KEY: AI 機能利用時に必要
- PAPER_FILL_MODE: paper_trading の MockBroker の挙動（instant | partial | never | reject）、デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイルパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 をセット）

設定ミスがあると Settings クラスが例外を投げます（必須変数未設定など）。

---

## 使い方のワンライナー例

- 監視をデーモンとして動かす（簡易例）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring &

- Paper Trading で実行エンジンを起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## AI 機能（ニューススコア / レジーム判定）について

- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して target_date のニュースウィンドウを集め、OpenAI API で銘柄ごとのセンチメントを ai_scores に書き込みます。
  - OPENAI_API_KEY 環境変数または api_key 引数が必要。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 1321 の MA200 乖離とマクロニュースの LLM 判定を合成して market_regime テーブルへ書き込みます。

両機能とも LLM 呼び出しは堅牢化（リトライ・バックオフ・部分失敗のフォールバック等）が組み込まれています。API キー未設定時は ValueError が出ます。

---

## 注意点 / 実装上の備考

- settings（kabusys.config）:
  - .env / .env.local の自動読込機能あり。OS 環境変数が優先されます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - プロジェクトルートの判定は .git または pyproject.toml で行います。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は存在しないテーブル・カラムを作成する安全な（冪等）実装です。既存 DB に対して `peak_value` や `latency_ms` カラムがない場合は自動で追加します。

- プロセス優先度:
  - run_monitoring / run_execution は起動直後に set_process_priority("high") を呼びます。プラットフォーム依存（Windows / Linux / macOS）で内部的に psutil を使い処理します。権限や対応プラットフォームによって失敗することがあり、その場合は警告ログが出て継続します。

- Paper Trading:
  - KABUSYS_ENV=paper_trading のとき、Execution は MockBrokerClient を使用し、データはデフォルトで `data/paper_trading.db` に記録されます（本番 DB と完全分離）。

- KillSwitch:
  - リスク閾値（ドローダウン・ポジション上限）を満たすと `KILL_FLAG_PATH` にフラグを書き、Execution 停止シグナルとして利用します。既にフラグが存在する場合は再書き込みしません（冪等）。

---

## 主要なディレクトリ構成（抜粋）

以下はプロジェクト内の主なモジュールとファイルの一覧（本リポジトリ内の該当ファイルに基づく）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite ベースの永続化層（system_status 等）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository 等が存在)
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
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py

（上記は主要ファイルのみを抜粋しています。実動作に必要な追加モジュールやファイルが他にも存在する可能性があります。）

---

## 開発者向けメモ

- ローカルでのデバッグ:
  - DuckDB / SQLite を直接開いてテーブル構造やレコードを確認できます。
  - monitoring_db の初期化は冪等なので、テスト実行前に安全に呼び出せます。

- ロギング:
  - run_*.py の main は logging.basicConfig(level=logging.INFO) を使っています。詳細ログが必要なら LOG_LEVEL=DEBUG を設定してください（Settings.log_level を通す設計になっています）。

- テスト容易性:
  - AI 呼び出しや外部 API 呼び出しは `_call_openai_api` 等で分離されており、ユニットテストでパッチ差し替え（モック）しやすく設計されています。

---

必要に応じて README の章立てやコマンド例を追加できます。特定の使い方（例: ExecutionEngine の設定項目、OrderManager の API、DuckDB テーブルスキーマの詳細）を README に追加したい場合は、どの部分を詳しく記載するか教えてください。