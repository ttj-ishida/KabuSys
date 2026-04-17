# KabuSys

日本株向け自動売買（バックテスト / Execution / Monitoring / Research / AI補助）用のモジュール群です。本リポジトリはエンジン起動スクリプト、監視・アラート、ポートフォリオ構築、ファクター計算、OpenAI を使ったニュース NLP 等の機能を含みます。

以下はコードベース（src/kabusys）に基づく README です。

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するライブラリ群およびランタイムスクリプト群です。主な関心事は以下です。

- ExecutionEngine：ブローカークライアント経由の実注文管理（本番 / Paper Trading 切替対応）
- Monitoring：システム稼働・注文状況・リスクの継続監視とアラート（LINE）
- Portfolio construction：候補選定、重み付け、株数計算（等金額・スコア・リスクベース）
- Research：DuckDB 上の株価・財務データを使ったファクター計算・特徴量探索
- AI：ニュースの NLP 評価（OpenAI）と市場レジーム判定
- Tools：Paper Trading の検証レポート生成、Streamlit ダッシュボード等

設計方針として「外部 API（ブローカー / OpenAI / など）は明示的にラップ」「DB（SQLite / DuckDB）経由のデータ処理」「ルックアヘッドバイアス回避」などが採られています。

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用して paper_trading 用 DB に完全分離して記録
  - プロセス優先度設定、リコンシリエーション、リスク管理、注文管理を組み合わせてセッションを実行
- 監視ループ起動スクリプト（run_monitoring.py）
  - システムステータス取得（CPU / メモリ / ディスク / 実行プロセス生存確認）
  - Trade / Risk モニタ（滞留注文、約定異常、ドローダウン監視）
  - Kill Switch による停止フラグ作成と LINE アラート連携
- Monitoring DB レイヤ（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・更新
- Portfolio モジュール
  - 候補選定（select_candidates）、等重・スコア重み計算、ポジションサイズ計算（単元丸め / aggregate cap）
  - セクター上限の適用、レジーム乗数
- Research モジュール（DuckDB）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI モジュール
  - ニュースを OpenAI でスコアリングして ai_scores に保存（news_nlp）
  - マクロ記事 + ETF ma200 乖離を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - paper_verification_report: Paper Trading DB の指標を集計して PASS/FAIL レポートを標準出力
  - streamlit_dashboard: monitoring.db を参照するダッシュボード

## セットアップ手順

推奨 Python バージョン: 3.10+（型注釈に PEP 604 を利用しています）。実運用では 3.11 を推奨します。

1. リポジトリをクローン、プロジェクトルートへ移動
   - この README は src/kabusys 配下の実装を前提としています。

2. 仮想環境の準備（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例（pip）:
     pip install duckdb psutil openai requests streamlit
   - 追加で開発用に必要なパッケージがあれば適宜インストールしてください。

4. 環境変数 / .env
   - プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して、`.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須変数（一部）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を設定
   - 実行環境切替:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - 監視関連:
     - PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

5. データディレクトリ
   - デフォルトの DB パス:
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
   - スクリプト実行時に存在しない場合は自動生成または接続エラーになるので、適宜初期化スクリプトを準備してください（Monitoring は起動時にテーブルの冪等作成を行います）。

## 使い方（主要スクリプト）

- 監視ループ起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成するとループは検知して終了します（または Ctrl+C）

- 実行エンジン起動
  - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB と MockBrokerClient が利用されます（本番 DB と完全分離）
  - 実行:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成するとエンジンは停止処理します
  - 実行時は data/execution.pid に PID を書く設計です（既存の停止フラグ等を考慮します）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 引数:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 標準出力に統計サマリ（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で monitoring.db を開き、Overview/Positions/Orders/System を確認可能

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - news_nlp.score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str|None)
  - regime_detector.score_regime(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str|None)
  - どちらも OPENAI_API_KEY を環境変数で与えるか、api_key 引数で渡します

## 運用と監視の注意点

- Kill Switch / Stop Flags
  - KillSwitch はリスク条件（ドローダウン超過やポジション上限）で data/kill.flag を作成して ExecutionEngine に停止を促します（ExecutionEngine は起動時や実行中に kill.flag を検知する挙動を持ちます）。
  - run_* スクリプトは data/stop_requested.flag を監視して安全にシャットダウンします。

- DB の分離
  - Paper Trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db と分離します。
  - DuckDB（分析用）は data/kabusys.duckdb を使用。

- 環境変数の自動ロード
  - プロジェクトルートの .env および .env.local を自動ロード（OS 環境変数上書き不可）。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

## 主要な設定項目（環境変数）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB パス
- SQLITE_PATH: monitoring DB パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / MONITOR_POLL_INTERVAL / LOG_LEVEL 等

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル（本 README 作成時点）の構成と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env 読み込み / Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定（ルール実装）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を書き込むロジック
    - regime_detector.py — 市場レジーム判定（ma200 + macro sentiment）
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite テーブル作成 / MonitoringDB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
    - trade_monitor.py — 滞留注文 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知プッシュ（クールダウン付き）
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — OrderState 管理の外向き API
    - reconciler.py — 起動時の注文 / ポジション照合
    - （その他ブローカー / リスク等のモジュールが存在する想定）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- data/
  - （実行時生成されるファイル群）
  - execution.pid
  - stop_requested.flag
  - kill.flag
  - monitoring.db / paper_trading.db / kabusys.duckdb など

## データベース（Monitoring）スキーマ概要

monitoring_db.init_monitoring_db により冪等で作成されるテーブル：

- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の1行保持: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

## 開発・拡張ポイント（メモ）

- DuckDB を使ったファクター集計は SQL ウォークスルーで設計されているため、データスキーマ変更時は該当クエリの更新が必要です。
- AI 呼び出しは OpenAI SDK を直接利用しており、API レスポンスのフォールトトレランス（リトライ、JSON 復元、クリッピング）を組み込んでいます。テスト時は _call_openai_api をモックしてください。
- position_sizing の lot_size は将来的に銘柄別対応に拡張可能です（現状は単一 lot_size 前提）。
- 設定は Settings クラスから読み出し・バリデーションされます。環境変数の命名やデフォルト値を変更するときは config.py を更新してください。

---

疑問点や README に追加したい手順（例: CI、データ初期化スクリプト、requirements.txt の自動生成など）があれば教えてください。必要に応じて例の .env.example も作成します。