# KabuSys

日本株自動売買システムのコードベース README。  
このドキュメントはプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関連するコンポーネント群を提供する Python ベースのシステムです。主な機能は以下のとおりです。

- 注文作成・送信・状態管理を行う ExecutionEngine（ブローカー抽象化）
- システム稼働状況・注文状態・リスク監視を行う Monitoring コンポーネント群
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、リスク制限）
- DuckDB を用いたファクター計算・研究（ファクター生成、IC 計算、将来リターン）
- OpenAI を使ったニュースセンチメント評価（AI スコアリング）と市場レジーム判定
- Paper Trading 用ツール（検証レポート生成、paper_trading 用 DB 分離）
- Streamlit ベースの監視ダッシュボード

設計方針として、以下を重視しています：
- 本番と Paper Trading の分離（DB・モックブローカー）
- ルックアヘッドバイアス防止（日時参照の取り扱いに注意）
- 外部 API 呼び出しはフェイルセーフ（失敗時のフォールバックやスキップ）
- DuckDB / SQLite によるデータ永続化・分析

---

## 機能一覧（概要）

- Execution
  - 注文の生成・送信・状態同期（Reconciler による再起動時のリカバリ）
  - Risk manager / OrderManager / OrderRepository を組み合わせた発注フロー
  - Paper Trading モード（MockBrokerClient、専用 SQLite）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセスPID/データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格の異常検知
  - RiskMonitor：ドローダウン監視・ポジション上限監視
  - KillSwitch：閾値到達時に flag ファイルを書いて ExecutionEngine を停止させる仕組み
  - AlertManager：LINE Messaging API 経由でアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Research / Data
  - ファクター生成（Momentum, Volatility, Value 等）
  - 将来リターン計算・IC（情報係数）・統計サマリ
  - DuckDB を用いたデータ処理
- AI
  - news_nlp: raw_news を LLM で評価して銘柄ごとのスコアを ai_scores に保存
  - regime_detector: ETF の MA とマクロ記事センチメントを合成して日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定レポートを生成
- Utilities
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - config: 環境変数 / .env 読み込み、Settings クラス

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（PEP 604 の型記法などを使用）
- OS: Linux / macOS / Windows（psutil のサポート範囲に注意）

1. リポジトリをクローン／プロジェクトを配置する

2. 仮想環境を作成・有効化（例）
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存ライブラリをインストール（例: pip）
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - インストール例:
     ```bash
     pip install duckdb psutil requests openai streamlit
     ```
   - 実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（ただし OS 環境変数が優先されます）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等

5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（コマンド例）

- ExecutionEngine を起動する
  - 本番 / development / paper_trading の動作は KABUSYS_ENV に依存します。
  - Paper Trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録し、MockBrokerClient を使用します。
  ```bash
  python -m kabusys.run_execution
  ```
  （またはスクリプトを直接実行: `src/kabusys/run_execution.py`）

- Monitoring のポーリングを開始する
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 注意: run_monitoring は Monitoring 用の sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV にかかわらず本番 monitoring DB）。

- Streamlit ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成ツール
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

- AI モジュール（ニュース評価・レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - これらはライブラリ関数として使用される設計です（例: kabusys.ai.score_news）。

---

## 重要な挙動メモ

- run_execution:
  - 起動時にプロセス優先度を "high" に変更しようとします（psutil により権限が必要な場合あり）。
  - Paper Trading モードでは、ブローカーはモック、DB は paper_trading 用の別ファイルを使用します（本番 DB と分離）。

- run_monitoring:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - Monitoring は Settings.sqlite_path を用いるため、環境にかかわらず定められた monitoring DB を使用します。

- KillSwitch:
  - kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine を停止させる合図を送ります。存在チェック / 再書き込みの冪等性を保証します。

- Settings（kabusys.config）
  - .env / .env.local の自動読み込みを行います（プロジェクトルートは .git または pyproject.toml から探索）。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。
  - 多くの設定値が環境変数経由で提供され、未設定の必須キーは例外になります（_require）。

---

## ディレクトリ構成（主要ファイル）

（以下は src/kabusys 以下の主要モジュール一覧と簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 読み込み・Settings クラス
  - run_execution.py — ExecutionEngine 起動エントリポイント
  - run_monitoring.py — SystemMonitor ポーリング起動エントリポイント
- src/kabusys/execution/
  - order_manager.py — 注文の作成・送信を管理
  - reconciler.py — 再起動時の注文・ポジション照合
  - （他: broker_factory, execution_engine, order_repository 等が存在）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル定義・CRUD ラッパー（MonitoringDB）
  - system_monitor.py — CPU/メモリ/プロセス/PID/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル
  - alert_manager.py — LINE 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 発注株数計算（リスク・上限考慮）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロセンチメントを合成して市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

データディレクトリ（デフォルト）
- data/kabusys.duckdb — DuckDB（prices_daily, raw_financials 等のテーブル）
- data/monitoring.db — Monitoring 用 SQLite DB（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db — Paper Trading 用 SQLite DB（paper_trading 用に分離）

---

## 開発時の注意点

- DB スキーマの初期化は init_monitoring_db() により冪等に行われます。monitoring 用 DB は run_monitoring/run_execution の起動時に自動で整備されます。
- OpenAI を利用する機能は API キーが必須です。キーが未設定だと例外またはフェイルセーフ動作になります（モジュールによる）。
- psutil によるプロセス優先度設定や CPU affinity は権限不足やプラットフォーム依存のため、失敗時はロギングしてスキップする実装です。
- DuckDB を使った分析関数は外部 API に依存せず、prices_daily / raw_financials 等のテーブルを前提とします。データ整備が必要です。

---

問題や追加で README に含めたい項目（環境変数の完全一覧や実行例のスクリーンショット、CI/テスト手順など）があれば教えてください。README を用途に合わせて詳しく拡張します。