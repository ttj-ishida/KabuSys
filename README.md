# KabuSys — README

本リポジトリは日本株向け自動売買システム KabuSys の一部実装です。本ドキュメントはコードベース（src/kabusys 以下）をもとに、プロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

目次
- プロジェクト概要
- 機能一覧
- 環境変数（主要設定）
- セットアップ手順
- 使い方（主要スクリプト／ツール）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。本コードベースは次のような機能群を含みます。

- Execution（発注実行エンジン、リスク管理、リコンシリエーション）
- Monitoring（稼働監視、注文監視、リスク監視、アラート送信）
- Portfolio（銘柄選定、重み計算、ポジションサイズ算出）
- Research（ファクター計算、将来リターン・IC 計算、特徴量探索）
- AI（ニュースの NLP スコアリング、レジーム判定 — OpenAI を利用）
- Tools（Paper Trading の検証レポート生成、Streamlit ダッシュボード起動補助 等）
- 設定管理（.env 読み込み・Settings）

設計方針としては、DB（SQLite / DuckDB）や外部 API（ブローカー、OpenAI）へのアクセスを明確に分離し、フェイルセーフ（部分失敗でシステム全体が停止しない）を重視しています。

---

## 機能一覧（主な機能）

- Execution / Order 管理
  - OrderManager：作成・送信・同期を行う
  - Reconciler：再起動時の同期処理（OrderSent の照合、ポジション差分検出）
  - Broker クライアントは環境に応じて Mock / 実ブローカーを切り替え

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
  - TradeMonitor：滞留注文（stale）・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件に応じて kill.flag を書き込み ExecutionEngine の停止を促す
  - AlertManager：LINE Push によるアラート送信（クールダウン管理）
  - MonitoringEngine：上記をまとめてポーリング

- Portfolio
  - 候補選定（スコア/等配分）
  - セクター集中除外、レジーム乗数
  - 発注株数（ロット）算出・aggregate cap 調整

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI
  - news_nlp.score_news：OpenAI を使ったニュースセンチメント（銘柄毎のスコア）生成
  - regime_detector.score_regime：ETF MA 乖離と LLM マクロセンチメント合成によりレジーム判定

- Tools
  - paper_verification_report：Paper Trading DB から検証レポートを出力
  - streamlit_dashboard：監視ダッシュボード（Streamlit）を起動

---

## 環境変数（主要設定）

自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。必須・重要な環境変数の一例：

- KABUSYS_ENV: 起動環境。development / paper_trading / live のいずれか（デフォルト development）
  - paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH を使用
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API 用パスワード
- OPENAI_API_KEY: OpenAI API を使う機能（news_nlp, regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のマッチング挙動（instant/partial/never/reject）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- PID_FILE_PATH: Execution の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）

Settings クラスはコード内に定義されており、その他の設定もそこから取得されます。詳細は src/kabusys/config.py を参照してください。

---

## セットアップ手順（開発用）

ここではローカルで動かすための最低限の手順を示します。実運用時はリスク管理・認証情報管理を適切に行ってください。

1. Python 環境準備（推奨: venv）
   - python >= 3.10 を想定
   - 仮想環境作成・有効化
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージのインストール（requirements.txt がある想定）
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - インストール例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、必要な環境変数をエクスポートしてください。
   - 例（最小）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. データベース初期化
   - Monitoring 用テーブルは run_monitoring.py や run_execution.py が起動時に init_monitoring_db を呼びます。初回はこれらのスクリプトを実行するとテーブル作成されます。
   - DuckDB の prices_daily / raw_financials 等のテーブルはリサーチ機能で必要です。データの投入は別途用意してください（本 README ではデータロード手順は含めません）。

---

## 使い方（主要スクリプト／ツール）

以下は主要な起動方法とオプション（モジュールをパッケージとして実行する方法）です。

- Monitoring のポーリングループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 挙動:
    - プロセス優先度を "high" に設定（set_process_priority）
    - monitoring DB（SQLite）と DuckDB に接続
    - SystemMonitor.check_once() を interval で繰り返す
    - KABUSYS_ENV に関わらず monitoring は本番 sqlite_path を使用します（Settings 参照）

- ExecutionEngine（発注エンジン）を起動
  - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用 DB に記録します（本番 DB と分離）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - プロセス優先度を "high" に設定
    - BrokerClientFactory によりブローカークライアントを生成（環境依存）
    - リスク管理、OrderManager、Reconciler 等を組み立ててセッションを実行

- Streamlit ダッシュボード
  - ローカルで監視状況を可視化
  - 実行例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - read-only モードで SQLite を開く（存在しない場合はエラー表示）

- Paper Trading 検証レポート生成
  - Paper Trading の SQLite（デフォルト data/paper_trading.db）から指標を集計して標準出力に出力します
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - news_nlp.score_news(conn, target_date) / regime_detector.score_regime(conn, target_date) をプログラムから呼び出して使用
  - 両モジュールはリトライやエラー時のフォールバック（スコア 0.0 等）を実装しており、部分失敗時も安全に進行する設計です

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py: パッケージ定義（バージョン等）
  - config.py: .env ロードロジックと Settings クラス（環境変数管理）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite のテーブル初期化と MonitoringDB ラッパー（読み書き）
  - system_monitor.py: システムリソース・データ鮮度・PID チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン・ポジション上限モニタ
  - kill_switch.py: kill.flag の生成・管理
  - alert_manager.py: LINE Push による通知
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - reconciler.py: 起動時のリコンシリエーション（注文同期・ポジション差分検出）
  - order_manager.py: 注文状態遷移 API（create/send/sync 等）
  - （他に broker_factory, execution_engine, order_repository 等が存在する想定）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定、aggregate cap と単元丸め
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算（DuckDB 使用）
  - feature_exploration.py: 将来リターン算出、IC、統計サマリー

- src/kabusys/ai/
  - news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄別スコアを ai_scores テーブルへ書き込む
  - regime_detector.py: MA 乖離と LLM マクロセンチメントを合成して market_regime に書き込む

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading 検証レポート出力スクリプト

- src/kabusys/utils/
  - process_priority.py: OS に依存しないプロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意点

- データ鮮度
  - SystemMonitor は DuckDB の get_last_price_date を参照して、price データの鮮度をチェックします。研究・トレードに使う prices_daily テーブルは定期的に更新してください。

- kill.flag / PID ファイル
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine の停止を促します。ExecutionEngine 起動時に kill.flag を自動で削除したい場合は Settings.kill_flag_clear_on_start を有効にしてください。
  - PID ファイルは ExecutionEngine の生存判定に使われます。PID が死んでいるがファイルが残っている場合は stale PID として削除され、リスクイベントが記録されます。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、発注処理はモックブローカーを使い、paper_trading 用 SQLite DB（デフォルト data/paper_trading.db）へ記録されます。本番 DB と分離できるため検証に便利です。

- OpenAI / API 利用
  - news_nlp / regime_detector は外部 API を使用します。API 呼び出しはレート制限や一時的なエラーを考慮して実装されていますが、API キー管理は厳重に行ってください。
  - API 失敗時はフォールバック値（例: macro_sentiment = 0.0）で継続する設計です。

- ログレベル・監視閾値
  - Settings からログレベルや監視閾値（CPU/MEM/DISK 等）を変更できます。運用環境に応じて調整してください。

---

この README は現状のソースコード（src/kabusys 以下）を参照して作成しています。運用手順や CI/CD、デプロイに関する追加情報がある場合は追記してください。追加で README に含めたい例（.env.example の雛形、requirements.txt の内容、DB 初期データロード手順など）があればお知らせください。