# KabuSys

KabuSys は日本株向けの自動売買・研究・監視プラットフォームです。本リポジトリは以下の主要機能を提供します:

- 発注エンジン (ExecutionEngine) と OrderManager による発注・状態管理・リコンシリエーション
- 監視コンポーネント (System / Trade / Risk) とアラート送信 (LINE)
- Paper Trading モード（MockBroker を使用／本番 DB と分離）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- 研究用モジュール（ファクター計算、特徴量探索、前方リターン・IC 計算）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 監視ダッシュボード（Streamlit）と Paper Trading 検証レポート生成ツール

以下は本リポジトリの概要、セットアップ方法、使い方、ディレクトリ構成です。

## 主要な機能一覧

- Execution
  - 発注の作成・送信・同期（OrderManager, OrderRepository, ExecutionEngine）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で MockBroker を使用し、データを data/paper_trading.db に分離
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / 実行プロセス）
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - LINE への通知（AlertManager）
  - Streamlit を使った監視ダッシュボード
- Portfolio
  - 候補選定、等金額／スコア加重、リスクベースの株数算出
  - セクターキャップ適用、レジーム乗数計算
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を参照）
  - 将来リターン、IC 計算、ファクター統計
- AI
  - ニュース記事を OpenAI でスコアリング（ai_scores への書き込み）
  - マクロニュース＋ETF MA200 を統合した市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## 要求環境（推奨）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリに含まれます）
- ネットワーク接続（OpenAI API、LINE API を使う場合）

（実際のプロジェクトでは requirements.txt を用意してください。ここではコードから必要と思われる依存のみ列挙しています。）

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

4. データディレクトリを作成
   ```bash
   mkdir -p data
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 主要な環境変数（必要に応じて設定してください）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所で使用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須な箇所で使用）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant|partial|never|reject（Paper Trading の約定挙動）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で利用）

   例（.env）
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

## 使い方

以下は代表的なスクリプトの起動方法です。プロジェクトルート（src を Python パッケージとして扱えるよう設定済みであることを前提）で実行してください。

- 監視ループの起動（SystemMonitor をポーリングして monitoring DB を更新）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` (秒) でポーリング間隔を上書きできます（デフォルト: 60秒）。
  - 監視は Settings（環境変数）に関わらず本番用の sqlite_path を使用します。

- Execution エンジンの起動（実際の発注処理を行う）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い注文を data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成することで行えます。

- 監視ダッシュボード（Streamlit）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only モードで SQLite を開きます。監視ループを先に起動してデータを生成してください。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可。

- AI / レジーム判定（プログラム内 API）
  - OpenAI API キー（環境変数または引数）を渡して kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用できます。
  - これらは DuckDB 接続を受け取り、raw_news / prices_daily 等のテーブルを参照します。

- Kill / Stop 制御
  - data/kill.flag: KillSwitch が生成するフラグ（ExecutionEngine に停止を促す）
  - data/stop_requested.flag: run_monitoring / run_execution の外部停止用フラグ（存在を検知して安全停止）

注意点:
- set_process_priority("high") を呼ぶため psutil が必要です。権限や OS によっては設定がスキップされます（警告ログのみ）。
- OpenAI や LINE API を使う機能はそれぞれの API キーが必要です。API 呼び出し失敗時のフェイルセーフ処理が組み込まれていますが、事前に設定してください。

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
  - パッケージの公開 API とバージョン定義

- config.py
  - 環境変数の読み込み・解析、Settings クラス（.env の自動読み込み機能含む）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）

- run_execution.py
  - ExecutionEngine の起動スクリプト（KABUSYS_ENV=paper_trading の分離動作）

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と永続化層（MonitoringDB）
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の生成・管理
  - alert_manager.py: LINE Push 通知送信
  - monitoring_engine.py: 監視コンポーネントをまとめるランナー
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py: 発注 API（OrderManager）
  - reconciler.py: 起動時のリコンシリエーション
  - order_repository.py, order_record.py, execution_engine.py, broker_factory.py ... （発注関連実装）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出・資金配分ロジック
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value などのファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py: raw_news を OpenAI でセンチメント評価し ai_scores を更新
  - regime_detector.py: ETF（1321）の MA200 とマクロニュースを組み合わせてレジーム判定

- tools/
  - paper_verification_report.py: Paper Trading のログを集計してレポート出力

- utils/
  - process_priority.py: プロセス優先度 / CPU affinity の設定ユーティリティ

- data/
  - （実行時に生成される SQLite / DuckDB ファイル、フラグファイル、PID など）
  - デフォルト:
    - data/monitoring.db (Settings.sqlite_path)
    - data/paper_trading.db (paper trading 用)
    - data/kabusys.duckdb (Settings.duckdb_path)
    - data/execution.pid
    - data/stop_requested.flag
    - data/kill.flag

## モニタリング DB スキーマ（概要）

init_monitoring_db により以下のテーブルが作成されます（冪等）:

- system_status (cpu_percent, memory_percent, disk_percent, process_ok, recorded_at)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PK, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (single row, id=1 に集計情報)

## 開発上の注意・ベストプラクティス

- 環境変数の自動ロードは .env / .env.local によるが、CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って制御できます。
- Paper Trading を使う場合は必ず KABUSYS_ENV=paper_trading を設定し、データ分離（PAPER_TRADING_SQLITE_PATH）を確認してください。
- OpenAI や外部 API の呼び出しはリトライ・バックオフ・フェイルセーフが組み込まれているが、API 利用量・レート制限に注意してください。
- process priority / cpu affinity の変更は権限に依存します。権限不足時は警告ログのみ出ます。

---

必要であれば、README に依存関係の完全な requirements.txt の例や、よく使うコマンド群（systemd / supervisor のサービス定義例、デバッグ用テストコマンドなど）を追加できます。どの情報を優先して追記しましょうか？